from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.hazards.base import HazardAdapter
from app.hazards.models import HazardEvent

_HAZARD = {"EQ": "earthquake", "TC": "cyclone", "FL": "flood", "VO": "volcano", "DR": "drought", "WF": "wildfire",
           "TS": "tsunami"}
_TTL_HOURS = {"cyclone": 96, "flood": 168, "drought": 720, "volcano": 168, "wildfire": 168}


def _dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class GDACSAdapter(HazardAdapter):
    """GDACS (UN/EC) global alert feed with Red/Orange/Green levels.

    The endpoint and field names below follow GDACS's public GeoJSON event list. VERIFY them
    against a recorded live response before relying on this adapter in production (the
    fixture in tests/fixtures is a hand-written approximation).
    """

    source_id = "gdacs"
    feed_url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
    default_ttl_hours = 120

    def parse(self, payload: Any) -> list[HazardEvent]:
        out: list[HazardEvent] = []
        for feat in (payload or {}).get("features", []):
            try:
                props = feat["properties"]
                geom = feat["geometry"]
                if geom.get("type") != "Point":
                    continue  # footprint/track geometries are separate features; Phase 3
                lon, lat = geom["coordinates"][:2]
                hazard = _HAZARD.get(props.get("eventtype"), "other")
                started = _dt(props.get("fromdate")) or datetime.now(timezone.utc)
                updated = _dt(props.get("datemodified")) or started
                ends = _dt(props.get("todate"))
                ttl = timedelta(hours=_TTL_HOURS.get(hazard, self.default_ttl_hours))
                sev = props.get("severitydata") or {}
                urls = props.get("url") or {}
                out.append(HazardEvent(
                    event_id=f"{self.source_id}:{props['eventtype']}{props['eventid']}",
                    hazard=hazard,
                    source=self.source_id,
                    source_url=urls.get("report") or urls.get("details"),
                    title=str(props.get("name") or props.get("htmldescription") or hazard.title())[:300],
                    description=str(props.get("description") or "")[:2000],
                    lat=float(lat), lon=float(lon),
                    magnitude=float(sev["severity"]) if sev.get("severity") is not None else None,
                    severity_raw=(props.get("alertlevel") or "").lower() or None,
                    event_time=started,
                    updated_at=updated,
                    expires_at=max(updated + ttl, ends) if ends else updated + ttl,
                    extra={"country": props.get("country"), "alertscore": props.get("alertscore"),
                           "severity_text": sev.get("severitytext"), "severity_unit": sev.get("severityunit"),
                           "population": props.get("population")},
                ))
            except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
                self._skip(self.source_id, repr(exc), feat)
        return out
