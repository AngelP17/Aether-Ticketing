from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from apps.api.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 8
USERS_FILE_LOCATIONS = [
    "/Users/apinzon/Desktop/Active Projects/ticketing/users.json",
    ".env/users.json",
    "/etc/secrets/users_data.json",
    "users.json",
]


class AuthService:
    def login(self, username: str, password: str) -> dict[str, Any] | None:
        user = self._get_user(username)
        if user is None:
            return None
        if not self._verify_password(password, user["password_hash"]):
            return None

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

    def _load_users(self) -> list[dict[str, Any]]:
        for path in USERS_FILE_LOCATIONS:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data.get("users", [])
        return []

    def _verify_password(self, password: str, password_hash: str) -> bool:
        return hashlib.sha256(password.encode()).hexdigest() == password_hash
