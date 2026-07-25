import numpy as np
import pytest

from algorithms.mesh.extraction import extract_rod_mesh, extract_shell_mesh
from algorithms.tpms.fields import diamond_field, gyroid_field, schwarz_p_field


def test_gyroid_field_shape() -> None:
    x, y, z = np.meshgrid(
        np.linspace(0, 8, 10),
        np.linspace(0, 8, 10),
        np.linspace(0, 8, 10),
        indexing="ij",
    )

    field = gyroid_field(
        x,
        y,
        z,
        cell_size=8,
    )

    assert field.shape == (10, 10, 10)
    assert np.isfinite(field).all()


def test_gyroid_field_rejects_invalid_cell_size() -> None:
    values = np.zeros((2, 2, 2))

    with pytest.raises(ValueError):
        gyroid_field(
            values,
            values,
            values,
            cell_size=0,
        )


def test_extract_gyroid_shell_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = gyroid_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_shell_mesh(
        field,
        half_thickness=0.35,
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_extract_gyroid_negative_rod_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = gyroid_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_rod_mesh(
        field,
        phase="negative",
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_extract_gyroid_positive_rod_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = gyroid_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_rod_mesh(
        field,
        phase="positive",
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_schwarz_p_field_shape() -> None:
    x, y, z = np.meshgrid(
        np.linspace(0, 8, 10),
        np.linspace(0, 8, 10),
        np.linspace(0, 8, 10),
        indexing="ij",
    )

    field = schwarz_p_field(
        x,
        y,
        z,
        cell_size=8,
    )

    assert field.shape == (10, 10, 10)
    assert np.isfinite(field).all()


def test_extract_schwarz_p_shell_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = schwarz_p_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_shell_mesh(
        field,
        half_thickness=0.35,
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_extract_schwarz_p_negative_rod_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = schwarz_p_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_rod_mesh(
        field,
        phase="negative",
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_extract_schwarz_p_positive_rod_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = schwarz_p_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_rod_mesh(
        field,
        phase="positive",
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_diamond_field_shape() -> None:
    x, y, z = np.meshgrid(
        np.linspace(0, 8, 10),
        np.linspace(0, 8, 10),
        np.linspace(0, 8, 10),
        indexing="ij",
    )

    field = diamond_field(
        x,
        y,
        z,
        cell_size=8,
    )

    assert field.shape == (10, 10, 10)
    assert np.isfinite(field).all()


def test_extract_diamond_shell_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = diamond_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_shell_mesh(
        field,
        half_thickness=0.35,
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_extract_diamond_negative_rod_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = diamond_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_rod_mesh(
        field,
        phase="negative",
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight


def test_extract_diamond_positive_rod_mesh() -> None:
    cell_size = 8.0
    axis = np.linspace(0, cell_size, 32)
    spacing = float(axis[1] - axis[0])

    x, y, z = np.meshgrid(
        axis,
        axis,
        axis,
        indexing="ij",
    )

    field = diamond_field(
        x,
        y,
        z,
        cell_size=cell_size,
    )

    mesh = extract_rod_mesh(
        field,
        phase="positive",
        spacing=spacing,
    )

    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight
