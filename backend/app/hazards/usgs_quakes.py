from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any

from app.hazards.base import HazardAdapter
from app.hazards.models import HazardEvent


def _ms(ts: int | float) -> datetime:
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


class USGSQuakeAdapter(HazardAdapter):
    """USGS Earthquake GeoJSON summary feed (global, ~1-5 min update)."""

    source_id = "usgs_quakes"
    # M4.5+ past day; other windows/magnitudes are sibling files under the same path.
    feed_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
    default_ttl_hours = 72

    def parse(self, payload: Any) -> list[HazardEvent]:
        out: list[HazardEvent] = []
        for feat in (payload or {}).get("features", []):
            try:
                props = feat["properties"]
                if props.get("type") not in (None, "earthquake"):
                    continue  # quarry blasts, explosions, etc.
                lon, lat = feat["geometry"]["coordinates"][:2]
                depth = feat["geometry"]["coordinates"][2] if len(feat["geometry"]["coordinates"]) > 2 else None
                event_time = _ms(props["time"])
                updated = _ms(props.get("updated") or props["time"])
                out.append(HazardEvent(
                    event_id=f"{self.source_id}:{feat['id']}",
                    hazard="earthquake",
                    source=self.source_id,
                    source_url=props.get("url"),
                    title=str(props.get("title") or props.get("place") or "Earthquake")[:300],
                    description=str(props.get("place") or "")[:2000],
                    lat=float(lat), lon=float(lon),
                    magnitude=float(props["mag"]) if props.get("mag") is not None else None,
                    severity_raw=props.get("alert"),  # PAGER: green/yellow/orange/red or None
                    event_time=event_time,
                    updated_at=updated,
                    expires_at=updated + timedelta(hours=self.default_ttl_hours),
                    extra={"depth_km": depth, "tsunami": bool(props.get("tsunami")), "felt": props.get("felt"),
                           "sig": props.get("sig")},
                ))
            except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
                self._skip(self.source_id, repr(exc), feat)
        return out
