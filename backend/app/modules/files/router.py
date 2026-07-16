from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.repositories.mock_data import PROJECT_FILES, PROJECT_GCODE_FILES, PROJECTS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import FileUploadRead
from backend.app.services.storage import get_storage_service

router = APIRouter(prefix="/projects/{project_id}/files", tags=["files"])


def safe_filename(filename: str) -> str:
    return Path(filename).name.replace("\\", "_").replace("/", "_")


def ensure_project_exists(project_id: str) -> None:
    if not any(project.id == project_id for project in PROJECTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


def to_file_read(project_id: str, path: Path) -> FileUploadRead:
    return FileUploadRead(
        project_id=project_id,
        filename=path.name,
        content_type=None,
        size_bytes=path.stat().st_size,
        status="accepted",
        file_url=f"/api/v1/projects/{project_id}/files/{path.name}",
    )


def to_gcode_read(project_id: str, path: Path) -> FileUploadRead:
    return FileUploadRead(
        project_id=project_id,
        filename=path.name,
        content_type="text/plain",
        size_bytes=path.stat().st_size,
        status="accepted",
        file_url=f"/api/v1/projects/{project_id}/files/gcodes/{path.name}",
    )


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
    storage.set_latest_input_file(_current_user.id, project_id, filename)
    PROJECT_FILES[project_id] = str(target_path)

    for project in PROJECTS:
        if project.id == project_id:
            project.model_file = filename

    return to_file_read(project_id, target_path)


@router.get("")
def list_project_files(
    project_id: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> list[FileUploadRead]:
    ensure_project_exists(project_id)
    storage = get_storage_service()
    files = storage.list_input_files(current_user.id, project_id)
    latest = storage.latest_input_file(current_user.id, project_id)
    if latest is not None:
        files = [latest, *(path for path in files if path != latest)]
    return [to_file_read(project_id, path) for path in files]


@router.get("/latest")
def read_latest_project_file(
    project_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> FileUploadRead:
    ensure_project_exists(project_id)
    storage = get_storage_service()
    path = storage.latest_input_file(_current_user.id, project_id)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project file not found")
    PROJECT_FILES[project_id] = str(path)
    return to_file_read(project_id, path)


@router.get("/gcodes")
def list_project_gcode_files(
    project_id: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> list[FileUploadRead]:
    ensure_project_exists(project_id)
    files = get_storage_service().list_output_files(current_user.id, project_id)
    return [to_gcode_read(project_id, path) for path in files]


@router.get("/gcodes/{filename}")
def download_project_gcode_file(
    project_id: str,
    filename: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> FileResponse:
    ensure_project_exists(project_id)
    path = get_storage_service().find_output_file(
        current_user.id,
        project_id,
        safe_filename(filename),
    )
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="G-code file not found")
    return FileResponse(path, media_type="text/plain", filename=path.name)


@router.delete("/gcodes/{filename}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_gcode_file(
    project_id: str,
    filename: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> Response:
    ensure_project_exists(project_id)
    storage = get_storage_service()
    path = storage.find_output_file(current_user.id, project_id, safe_filename(filename))
    if path is None or not storage.delete_output_file(current_user.id, project_id, path.name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="G-code file not found")

    for task_id, file_path in list(PROJECT_GCODE_FILES.items()):
        if Path(file_path) == path:
            del PROJECT_GCODE_FILES[task_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{filename}")
def download_project_file(
    project_id: str,
    filename: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> FileResponse:
    ensure_project_exists(project_id)
    path = get_storage_service().find_input_file(
        _current_user.id,
        project_id,
        safe_filename(filename),
    )
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project file not found")

    return FileResponse(path)


@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_file(
    project_id: str,
    filename: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> Response:
    ensure_project_exists(project_id)
    storage = get_storage_service()
    path = storage.find_input_file(current_user.id, project_id, safe_filename(filename))
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project file not found")

    next_file = storage.delete_input_file(current_user.id, project_id, path.name)
    if next_file is None:
        PROJECT_FILES.pop(project_id, None)
    else:
        PROJECT_FILES[project_id] = str(next_file)

    for project in PROJECTS:
        if project.id == project_id:
            project.model_file = next_file.name if next_file is not None else ""
    return Response(status_code=status.HTTP_204_NO_CONTENT)
