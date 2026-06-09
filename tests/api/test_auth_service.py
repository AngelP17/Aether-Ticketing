import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from apps.api.config import settings, validate_production_settings
from apps.api.main import app
from apps.api.services import auth_service as auth_module
from apps.api.services.auth_service import AuthService, login_rate_limiter, pwd_context


@pytest.fixture()
def users_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    path = tmp_path / "users.json"
    path.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": "admin",
                        "password_hash": pwd_context.hash("password"),
                        "role": "admin",
                        "display_name": "Admin User",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(auth_module, "USERS_FILE_LOCATIONS", [path])
    login_rate_limiter.clear()
    return path


def test_valid_bcrypt_login(users_file: Path) -> None:
    payload = AuthService().login("admin", "password")

    assert payload is not None
    assert payload["user"]["username"] == "admin"
    assert payload["access_token"]


def test_login_trims_username(users_file: Path) -> None:
    payload = AuthService().login("  admin  ", "password")

    assert payload is not None
    assert payload["user"]["username"] == "admin"


def test_bad_password_rejected(users_file: Path) -> None:
    assert AuthService().login("admin", "wrong-password") is None


def test_legacy_sha256_hash_migrates_after_successful_login(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    path = tmp_path / "users.json"
    legacy_hash = hashlib.sha256("password".encode()).hexdigest()
    path.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": "admin",
                        "password_hash": legacy_hash,
                        "role": "admin",
                        "display_name": "Admin User",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(auth_module, "USERS_FILE_LOCATIONS", [path])

    payload = AuthService().login("admin", "password")
    stored_hash = json.loads(path.read_text(encoding="utf-8"))["users"][0]["password_hash"]

    assert payload is not None
    assert stored_hash != legacy_hash
    assert pwd_context.verify("password", stored_hash)


def test_password_change_rehashes(users_file: Path) -> None:
    AuthService().change_password("admin", "password", "new-password")
    stored_hash = json.loads(users_file.read_text(encoding="utf-8"))["users"][0]["password_hash"]

    assert pwd_context.verify("new-password", stored_hash)
    assert not stored_hash.endswith(hashlib.sha256("new-password".encode()).hexdigest())


def test_login_rate_limit_returns_429(users_file: Path) -> None:
    client = TestClient(app)

    for _ in range(5):
        response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
        assert response.status_code == 401

    limited = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})

    assert limited.status_code == 429


def test_successful_login_resets_rate_limit(users_file: Path) -> None:
    client = TestClient(app)

    for _ in range(3):
        response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
        assert response.status_code == 401

    success = client.post("/api/auth/login", json={"username": "admin", "password": "password"})
    next_failure = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})

    assert success.status_code == 200
    assert next_failure.status_code == 401


def test_production_validation_rejects_default_secret(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "change-me-in-production")
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "https://example.com")

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings()


def test_production_validation_rejects_wildcard_cors(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "not-default")
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "https://example.com,*")

    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS"):
        validate_production_settings()
