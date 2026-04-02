from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

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
