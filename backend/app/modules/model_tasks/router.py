from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.modules.auth.dependencies import get_current_user
from backend.app.repositories.mock_data import TASKS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import TaskRead

router = APIRouter(prefix="/model-tasks", tags=["model-tasks"])


@router.get("/{task_id}")
def read_model_task(
    task_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> TaskRead:
    for task in TASKS:
        if task.id == task_id and task.type == "model-generation":
            return task

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model task not found")
