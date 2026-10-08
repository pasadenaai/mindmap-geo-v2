"""
USGS Mineral Commodity Summaries (MCS) ingestor — ScienceBase edition.

Data source: USGS ScienceBase catalog, NMIC MCS annual data releases.
Each commodity is published as a separate ScienceBase item containing two CSVs:
  *_salient.csv  — US-only salient statistics
  *_world.csv    — world production & reserves by country  ← we use this one

World CSV column pattern:
  Country | Type | Prod_{unit}_{year} | Prod_{unit}_est_{year} | Reserves_{unit} | Reserves_notes
Unit suffix: kt (kilotons), t (metric tons), kg (kilograms) — auto-detected.

ScienceBase discovery:
  1. Search for "{year} - COPPER" to get a known item
  2. Read its parentId
  3. List all sibling items under that parent (= the full MCS collection for that year)
  4. For each item with a _world.csv, download and parse

Data is merged into geo_country_elements — existing manual fields are preserved;
USGS figures for reserves + world_share_pct + world_rank are updated.
"""
from __future__ import annotations
import csv
import io
import logging
from datetime import datetime, timezone

import httpx

from app.repositories import dynamo
from .base import BaseIngestor, IngestResult, utcnow

logger = logging.getLogger(__name__)

SCIENCEBASE_API = "https://www.sciencebase.gov/catalog"

# Commodity title keyword → (atomic_number, symbol, element_name, reserve_unit_key)
# reserve_unit_key is our internal unit label (used only as a hint; actual unit
# is read from the CSV column name and may override this).
COMMODITY_MAP: dict[str, tuple[str, str, str, str]] = {
    "ALUMINUM":     ("13",  "Al", "Aluminium",  "mt_bauxite"),
    "BAUXITE":      ("13",  "Al", "Aluminium",  "mt_bauxite"),
    "ANTIMONY":     ("51",  "Sb", "Antimony",   "mt"),
    "ARSENIC":      ("33",  "As", "Arsenic",    "mt"),
    "BERYLLIUM":    ("4",   "Be", "Beryllium",  "mt"),
    "BISMUTH":      ("83",  "Bi", "Bismuth",    "mt"),
    "BORON":        ("5",   "B",  "Boron",      "mt_b2o3"),
    "BROMINE":      ("35",  "Br", "Bromine",    "mt"),
    "CADMIUM":      ("48",  "Cd", "Cadmium",    "mt"),
    "CHROMIUM":     ("24",  "Cr", "Chromium",   "mt"),
    "COBALT":       ("27",  "Co", "Cobalt",     "mt"),
    "COPPER":       ("29",  "Cu", "Copper",     "mt"),
    "GALLIUM":      ("31",  "Ga", "Gallium",    "mt"),
    "GERMANIUM":    ("32",  "Ge", "Germanium",  "mt"),
    "GOLD":         ("79",  "Au", "Gold",       "mt"),
    "GRAPHITE":     ("6",   "C",  "Carbon",     "mt"),
    "HELIUM":       ("2",   "He", "Helium",     "bcm"),
    "INDIUM":       ("49",  "In", "Indium",     "mt"),
    "IODINE":       ("53",  "I",  "Iodine",     "mt"),
    "IRON ORE":     ("26",  "Fe", "Iron",       "mt_ore"),
    "LEAD":         ("82",  "Pb", "Lead",       "mt"),
    "LITHIUM":      ("3",   "Li", "Lithium",    "mt"),
    "MAGNESIUM":    ("12",  "Mg", "Magnesium",  "mt"),
    "MANGANESE":    ("25",  "Mn", "Manganese",  "mt"),
    "MERCURY":      ("80",  "Hg", "Mercury",    "mt"),
    "MOLYBDENUM":   ("42",  "Mo", "Molybdenum", "mt"),
    "NICKEL":       ("28",  "Ni", "Nickel",     "mt"),
    "NIOBIUM":      ("41",  "Nb", "Niobium",    "mt"),
    "PHOSPHATE":    ("15",  "P",  "Phosphorus", "mt"),
    "PLATINUM":     ("78",  "Pt", "Platinum",   "mt"),
    "POTASH":       ("19",  "K",  "Potassium",  "mt_k2o"),
    "RARE EARTHS":  ("57",  "La", "Lanthanum",  "mt_reo"),
    "RHENIUM":      ("75",  "Re", "Rhenium",    "mt"),
    "SELENIUM":     ("34",  "Se", "Selenium",   "mt"),
    "SILICON":      ("14",  "Si", "Silicon",    "mt"),
    "SILVER":       ("47",  "Ag", "Silver",     "mt"),
    "STRONTIUM":    ("38",  "Sr", "Strontium",  "mt"),
    "TANTALUM":     ("73",  "Ta", "Tantalum",   "mt"),
    "TELLURIUM":    ("52",  "Te", "Tellurium",  "mt"),
    "TIN":          ("50",  "Sn", "Tin",        "mt"),
    "TITANIUM":     ("22",  "Ti", "Titanium",   "mt_tio2"),
    "TUNGSTEN":     ("74",  "W",  "Tungsten",   "mt"),
    "URANIUM":      ("92",  "U",  "Uranium",    "mt"),
    "VANADIUM":     ("23",  "V",  "Vanadium",   "mt"),
    "ZINC":         ("30",  "Zn", "Zinc",       "mt"),
    "ZIRCONIUM":    ("40",  "Zr", "Zirconium",  "mt"),
}

