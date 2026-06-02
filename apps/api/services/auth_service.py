from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Protocol, cast

import redis
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from redis import Redis

from apps.api.config import settings

__all__ = [
    "ALGORITHM",
    "ACCESS_TOKEN_MINUTES",
    "AuthService",
    "InMemoryLoginRateLimiter",
    "LOGIN_RATE_LIMIT_ATTEMPTS",
    "LOGIN_RATE_LIMIT_KEY_PREFIX",
    "LOGIN_RATE_LIMIT_WINDOW_SECONDS",
    "PROJECT_ROOT",
    "RedisLoginRateLimiter",
    "build_login_rate_limiter",
    "redis",
    "settings",
]

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 8
LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 15 * 60
LOGIN_RATE_LIMIT_KEY_PREFIX = "login_failures:"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
VALID_ROLES = {"admin", "agent", "viewer"}
USERS_FILE_LOCATIONS = [
    Path(settings.USERS_FILE).expanduser() if settings.USERS_FILE else None,
    PROJECT_ROOT / ".env" / "users.json",
    Path("/etc/secrets/users_data.json"),
    PROJECT_ROOT / "users.json",
    Path("users.json"),
]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)


class LoginRateLimiter(Protocol):
    def is_limited(self, username: str, client_id: str) -> bool: ...

    def record_failure(self, username: str, client_id: str) -> None: ...

    def reset(self, username: str, client_id: str) -> None: ...

    def clear(self) -> None: ...


