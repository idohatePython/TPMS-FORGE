import numpy as np
import pytest
import trimesh

from algorithms.mesh.extraction import (
    extract_rod_mesh,
    extract_shell_mesh,
    extract_shell_mesh_by_thickness,
)
from algorithms.pipeline.model_generation import ModelGenerationInput, run_model_generation
from algorithms.tpms.fields import (
    TPMS_FIELD_FUNCTIONS,
    diamond_field,
    gyroid_field,
    schwarz_p_field,
)


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


def test_field_functions_accept_axis_specific_cell_sizes() -> None:
    x, y, z = np.meshgrid(
        np.linspace(0, 8, 10),
        np.linspace(0, 10, 10),
        np.linspace(0, 12, 10),
        indexing="ij",
    )

    field = gyroid_field(
        x,
        y,
        z,
        cell_size=(8, 10, 12),
    )

    assert field.shape == (10, 10, 10)
    assert np.isfinite(field).all()


@pytest.mark.parametrize("tpms_type", ["iwp", "neovius", "lidinoid"])
def test_extended_tpms_field_shape(tpms_type: str) -> None:
    x, y, z = np.meshgrid(
        np.linspace(0, 8, 10),
        np.linspace(0, 8, 10),
        np.linspace(0, 8, 10),
        indexing="ij",
    )

    field = TPMS_FIELD_FUNCTIONS[tpms_type](
        x,
        y,
        z,
        cell_size=8,
    )

    assert field.shape == (10, 10, 10)
    assert np.isfinite(field).all()


@pytest.mark.parametrize(
    ("tpms_type", "parameter_name", "baseline", "modified"),
    [
        ("gyroid", "gyroid_term_weight", 1.0, 1.4),
        ("schwarz_p", "schwarz_cross_weight", 0.0, 0.4),
        ("diamond", "diamond_nodal_weight", 1.0, 1.4),
        ("iwp", "iwp_second_harmonic_weight", 1.0, 1.4),
        ("neovius", "neovius_product_weight", 4.0, 5.0),
        ("lidinoid", "lidinoid_bias", 0.15, 0.35),
    ],
)
def test_type_specific_parameters_change_field(
    tpms_type: str,
    parameter_name: str,
    baseline: float,
    modified: float,
) -> None:
    x, y, z = np.meshgrid(
        np.linspace(0.2, 7.8, 12),
        np.linspace(0.2, 7.8, 12),
        np.linspace(0.2, 7.8, 12),
        indexing="ij",
    )

    field_function = TPMS_FIELD_FUNCTIONS[tpms_type]
    baseline_field = field_function(x, y, z, cell_size=8, **{parameter_name: baseline})
    modified_field = field_function(x, y, z, cell_size=8, **{parameter_name: modified})

    assert not np.allclose(baseline_field, modified_field)


@pytest.mark.parametrize("tpms_type", ["iwp", "neovius", "lidinoid"])
def test_model_generation_accepts_extended_tpms_types(
    tmp_path,
    tpms_type: str,
) -> None:
    result = run_model_generation(
        ModelGenerationInput(
            input_file=tmp_path / "input.stl",
            output_dir=tmp_path,
            params={
                "tpms_type": tpms_type,
                "structure_type": "sheet",
                "cell_size": 6.0,
                "nx": 1,
                "ny": 1,
                "nz": 1,
                "wall_thickness_mm": 0.6,
                "quality": "fast",
            },
        )
    )

    assert result.output_file.exists()
    assert result.output_file.stat().st_size > 84


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


