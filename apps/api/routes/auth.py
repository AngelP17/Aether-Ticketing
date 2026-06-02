from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from apps.api.schemas.management import (
    ChangePasswordRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from apps.api.security import get_current_user, require_admin
from apps.api.services.auth_service import AuthService as AuthService, login_rate_limiter as login_rate_limiter

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request) -> dict[str, Any]:
    client_id = request.client.host if request.client else "unknown"
    if login_rate_limiter.is_limited(body.username, client_id):
        raise HTTPException(status_code=429, detail="Too many failed login attempts")

    payload = AuthService().login(body.username, body.password)
    if payload is None:
        login_rate_limiter.record_failure(body.username, client_id)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    login_rate_limiter.reset(body.username, client_id)
    return payload


@router.post("/logout")
def logout() -> dict[str, Any]:
    return {"status": "success", "message": "Client session cleared; token remains valid until expiry"}


@router.get("/me")
def get_me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.replace("Bearer ", "", 1)
    user = AuthService().current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.get("/users")
def list_users(_: dict[str, Any] = Depends(require_admin)) -> list[dict[str, Any]]:
    return AuthService().list_users()


@router.post("/users", status_code=201)
def create_user(
    body: UserCreateRequest,
    _: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    try:
        return AuthService().create_user(
            username=body.username,
            password=body.password,
            role=body.role,
            display_name=body.display_name,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/users/{username}")
def update_user(
    username: str,
    body: UserUpdateRequest,
    _: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    user = AuthService().update_user(
        username=username,
        password=body.password,
        role=body.role,
        display_name=body.display_name,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/users/{username}")
def delete_user(username: str, _: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    try:
        deleted = AuthService().delete_user(username)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        AuthService().change_password(
            username=current_user["username"],
            current_password=body.current_password,
            new_password=body.new_password,
        )
    except PermissionError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"status": "success"}