class InMemoryLoginRateLimiter:
    def __init__(self) -> None:
        self._failures: defaultdict[tuple[str, str], deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def is_limited(self, username: str, client_id: str) -> bool:
        key = self._key(username, client_id)
        now = datetime.now(timezone.utc)
        with self._lock:
            self._prune(key, now)
            return len(self._failures[key]) >= LOGIN_RATE_LIMIT_ATTEMPTS

    def record_failure(self, username: str, client_id: str) -> None:
        key = self._key(username, client_id)
        now = datetime.now(timezone.utc)
        with self._lock:
            self._prune(key, now)
            self._failures[key].append(now)

    def reset(self, username: str, client_id: str) -> None:
        with self._lock:
            self._failures.pop(self._key(username, client_id), None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()

    def _key(self, username: str, client_id: str) -> tuple[str, str]:
        return (username.strip().lower(), client_id)

    def _prune(self, key: tuple[str, str], now: datetime) -> None:
        cutoff = now.timestamp() - LOGIN_RATE_LIMIT_WINDOW_SECONDS
        failures = self._failures[key]
        while failures and failures[0].timestamp() < cutoff:
            failures.popleft()


class RedisLoginRateLimiter:
    def __init__(self, client: Redis) -> None:
        self._client = client

    def is_limited(self, username: str, client_id: str) -> bool:
        value = self._client.get(self._key(username, client_id))
        if value is None:
            return False
        try:
            return int(value) >= LOGIN_RATE_LIMIT_ATTEMPTS
        except (TypeError, ValueError):
            return False

    def record_failure(self, username: str, client_id: str) -> None:
        key = self._key(username, client_id)
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, LOGIN_RATE_LIMIT_WINDOW_SECONDS)
        pipe.execute()

    def reset(self, username: str, client_id: str) -> None:
        self._client.delete(self._key(username, client_id))

    def clear(self) -> None:
        cursor = 0
        pattern = f"{LOGIN_RATE_LIMIT_KEY_PREFIX}*"
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                self._client.delete(*keys)
            if cursor == 0:
                return

    def _key(self, username: str, client_id: str) -> str:
        return f"{LOGIN_RATE_LIMIT_KEY_PREFIX}{username.strip().lower()}:{client_id}"


def build_login_rate_limiter() -> LoginRateLimiter:
    backend = settings.RATE_LIMIT_BACKEND.lower()
    if backend == "redis":
        if not settings.REDIS_URL:
            logger.warning(
                "RATE_LIMIT_BACKEND=redis but REDIS_URL is unset; falling back to in-memory limiter"
            )
            return InMemoryLoginRateLimiter()
        try:
            client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            client.ping()
        except redis.RedisError as exc:
            logger.warning(
                "Redis rate limiter unavailable (%s); falling back to in-memory limiter", exc
            )
            return InMemoryLoginRateLimiter()
        return RedisLoginRateLimiter(client)
    return InMemoryLoginRateLimiter()


login_rate_limiter: LoginRateLimiter = build_login_rate_limiter()


class AuthService:
    def login(self, username: str, password: str) -> dict[str, Any] | None:
        user = self._get_user(username)
        if user is None:
            return None
        verified, needs_migration = self._verify_password(password, user["password_hash"])
        if not verified:
            return None
        if needs_migration:
            self.update_user(username=user["username"], password=password)

        public_user = {
            "username": user["username"],
            "role": user["role"],
            "display_name": user["display_name"],
        }
        return {
            "access_token": self._create_token(public_user),
            "token_type": "bearer",
            "user": public_user,
        }

    def current_user(self, token: str) -> dict[str, Any] | None:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            return None
        username = payload.get("sub")
        if not username:
            return None
        user = self._get_user(username)
        if user is None:
            return None
        return {
            "username": user["username"],
            "role": user["role"],
            "display_name": user["display_name"],
        }

    def list_users(self) -> list[dict[str, Any]]:
        return [self._public_user(user) for user in self._load_users()]

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        display_name: str | None,
    ) -> dict[str, Any]:
        normalized_username = username.strip()
        normalized_role = role if role in VALID_ROLES else "viewer"
        if not normalized_username or not password:
            raise ValueError("Username and password required")
        if self._get_user(normalized_username) is not None:
            raise ValueError("Username already exists")

        users = self._load_users()
        user = {
            "username": normalized_username,
            "password_hash": self._hash_password(password),
            "role": normalized_role,
            "display_name": (display_name or normalized_username).strip(),
        }
        users.append(user)
        self._save_users(users)
        return self._public_user(user)

    def update_user(
        self,
        username: str,
        password: str | None = None,
        role: str | None = None,
        display_name: str | None = None,
    ) -> dict[str, Any] | None:
        users = self._load_users()
        for user in users:
            if user["username"] != username:
                continue
            if role is not None:
                user["role"] = role if role in VALID_ROLES else user["role"]
            if display_name is not None and display_name.strip():
                user["display_name"] = display_name.strip()
            if password:
                user["password_hash"] = self._hash_password(password)
            self._save_users(users)
            return self._public_user(user)
        return None

    def delete_user(self, username: str) -> bool:
        if username == "admin":
            raise ValueError("Cannot delete admin user")
        users = self._load_users()
        remaining_users = [user for user in users if user["username"] != username]
        if len(remaining_users) == len(users):
            return False
        self._save_users(remaining_users)
        return True

    def change_password(self, username: str, current_password: str, new_password: str) -> None:
        if not new_password:
            raise ValueError("New password required")
        users = self._load_users()
        for user in users:
            if user["username"] != username:
                continue
            verified, _ = self._verify_password(current_password, user["password_hash"])
            if not verified:
                raise PermissionError("Current password incorrect")
            user["password_hash"] = self._hash_password(new_password)
            self._save_users(users)
            return
        raise LookupError("User not found")

    def _create_token(self, user: dict[str, Any]) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_MINUTES)
        payload = {
            "sub": user["username"],
            "role": user["role"],
            "display_name": user["display_name"],
            "exp": expires_at,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

    def _get_user(self, username: str) -> dict[str, Any] | None:
        for user in self._load_users():
            if user["username"] == username:
                return user
        return None

    def _public_user(self, user: dict[str, Any]) -> dict[str, Any]:
        return {
            "username": user["username"],
            "role": user.get("role", "viewer"),
            "display_name": user.get("display_name", user["username"]),
        }

    def _load_users(self) -> list[dict[str, Any]]:
        for path in USERS_FILE_LOCATIONS:
            if path is None or not path.exists():
                continue
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            return cast(list[dict[str, Any]], data.get("users", []))
        return []

    def _save_users(self, users: list[dict[str, Any]]) -> None:
        destination = self._resolve_users_file()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps({"users": users}, indent=2), encoding="utf-8")

    def _resolve_users_file(self) -> Path:
        for path in USERS_FILE_LOCATIONS:
            if path is not None and path.exists():
                return path
        for path in USERS_FILE_LOCATIONS:
            if path is not None:
                return path
        return PROJECT_ROOT / "users.json"

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, password: str, password_hash: str) -> tuple[bool, bool]:
        if self._is_legacy_sha256_hash(password_hash):
            return hashlib.sha256(password.encode()).hexdigest() == password_hash, True
        try:
            return pwd_context.verify(password, password_hash), False
        except UnknownHashError:
            return False, False

    def _is_legacy_sha256_hash(self, password_hash: str) -> bool:
        return len(password_hash) == 64 and all(char in "0123456789abcdef" for char in password_hash)
