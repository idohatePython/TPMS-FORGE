from __future__ import annotations

from typing import Literal

import numpy as np
import trimesh
from numpy.typing import NDArray
from skimage.measure import marching_cubes

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
RodPhase = Literal["negative", "positive"]
type MeshSpacing = float | tuple[float, float, float]


def _spacing_tuple(spacing: MeshSpacing) -> tuple[float, float, float]:
    if isinstance(spacing, tuple):
        if len(spacing) != 3:
            raise ValueError("spacing tuple must have three values")
        spacing_x, spacing_y, spacing_z = spacing
    else:
        spacing_x = spacing_y = spacing_z = spacing

    if spacing_x <= 0 or spacing_y <= 0 or spacing_z <= 0:
        raise ValueError("spacing must be greater than zero")

    return (spacing_x, spacing_y, spacing_z)


def _extract_mesh_from_level_set(
    level_set: FloatArray,
    *,
    spacing: MeshSpacing,
    material_mask: BoolArray | None = None,
) -> trimesh.Trimesh:
    if level_set.ndim != 3:
        raise ValueError("level_set must be a 3D array")

    if level_set.size == 0:
        raise ValueError("level_set must not be empty")

    spacing_values = _spacing_tuple(spacing)

    outside_value = float(np.max(np.abs(level_set)) + 1.0)
    if material_mask is not None:
        if material_mask.shape != level_set.shape:
            raise ValueError("material_mask shape must match level_set")
        level_set = np.where(material_mask, level_set, outside_value)

    padded = np.pad(
        level_set,
        pad_width=1,
        mode="constant",
        constant_values=outside_value,
    )

    vertices, faces, _, _ = marching_cubes(  # type: ignore[no-untyped-call]
        padded,
        level=0.0,
        spacing=spacing_values,
    )

    vertices -= np.array(spacing_values)

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
    half_thickness: float | FloatArray,
    spacing: MeshSpacing,
    material_mask: BoolArray | None = None,
) -> trimesh.Trimesh:
    """Extract the material region -d <= field <= d."""

    if isinstance(half_thickness, np.ndarray):
        if half_thickness.shape != field.shape:
            raise ValueError("half_thickness field shape must match field")
        if float(np.min(half_thickness)) <= 0:
            raise ValueError("half_thickness field values must be greater than zero")
    elif half_thickness <= 0:
        raise ValueError("half_thickness must be greater than zero")

    level_set = np.abs(field) - half_thickness

    return _extract_mesh_from_level_set(
        level_set,
        spacing=spacing,
        material_mask=material_mask,
    )


def extract_shell_mesh_by_thickness(
    field: FloatArray,
    *,
    wall_thickness: float | FloatArray,
    spacing: MeshSpacing,
    material_mask: BoolArray | None = None,
) -> trimesh.Trimesh:
    """Extract a sheet using an approximate physical wall thickness."""

    if isinstance(wall_thickness, np.ndarray):
        if wall_thickness.shape != field.shape:
            raise ValueError("wall_thickness field shape must match field")
        if float(np.min(wall_thickness)) <= 0:
            raise ValueError("wall_thickness field values must be greater than zero")
    elif wall_thickness <= 0:
        raise ValueError("wall_thickness must be greater than zero")

    spacing_values = _spacing_tuple(spacing)
    gradient_magnitude_squared = np.zeros_like(field)
    for axis, axis_spacing in enumerate(spacing_values):
        component = np.gradient(field, axis_spacing, axis=axis, edge_order=1)
        np.square(component, out=component)
        gradient_magnitude_squared += component
        del component
    np.sqrt(gradient_magnitude_squared, out=gradient_magnitude_squared)
    gradient_magnitude = gradient_magnitude_squared
    approximate_distance = field / np.maximum(gradient_magnitude, 1e-9)
    level_set = np.abs(approximate_distance) - wall_thickness / 2.0

    return _extract_mesh_from_level_set(
        level_set,
        spacing=spacing,
        material_mask=material_mask,
    )


def extract_rod_mesh(
    field: FloatArray,
    *,
    phase: RodPhase,
    spacing: MeshSpacing,
    material_mask: BoolArray | None = None,
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
        material_mask=material_mask,
    )
