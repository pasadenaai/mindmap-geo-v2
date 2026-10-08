"""
EIA International Energy Statistics ingestor.

Fetches annual production data for crude oil and natural gas from the EIA
API v2 international route, then coal production from the EIA coal route.
Writes results to geo_country_resources (one record per country, keyed by cca2).
World share percentages are computed once all country values are collected.

NOTE on data type: The EIA international API exposes Production, Consumption,
Imports, and Stocks — not proved reserves. Proved reserves for international
countries are published by EIA only as annual Excel downloads, not via the API.
We therefore store production figures (data_type="production"), which accurately
reflect each country's energy footprint and are updated more frequently.
For proved reserves use OPEC Statistical Bulletin (OPEC members) or the
Energy Institute Statistical Review (all countries) — both registered as
inactive sources in geo_ingest_sources pending their format parsers.

API docs: https://www.eia.gov/opendata/documentation.php
Free key: https://www.eia.gov/opendata/register.php

EIA country codes: ISO alpha-3 standard (e.g. USA, SAU, RUS, CHN).
Aggregate regions use 4-letter codes (WORL, OPEC, OECD…) — filtered out.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.repositories import dynamo
from .base import BaseIngestor, IngestResult, utcnow

logger = logging.getLogger(__name__)

EIA_INTL_BASE = "https://api.eia.gov/v2/international/data/"

# EIA international data product IDs (numeric) + activityId=1 (Production).
# Units as returned by the API.
PRODUCTS = {
    "oil": {
        "product_id":   "55",
        "activity_id":  "1",
        "name":         "Crude oil + NGPL production",
        "unit":         "thousand barrels per day",
        "unit_key":     "tbpd",
        "data_type":    "production",
    },
    "gas": {
        "product_id":   "26",
        "activity_id":  "1",
        "name":         "Dry natural gas production",
        "unit":         "billion cubic feet",
        "unit_key":     "bcf",
        "data_type":    "production",
    },
}

# ISO alpha-3 → ISO alpha-2 for every country the EIA reports.
# EIA uses standard ISO 3166-1 alpha-3 codes for individual countries;
# 4-letter codes are aggregates (WORL, OPEC, OECD…) and are skipped.
ISO3_TO_CCA2: dict[str, str] = {
    "ABW": "AW", "AFG": "AF", "AGO": "AO", "ALB": "AL", "AND": "AD",
    "ARE": "AE", "ARG": "AR", "ARM": "AM", "ATG": "AG", "AUS": "AU",
    "AUT": "AT", "AZE": "AZ", "BDI": "BI", "BEL": "BE", "BEN": "BJ",
    "BFA": "BF", "BGD": "BD", "BGR": "BG", "BHR": "BH", "BHS": "BS",
    "BIH": "BA", "BLR": "BY", "BLZ": "BZ", "BMU": "BM", "BOL": "BO",
    "BRA": "BR", "BRB": "BB", "BRN": "BN", "BTN": "BT", "BWA": "BW",
    "CAF": "CF", "CAN": "CA", "CHE": "CH", "CHL": "CL", "CHN": "CN",
    "CIV": "CI", "CMR": "CM", "COD": "CD", "COG": "CG", "COL": "CO",
    "COM": "KM", "CPV": "CV", "CRI": "CR", "CUB": "CU", "CYP": "CY",
    "CZE": "CZ", "DEU": "DE", "DJI": "DJ", "DMA": "DM", "DNK": "DK",
    "DOM": "DO", "DZA": "DZ", "ECU": "EC", "EGY": "EG", "ERI": "ER",
    "ESP": "ES", "EST": "EE", "ETH": "ET", "FIN": "FI", "FJI": "FJ",
    "FRA": "FR", "FSM": "FM", "GAB": "GA", "GBR": "GB", "GEO": "GE",
    "GHA": "GH", "GIN": "GN", "GMB": "GM", "GNB": "GW", "GNQ": "GQ",
    "GRC": "GR", "GRD": "GD", "GTM": "GT", "GUY": "GY", "HND": "HN",
    "HRV": "HR", "HTI": "HT", "HUN": "HU", "IDN": "ID", "IND": "IN",
    "IRL": "IE", "IRN": "IR", "IRQ": "IQ", "ISL": "IS", "ISR": "IL",
    "ITA": "IT", "JAM": "JM", "JOR": "JO", "JPN": "JP", "KAZ": "KZ",
    "KEN": "KE", "KGZ": "KG", "KHM": "KH", "KIR": "KI", "KNA": "KN",
    "KOR": "KR", "KWT": "KW", "LAO": "LA", "LBN": "LB", "LBR": "LR",
    "LBY": "LY", "LCA": "LC", "LIE": "LI", "LKA": "LK", "LSO": "LS",
    "LTU": "LT", "LUX": "LU", "LVA": "LV", "MAC": "MO", "MAR": "MA",
    "MDA": "MD", "MDG": "MG", "MDV": "MV", "MEX": "MX", "MHL": "MH",
    "MKD": "MK", "MLI": "ML", "MLT": "MT", "MMR": "MM", "MNE": "ME",
    "MNG": "MN", "MOZ": "MZ", "MRT": "MR", "MUS": "MU", "MWI": "MW",
    "MYS": "MY", "NAM": "NA", "NER": "NE", "NGA": "NG", "NIC": "NI",
    "NLD": "NL", "NOR": "NO", "NPL": "NP", "NRU": "NR", "NZL": "NZ",
    "OMN": "OM", "PAK": "PK", "PAN": "PA", "PER": "PE", "PHL": "PH",
    "PLW": "PW", "PNG": "PG", "POL": "PL", "PRK": "KP", "PRT": "PT",
    "PRY": "PY", "PSE": "PS", "QAT": "QA", "ROU": "RO", "RUS": "RU",
    "RWA": "RW", "SAU": "SA", "SDN": "SD", "SEN": "SN", "SGP": "SG",
    "SLB": "SB", "SLE": "SL", "SLV": "SV", "SMR": "SM", "SOM": "SO",
    "SRB": "RS", "SSD": "SS", "STP": "ST", "SUR": "SR", "SVK": "SK",
    "SVN": "SI", "SWE": "SE", "SWZ": "SZ", "SYC": "SC", "SYR": "SY",
    "TCA": "TC", "TCD": "TD", "TGO": "TG", "THA": "TH", "TJK": "TJ",
    "TKM": "TM", "TLS": "TL", "TON": "TO", "TTO": "TT", "TUN": "TN",
    "TUR": "TR", "TUV": "TV", "TZA": "TZ", "UGA": "UG", "UKR": "UA",
    "URY": "UY", "USA": "US", "UZB": "UZ", "VCT": "VC", "VEN": "VE",
    "VNM": "VN", "VUT": "VU", "WSM": "WS", "YEM": "YE", "ZAF": "ZA",
    "ZMB": "ZM", "ZWE": "ZW",
}


def _iso3_to_cca2(iso3: str) -> str | None:
    """Convert ISO alpha-3 to alpha-2. Returns None for aggregates (len != 3)."""
    if len(iso3) != 3:
        return None  # aggregate region (WORL, OPEC, OECD…)
    return ISO3_TO_CCA2.get(iso3)


class EIAIngestor(BaseIngestor):
    source_id = "eia_international"
    SOURCE_URL = EIA_INTL_BASE

    async def run(self) -> IngestResult:
        api_key = settings.eia_api_key
        if not api_key:
            return IngestResult(
                source_id=self.source_id,
                status="skipped",
                source_url=self.SOURCE_URL,
                error="EIA_API_KEY not configured. Register at https://www.eia.gov/opendata/register.php",
                summary="Skipped — no API key. Set EIA_API_KEY env var and restart.",
            )

        fetched_at = utcnow()
        country_data: dict[str, dict] = {}           # cca2 → {resource_type → entry}
        world_totals: dict[str, float] = {rt: 0.0 for rt in PRODUCTS}
        records_fetched = 0
        records_failed = 0
        latest_data_year = str(datetime.now(timezone.utc).year - 1)

        async with httpx.AsyncClient(timeout=60) as client:
            for resource_type, cfg in PRODUCTS.items():
                try:
                    params = {
                        "frequency": "annual",
                        "data[0]": "value",
                        "facets[productId][]": cfg["product_id"],
                        "facets[activityId][]": cfg["activity_id"],
                        "start": str(int(latest_data_year) - 2),
                        "sort[0][column]": "period",
                        "sort[0][direction]": "desc",
                        "length": 5000,
                        "api_key": api_key,
                    }
                    resp = await client.get(EIA_INTL_BASE, params=params)
                    resp.raise_for_status()
                    rows = resp.json().get("response", {}).get("data", [])

                    # Keep only the most recent value per country
                    best: dict[str, dict] = {}
                    for row in rows:
                        cca2 = _iso3_to_cca2(row.get("countryRegionId", ""))
                        if not cca2:
                            continue
                        raw = row.get("value")
                        if raw is None or str(raw) in ("--", "W", "NA", ""):
                            continue
                        try:
                            val = float(raw)
                        except (TypeError, ValueError):
                            continue
                        if val <= 0:
                            continue
                        period = str(row.get("period", ""))
                        if cca2 not in best or period > best[cca2]["period"]:
                            best[cca2] = {
                                "value": val,
                                "period": period,
                                "country_name": row.get("countryRegionName", ""),
                                "api_unit": row.get("unit", cfg["unit_key"]),
                            }

                    for cca2, entry in best.items():
                        records_fetched += 1
                        country_data.setdefault(cca2, {})[resource_type] = {
                            "resource_type": resource_type,
                            "name": cfg["name"],
                            "value": entry["value"],
                            "unit": cfg["unit"],
                            "unit_key": cfg["unit_key"],
                            "data_type": cfg["data_type"],
                            "data_year": entry["period"],
                            "source_id": self.source_id,
                            "source_url": self.SOURCE_URL,
                            "fetched_at": fetched_at,
                        }
                        world_totals[resource_type] += entry["value"]
                        if entry["period"] > latest_data_year:
                            latest_data_year = entry["period"]

                except Exception:
                    logger.exception("EIA fetch failed for resource_type=%s", resource_type)
                    records_failed += 1

        # Compute world share percentages
        records_updated = 0
        for cca2, by_type in country_data.items():
            resources_list = []
            for rt, entry in by_type.items():
                total = world_totals.get(rt, 0)
                entry["world_share_pct"] = (
                    round(entry["value"] / total * 100, 2) if total > 0 else None
                )
                resources_list.append(entry)

            record = {
                "cca2": cca2,
                "resources": resources_list,
                "_last_ingested": fetched_at,
                "_ingest_source_id": self.source_id,
            }
            try:
                await dynamo.upsert_country_resources(record)
                records_updated += 1
            except Exception:
                logger.exception("Failed to write resources for %s", cca2)
                records_failed += 1

        status = (
            "success" if records_failed == 0
            else "partial" if records_updated > 0
            else "failed"
        )
        return IngestResult(
            source_id=self.source_id,
            status=status,
            records_fetched=records_fetched,
            records_updated=records_updated,
            records_skipped=0,
            records_failed=records_failed,
            source_url=self.SOURCE_URL,
            data_date=latest_data_year,
            summary=(
                f"EIA production data ingested for {records_updated} countries "
                f"(oil + gas, data year ~{latest_data_year}). "
                f"data_type=production (EIA intl API does not expose proved reserves)."
            ),
            details={"world_totals": world_totals, "products_fetched": list(PRODUCTS.keys())},
        )
