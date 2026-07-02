from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.modules.auth.dependencies import require_admin
from backend.app.repositories.mock_data import PROJECTS, TASKS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import AdminSummaryRead, AdminUserRead, TaskRead

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_USERS = [
    AdminUserRead(
        username="machuang",
        role="admin",
        status="active",
        last_active="2026-07-03 10:48",
    ),
    AdminUserRead(
        username="researcher",
        role="user",
        status="active",
        last_active="2026-07-02 21:18",
    ),
]


@router.get("/summary")
def read_admin_summary(
    _current_user: Annotated[UserRead, Depends(require_admin)],
) -> AdminSummaryRead:
    return AdminSummaryRead(users=2, projects=len(PROJECTS), tasks=len(TASKS))


@router.get("/tasks")
def list_admin_tasks(_current_user: Annotated[UserRead, Depends(require_admin)]) -> list[TaskRead]:
    return TASKS


@router.get("/users")
def list_admin_users(
    _current_user: Annotated[UserRead, Depends(require_admin)],
) -> list[AdminUserRead]:
    return ADMIN_USERS
