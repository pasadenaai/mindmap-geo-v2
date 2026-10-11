"""
Source registry — canonical list of all external data sources.
Seeded into DynamoDB at startup; records are upserted so updates
to this list propagate on the next container restart.
"""

SOURCES: list[dict] = [
    {
        "source_id": "usgs_mcs",
        "name": "USGS Mineral Commodity Summaries",
        "organization": "U.S. Geological Survey",
        "url": "https://www.sciencebase.gov/catalog/items?parentId=65a6e45fd34e5af967a46749",
        "url_template": "https://www.sciencebase.gov/catalog/items?q=Mineral+Commodity+Summaries+{year}+COPPER",
        "data_type": "minerals",
        "format": "sciencebase_csv",
        "schedule_cron": "0 0 1 3 *",  # annually, early March (MCS published in February)
        "active": True,
        "notes": (
            "Published every February. Per-commodity _world.csv files on USGS ScienceBase. "
            "~87 commodities, 57+ countries per run. Discovery is dynamic — ingestor searches "
            "ScienceBase by year (current → prior) and picks the most recent collection with "
            "_world.csv files. NOTE: MCS 2025 dropped _world.csv; ingestor correctly falls back "
            "to MCS 2024."
        ),
    },
    {
        "source_id": "eia_international",
        "name": "EIA International Energy Statistics",
        "organization": "U.S. Energy Information Administration",
        "url": "https://api.eia.gov/v2/international/data/",
        "data_type": "energy",
        "format": "api_json",
        "api_key_env": "EIA_API_KEY",
        "schedule_cron": "0 0 1 * *",  # monthly
        "active": True,
        "notes": (
            "Free API key required — register at https://www.eia.gov/opendata/. "
            "Set EIA_API_KEY env var. Covers crude oil, natural gas, and coal "
            "proved reserves and production by country. Writes to geo_country_resources."
        ),
    },
    {
        "source_id": "bgs_world_mineral_statistics",
        "name": "BGS World Mineral Statistics",
        "organization": "British Geological Survey",
        "url": "https://www2.bgs.ac.uk/mineralsuk/statistics/wms.cfc",
        "data_type": "minerals",
        "format": "csv_query",
        "schedule_cron": "0 0 1 6 *",  # annually in June (BGS updates ~mid-year)
        "active": False,
        "notes": (
            "Web query interface — no direct CSV download URL. Requires form submission "
            "with commodity + country selections. Strong on historical production data "
            "back to 1970. Manual download recommended; automated ingestion requires "
            "a headless browser or scraper."
        ),
    },
    {
        "source_id": "opec_statistical_bulletin",
        "name": "OPEC Annual Statistical Bulletin",
        "organization": "Organization of the Petroleum Exporting Countries",
        "url": "https://www.opec.org/opec_web/en/data_graphs/330.htm",
        "data_type": "energy",
        "format": "excel",
        "schedule_cron": "0 0 1 8 *",  # annually in August (published June/July)
        "active": False,
        "notes": (
            "Published annually, usually June–July. Excel download available from the page. "
            "Covers proven oil reserves for the 13 OPEC member states with historical series. "
            "Definitive for OPEC members; cross-check against EIA for non-OPEC."
        ),
    },
    {
        "source_id": "ei_statistical_review",
        "name": "Energy Institute Statistical Review of World Energy",
        "organization": "Energy Institute (formerly BP Statistical Review)",
        "url": "https://www.energyinst.org/statistical-review/resources-and-data/downloads",
        "data_type": "energy",
        "format": "excel",
        "schedule_cron": "0 0 1 7 *",  # annually in July (published June)
        "active": False,
        "notes": (
            "Published annually in June. Comprehensive Excel download covering oil, gas, coal, "
            "nuclear, hydro, and renewables for ~70 countries back to 1965. "
            "Good independent cross-check against EIA."
        ),
    },
    {
        "source_id": "world_mining_data",
        "name": "World Mining Data",
        "organization": "Austrian Federal Ministry of Finance / Montanuniversitaet Leoben",
        "url": "https://www.world-mining-data.info",
        "data_type": "minerals",
        "format": "excel",
        "schedule_cron": "0 0 1 5 *",  # annually in May
        "active": False,
        "notes": (
            "Published annually. Covers ~70 mineral raw materials across ~180 countries. "
            "Good cross-check against USGS MCS; slightly different reserve methodology. "
            "Excel download from main page."
        ),
    },
    {
        "source_id": "usgs_quakes",
        "name": "USGS Earthquake Hazards Program — GeoJSON feeds",
        "organization": "U.S. Geological Survey",
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
        "data_type": "hazard_events",
        "format": "geojson",
        "schedule_cron": "*/10 * * * *",
        "active": False,
        "notes": "Global, no key. Parser: app/hazards/usgs_quakes.py. Activated in Phase 1 (docs/HAZARD_ALERTS_DESIGN.md).",
    },
    {
        "source_id": "gdacs",
        "name": "GDACS — Global Disaster Alert and Coordination System",
        "organization": "UN OCHA / European Commission JRC",
        "url": "https://www.gdacs.org/",
        "data_type": "hazard_events",
        "format": "geojson",
        "schedule_cron": "0 * * * *",
        "active": False,
        "notes": "Global alert levels (Green/Orange/Red). Parser: app/hazards/gdacs.py; verify feed format against a recorded response before activating (Phase 1).",
    },
]
