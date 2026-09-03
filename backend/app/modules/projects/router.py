import json
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.modules.auth.dependencies import get_current_user
from backend.app.repositories.mock_data import PROJECTS, TASKS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import (
    DashboardStatsRead,
    ProjectCreateRequest,
    ProjectRead,
    ProjectUpdateRequest,
    TaskRead,
)
from backend.app.services.storage import get_storage_service

router = APIRouter(prefix="/projects", tags=["projects"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _tasks_for_project(project_id: str) -> list[TaskRead]:
    return [task for task in TASKS if task.project_id == project_id]


def _metadata_file(project_id: str, user_id: str) -> Path:
    return get_storage_service().project_dir(user_id, project_id) / "project.json"


def _read_project_metadata(project_id: str, user_id: str) -> dict[str, str]:
    path = _metadata_file(project_id, user_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _persist_project_metadata(project: ProjectRead, user_id: str) -> None:
    path = _metadata_file(project.id, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "name": project.name,
                "material": project.material,
                "updated_at": project.updated_at,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _derive_project_status(project_id: str, user_id: str) -> str:
    tasks = _tasks_for_project(project_id)
    if any(task.status == "failed" for task in tasks):
        return "failed"
    if any(task.status == "running" for task in tasks):
        return "running"
    if any(task.status == "queued" for task in tasks):
        return "queued"
    if any(task.status == "completed" for task in tasks):
        return "completed"

    storage = get_storage_service()
    if storage.list_output_files(user_id, project_id):
        return "completed"
    return "queued"


def _project_for_user(project: ProjectRead, user: UserRead) -> ProjectRead:
    latest_file = get_storage_service().latest_input_file(user.id, project.id)
    metadata = _read_project_metadata(project.id, user.id)
    return project.model_copy(
        update={
            "name": metadata.get("name", project.name),
            "material": metadata.get("material", project.material),
            "updated_at": metadata.get("updated_at", project.updated_at),
            "model_file": latest_file.name if latest_file is not None else "",
            "status": _derive_project_status(project.id, user.id),
        }
    )


@dashboard_router.get("/stats")
def read_dashboard_stats(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> DashboardStatsRead:
    storage = get_storage_service()
    storage_gb = 0.0
    for project in PROJECTS:
        project_dir = storage.project_dir(current_user.id, project.id)
        if project_dir.exists():
            storage_gb += sum(
                path.stat().st_size
                for path in project_dir.rglob("*")
                if path.is_file()
            ) / 1024**3

    return DashboardStatsRead(
        projects=len(PROJECTS),
        running_tasks=sum(task.status in {"queued", "running"} for task in TASKS),
        completed_tasks=sum(task.status == "completed" for task in TASKS),
        storage_gb=round(storage_gb, 3),
    )


@router.get("")
def list_projects(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> list[ProjectRead]:
    return [_project_for_user(project, current_user) for project in PROJECTS]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ProjectRead:
    numeric_ids = [
        int(project.id.removeprefix("p-"))
        for project in PROJECTS
        if project.id.removeprefix("p-").isdigit()
    ]
    project_id = f"p-{max(numeric_ids, default=1000) + 1}"
    project = ProjectRead(
        id=project_id,
        name=payload.name,
        owner=current_user.username,
        material=payload.material,
        model_file="",
        updated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        status="queued",
    )
    PROJECTS.append(project)
    _persist_project_metadata(project, current_user.id)
    return project


@router.get("/{project_id}")
def read_project(
    project_id: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ProjectRead:
    for project in PROJECTS:
        if project.id == project_id:
            return _project_for_user(project, current_user)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ProjectRead:
    for index, project in enumerate(PROJECTS):
        if project.id == project_id:
            updated_project = project.model_copy(
                update={
                    "name": payload.name,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )
            PROJECTS[index] = updated_project
            _persist_project_metadata(updated_project, current_user.id)
            return _project_for_user(updated_project, current_user)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.get("/{project_id}/tasks")
def list_project_tasks(
    project_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> list[TaskRead]:
    if not any(project.id == project_id for project in PROJECTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return _tasks_for_project(project_id)
