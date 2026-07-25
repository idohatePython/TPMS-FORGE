from __future__ import annotations

from typing import Literal

import numpy as np
import trimesh
from numpy.typing import NDArray
from skimage.measure import marching_cubes

FloatArray = NDArray[np.float64]
RodPhase = Literal["negative", "positive"]


def _extract_mesh_from_level_set(
    level_set: FloatArray,
    *,
    spacing: float,
) -> trimesh.Trimesh:
    if level_set.ndim != 3:
        raise ValueError("level_set must be a 3D array")

    if level_set.size == 0:
        raise ValueError("level_set must not be empty")

    if spacing <= 0:
        raise ValueError("spacing must be greater than zero")

    outside_value = float(np.max(np.abs(level_set)) + 1.0)

    padded = np.pad(
        level_set,
        pad_width=1,
        mode="constant",
        constant_values=outside_value,
    )

    vertices, faces, _, _ = marching_cubes(  # type: ignore[no-untyped-call]
        padded,
        level=0.0,
        spacing=(spacing, spacing, spacing),
    )

    vertices -= spacing

    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        process=True,
    )

    if mesh.is_empty:
        raise ValueError("generated mesh is empty")

    return mesh


def extract_shell_mesh(
    field: FloatArray,
    *,
    half_thickness: float,
    spacing: float,
) -> trimesh.Trimesh:
    """Extract the material region -d <= field <= d."""

    if half_thickness <= 0:
        raise ValueError("half_thickness must be greater than zero")

    level_set = np.abs(field) - half_thickness

    return _extract_mesh_from_level_set(
        level_set,
        spacing=spacing,
    )


def extract_rod_mesh(
    field: FloatArray,
    *,
    phase: RodPhase,
    spacing: float,
) -> trimesh.Trimesh:
    """Extract one of the two solid TPMS phases."""

    epsilon = 1e-6

    if phase == "negative":
        level_set = field + epsilon
    elif phase == "positive":
        level_set = -field + epsilon
    else:
        raise ValueError("phase must be negative or positive")

    return _extract_mesh_from_level_set(
        level_set,
        spacing=spacing,
    )
