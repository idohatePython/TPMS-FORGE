from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.schemas.auth import UserRead, UserRole

security = HTTPBearer(auto_error=False)


def build_mock_token(username: str, role: str) -> str:
    return f"mock:{role}:{username}"


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> UserRead:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    parts = credentials.credentials.split(":", maxsplit=2)
    if len(parts) != 3 or parts[0] != "mock" or parts[1] not in {"user", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    role: UserRole = "admin" if parts[1] == "admin" else "user"

    return UserRead(
        id="admin-001" if role == "admin" else "user-001",
        username=parts[2],
        role=role,
    )


def require_admin(current_user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
