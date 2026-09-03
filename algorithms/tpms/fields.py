from __future__ import annotations

from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
type CellSize = float | tuple[float, float, float]


class TpmsFieldFunction(Protocol):
    def __call__(
        self,
        x: FloatArray,
        y: FloatArray,
    z: FloatArray,
    *,
    cell_size: CellSize,
    **field_parameters: float,
    ) -> FloatArray: ...


def _axis_scales(cell_size: CellSize) -> tuple[float, float, float]:
    if isinstance(cell_size, tuple):
        if len(cell_size) != 3:
            raise ValueError("cell_size tuple must have three values")

        cell_size_x, cell_size_y, cell_size_z = cell_size
    else:
        cell_size_x = cell_size_y = cell_size_z = cell_size

    if cell_size_x <= 0 or cell_size_y <= 0 or cell_size_z <= 0:
        raise ValueError("cell_size must be greater than zero")

    return (
        2.0 * np.pi / cell_size_x,
        2.0 * np.pi / cell_size_y,
        2.0 * np.pi / cell_size_z,
    )


def gyroid_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: CellSize,
    gyroid_term_weight: float = 1.0,
    **_: float,
) -> FloatArray:
    """Calculate the Gyroid implicit scalar field."""

    scale_x, scale_y, scale_z = _axis_scales(cell_size)

    x_scaled = x * scale_x
    y_scaled = y * scale_y
    z_scaled = z * scale_z

    result = (
        np.sin(x_scaled) * np.cos(y_scaled)
        + np.sin(y_scaled) * np.cos(z_scaled)
        + gyroid_term_weight * np.sin(z_scaled) * np.cos(x_scaled)
    )

    return cast(FloatArray, result)


def schwarz_p_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: CellSize,
    schwarz_cross_weight: float = 0.0,
    **_: float,
) -> FloatArray:
    """Calculate the Schwarz-P implicit scalar field."""

    scale_x, scale_y, scale_z = _axis_scales(cell_size)

    x_scaled = x * scale_x
    y_scaled = y * scale_y
    z_scaled = z * scale_z

    cos_x = np.cos(x_scaled)
    cos_y = np.cos(y_scaled)
    cos_z = np.cos(z_scaled)

    result = (
        cos_x
        + cos_y
        + cos_z
        + schwarz_cross_weight * (cos_x * cos_y + cos_y * cos_z + cos_z * cos_x)
    )

    return cast(FloatArray, result)


def diamond_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: CellSize,
    diamond_nodal_weight: float = 1.0,
    **_: float,
) -> FloatArray:
    """Calculate the Diamond implicit scalar field."""

    scale_x, scale_y, scale_z = _axis_scales(cell_size)

    x_scaled = x * scale_x
    y_scaled = y * scale_y
    z_scaled = z * scale_z

    result = (
        diamond_nodal_weight * np.sin(x_scaled) * np.sin(y_scaled) * np.sin(z_scaled)
        + np.sin(x_scaled) * np.cos(y_scaled) * np.cos(z_scaled)
        + np.cos(x_scaled) * np.sin(y_scaled) * np.cos(z_scaled)
        + np.cos(x_scaled) * np.cos(y_scaled) * np.sin(z_scaled)
    )

    return cast(FloatArray, result)


def iwp_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: CellSize,
    iwp_second_harmonic_weight: float = 1.0,
    **_: float,
) -> FloatArray:
    """Calculate the I-WP implicit scalar field."""

    scale_x, scale_y, scale_z = _axis_scales(cell_size)

    x_scaled = x * scale_x
    y_scaled = y * scale_y
    z_scaled = z * scale_z

    result = 2.0 * (
        np.cos(x_scaled) * np.cos(y_scaled)
        + np.cos(y_scaled) * np.cos(z_scaled)
        + np.cos(z_scaled) * np.cos(x_scaled)
    ) - iwp_second_harmonic_weight * (
        np.cos(2.0 * x_scaled)
        + np.cos(2.0 * y_scaled)
        + np.cos(2.0 * z_scaled)
    )

    return cast(FloatArray, result)


def neovius_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: CellSize,
    neovius_product_weight: float = 4.0,
    **_: float,
) -> FloatArray:
    """Calculate the Neovius implicit scalar field."""

    scale_x, scale_y, scale_z = _axis_scales(cell_size)

    x_scaled = x * scale_x
    y_scaled = y * scale_y
    z_scaled = z * scale_z

    result = 3.0 * (
        np.cos(x_scaled)
        + np.cos(y_scaled)
        + np.cos(z_scaled)
    ) + neovius_product_weight * np.cos(x_scaled) * np.cos(y_scaled) * np.cos(z_scaled)

    return result


def lidinoid_field(
    x: FloatArray,
    y: FloatArray,
    z: FloatArray,
    *,
    cell_size: CellSize,
    lidinoid_harmonic_weight: float = 0.5,
    lidinoid_bias: float = 0.15,
    **_: float,
) -> FloatArray:
    """Calculate a commonly used Lidinoid trigonometric approximation."""

    scale_x, scale_y, scale_z = _axis_scales(cell_size)

    x_scaled = x * scale_x
    y_scaled = y * scale_y
    z_scaled = z * scale_z

    result = (
        lidinoid_harmonic_weight
        * (
            np.sin(2.0 * x_scaled) * np.cos(y_scaled) * np.sin(z_scaled)
            + np.sin(2.0 * y_scaled) * np.cos(z_scaled) * np.sin(x_scaled)
            + np.sin(2.0 * z_scaled) * np.cos(x_scaled) * np.sin(y_scaled)
        )
        - lidinoid_harmonic_weight
        * (
            np.cos(2.0 * x_scaled) * np.cos(2.0 * y_scaled)
            + np.cos(2.0 * y_scaled) * np.cos(2.0 * z_scaled)
            + np.cos(2.0 * z_scaled) * np.cos(2.0 * x_scaled)
        )
        + lidinoid_bias
    )

    return cast(FloatArray, result)


TPMS_FIELD_FUNCTIONS: dict[str, TpmsFieldFunction] = {
    "gyroid": gyroid_field,
    "schwarz_p": schwarz_p_field,
    "diamond": diamond_field,
    "iwp": iwp_field,
    "neovius": neovius_field,
    "lidinoid": lidinoid_field,
}
