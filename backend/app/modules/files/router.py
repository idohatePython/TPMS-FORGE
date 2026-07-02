from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.core.config import settings
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.repositories.mock_data import PROJECTS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import FileUploadRead

router = APIRouter(prefix="/projects/{project_id}/files", tags=["files"])


@router.post("")
def upload_project_file(
    project_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
) -> FileUploadRead:
    if not any(project.id == project_id for project in PROJECTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    filename = file.filename
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

    return FileUploadRead(
        project_id=project_id,
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(content),
        status="accepted",
    )
