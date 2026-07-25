from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from algorithms.mesh.extraction import extract_rod_mesh, extract_shell_mesh
from algorithms.tpms.fields import diamond_field, gyroid_field, schwarz_p_field


@dataclass(frozen=True)
class ModelGenerationInput:
    input_file: Path
    output_dir: Path
    params: dict[str, object]


@dataclass(frozen=True)
class ModelGenerationResult:
    output_file: Path
    preview_file: Path | None = None


def _get_float(
    params: dict[str, object],
    key: str,
    default: float,
) -> float:
    value = params.get(key, default)

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")

    return float(value)


def _get_int(
    params: dict[str, object],
    key: str,
    default: int,
) -> int:
    value = params.get(key, default)

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")

    return value


def _get_str(
    params: dict[str, object],
    key: str,
    default: str,
) -> str:
    value = params.get(key, default)

    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")

    return value


def run_model_generation(
    payload: ModelGenerationInput,
) -> ModelGenerationResult:
    cell_size = _get_float(payload.params, "cell_size", 8.0)
    repeats = _get_int(payload.params, "n", 2)
    half_thickness = _get_float(payload.params, "d", 0.35)
    quality = _get_str(payload.params, "quality", "standard")
    structure_type = _get_str(payload.params, "structure_type", "sheet")
    tpms_type = _get_str(payload.params, "tpms_type", "gyroid")

    if cell_size <= 0:
        raise ValueError("cell_size must be greater than zero")

    if repeats <= 0:
        raise ValueError("n must be greater than zero")

    points_per_cell = {
        "fast": 16,
        "standard": 24,
        "high": 32,
    }.get(quality)

    if points_per_cell is None:
        raise ValueError("quality must be fast, standard, or high")

    domain_size = cell_size * repeats
    sample_count = repeats * points_per_cell + 1

    axis = np.linspace(
        0.0,
        domain_size,
        sample_count,
    )

    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    if tpms_type == "gyroid":
        field = gyroid_field(
            x,
            y,
            z,
            cell_size=cell_size,
        )
    elif tpms_type == "schwarz_p":
        field = schwarz_p_field(
            x,
            y,
            z,
            cell_size=cell_size,
        )
    elif tpms_type == "diamond":
        field = diamond_field(
            x,
            y,
            z,
            cell_size=cell_size,
        )
    else:
        raise ValueError("tpms_type must be gyroid, schwarz_p, or diamond")

    if structure_type == "sheet":
        mesh = extract_shell_mesh(
            field,
            half_thickness=half_thickness,
            spacing=spacing,
        )
    elif structure_type == "rod_negative":
        mesh = extract_rod_mesh(
            field,
            phase="negative",
            spacing=spacing,
        )
    elif structure_type == "rod_positive":
        mesh = extract_rod_mesh(
            field,
            phase="positive",
            spacing=spacing,
        )
    else:
        raise ValueError("structure_type must be sheet, rod_negative, or rod_positive")

    payload.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = payload.output_dir / f"{tpms_type}_{structure_type}.stl"

    mesh.export(output_file)

    return ModelGenerationResult(
        output_file=output_file,
    )
