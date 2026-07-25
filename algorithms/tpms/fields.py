from __future__ import annotations

from typing import cast

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def _validate_cell_size(cell_size: float) -> None:
    if cell_size <= 0:
        raise ValueError("cell_size must be greater than zero")


def gyroid_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: float,
) -> FloatArray:
    """Calculate the Gyroid implicit scalar field."""

    _validate_cell_size(cell_size)

    scale = 2.0 * np.pi / cell_size

    x_scaled = x * scale
    y_scaled = y * scale
    z_scaled = z * scale

    result = (
        np.sin(x_scaled) * np.cos(y_scaled)
        + np.sin(y_scaled) * np.cos(z_scaled)
        + np.sin(z_scaled) * np.cos(x_scaled)
    )

    return cast(FloatArray, result)


def schwarz_p_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: float,
) -> FloatArray:
    """Calculate the Schwarz-P implicit scalar field."""

    _validate_cell_size(cell_size)

    scale = 2.0 * np.pi / cell_size

    x_scaled = x * scale
    y_scaled = y * scale
    z_scaled = z * scale

    result = np.cos(x_scaled) + np.cos(y_scaled) + np.cos(z_scaled)

    return cast(FloatArray, result)


def diamond_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: float,
) -> FloatArray:
    """Calculate the Diamond implicit scalar field."""

    _validate_cell_size(cell_size)

    scale = 2.0 * np.pi / cell_size

    x_scaled = x * scale
    y_scaled = y * scale
    z_scaled = z * scale

    result = (
        np.sin(x_scaled) * np.sin(y_scaled) * np.sin(z_scaled)
        + np.sin(x_scaled) * np.cos(y_scaled) * np.cos(z_scaled)
        + np.cos(x_scaled) * np.sin(y_scaled) * np.cos(z_scaled)
        + np.cos(x_scaled) * np.cos(y_scaled) * np.sin(z_scaled)
    )

    return cast(FloatArray, result)
