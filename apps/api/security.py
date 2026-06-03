from collections.abc import Callable

from fastapi import Header, HTTPException

from apps.api.config import settings
from apps.api.services.auth_service import AuthService


CurrentUser = dict[str, str]

SERVICE_ROLE = {"username": "service", "role": "service"}


def get_current_user(authorization: str | None = Header(default=None), x_service_token: str | None = Header(default=None)) -> CurrentUser:
    if x_service_token and x_service_token in (settings.SERVICE_TOKENS or "").split(","):
        return SERVICE_ROLE
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.replace("Bearer ", "", 1)
    user = AuthService().current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def require_roles(*roles: str) -> Callable[[str | None], CurrentUser]:
    allowed = set(roles)

    def dependency(authorization: str | None = Header(default=None)) -> CurrentUser:
        user = get_current_user(authorization)
        if user.get("role") not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return user

    return dependency


def require_ticket_write(authorization: str | None = Header(default=None)) -> CurrentUser:
    return require_roles("admin", "agent")(authorization)


def require_admin(authorization: str | None = Header(default=None)) -> CurrentUser:
    return require_roles("admin")(authorization)