def test_extract_gyroid_shell_mesh_accepts_spatial_thickness_field() -> None:
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
    wall_thickness = np.broadcast_to(
        np.linspace(0.35, 0.9, field.shape[2]).reshape(1, 1, -1),
        field.shape,
    )

    mesh = extract_shell_mesh_by_thickness(
        field,
        wall_thickness=wall_thickness,
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


def test_model_generation_accepts_anisotropic_cells_and_level_set_offset(
    tmp_path,
) -> None:
    result = run_model_generation(
        ModelGenerationInput(
            input_file=tmp_path / "input.stl",
            output_dir=tmp_path,
            params={
                "tpms_type": "gyroid",
                "structure_type": "rod_positive",
                "cell_size": 6.0,
                "cell_size_x": 6.0,
                "cell_size_y": 7.0,
                "cell_size_z": 8.0,
                "nx": 2,
                "ny": 1,
                "nz": 1,
                "level_set_offset": 0.15,
                "phase_shift_x": 0.25,
                "phase_shift_y": -0.15,
                "phase_shift_z": 0.5,
                "gradient_axis": "x",
                "gradient_strength": 0.2,
                "field_sign": -1.0,
                "quality": "fast",
            },
        )
    )

    assert result.output_file.exists()
    assert result.output_file.stat().st_size > 84
    assert result.effective_level_set_offset == pytest.approx(0.15)


def test_model_generation_accepts_density_gradient_parameters(
    tmp_path,
) -> None:
    result = run_model_generation(
        ModelGenerationInput(
            input_file=tmp_path / "input.stl",
            output_dir=tmp_path,
            params={
                "tpms_type": "gyroid",
                "structure_type": "sheet",
                "cell_size": 6.0,
                "nx": 1,
                "ny": 1,
                "nz": 1,
                "wall_thickness_mm": 0.6,
                "density_gradient_mode": "linear",
                "density_gradient_axis": "z",
                "density_gradient_start_offset": -0.25,
                "density_gradient_end_offset": 0.25,
                "density_gradient_curve": "smooth",
                "quality": "fast",
            },
        )
    )

    assert result.output_file.exists()
    assert result.output_file.stat().st_size > 84
    assert result.effective_level_set_offset == pytest.approx(0.0)


def test_model_generation_accepts_thickness_gradient_field(
    tmp_path,
) -> None:
    result = run_model_generation(
        ModelGenerationInput(
            input_file=tmp_path / "input.stl",
            output_dir=tmp_path,
            params={
                "tpms_type": "gyroid",
                "structure_type": "sheet",
                "cell_size": 6.0,
                "nx": 1,
                "ny": 1,
                "nz": 1,
                "wall_thickness_mm": 0.6,
                "thickness_gradient_mode": "linear",
                "thickness_gradient_axis": "z",
                "thickness_gradient_start_mm": 0.35,
                "thickness_gradient_end_mm": 1.0,
                "thickness_gradient_curve": "smooth",
                "quality": "fast",
            },
        )
    )

    assert result.output_file.exists()
    assert result.output_file.stat().st_size > 84


def test_model_generation_can_clip_to_uploaded_boundary(
    tmp_path,
) -> None:
    boundary_file = tmp_path / "insole_boundary.stl"
    trimesh.creation.box(extents=(8.0, 6.0, 4.0)).export(boundary_file)

    result = run_model_generation(
        ModelGenerationInput(
            input_file=boundary_file,
            output_dir=tmp_path,
            params={
                "generation_domain": "boundary",
                "tpms_type": "gyroid",
                "structure_type": "sheet",
                "cell_size": 4.0,
                "wall_thickness_mm": 0.4,
                "quality": "fast",
            },
        )
    )

    mesh = trimesh.load_mesh(result.output_file, process=False)

    assert result.output_file.exists()
    assert len(mesh.vertices) > 0
    assert mesh.bounds[0, 0] >= -4.01
    assert mesh.bounds[1, 0] <= 4.01


def test_model_generation_can_use_open_footprint_boundary(
    tmp_path,
) -> None:
    boundary_file = tmp_path / "open_insole_surface.stl"
    vertices = np.array(
        [
            [-4.0, -2.0, 0.0],
            [4.0, -2.0, 0.0],
            [4.0, 2.0, 2.0],
            [-4.0, 2.0, 2.0],
        ],
    )
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    trimesh.Trimesh(vertices=vertices, faces=faces, process=False).export(boundary_file)

    result = run_model_generation(
        ModelGenerationInput(
            input_file=boundary_file,
            output_dir=tmp_path,
            params={
                "generation_domain": "boundary",
                "boundary_mode": "footprint",
                "tpms_type": "gyroid",
                "structure_type": "sheet",
                "cell_size": 4.0,
                "wall_thickness_mm": 0.4,
                "quality": "fast",
            },
        )
    )

    mesh = trimesh.load_mesh(result.output_file, process=False)

    assert result.output_file.exists()
    assert len(mesh.vertices) > 0
    assert mesh.bounds[0, 0] >= -4.01
    assert mesh.bounds[1, 0] <= 4.01


def test_closed_boundary_mode_rejects_open_mesh(
    tmp_path,
) -> None:
    boundary_file = tmp_path / "open_surface.stl"
    trimesh.Trimesh(
        vertices=np.array([[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [0.0, 1.0, 1.0]]),
        faces=np.array([[0, 1, 2]]),
        process=False,
    ).export(boundary_file)

    with pytest.raises(ValueError, match="not watertight"):
        run_model_generation(
            ModelGenerationInput(
                input_file=boundary_file,
                output_dir=tmp_path,
                params={
                    "generation_domain": "boundary",
                    "boundary_mode": "closed",
                    "tpms_type": "gyroid",
                    "structure_type": "sheet",
                    "cell_size": 4.0,
                    "wall_thickness_mm": 0.4,
                    "quality": "fast",
                },
            )
        )


def test_boundary_generation_rejects_oversized_grid_before_allocating(
    tmp_path,
) -> None:
    boundary_file = tmp_path / "large_insole.stl"
    trimesh.creation.box(extents=(300.0, 120.0, 20.0)).export(boundary_file)

    with pytest.raises(ValueError, match="generation grid is too large"):
        run_model_generation(
            ModelGenerationInput(
                input_file=boundary_file,
                output_dir=tmp_path,
                params={
                    "generation_domain": "boundary",
                    "tpms_type": "gyroid",
                    "structure_type": "sheet",
                    "cell_size": 4.0,
                    "wall_thickness_mm": 0.4,
                    "quality": "high",
                },
            )
        )


def test_model_generation_can_solve_solid_target_relative_density(
    tmp_path,
) -> None:
    result = run_model_generation(
        ModelGenerationInput(
            input_file=tmp_path / "input.stl",
            output_dir=tmp_path,
            params={
                "tpms_type": "schwarz_p",
                "structure_type": "rod_positive",
                "cell_size": 6.0,
                "nx": 1,
                "ny": 1,
                "nz": 1,
                "density_mode": "target",
                "target_relative_density": 0.25,
                "quality": "fast",
            },
        )
    )

    assert result.output_file.exists()
    assert result.output_file.stat().st_size > 84
    assert result.effective_level_set_offset != 0


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
