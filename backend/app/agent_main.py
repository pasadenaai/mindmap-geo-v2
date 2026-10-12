"""Lambda entrypoint for the agent route (`POST /api/agent`).

Deployed as its OWN function, outside the VPC, because the API Lambda has no internet egress and
the Anthropic API is a public endpoint. Same image, different handler (`app.agent_main.handler`).
It carries only what it needs: the JWT secret (to verify access tokens), read access to the countries
table, and the Anthropic key. It exposes no other routes.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import agent

logging.basicConfig(level=logging.INFO)

# Kept identical to app.main.SECURITY_HEADERS (a test asserts they match).
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}
if settings.app_env == "aws":
    SECURITY_HEADERS["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

app = FastAPI(title="mindmap-geo agent", docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logging.getLogger(__name__).error("unhandled %s on %s", type(exc).__name__, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"}, headers=SECURITY_HEADERS)


app.include_router(agent.router, prefix="/api")

try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    pass
