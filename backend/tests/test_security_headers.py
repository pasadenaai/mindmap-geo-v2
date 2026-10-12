"""Security headers must be present on normal responses AND on unhandled-500 responses."""
from fastapi.testclient import TestClient

from app.main import SECURITY_HEADERS, app


def _assert_headers(resp):
    for name, value in SECURITY_HEADERS.items():
        assert resp.headers.get(name) == value, f"missing/incorrect {name}"
    assert resp.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]


def test_health_has_security_headers():
    _assert_headers(TestClient(app).get("/health"))


def test_unhandled_500_has_security_headers():
    async def boom():
        raise RuntimeError("boom")

    app.add_api_route("/__test_boom", boom)
    try:
        resp = TestClient(app, raise_server_exceptions=False).get("/__test_boom")
    finally:
        app.router.routes.pop()   # keep the shared app clean for other tests
    assert resp.status_code == 500
    _assert_headers(resp)
