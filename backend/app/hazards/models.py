from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

Hazard = Literal["earthquake", "cyclone", "volcano", "flood", "wildfire", "drought", "tsunami", "other"]


class HazardEvent(BaseModel):
    """Source-agnostic event. `title`/`description` are untrusted feed text (design §8)."""

    event_id: str                     # "{source}:{source_event_id}" — stable across updates
    hazard: Hazard
    source: str                       # adapter source_id
    source_url: Optional[str] = None  # link back to the authority; shown in the UI
    title: str = Field(max_length=300)
    description: str = Field(default="", max_length=2000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    magnitude: Optional[float] = None      # source-native magnitude where meaningful
    severity_raw: Optional[str] = None     # source-native level, e.g. "orange", "yellow"
    event_time: datetime
    updated_at: datetime
    expires_at: datetime                   # drives the DynamoDB TTL on the events table
    extra: dict = Field(default_factory=dict)
