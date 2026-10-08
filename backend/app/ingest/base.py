"""
BaseIngestor — abstract base class for all external data source ingestors.

Each concrete ingestor implements `run()` and returns an IngestResult.
The router calls `run()` and writes the result to `geo_ingest_log`.
"""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class IngestResult:
    source_id: str
    status: str          # "success" | "partial" | "failed" | "skipped"
    records_fetched: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    source_url: str = ""
    data_date: str = ""  # year or ISO date the *data* represents (not the fetch date)
    error: str | None = None
    summary: str = ""
    details: dict = field(default_factory=dict)

    def to_log_entry(self, run_id: str, triggered_by: str, started_at: str) -> dict:
        return {
            "run_id": run_id,
            "source_id": self.source_id,
            "triggered_by": triggered_by,
            "started_at": started_at,
            "completed_at": utcnow(),
            "status": self.status,
            "records_fetched": self.records_fetched,
            "records_updated": self.records_updated,
            "records_skipped": self.records_skipped,
            "records_failed": self.records_failed,
            "source_url": self.source_url,
            "data_date": self.data_date,
            "error": self.error,
            "summary": self.summary,
            "details": self.details,
        }


class BaseIngestor(ABC):
    source_id: str

    @abstractmethod
    async def run(self) -> IngestResult:
        """Fetch external data and write to DynamoDB. Return an IngestResult."""
        ...
