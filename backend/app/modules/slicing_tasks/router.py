from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from algorithms.pipeline.slicing_gcode import (
    SlicerExecutionError,
    SlicerUnavailableError,
    SlicingGcodeInput,
    run_slicing_gcode,
)
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.repositories.mock_data import PROJECT_FILES, PROJECT_GCODE_FILES, PROJECTS, TASKS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import SlicingRequest, SlicingRunRead, TaskRead
from backend.app.services.storage import get_storage_service

router = APIRouter(prefix="/slicing-tasks", tags=["slicing-tasks"])
project_router = APIRouter(prefix="/projects/{project_id}/slicing-tasks", tags=["slicing-tasks"])


@router.get("/{task_id}")
def read_slicing_task(
    task_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> TaskRead:
    for task in TASKS:
        if task.id == task_id and task.type == "slicing-gcode":
            return task

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slicing task not found")


@project_router.post("")
def create_slicing_task(
    project_id: str,
    payload: SlicingRequest,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> SlicingRunRead:
    if not any(project.id == project_id for project in PROJECTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    input_file = PROJECT_FILES.get(project_id)
    if input_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload an STL/OBJ model before slicing.",
        )

    output_dir = get_storage_service().output_dir(current_user.id, project_id)

    try:
        result = run_slicing_gcode(
            SlicingGcodeInput(
                input_file=Path(input_file),
                output_dir=output_dir,
                params={
                    "layer_height": payload.layer_height,
                    "line_width": payload.line_width,
                    "print_speed": payload.print_speed,
                },
            )
        )
    except SlicerUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except SlicerExecutionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    task = TaskRead(
        id=f"sg-{len(TASKS) + 1025}",
        project_id=project_id,
        name=f"{payload.layer_height}mm 层高 G-code",
        type="slicing-gcode",
        status="completed",
        progress=100,
        updated_at="2026-07-03 12:00",
    )
    TASKS.append(task)
    PROJECT_GCODE_FILES[task.id] = str(result.gcode_file)

    return SlicingRunRead(
        task=task,
        gcode_filename=result.gcode_file.name,
        gcode_url=f"/api/v1/slicing-tasks/{task.id}/gcode",
    )


@router.get("/{task_id}/gcode")
def download_gcode(
    task_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> FileResponse:
    file_path = PROJECT_GCODE_FILES.get(task_id)
    if file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="G-code file not found")

    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="G-code file not found")

    return FileResponse(path, media_type="text/plain", filename=path.name)