# USGS country name → ISO alpha-2
COUNTRY_MAP: dict[str, str] = {
    "United States":                "US",
    "Australia":                    "AU",
    "Brazil":                       "BR",
    "Canada":                       "CA",
    "China":                        "CN",
    "India":                        "IN",
    "Russia":                       "RU",
    "South Africa":                 "ZA",
    "Chile":                        "CL",
    "Peru":                         "PE",
    "Indonesia":                    "ID",
    "Philippines":                  "PH",
    "Kazakhstan":                   "KZ",
    "Mexico":                       "MX",
    "Argentina":                    "AR",
    "Bolivia":                      "BO",
    "Democratic Republic of the Congo": "CD",
    "Congo (Kinshasa)":             "CD",
    "DRC":                          "CD",
    "Morocco":                      "MA",
    "Turkey":                       "TR",
    "Türkiye":                      "TR",
    "Germany":                      "DE",
    "France":                       "FR",
    "Poland":                       "PL",
    "Vietnam":                      "VN",
    "Viet Nam":                     "VN",
    "Myanmar":                      "MM",
    "Japan":                        "JP",
    "South Korea":                  "KR",
    "Korea, Republic of":           "KR",
    "Iran":                         "IR",
    "Saudi Arabia":                 "SA",
    "Zambia":                       "ZM",
    "Zimbabwe":                     "ZW",
    "Namibia":                      "NA",
    "Gabon":                        "GA",
    "Guinea":                       "GN",
    "Ghana":                        "GH",
    "Tanzania":                     "TZ",
    "Mozambique":                   "MZ",
    "Madagascar":                   "MG",
    "Rwanda":                       "RW",
    "Ethiopia":                     "ET",
    "Egypt":                        "EG",
    "Algeria":                      "DZ",
    "Tunisia":                      "TN",
    "Jordan":                       "JO",
    "Israel":                       "IL",
    "Norway":                       "NO",
    "Finland":                      "FI",
    "Sweden":                       "SE",
    "Belgium":                      "BE",
    "Spain":                        "ES",
    "Ukraine":                      "UA",
    "Belarus":                      "BY",
    "Kyrgyzstan":                   "KG",
    "Tajikistan":                   "TJ",
    "Uzbekistan":                   "UZ",
    "Mongolia":                     "MN",
    "Venezuela":                    "VE",
    "Colombia":                     "CO",
    "Cuba":                         "CU",
    "Jamaica":                      "JM",
    "Qatar":                        "QA",
    "United Arab Emirates":         "AE",
    "Kuwait":                       "KW",
    "Oman":                         "OM",
    "Pakistan":                     "PK",
    "Malaysia":                     "MY",
    "Senegal":                      "SN",
    "Mali":                         "ML",
    "Niger":                        "NE",
    "Nigeria":                      "NG",
    "Uganda":                       "UG",
    "New Caledonia":                "NC",
    "Papua New Guinea":             "PG",
    "Afghanistan":                  "AF",
    "Serbia":                       "RS",
    "Portugal":                     "PT",
    "Austria":                      "AT",
    "Czech Republic":               "CZ",
    "Czechia":                      "CZ",
    "Slovakia":                     "SK",
    "Hungary":                      "HU",
    "Romania":                      "RO",
    "Bulgaria":                     "BG",
    "Greece":                       "GR",
    "Ecuador":                      "EC",
    "Guatemala":                    "GT",
    "Honduras":                     "HN",
    "Nicaragua":                    "NI",
    "Costa Rica":                   "CR",
    "Angola":                       "AO",
    "Botswana":                     "BW",
    "Sudan":                        "SD",
    "Eritrea":                      "ER",
    "Mali":                         "ML",
}

# Unit conversion to metric tons (our canonical unit)
UNIT_CONVERSIONS = {
    "kt":  1_000,        # kilotons  → metric tons
    "t":   1,            # metric tons (no conversion)
    "kg":  0.001,        # kilograms → metric tons
    "mt":  1_000_000,    # million metric tons → metric tons (rare in MCS)
    "lb":  0.000454,     # pounds → metric tons (very rare)
}


