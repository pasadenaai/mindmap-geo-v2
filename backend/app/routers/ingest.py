"""
Ingestion router — /api/geo/ingest/*

Endpoints:
  GET    /api/geo/ingest/sources              — list all registered sources
  GET    /api/geo/ingest/sources/{source_id}  — get one source record
  POST   /api/geo/ingest/run/{source_id}      — trigger a manual ingestion run
  GET    /api/geo/ingest/log                  — list recent runs (newest first)
  GET    /api/geo/ingest/log/{run_id}         — get a specific run

All ingestion runs execute as FastAPI background tasks so the trigger
endpoint returns immediately with the run_id; callers poll /log/{run_id}.
"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.repositories import dynamo
from app.ingest.base import utcnow
from app.ingest.eia import EIAIngestor
from app.ingest.usgs import USGSIngestor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/geo/ingest", tags=["ingest"])

# Registry of concrete ingestor instances keyed by source_id.
# Add new ingestors here when implemented.
INGESTORS = {
    "eia_international": EIAIngestor(),
    "usgs_mcs": USGSIngestor(),
}


async def _execute_run(source_id: str, run_id: str, triggered_by: str) -> None:
    """Background task: run the ingestor and write the result to the log."""
    started_at = utcnow()
    ingestor = INGESTORS.get(source_id)

    if not ingestor:
        await dynamo.update_ingest_log(run_id, {
            "status": "failed",
            "completed_at": utcnow(),
            "error": f"No ingestor implemented for source_id '{source_id}'.",
            "summary": "Source registered but no ingestor code exists yet.",
        })
        return

    try:
        result = await ingestor.run()
    except Exception as exc:
        logger.exception("Ingestor %s raised unexpectedly", source_id)
        await dynamo.update_ingest_log(run_id, {
            "status": "failed",
            "completed_at": utcnow(),
            "error": str(exc),
            "summary": "Ingestor raised an unhandled exception.",
        })
        return

    log_entry = result.to_log_entry(run_id, triggered_by, started_at)
    # update_ingest_log only writes changed keys; completed_at etc. are set here
    await dynamo.update_ingest_log(run_id, {
        k: v for k, v in log_entry.items() if k != "run_id"
    })

    # Stamp the source record with last_run metadata
    await dynamo.upsert_ingest_source({
        "source_id": source_id,
        "last_run_id": run_id,
        "last_run_status": result.status,
        "last_fetched_at": log_entry["completed_at"],
        "last_data_date": result.data_date,
    })

    logger.info(
        "Ingest run %s (%s) finished: %s — %s",
        run_id, source_id, result.status, result.summary,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/sources")
async def list_sources():
    """Return all registered ingest sources."""
    return await dynamo.list_ingest_sources()


@router.get("/sources/{source_id}")
async def get_source(source_id: str):
    """Return a single ingest source record."""
    source = await dynamo.get_ingest_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return source


@router.post("/run/{source_id}", status_code=202)
async def trigger_run(source_id: str, background_tasks: BackgroundTasks):
    """
    Trigger a manual ingestion run for the given source.
    Returns immediately with the run_id; poll /log/{run_id} for status.
    """
    source = await dynamo.get_ingest_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not registered")

    run_id = str(uuid.uuid4())
    # Create a "running" log entry immediately so callers can poll
    await dynamo.create_ingest_log({
        "run_id": run_id,
        "source_id": source_id,
        "triggered_by": "manual",
        "started_at": utcnow(),
        "status": "running",
        "records_fetched": 0,
        "records_updated": 0,
        "records_skipped": 0,
        "records_failed": 0,
        "source_url": source.get("url", ""),
        "data_date": "",
        "error": None,
        "summary": f"Run triggered manually for {source_id}.",
        "details": {},
    })

    background_tasks.add_task(_execute_run, source_id, run_id, "manual")

    return {
        "run_id": run_id,
        "source_id": source_id,
        "status": "running",
        "poll_url": f"/api/geo/ingest/log/{run_id}",
        "message": f"Ingestion started. Poll {'/api/geo/ingest/log/' + run_id} for status.",
    }


@router.get("/log")
async def list_log(limit: int = 50):
    """Return the most recent ingestion log entries, newest first."""
    return await dynamo.list_ingest_logs(limit=limit)


@router.get("/log/{run_id}")
async def get_log_entry(run_id: str):
    """Return a specific ingestion run log entry."""
    entry = await dynamo.get_ingest_log(run_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Log entry '{run_id}' not found")
    return entry


@router.get("/resources/{cca2}")
async def get_country_resources(cca2: str):
    """
    Return the natural-resources record for a country (Phase 2 — EIA oil/gas/coal).
    Returns {cca2, resources:[]} shape; empty resources list if no data yet.
    """
    record = await dynamo.get_country_resources(cca2.upper())
    if not record:
        return {"cca2": cca2.upper(), "resources": []}
    return record
