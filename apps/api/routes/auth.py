from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from apps.api.schemas.management import (
    ChangePasswordRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from apps.api.security import get_current_user, require_admin
from apps.api.services.auth_service import AuthService

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    payload = AuthService().login(body.username, body.password)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return payload


@router.post("/logout")
def logout():
    return {"status": "success"}


@router.get("/me")
def get_me(authorization: str | None = Header(default=None)):
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.replace("Bearer ", "", 1)
    user = AuthService().current_user(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.get("/users")
def list_users(_: dict = Depends(require_admin)):
    return AuthService().list_users()


@router.post("/users", status_code=201)
def create_user(body: UserCreateRequest, _: dict = Depends(require_admin)):
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
def update_user(username: str, body: UserUpdateRequest, _: dict = Depends(require_admin)):
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
def delete_user(username: str, _: dict = Depends(require_admin)):
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
    current_user: dict = Depends(get_current_user),
):
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
