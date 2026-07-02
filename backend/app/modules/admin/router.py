from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.modules.auth.dependencies import require_admin
from backend.app.repositories.mock_data import PROJECTS, TASKS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import AdminSummaryRead, TaskRead

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/summary")
def read_admin_summary(
    _current_user: Annotated[UserRead, Depends(require_admin)],
) -> AdminSummaryRead:
    return AdminSummaryRead(users=2, projects=len(PROJECTS), tasks=len(TASKS))


@router.get("/tasks")
def list_admin_tasks(_current_user: Annotated[UserRead, Depends(require_admin)]) -> list[TaskRead]:
    return TASKS
