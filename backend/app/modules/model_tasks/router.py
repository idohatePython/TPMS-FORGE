from typing import Annotated

import trimesh
from fastapi import APIRouter, Depends, HTTPException, status

from algorithms.pipeline.model_generation import ModelGenerationInput, run_model_generation
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.repositories.mock_data import PROJECT_FILES, PROJECT_MODEL_TASK_FILES, PROJECTS, TASKS
from backend.app.schemas.auth import UserRead
from backend.app.schemas.projects import ModelGenerationRequest, ModelGenerationRunRead, TaskRead
from backend.app.services.storage import get_storage_service

router = APIRouter(prefix="/model-tasks", tags=["model-tasks"])
project_router = APIRouter(prefix="/projects/{project_id}/model-tasks", tags=["model-tasks"])


@router.get("/{task_id}")
def read_model_task(
    task_id: str,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
) -> TaskRead:
    for task in TASKS:
        if task.id == task_id and task.type == "model-generation":
            return task

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model task not found")


@project_router.post("")
def create_model_task(
    project_id: str,
    payload: ModelGenerationRequest,
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ModelGenerationRunRead:
    if not any(project.id == project_id for project in PROJECTS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    storage = get_storage_service()
    output_dir = storage.generated_dir(current_user.id, project_id)
    input_file = storage.latest_input_file(current_user.id, project_id)
    if payload.generation_domain == "boundary" and input_file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Boundary TPMS generation requires an uploaded STL/OBJ model.",
        )

    try:
        result = run_model_generation(
            ModelGenerationInput(
                input_file=input_file or output_dir / "project.input",
                output_dir=output_dir,
                params={
                    "generation_domain": payload.generation_domain,
                    "boundary_mode": payload.boundary_mode,
                    "tpms_type": payload.tpms_type,
                    "structure_type": payload.structure_type,
                    "cell_size": payload.cell_size,
                    "cell_size_x": payload.cell_size_x or payload.cell_size,
                    "cell_size_y": payload.cell_size_y or payload.cell_size,
                    "cell_size_z": payload.cell_size_z or payload.cell_size,
                    "nx": payload.cell_count_x,
                    "ny": payload.cell_count_y,
                    "nz": payload.cell_count_z,
                    "wall_thickness_mm": payload.wall_thickness_mm,
                    "level_set_offset": payload.level_set_offset,
                    "phase_shift_x": payload.phase_shift_x,
                    "phase_shift_y": payload.phase_shift_y,
                    "phase_shift_z": payload.phase_shift_z,
                    "gradient_axis": payload.gradient_axis,
                    "gradient_strength": payload.gradient_strength,
                    "density_gradient_mode": payload.density_gradient_mode,
                    "density_gradient_axis": payload.density_gradient_axis,
                    "density_gradient_start_offset": payload.density_gradient_start_offset,
                    "density_gradient_end_offset": payload.density_gradient_end_offset,
                    "density_gradient_curve": payload.density_gradient_curve,
                    "thickness_gradient_mode": payload.thickness_gradient_mode,
                    "thickness_gradient_axis": payload.thickness_gradient_axis,
                    "thickness_gradient_start_mm": payload.thickness_gradient_start_mm,
                    "thickness_gradient_end_mm": payload.thickness_gradient_end_mm,
                    "thickness_gradient_curve": payload.thickness_gradient_curve,
                    "density_mode": payload.density_mode,
                    "target_relative_density": payload.target_relative_density,
                    "gyroid_term_weight": payload.gyroid_term_weight,
                    "schwarz_cross_weight": payload.schwarz_cross_weight,
                    "diamond_nodal_weight": payload.diamond_nodal_weight,
                    "iwp_second_harmonic_weight": payload.iwp_second_harmonic_weight,
                    "neovius_product_weight": payload.neovius_product_weight,
                    "lidinoid_harmonic_weight": payload.lidinoid_harmonic_weight,
                    "lidinoid_bias": payload.lidinoid_bias,
                    "field_sign": -1.0 if payload.invert_field else 1.0,
                    "quality": payload.quality,
                },
            )
        )
        mesh = trimesh.load_mesh(result.output_file, process=False)
    except (OSError, RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    storage.set_latest_input_file(current_user.id, project_id, result.output_file.name)
    PROJECT_FILES[project_id] = str(result.output_file)

    # Keep the uploaded source as a temporary input while the generated TPMS
    # model is being explored.  This lets users switch back to ordinary
    # infill or regenerate with a different TPMS structure without uploading
    # the same model again.  Ordinary slicing still removes its input after a
    # successful G-code run, and the storage service applies the normal TTL to
    # temporary uploads.

    for project in PROJECTS:
        if project.id == project_id:
            project.model_file = result.output_file.name
            project.status = "completed"

    task = TaskRead(
        id=f"mg-{len(TASKS) + 2048}",
        project_id=project_id,
        name=f"{payload.tpms_type} {payload.structure_type} TPMS 结构生成",
        type="model-generation",
        status="completed",
        progress=100,
        updated_at="2026-08-02 21:00",
    )
    TASKS.append(task)
    PROJECT_MODEL_TASK_FILES[task.id] = str(result.output_file)

    cell_size_x = payload.cell_size_x or payload.cell_size
    cell_size_y = payload.cell_size_y or payload.cell_size
    cell_size_z = payload.cell_size_z or payload.cell_size
    bounding_volume = (
        cell_size_x
        * payload.cell_count_x
        * cell_size_y
        * payload.cell_count_y
        * cell_size_z
        * payload.cell_count_z
    )
    mesh_volume = abs(float(mesh.volume)) if mesh.is_watertight else 0.0

    return ModelGenerationRunRead(
        task=task,
        model_filename=result.output_file.name,
        model_url=f"/api/v1/projects/{project_id}/files/{result.output_file.name}",
        vertices=len(mesh.vertices),
        triangles=len(mesh.faces),
        volume_mm3=round(mesh_volume, 3),
        surface_area_mm2=round(float(mesh.area), 3),
        relative_density=round(mesh_volume / bounding_volume, 4) if bounding_volume > 0 else 0,
        effective_level_set_offset=round(result.effective_level_set_offset, 4),
    )
