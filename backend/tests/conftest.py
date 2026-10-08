import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Settings are read at import time: set test config before importing the app.
os.environ.update({"APP_ENV": "local", "SECRETS_BACKEND": "env", "SECRET_KEY": "t" * 48,
                   "ALLOW_REGISTRATION": "true"})
for k in ("REQUIRE_AUTH_FOR_READS", "DYNAMODB_ENDPOINT_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class FakeUsers:
    """In-memory stand-in for the DynamoDB user helpers (no AWS/LocalStack needed)."""

    def __init__(self):
        self.by_id: dict[str, dict] = {}

    async def create_user(self, username, hashed_password):
        u = {"user_id": str(uuid.uuid4()), "username": username, "hashed_password": hashed_password,
             "created_at": datetime.now(timezone.utc).isoformat()}
        self.by_id[u["user_id"]] = u
        return u

    async def get_user_by_username(self, username):
        return next((u for u in self.by_id.values() if u["username"] == username), None)

    async def get_user_by_id(self, user_id):
        return self.by_id.get(user_id)

    async def record_login_failure(self, user_id, max_failures, lockout_until_iso):
        u = self.by_id[user_id]
        u["failed_logins"] = u.get("failed_logins", 0) + 1
        if u["failed_logins"] >= max_failures:
            u["locked_until"], u["failed_logins"] = lockout_until_iso, 0
        return u

    async def reset_login_failures(self, user_id):
        u = self.by_id[user_id]
        u["failed_logins"] = 0
        u.pop("locked_until", None)

    async def bump_token_version(self, user_id):
        u = self.by_id[user_id]
        u["token_version"] = u.get("token_version", 0) + 1


@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.repositories import dynamo

    fake = FakeUsers()
    for name in ("create_user", "get_user_by_username", "get_user_by_id", "record_login_failure",
                 "reset_login_failures", "bump_token_version"):
        monkeypatch.setattr(dynamo, name, getattr(fake, name))
    c = TestClient(app, base_url="https://testserver")
    c.fake = fake
    return c