def _extract_unit(col_name: str) -> str | None:
    """Extract the unit suffix from a Reserves_* column name."""
    lower = col_name.lower()
    if lower.startswith("reserves_"):
        raw = col_name[len("reserves_"):]
        # Strip trailing suffixes like _reo, _tio2 etc.
        base = raw.split("_")[0].lower()
        return base
    return None


def _to_float(val) -> float | None:
    if val is None:
        return None
    s = str(val).replace(",", "").replace(" ", "").strip()
    if s in ("", "W", "—", "-", "NA", "N/A", "e"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _commodity_from_title(title: str) -> tuple[str, str, str, str] | None:
    """Map ScienceBase item title to element info tuple, or None if not relevant."""
    upper = title.upper()
    # Remove prefix
    for prefix in ["MINERAL COMMODITY SUMMARIES 2024 - ", "MINERAL COMMODITY SUMMARIES 2025 - ",
                   "MINERAL COMMODITY SUMMARIES 2026 - "]:
        upper = upper.replace(prefix, "")
    for keyword, info in COMMODITY_MAP.items():
        if keyword in upper:
            return info
    return None


def _parse_world_csv(
    content: str,
    element_info: tuple[str, str, str, str],
    source_id: str,
    data_year: int,
    source_url: str,
) -> dict[str, dict]:
    """
    Parse a _world.csv and return {cca2: element_entry}.
    Only rows with non-null Reserves are included.
    """
    atomic_number, symbol, el_name, hint_unit = element_info
    reader = csv.DictReader(io.StringIO(content))
    fieldnames = reader.fieldnames or []

    # Find the reserves column (not reserves_notes)
    reserve_col = next(
        (f for f in fieldnames
         if f.lower().startswith("reserves_") and "note" not in f.lower()),
        None,
    )
    if not reserve_col:
        return {}

    unit_suffix = _extract_unit(reserve_col)
    multiplier = UNIT_CONVERSIONS.get(unit_suffix, 1) if unit_suffix else 1

    results: dict[str, dict] = {}
    for row in reader:
        raw_country = (row.get("Country") or "").replace("\xa0", " ").strip()
        cca2 = COUNTRY_MAP.get(raw_country)
        if not cca2:
            continue
        raw_val = row.get(reserve_col)
        val = _to_float(raw_val)
        if val is None or val <= 0:
            continue

        val_mt = val * multiplier

        # Use hint_unit for non-standard commodities (REO, TiO2, K2O, B2O3)
        # otherwise derive from unit suffix
        if unit_suffix in ("kt", "t", "kg", "mt", "lb"):
            final_unit = "mt"
        else:
            final_unit = hint_unit  # e.g. mt_reo, mt_tio2

        note = (row.get("Reserves_notes") or "").strip()
        results[cca2] = {
            "atomic_number": atomic_number,
            "symbol": symbol,
            "name": el_name,
            "estimated_reserves": val_mt,
            "reserve_unit": final_unit,
            "data_type": "reserves",
            "world_share_pct": None,  # computed below
            "world_rank": None,
            "notes": f"USGS MCS {data_year}. {note}".strip(". "),
            "_source_id": source_id,
            "_data_year": data_year,
            "_source_url": source_url,
        }

    # Compute world share and rank
    world_total = sum(e["estimated_reserves"] for e in results.values())
    ranked = sorted(results.values(), key=lambda e: e["estimated_reserves"], reverse=True)
    for rank, entry in enumerate(ranked, start=1):
        entry["world_rank"] = rank
        entry["world_share_pct"] = (
            round(entry["estimated_reserves"] / world_total * 100, 2)
            if world_total > 0 else None
        )

    return results


class USGSIngestor(BaseIngestor):
    source_id = "usgs_mcs"

    async def _find_mcs_collection(self, client: httpx.AsyncClient, year: int) -> str | None:
        """
        Discover the ScienceBase parentId for the given MCS year by searching
        for a known commodity item (COPPER) and reading its parentId.
        Returns None if the collection exists but has no _world.csv files
        (e.g. MCS 2025 only includes _salient.csv).
        """
        search_url = (
            f"{SCIENCEBASE_API}/items"
            f"?q=Mineral+Commodity+Summaries+{year}+COPPER"
            f"&format=json&max=5&fields=id,title,parentId,files"
        )
        resp = await client.get(search_url)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        for item in items:
            if str(year) not in item.get("title", "") or "COPPER" not in item.get("title", "").upper():
                continue
            # Verify this collection actually has _world.csv files
            has_world = any(
                "_world" in f.get("name", "")
                for f in item.get("files", [])
            )
            if has_world:
                return item.get("parentId")
            # Collection exists but no world files (e.g. MCS 2025) — skip
            logger.info("MCS %d found on ScienceBase but has no _world.csv — skipping", year)
            return None
        return None

    async def _list_collection_items(self, client: httpx.AsyncClient, parent_id: str) -> list[dict]:
        """Return all items in a ScienceBase collection with their file metadata."""
        url = (
            f"{SCIENCEBASE_API}/items"
            f"?parentId={parent_id}&format=json&max=200&fields=id,title,files"
        )
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def run(self) -> IngestResult:
        current_year = datetime.now(timezone.utc).year
        fetched_at = utcnow()
        actual_year = None
        parent_id = None

        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
            headers={"User-Agent": "mindmap-geo/0.1 USGS-MCS-ingestor"},
        ) as client:
            # Try current year, then fall back to prior year
            for try_year in [current_year, current_year - 1, current_year - 2]:
                pid = await self._find_mcs_collection(client, try_year)
                if pid:
                    actual_year = try_year
                    parent_id = pid
                    logger.info("Found MCS %d collection on ScienceBase: %s", try_year, pid)
                    break

            if not parent_id or not actual_year:
                return IngestResult(
                    source_id=self.source_id,
                    status="failed",
                    error=f"Could not locate MCS collection on ScienceBase for {current_year} or earlier.",
                    summary="ScienceBase discovery failed — check network or USGS availability.",
                )

            items = await self._list_collection_items(client, parent_id)
            collection_url = f"{SCIENCEBASE_API}/items?parentId={parent_id}"

            # {cca2: {symbol: element_entry}} — accumulate across all commodities
            country_element_map: dict[str, dict[str, dict]] = {}
            records_fetched = 0
            parse_errors = 0

            for item in items:
                title = item.get("title", "")
                element_info = _commodity_from_title(title)
                if not element_info:
                    continue

                world_file = next(
                    (f for f in item.get("files", []) if "_world" in f.get("name", "")),
                    None,
                )
                if not world_file:
                    continue

                file_url = world_file.get("downloadUri", "")
                if not file_url:
                    continue

                try:
                    resp = await client.get(file_url)
                    resp.raise_for_status()
                    content = resp.content.decode("utf-8-sig", errors="ignore")
                    commodity_results = _parse_world_csv(
                        content, element_info, self.source_id, actual_year, file_url
                    )
                    records_fetched += len(commodity_results)
                    for cca2, entry in commodity_results.items():
                        country_element_map.setdefault(cca2, {})[entry["symbol"]] = entry
                except Exception as exc:
                    logger.warning("Failed to fetch/parse %s: %s", title, exc)
                    parse_errors += 1

            # Merge into existing geo_country_elements records
            records_updated = 0
            records_failed = 0
            for cca2, new_by_sym in country_element_map.items():
                try:
                    existing = await dynamo.get_country_elements(cca2) or {
                        "cca2": cca2, "elements": []
                    }
                    existing_by_sym = {e.get("symbol", ""): e for e in existing.get("elements", [])}
                    for sym, new_entry in new_by_sym.items():
                        if sym in existing_by_sym:
                            # Update USGS fields; preserve manually-written notes if they're longer
                            old = existing_by_sym[sym]
                            old_note = old.get("notes", "")
                            new_note = new_entry.get("notes", "")
                            merged_note = new_note if len(new_note) > len(old_note) else old_note
                            existing_by_sym[sym] = {
                                **old,
                                **{k: v for k, v in new_entry.items() if not k.startswith("_")},
                                "notes": merged_note,
                                "_source_id": new_entry.get("_source_id"),
                                "_data_year": new_entry.get("_data_year"),
                                "_source_url": new_entry.get("_source_url"),
                            }
                        else:
                            existing_by_sym[sym] = new_entry

                    updated_record = {
                        **existing,
                        "elements": list(existing_by_sym.values()),
                        "_last_ingested": fetched_at,
                        "_ingest_source_id": self.source_id,
                    }
                    await dynamo.upsert_country_elements(updated_record)
                    records_updated += 1
                except Exception:
                    logger.exception("Failed to write country_elements for %s", cca2)
                    records_failed += 1

        status = (
            "success" if parse_errors == 0 and records_failed == 0
            else "partial" if records_updated > 0
            else "failed"
        )
        return IngestResult(
            source_id=self.source_id,
            status=status,
            records_fetched=records_fetched,
            records_updated=records_updated,
            records_skipped=0,
            records_failed=records_failed + parse_errors,
            source_url=collection_url,
            data_date=str(actual_year),
            summary=(
                f"USGS MCS {actual_year} via ScienceBase — updated {records_updated} countries "
                f"with {records_fetched} element entries ({parse_errors} commodity parse errors)."
            ),
            details={
                "mcs_year": actual_year,
                "parent_id": parent_id,
                "countries_updated": sorted(country_element_map.keys()),
                "commodity_errors": parse_errors,
            },
        )
