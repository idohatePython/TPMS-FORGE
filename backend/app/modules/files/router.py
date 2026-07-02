from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.repositories.mock_data import PROJECT_FILES, PROJECTS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import FileUploadRead
from backend.app.services.storage import get_storage_service

router = APIRouter(prefix="/projects/{project_id}/files", tags=["files"])


def safe_filename(filename: str) -> str:
    return Path(filename).name.replace("\\", "_").replace("/", "_")


def ensure_project_exists(project_id: str) -> None:
    if not any(project.id == project_id for project in PROJECTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post("")
def upload_project_file(
    project_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
) -> FileUploadRead:
    ensure_project_exists(project_id)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    filename = safe_filename(file.filename)
    suffix = filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""
    if suffix not in {"stl", "obj"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only STL and OBJ files are accepted",
        )

    content = file.file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds configured upload limit",
        )

    storage = get_storage_service()
    target_path = storage.input_dir(_current_user.id, project_id) / filename
    target_path.write_bytes(content)
    PROJECT_FILES[project_id] = str(target_path)

    for project in PROJECTS:
        if project.id == project_id:
            project.model_file = filename

    return FileUploadRead(
        project_id=project_id,
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(content),
        status="accepted",
        file_url=f"/api/v1/projects/{project_id}/files/{filename}",
    )


@router.get("/latest")
def read_latest_project_file(
    project_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> FileUploadRead:
    ensure_project_exists(project_id)
    file_path = PROJECT_FILES.get(project_id)

    if file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project file not found")

    path = Path(file_path)
    return FileUploadRead(
        project_id=project_id,
        filename=path.name,
        content_type=None,
        size_bytes=path.stat().st_size,
        status="accepted",
        file_url=f"/api/v1/projects/{project_id}/files/{path.name}",
    )


@router.get("/{filename}")
def download_project_file(
    project_id: str,
    filename: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> FileResponse:
    ensure_project_exists(project_id)
    file_path = PROJECT_FILES.get(project_id)

    if file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project file not found")

    path = Path(file_path)
    if path.name != safe_filename(filename) or not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project file not found")

    return FileResponse(path)
