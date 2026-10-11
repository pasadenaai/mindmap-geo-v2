from app.hazards.base import HazardAdapter
from app.hazards.gdacs import GDACSAdapter
from app.hazards.usgs_quakes import USGSQuakeAdapter

ADAPTERS: dict[str, HazardAdapter] = {a.source_id: a for a in (USGSQuakeAdapter(), GDACSAdapter())}
