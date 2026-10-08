import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.repositories.dynamo import ensure_tables
from app.routers import geo, elements, ingest, auth
from app.ingest.registry import SOURCES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _seed_ingest_sources() -> None:
    """Upsert the canonical source registry into DynamoDB at startup."""
    from app.repositories import dynamo as _dynamo
    for source in SOURCES:
        existing = await _dynamo.get_ingest_source(source["source_id"])
        if existing:
            # Preserve last_run_* fields; update static metadata only
            merged = {**source, **{
                k: v for k, v in existing.items()
                if k.startswith("last_")
            }}
            await _dynamo.upsert_ingest_source(merged)
        else:
            await _dynamo.upsert_ingest_source(source)
    logger.info("Seeded %d ingest sources", len(SOURCES))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env == "aws":
        # Tables are pre-created by CDK; skip ensure_tables to avoid IAM describe-table calls
        # at every cold start. Ingest sources are seeded on first ingest run.
        logger.info("Starting up (AWS Lambda — skipping table creation)")
    else:
        logger.info("Starting up — ensuring DynamoDB tables exist")
        await ensure_tables()
        logger.info("Tables ready")
        await _seed_ingest_sources()
    yield


app = FastAPI(title="mindmap-geo API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(geo.router, prefix="/api")
app.include_router(elements.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception on %s %s:\n%s",
        request.method,
        request.url,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


# Lambda entrypoint — ignored when running via uvicorn locally
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass
