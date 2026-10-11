from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Any

from app.hazards.models import HazardEvent

logger = logging.getLogger(__name__)


class HazardAdapter(ABC):
    """One adapter per external feed.

    `parse` is pure (payload in, events out) and is what tests exercise with recorded
    fixtures. `fetch` is the only method that touches the network.
    """

    source_id: str
    feed_url: str
    default_ttl_hours: int = 72

    @abstractmethod
    def parse(self, payload: Any) -> list[HazardEvent]:
        """Normalize a raw feed payload. Must skip (and log) malformed records, never raise on one."""

    async def fetch(self) -> list[HazardEvent]:
        import httpx  # local import: parsers/tests don't need a network client

        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "mindmap-geo-v2 hazard-ingest"}) as client:
            resp = await client.get(self.feed_url)
            resp.raise_for_status()
            return self.parse(resp.json())

    @staticmethod
    def _skip(source: str, reason: str, record: Any) -> None:
        rid = record.get("id") if isinstance(record, dict) else None
        logger.warning("hazard parse: skipped %s record id=%s: %s", source, rid, reason)
