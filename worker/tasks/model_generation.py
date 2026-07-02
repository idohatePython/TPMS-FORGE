from pathlib import Path

from algorithms.pipeline.model_generation import ModelGenerationInput, run_model_generation
from worker.celery_app import celery_app


@celery_app.task(name="tpms_forge.model_generation")
def model_generation_task(input_file: str, output_dir: str, params: dict[str, object]) -> str:
    result = run_model_generation(
        ModelGenerationInput(
            input_file=Path(input_file),
            output_dir=Path(output_dir),
            params=params,
        )
    )
    return str(result.output_file)

