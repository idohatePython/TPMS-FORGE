from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from algorithms.pipeline.slicing_gcode import (
    SlicerExecutionError,
    SlicerUnavailableError,
    SlicingGcodeInput,
    resolve_configured_slicer_binary,
    run_slicing_gcode,
)
from backend.app.core.config import settings
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.model_tasks.router import create_model_task
from backend.app.repositories.mock_data import (
    PROJECT_FILES,
    PROJECT_GCODE_FILES,
    PROJECT_MODEL_TASK_FILES,
    PROJECTS,
    TASKS,
)
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import (
    ModelGenerationRequest,
    SlicerStatusRead,
    SlicingRequest,
    SlicingRunRead,
    TaskRead,
)
from backend.app.services.storage import get_storage_service

router = APIRouter(prefix="/slicing-tasks", tags=["slicing-tasks"])
project_router = APIRouter(prefix="/projects/{project_id}/slicing-tasks", tags=["slicing-tasks"])


@router.get("/engine/status")
def read_slicer_status(
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> SlicerStatusRead:
    try:
        executable = resolve_configured_slicer_binary()
    except SlicerUnavailableError as error:
        return SlicerStatusRead(
            engine=settings.slicer_engine,
            available=False,
            executable=None,
            message=str(error),
        )

    return SlicerStatusRead(
        engine=settings.slicer_engine,
        available=True,
        executable=executable,
        message="Slicer executable found.",
    )


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

    storage = get_storage_service()
    if payload.input_filename:
        input_path = storage.find_model_file(current_user.id, project_id, payload.input_filename)
    else:
        input_path = storage.latest_input_file(current_user.id, project_id)

    if input_path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload an STL/OBJ model before slicing.",
        )

    workflow_task: TaskRead | None = None
    intermediate_filename: str | None = None
    intermediate_url: str | None = None

    input_is_generated_tpms = input_path.parent.name == "generated"

    if payload.infill_mode == "tpms" and input_is_generated_tpms:
        workflow_task = TaskRead(
            id=f"wf-{len(TASKS) + 4096}",
            project_id=project_id,
            name=f"已有 TPMS 模型切片 · {input_path.name}",
            type="slicing-gcode",
            status="running",
            progress=60,
            updated_at="2026-08-23 12:00",
            stage="gcode-slicing",
            input_filename=input_path.name,
            intermediate_filename=input_path.name,
        )
        TASKS.append(workflow_task)
        intermediate_filename = input_path.name
        PROJECT_MODEL_TASK_FILES[workflow_task.id] = str(input_path)
    elif payload.infill_mode == "tpms":
        workflow_task = TaskRead(
            id=f"wf-{len(TASKS) + 4096}",
            project_id=project_id,
            name=f"{payload.tpms_type} TPMS 梯度填充与切片",
            type="slicing-gcode",
            status="running",
            progress=10,
            updated_at="2026-08-23 12:00",
            stage="tpms-generation",
            input_filename=input_path.name,
        )
        TASKS.append(workflow_task)
        gradient_is_thickness = payload.tpms_gradient_target == "thickness"
        try:
            generation = create_model_task(
                project_id,
                ModelGenerationRequest(
                    generation_domain="boundary",
                    boundary_mode="auto",
                    tpms_type=payload.tpms_type,
                    structure_type=payload.tpms_structure_type,
                    cell_size=payload.tpms_cell_size,
                    cell_size_x=payload.tpms_cell_size,
                    cell_size_y=payload.tpms_cell_size,
                    cell_size_z=payload.tpms_cell_size,
                    wall_thickness_mm=payload.tpms_wall_thickness_mm,
                    level_set_offset=payload.tpms_level_set_offset,
                    phase_shift_x=payload.tpms_phase_x,
                    phase_shift_y=payload.tpms_phase_y,
                    phase_shift_z=payload.tpms_phase_z,
                    density_gradient_mode="none" if gradient_is_thickness else "linear",
                    density_gradient_axis=payload.tpms_gradient_axis,
                    density_gradient_start_offset=payload.tpms_gradient_start if not gradient_is_thickness else 0,
                    density_gradient_end_offset=payload.tpms_gradient_end if not gradient_is_thickness else 0,
                    density_gradient_curve=payload.tpms_gradient_curve,
                    thickness_gradient_mode="linear" if gradient_is_thickness else "none",
                    thickness_gradient_axis=payload.tpms_gradient_axis,
                    thickness_gradient_start_mm=payload.tpms_gradient_start if gradient_is_thickness else payload.tpms_wall_thickness_mm,
                    thickness_gradient_end_mm=payload.tpms_gradient_end if gradient_is_thickness else payload.tpms_wall_thickness_mm,
                    thickness_gradient_curve=payload.tpms_gradient_curve,
                    invert_field=payload.tpms_invert_field,
                    quality=payload.tpms_quality,
                ),
                current_user,
            )
        except HTTPException as error:
            workflow_task.status = "failed"
            workflow_task.stage = "tpms-generation-failed"
            workflow_task.error_message = str(error.detail)
            workflow_task.progress = 0
            raise

        if generation.task in TASKS:
            TASKS.remove(generation.task)
        PROJECT_MODEL_TASK_FILES.pop(generation.task.id, None)
        intermediate_filename = generation.model_filename
        intermediate_url = generation.model_url
        input_path = storage.find_model_file(current_user.id, project_id, intermediate_filename)
        if input_path is None:
            workflow_task.status = "failed"
            workflow_task.stage = "tpms-generation-failed"
            workflow_task.error_message = "Generated TPMS model could not be reopened."
            raise HTTPException(status_code=500, detail=workflow_task.error_message)
        workflow_task.intermediate_filename = intermediate_filename
        workflow_task.stage = "gcode-slicing"
        workflow_task.progress = 60
        PROJECT_MODEL_TASK_FILES[workflow_task.id] = str(input_path)

    PROJECT_FILES[project_id] = str(input_path)
    output_dir = storage.output_dir(current_user.id, project_id)

    try:
        result = run_slicing_gcode(
            SlicingGcodeInput(
                input_file=input_path,
                output_dir=output_dir,
                params={
                    "layer_height": payload.layer_height,
                    "line_width": payload.line_width,
                    "print_speed": payload.print_speed,
                    "travel_speed": payload.travel_speed,
                    "wall_loops": payload.wall_loops,
                    "top_shell_layers": payload.top_shell_layers,
                    "bottom_shell_layers": payload.bottom_shell_layers,
                    "sparse_infill_density": payload.sparse_infill_density,
                    "sparse_infill_pattern": payload.sparse_infill_pattern,
                    "enable_support": payload.enable_support,
                    "support_type": payload.support_type,
                    "brim_width": payload.brim_width,
                    "nozzle_temperature": payload.nozzle_temperature,
                    "bed_temperature": payload.bed_temperature,
                    "filament_type": payload.filament_type,
                    "slicing_engine": payload.slicing_engine,
                },
            )
        )
    except SlicerUnavailableError as error:
        if workflow_task is not None:
            workflow_task.status = "failed"
            workflow_task.stage = "gcode-slicing-failed"
            workflow_task.error_message = str(error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except SlicerExecutionError as error:
        if workflow_task is not None:
            workflow_task.status = "failed"
            workflow_task.stage = "gcode-slicing-failed"
            workflow_task.error_message = str(error)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    task = workflow_task or TaskRead(
        id=f"sg-{len(TASKS) + 1025}", project_id=project_id,
        name=f"{payload.slicing_engine.upper()} · {payload.layer_height}mm 层高 G-code",
        type="slicing-gcode", status="completed", progress=100, updated_at="2026-08-23 12:00",
        stage="completed", input_filename=input_path.name,
    )
    if workflow_task is None:
        TASKS.append(task)
    else:
        task.status = "completed"
        task.progress = 100
        task.stage = "completed"
    task.output_filename = result.gcode_file.name
    PROJECT_GCODE_FILES[task.id] = str(result.gcode_file)

    if input_path.parent.name == "inputs":
        next_model = storage.delete_input_file(current_user.id, project_id, input_path.name)
        PROJECT_FILES.pop(project_id, None)
        if next_model is not None:
            PROJECT_FILES[project_id] = str(next_model)
        for project in PROJECTS:
            if project.id == project_id:
                project.model_file = next_model.name if next_model is not None else ""

    return SlicingRunRead(
        task=task,
        gcode_filename=result.gcode_file.name,
        gcode_url=f"/api/v1/slicing-tasks/{task.id}/gcode",
        intermediate_model_filename=intermediate_filename,
        intermediate_model_url=intermediate_url,
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
