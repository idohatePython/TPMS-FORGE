from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.modules.auth.dependencies import get_current_user
from backend.app.repositories.mock_data import DASHBOARD_STATS, PROJECTS, TASKS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import DashboardStatsRead, ProjectRead, TaskRead

router = APIRouter(prefix="/projects", tags=["projects"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("/stats")
def read_dashboard_stats(
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> DashboardStatsRead:
    return DASHBOARD_STATS


@router.get("")
def list_projects(
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> list[ProjectRead]:
    return PROJECTS


@router.get("/{project_id}")
def read_project(
    project_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ProjectRead:
    for project in PROJECTS:
        if project.id == project_id:
            return project

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.get("/{project_id}/tasks")
def list_project_tasks(
    project_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> list[TaskRead]:
    if not any(project.id == project_id for project in PROJECTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return [task for task in TASKS if task.project_id == project_id]
