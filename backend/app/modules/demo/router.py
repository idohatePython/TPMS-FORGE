from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import trimesh
from fastapi import APIRouter, HTTPException, Response, status

from algorithms.pipeline.model_generation import (
    ModelGenerationInput,
    run_model_generation,
)
from backend.app.schemas.demo import DemoTpmsRequest

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/tpms", response_class=Response)
def generate_demo_tpms(payload: DemoTpmsRequest) -> Response:
    started_at = perf_counter()

    try:
        with TemporaryDirectory(prefix="tpms-forge-demo-") as temporary_dir:
            result = run_model_generation(
                ModelGenerationInput(
                    input_file=Path(temporary_dir) / "demo.input",
                    output_dir=Path(temporary_dir),
                    params={
                        "tpms_type": payload.tpms_type,
                        "structure_type": "sheet",
                        "cell_size": payload.cell_size,
                        "n": payload.cell_count,
                        "wall_thickness_mm": payload.wall_thickness_mm,
                        "quality": payload.quality,
                        "density_gradient_mode": "linear",
                        "density_gradient_axis": payload.gradient_axis,
                        "density_gradient_start_offset": payload.gradient_start_offset,
                        "density_gradient_end_offset": payload.gradient_end_offset,
                        "density_gradient_curve": "smooth",
                    },
                )
            )
            mesh = trimesh.load_mesh(result.output_file, process=False)
            stl_bytes = result.output_file.read_bytes()
    except (OSError, RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    return Response(
        content=stl_bytes,
        media_type="model/stl",
        headers={
            "Cache-Control": "no-store",
            "X-TPMS-Vertices": str(len(mesh.vertices)),
            "X-TPMS-Triangles": str(len(mesh.faces)),
            "X-TPMS-Duration-Ms": str(round((perf_counter() - started_at) * 1000)),
        },
    )
