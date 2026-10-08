"""Auth / access-control behaviour (AC-3, AC-7, IA-5, AC-12)."""
from app.core.config import settings

PW = "correct-horse-battery"


def register(client, name="alice", pw=PW):
    return client.post("/api/auth/register", json={"username": name, "password": pw})


def test_write_without_token_is_rejected(client):
    for method, path in [("post", "/api/geo/points"), ("delete", "/api/geo/points/x"),
                         ("post", "/api/geo/ingest/run/usgs_mcs")]:
        r = getattr(client, method)(path, json={}) if method == "post" else getattr(client, method)(path)
        assert r.status_code == 401, (method, path, r.status_code)


def test_write_with_invalid_token_is_rejected(client):
    r = client.post("/api/geo/points", json={}, headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client):
    register(client)
    refresh = client.cookies.get("refresh_token")
    r = client.post("/api/geo/points", json={}, headers={"Authorization": f"Bearer {refresh}"})
    assert r.status_code == 401


def test_valid_token_passes_guard(client):
    token = register(client).json()["access_token"]
    r = client.post("/api/geo/points", json={}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code != 401  # reaches the route (422: empty body fails validation)


def test_reads_public_by_default_and_gated_when_configured(client, monkeypatch):
    assert client.get("/health").status_code == 200
    monkeypatch.setattr(settings, "require_auth_for_reads", True)
    assert client.get("/api/geo/points").status_code == 401


def test_registration_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_registration", False)
    assert register(client).status_code == 403


def test_password_policy(client):
    assert register(client, pw="short").status_code == 422
    assert register(client, name="bobby", pw="xx-bobby-xxxxxxxx").status_code == 422
    assert register(client, name="carol").status_code == 201


def test_lockout_after_repeated_failures(client, monkeypatch):
    monkeypatch.setattr(settings, "max_failed_logins", 3)
    register(client)
    for _ in range(3):
        assert client.post("/api/auth/login", json={"username": "alice", "password": "wrong"}).status_code == 401
    # correct password is refused while locked
    assert client.post("/api/auth/login", json={"username": "alice", "password": PW}).status_code == 429


def test_login_resets_failure_counter(client):
    register(client)
    client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert client.post("/api/auth/login", json={"username": "alice", "password": PW}).status_code == 200
    assert next(iter(client.fake.by_id.values()))["failed_logins"] == 0


def test_logout_revokes_refresh_token(client):
    register(client)
    old_refresh = client.cookies.get("refresh_token")
    assert client.post("/api/auth/refresh").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set("refresh_token", old_refresh, path="/api/auth")
    assert client.post("/api/auth/refresh").status_code == 401  # revoked server-side
