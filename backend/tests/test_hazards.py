"""Hazard adapters parse recorded fixtures into normalized, safe events (no network)."""
import json
from datetime import timedelta
from pathlib import Path

import pytest

from app.hazards.gdacs import GDACSAdapter
from app.hazards.models import HazardEvent
from app.hazards.registry import ADAPTERS
from app.hazards.usgs_quakes import USGSQuakeAdapter

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text())


def test_usgs_parses_quakes_and_skips_noise():
    events = USGSQuakeAdapter().parse(load("usgs_quakes_sample.geojson"))
    assert [e.event_id for e in events] == ["usgs_quakes:us7000test1", "usgs_quakes:us7000test2"]
    big = events[0]
    assert big.hazard == "earthquake" and big.magnitude == 6.4 and big.severity_raw == "yellow"
    assert (big.lat, big.lon) == (23.98, 122.65)          # GeoJSON order is [lon, lat, depth]
    assert big.extra["tsunami"] is True and big.extra["depth_km"] == 18.4
    assert big.source_url.startswith("https://earthquake.usgs.gov/")
    assert events[1].severity_raw is None


def test_usgs_expiry_after_update_time():
    e = USGSQuakeAdapter().parse(load("usgs_quakes_sample.geojson"))[0]
    assert e.expires_at == e.updated_at + timedelta(hours=72)
    assert e.event_time <= e.updated_at


def test_gdacs_parses_points_and_skips_tracks_and_malformed():
    events = GDACSAdapter().parse(load("gdacs_sample.geojson"))
    assert [e.event_id for e in events] == ["gdacs:TC1001234", "gdacs:FL1002000"]
    tc = events[0]
    assert tc.hazard == "cyclone" and tc.severity_raw == "orange" and tc.magnitude == 148.2
    assert (tc.lat, tc.lon) == (16.2, 127.4)
    assert tc.extra["country"] == "Philippines"
    assert tc.expires_at >= tc.event_time


@pytest.mark.parametrize("payload", [None, {}, {"features": []}, {"features": [{}]}, {"features": [{"properties": 1}]}])
def test_parsers_never_raise_on_garbage(payload):
    for adapter in ADAPTERS.values():
        assert adapter.parse(payload) == []


def test_event_ids_are_namespaced_and_models_validate():
    for adapter in ADAPTERS.values():
        assert adapter.source_id and adapter.feed_url.startswith("https://")
    ev = USGSQuakeAdapter().parse(load("usgs_quakes_sample.geojson"))[0]
    assert HazardEvent.model_validate(ev.model_dump()).event_id.startswith("usgs_quakes:")


def test_untrusted_text_is_length_bounded():
    payload = load("usgs_quakes_sample.geojson")
    payload["features"][0]["properties"]["title"] = "X" * 5000
    payload["features"][0]["properties"]["place"] = "Y" * 5000
    e = USGSQuakeAdapter().parse(payload)[0]
    assert len(e.title) <= 300 and len(e.description) <= 2000
