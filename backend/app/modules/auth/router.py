from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.modules.auth.dependencies import build_mock_token, get_current_user
from backend.app.schemas.auth import LoginRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest) -> TokenResponse:
    identifier = payload.identifier.strip().casefold()

    if identifier in {"researcher", "researcher@tpms-forge.local"}:
        expected_password = "dev-only"
        user = UserRead(
            id="user-001",
            username="researcher",
            role="user",
        )
    elif identifier in {"admin", "admin@tpms-forge.local"}:
        expected_password = "admin-only"
        user = UserRead(
            id="admin-001",
            username="admin",
            role="admin",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
        )

    if not compare_digest(payload.password, expected_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
        )

    return TokenResponse(
        access_token=build_mock_token(user.username, user.role),
        user=user,
    )


@router.get("/me")
def read_me(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> UserRead:
    return current_user