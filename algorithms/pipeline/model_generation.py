from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelGenerationInput:
    input_file: Path
    output_dir: Path
    params: dict[str, object]


@dataclass(frozen=True)
class ModelGenerationResult:
    output_file: Path
    preview_file: Path | None = None


def run_model_generation(payload: ModelGenerationInput) -> ModelGenerationResult:
    raise NotImplementedError("TPMS model generation pipeline is not implemented yet.")

