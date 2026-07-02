from pathlib import Path

from algorithms.pipeline.slicing_gcode import SlicingGcodeInput, run_slicing_gcode
from worker.celery_app import celery_app


@celery_app.task(name="tpms_forge.slicing_gcode")
def slicing_gcode_task(input_file: str, output_dir: str, params: dict[str, object]) -> str:
    result = run_slicing_gcode(
        SlicingGcodeInput(
            input_file=Path(input_file),
            output_dir=Path(output_dir),
            params=params,
        )
    )
    return str(result.gcode_file)

