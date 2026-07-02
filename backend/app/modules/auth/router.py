from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.modules.auth.dependencies import build_mock_token, get_current_user
from backend.app.schemas.auth import LoginRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest) -> TokenResponse:
    username = payload.username.strip()
    user = UserRead(
        id="admin-001" if payload.role == "admin" else "user-001",
        username=username,
        role=payload.role,
    )

    return TokenResponse(access_token=build_mock_token(username, payload.role), user=user)


@router.get("/me")
def read_me(current_user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
    return current_user
