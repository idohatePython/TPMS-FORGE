from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import trimesh

from algorithms.mesh.boundary import (
    points_inside_closed_mesh_grid,
    points_inside_projected_footprint,
)
from algorithms.mesh.extraction import (
    extract_rod_mesh,
    extract_shell_mesh,
    extract_shell_mesh_by_thickness,
)
from algorithms.tpms.fields import TPMS_FIELD_FUNCTIONS

MAX_SAMPLE_POINTS = 12_000_000


def _remove_isolated_fragments(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Drop tiny disconnected marching-cubes fragments.

    A clipped boundary can leave a few dozen-face island while the real TPMS
    body contains hundreds of thousands of faces. Those islands are visually
    distracting (and can cast dark shadows in the browser), so keep only
    components that are a meaningful fraction of the generated body.
    """

    if len(mesh.faces) < 1_000:
        return mesh

    components = mesh.split(only_watertight=False)
    if len(components) <= 1:
        return mesh

    minimum_faces = max(24, int(len(mesh.faces) * 0.0005))
    retained = [component for component in components if len(component.faces) >= minimum_faces]
    if not retained:
        return mesh

    return trimesh.util.concatenate(retained)


def _postprocess_generated_mesh(mesh: trimesh.Trimesh, *, quality: str) -> trimesh.Trimesh:
    """Apply a small amount of geometry cleanup after marching cubes.

    Marching cubes produces a valid triangulation, but its vertices follow the
    voxel grid and can look faceted even when the underlying TPMS field is
    smooth.  Taubin filtering reduces that stair-step appearance without the
    visible shrinkage of a plain Laplacian pass.  Keep the pass count small so
    the web workflow remains responsive for large boundary models.
    """

    iterations = {
        "fast": 1,
        "standard": 2,
        "high": 3,
    }.get(quality, 1)

    # Constructing the sparse Laplacian for very large meshes can consume a
    # substantial amount of memory. One pass still improves shading while
    # avoiding a second expensive matrix traversal.
    if len(mesh.faces) > 900_000:
        iterations = 1

    try:
        # Extraction already merges most duplicate vertices. Running this once
        # more before smoothing makes adjacent marching-cubes cells share the
        # same vertices, which gives the filter a continuous neighbourhood.
        mesh.merge_vertices(digits_vertex=5)
        mesh = _remove_isolated_fragments(mesh)
        trimesh.smoothing.filter_taubin(
            mesh,
            lamb=0.45,
            nu=0.48,
            iterations=iterations,
        )
        # Smoothing can create tiny numerical degeneracies at a clipped
        # boundary. `process(validate=True)` removes those and rebuilds the
        # derived normals/face caches.
        mesh.process(validate=True)
        mesh.fix_normals(multibody=True)
    except (ImportError, MemoryError, RuntimeError, ValueError):
        # Mesh cleanup is an enhancement, not a reason to fail an otherwise
        # successful generation. The unsmoothed marching-cubes mesh remains a
        # usable fallback when scipy or a sparse operation is unavailable.
        mesh.fix_normals(multibody=True)

    return mesh


@dataclass(frozen=True)
class ModelGenerationInput:
    input_file: Path
    output_dir: Path
    params: dict[str, object]


@dataclass(frozen=True)
class ModelGenerationResult:
    output_file: Path
    preview_file: Path | None = None
    effective_level_set_offset: float = 0.0


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


def _offset_for_target_relative_density(
    field: np.ndarray,
    *,
    structure_type: str,
    target_relative_density: float,
) -> float:
    if not 0 < target_relative_density < 1:
        raise ValueError("target_relative_density must be between 0 and 1")

    if structure_type == "rod_positive":
        return float(np.quantile(field, 1.0 - target_relative_density))

    if structure_type == "rod_negative":
        return float(np.quantile(field, target_relative_density))

    raise ValueError("target relative density is only supported for solid modes")


def _gradient_curve(coordinate: np.ndarray, curve: str) -> np.ndarray:
    if curve == "linear":
        return coordinate

    if curve == "smooth":
        return cast(np.ndarray, coordinate * coordinate * (3.0 - 2.0 * coordinate))

    if curve == "ease_in":
        return cast(np.ndarray, coordinate * coordinate)

    if curve == "ease_out":
        return cast(np.ndarray, 1.0 - (1.0 - coordinate) * (1.0 - coordinate))

    raise ValueError("density_gradient_curve must be linear, smooth, ease_in, or ease_out")


def _density_gradient_coordinate(
    *,
    axis: str,
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    domain_size_x: float,
    domain_size_y: float,
    domain_size_z: float,
) -> np.ndarray:
    if axis == "x":
        return x / max(domain_size_x, 1e-9)

    if axis == "y":
        return y / max(domain_size_y, 1e-9)

    if axis == "z":
        return z / max(domain_size_z, 1e-9)

    center_x = domain_size_x / 2.0
    center_y = domain_size_y / 2.0
    center_z = domain_size_z / 2.0
    radius = np.sqrt(
        (x - center_x) * (x - center_x)
        + (y - center_y) * (y - center_y)
        + (z - center_z) * (z - center_z)
    )
    max_radius = np.sqrt(center_x * center_x + center_y * center_y + center_z * center_z)
    return cast(np.ndarray, radius / max(max_radius, 1e-9))


def run_model_generation(
    payload: ModelGenerationInput,
) -> ModelGenerationResult:
    cell_size = _get_float(payload.params, "cell_size", 8.0)
    cell_size_x = _get_float(payload.params, "cell_size_x", cell_size)
    cell_size_y = _get_float(payload.params, "cell_size_y", cell_size)
    cell_size_z = _get_float(payload.params, "cell_size_z", cell_size)
    repeats = _get_int(payload.params, "n", 2)
    repeats_x = _get_int(payload.params, "nx", repeats)
    repeats_y = _get_int(payload.params, "ny", repeats)
    repeats_z = _get_int(payload.params, "nz", repeats)
    half_thickness = _get_float(payload.params, "d", 0.35)
    wall_thickness = payload.params.get("wall_thickness_mm")
    level_set_offset = _get_float(payload.params, "level_set_offset", 0.0)
    field_sign = _get_float(payload.params, "field_sign", 1.0)
    phase_shift_x = _get_float(payload.params, "phase_shift_x", 0.0)
    phase_shift_y = _get_float(payload.params, "phase_shift_y", 0.0)
    phase_shift_z = _get_float(payload.params, "phase_shift_z", 0.0)
    gradient_axis = _get_str(payload.params, "gradient_axis", "none")
    gradient_strength = _get_float(payload.params, "gradient_strength", 0.0)
    density_gradient_mode = _get_str(payload.params, "density_gradient_mode", "legacy")
    density_gradient_axis = _get_str(payload.params, "density_gradient_axis", gradient_axis)
    density_gradient_start_offset = _get_float(
        payload.params,
        "density_gradient_start_offset",
        level_set_offset - gradient_strength / 2.0,
    )
    density_gradient_end_offset = _get_float(
        payload.params,
        "density_gradient_end_offset",
        level_set_offset + gradient_strength / 2.0,
    )
    density_gradient_curve = _get_str(payload.params, "density_gradient_curve", "linear")
    thickness_gradient_mode = _get_str(payload.params, "thickness_gradient_mode", "none")
    thickness_gradient_axis = _get_str(payload.params, "thickness_gradient_axis", "z")
    thickness_gradient_start_mm = _get_float(
        payload.params,
        "thickness_gradient_start_mm",
        float(wall_thickness) if isinstance(wall_thickness, (int, float)) else half_thickness * 2.0,
    )
    thickness_gradient_end_mm = _get_float(
        payload.params,
        "thickness_gradient_end_mm",
        float(wall_thickness) if isinstance(wall_thickness, (int, float)) else half_thickness * 2.0,
    )
    thickness_gradient_curve = _get_str(payload.params, "thickness_gradient_curve", "linear")
    density_mode = _get_str(payload.params, "density_mode", "manual")
    target_relative_density = _get_float(payload.params, "target_relative_density", 0.3)
    gyroid_term_weight = _get_float(payload.params, "gyroid_term_weight", 1.0)
    schwarz_cross_weight = _get_float(payload.params, "schwarz_cross_weight", 0.0)
    diamond_nodal_weight = _get_float(payload.params, "diamond_nodal_weight", 1.0)
    iwp_second_harmonic_weight = _get_float(payload.params, "iwp_second_harmonic_weight", 1.0)
    neovius_product_weight = _get_float(payload.params, "neovius_product_weight", 4.0)
    lidinoid_harmonic_weight = _get_float(payload.params, "lidinoid_harmonic_weight", 0.5)
    lidinoid_bias = _get_float(payload.params, "lidinoid_bias", 0.15)
    quality = _get_str(payload.params, "quality", "standard")
    structure_type = _get_str(payload.params, "structure_type", "sheet")
    tpms_type = _get_str(payload.params, "tpms_type", "gyroid")
    generation_domain = _get_str(payload.params, "generation_domain", "block")
    boundary_mode = _get_str(payload.params, "boundary_mode", "auto")

    if cell_size <= 0 or cell_size_x <= 0 or cell_size_y <= 0 or cell_size_z <= 0:
        raise ValueError("cell sizes must be greater than zero")

    if repeats <= 0 or repeats_x <= 0 or repeats_y <= 0 or repeats_z <= 0:
        raise ValueError("cell counts must be greater than zero")

    if gradient_axis not in {"none", "x", "y", "z"}:
        raise ValueError("gradient_axis must be none, x, y, or z")

    if density_gradient_mode not in {"none", "linear", "legacy"}:
        raise ValueError("density_gradient_mode must be none, linear, or legacy")

    if density_gradient_axis not in {"x", "y", "z", "radial", "none"}:
        raise ValueError("density_gradient_axis must be x, y, z, radial, or none")

    if thickness_gradient_mode not in {"none", "linear"}:
        raise ValueError("thickness_gradient_mode must be none or linear")

    if thickness_gradient_axis not in {"x", "y", "z", "radial"}:
        raise ValueError("thickness_gradient_axis must be x, y, z, or radial")

    if thickness_gradient_start_mm <= 0 or thickness_gradient_end_mm <= 0:
        raise ValueError("thickness gradient values must be greater than zero")

    if density_mode not in {"manual", "target"}:
        raise ValueError("density_mode must be manual or target")

    if generation_domain not in {"block", "boundary"}:
        raise ValueError("generation_domain must be block or boundary")

    if boundary_mode not in {"auto", "closed", "footprint"}:
        raise ValueError("boundary_mode must be auto, closed, or footprint")

    points_per_cell = {
        "fast": 24,
        "standard": 36,
        "high": 48,
    }.get(quality)

    if points_per_cell is None:
        raise ValueError("quality must be fast, standard, or high")

    origin = np.zeros(3, dtype=np.float64)
    material_mask: np.ndarray | None = None

    if generation_domain == "boundary":
        if not payload.input_file.is_file():
            raise ValueError("boundary generation requires an uploaded STL/OBJ input model")

        boundary_mesh = trimesh.load_mesh(payload.input_file, process=True)
        if isinstance(boundary_mesh, trimesh.Scene):
            boundary_mesh = boundary_mesh.dump(concatenate=True)
        if not isinstance(boundary_mesh, trimesh.Trimesh) or boundary_mesh.is_empty:
            raise ValueError("uploaded boundary model could not be read as a mesh")
        bounds = np.asarray(boundary_mesh.bounds, dtype=np.float64)
        origin = bounds[0]
        domain_size_x, domain_size_y, domain_size_z = (bounds[1] - bounds[0]).tolist()
        effective_boundary_mode = boundary_mode
        if effective_boundary_mode == "auto":
            # Thin parts (e.g. insoles) have too few samples through their
            # thickness for a stable 3-D inside test. Their XY footprint is a
            # better boundary for continuous TPMS preview geometry.
            is_thin_boundary = domain_size_z <= max(cell_size_z * 1.5, 3.0)
            effective_boundary_mode = (
                "footprint" if is_thin_boundary or not boundary_mesh.is_watertight else "closed"
            )

        if effective_boundary_mode == "closed" and not boundary_mesh.is_watertight:
            raise ValueError(
                "uploaded boundary model is not watertight; please upload a closed solid STL"
            )

        repeats_x = max(1, int(np.ceil(domain_size_x / cell_size_x)))
        repeats_y = max(1, int(np.ceil(domain_size_y / cell_size_y)))
        repeats_z = max(1, int(np.ceil(domain_size_z / cell_size_z)))
    else:
        domain_size_x = cell_size_x * repeats_x
        domain_size_y = cell_size_y * repeats_y
        domain_size_z = cell_size_z * repeats_z

    if domain_size_x <= 0 or domain_size_y <= 0 or domain_size_z <= 0:
        raise ValueError("generation domain must have positive dimensions")

    if generation_domain == "boundary":
        # Boundary models such as insoles are long and thin. Sampling every axis
        # from rounded-up cell counts heavily oversamples their thin dimension.
        # Use the real model extents and lighter preview-oriented densities.
        boundary_points_per_cell = {
            "fast": 8,
            "standard": 10,
            "high": 16,
        }[quality]
        sample_count_x = max(
            3,
            int(np.ceil(domain_size_x / cell_size_x * boundary_points_per_cell)) + 1,
        )
        sample_count_y = max(
            3,
            int(np.ceil(domain_size_y / cell_size_y * boundary_points_per_cell)) + 1,
        )
        sample_count_z = max(
            3,
            int(np.ceil(domain_size_z / cell_size_z * boundary_points_per_cell)) + 1,
        )
    else:
        sample_count_x = repeats_x * points_per_cell + 1
        sample_count_y = repeats_y * points_per_cell + 1
        sample_count_z = repeats_z * points_per_cell + 1

    sample_shape = (sample_count_x, sample_count_y, sample_count_z)
    sample_points = int(np.prod(sample_shape, dtype=np.int64))
    if sample_points > MAX_SAMPLE_POINTS:
        raise ValueError(
            "generation grid is too large "
            f"({sample_count_x} x {sample_count_y} x {sample_count_z} = "
            f"{sample_points:,} samples); use Fast quality or a larger cell size "
            f"(limit: {MAX_SAMPLE_POINTS:,} samples)"
        )

    x_axis = np.linspace(
        0.0,
        domain_size_x,
        sample_count_x,
        dtype=np.float32,
    )
    y_axis = np.linspace(
        0.0,
        domain_size_y,
        sample_count_y,
        dtype=np.float32,
    )
    z_axis = np.linspace(
        0.0,
        domain_size_z,
        sample_count_z,
        dtype=np.float32,
    )

    spacing = (
        float(x_axis[1] - x_axis[0]),
        float(y_axis[1] - y_axis[0]),
        float(z_axis[1] - z_axis[0]),
    )

    # Broadcasted coordinate views avoid three full dense coordinate volumes.
    x = x_axis[:, None, None]
    y = y_axis[None, :, None]
    z = z_axis[None, None, :]

    if generation_domain == "boundary":
        if effective_boundary_mode == "closed":
            material_mask = points_inside_closed_mesh_grid(
                boundary_mesh,
                x_axis + origin[0],
                y_axis + origin[1],
                z_axis + origin[2],
            )
        else:
            footprint_points = np.column_stack(
                [
                    np.repeat(x_axis, sample_count_y) + origin[0],
                    np.tile(y_axis, sample_count_x) + origin[1],
                    np.full(sample_count_x * sample_count_y, origin[2]),
                ]
            )
            footprint_mask = points_inside_projected_footprint(
                boundary_mesh,
                footprint_points,
                check_z=False,
            ).reshape(sample_count_x, sample_count_y)
            material_mask = np.broadcast_to(footprint_mask[:, :, None], sample_shape)
        if not np.any(material_mask):
            raise ValueError("no TPMS sample points were found inside the uploaded boundary model")

    x_for_field = x + phase_shift_x * cell_size_x / (2.0 * np.pi)
    y_for_field = y + phase_shift_y * cell_size_y / (2.0 * np.pi)
    z_for_field = z + phase_shift_z * cell_size_z / (2.0 * np.pi)
    field_cell_size = (cell_size_x, cell_size_y, cell_size_z)

    field_function = TPMS_FIELD_FUNCTIONS.get(tpms_type)
    if field_function is None:
        supported_types = ", ".join(sorted(TPMS_FIELD_FUNCTIONS))
        raise ValueError(f"tpms_type must be one of: {supported_types}")

    field = field_function(
        x_for_field,
        y_for_field,
        z_for_field,
        cell_size=field_cell_size,
        gyroid_term_weight=gyroid_term_weight,
        schwarz_cross_weight=schwarz_cross_weight,
        diamond_nodal_weight=diamond_nodal_weight,
        iwp_second_harmonic_weight=iwp_second_harmonic_weight,
        neovius_product_weight=neovius_product_weight,
        lidinoid_harmonic_weight=lidinoid_harmonic_weight,
        lidinoid_bias=lidinoid_bias,
    )

    field = field * field_sign

    if density_mode == "target":
        level_set_offset = _offset_for_target_relative_density(
            field,
            structure_type=structure_type,
            target_relative_density=target_relative_density,
        )

    if density_gradient_mode == "legacy":
        density_gradient_mode = (
            "linear" if gradient_axis != "none" and gradient_strength != 0 else "none"
        )
        density_gradient_axis = gradient_axis

    if density_gradient_mode == "linear":
        if density_gradient_axis == "none":
            raise ValueError(
                "density_gradient_axis must be selected when density gradient is enabled"
            )

        gradient_coordinate = _density_gradient_coordinate(
            axis=density_gradient_axis,
            x=x,
            y=y,
            z=z,
            domain_size_x=domain_size_x,
            domain_size_y=domain_size_y,
            domain_size_z=domain_size_z,
        )
        gradient_weight = _gradient_curve(gradient_coordinate, density_gradient_curve)
        level_set_field = density_gradient_start_offset + (
            density_gradient_end_offset - density_gradient_start_offset
        ) * gradient_weight
        field = field - level_set_field
        level_set_offset = float(
            (density_gradient_start_offset + density_gradient_end_offset) / 2.0
        )
    else:
        field = field - level_set_offset

    wall_thickness_field: np.ndarray | None = None
    if thickness_gradient_mode == "linear":
        thickness_coordinate = _density_gradient_coordinate(
            axis=thickness_gradient_axis,
            x=x,
            y=y,
            z=z,
            domain_size_x=domain_size_x,
            domain_size_y=domain_size_y,
            domain_size_z=domain_size_z,
        )
        thickness_weight = _gradient_curve(thickness_coordinate, thickness_gradient_curve)
        wall_thickness_field = thickness_gradient_start_mm + (
            thickness_gradient_end_mm - thickness_gradient_start_mm
        ) * thickness_weight
        wall_thickness_field = np.broadcast_to(wall_thickness_field, sample_shape)

    if structure_type == "sheet":
        if wall_thickness is None:
            mesh = extract_shell_mesh(
                field,
                half_thickness=wall_thickness_field / 2.0
                if wall_thickness_field is not None
                else half_thickness,
                spacing=spacing,
                material_mask=material_mask,
            )
        else:
            if isinstance(wall_thickness, bool) or not isinstance(
                wall_thickness,
                (int, float),
            ):
                raise ValueError("wall_thickness_mm must be a number")
            mesh = extract_shell_mesh_by_thickness(
                field,
                wall_thickness=wall_thickness_field
                if wall_thickness_field is not None
                else float(wall_thickness),
                spacing=spacing,
                material_mask=material_mask,
            )
    elif structure_type == "rod_negative":
        mesh = extract_rod_mesh(
            field,
            phase="negative",
            spacing=spacing,
            material_mask=material_mask,
        )
    elif structure_type == "rod_positive":
        mesh = extract_rod_mesh(
            field,
            phase="positive",
            spacing=spacing,
            material_mask=material_mask,
        )
    else:
        raise ValueError("structure_type must be sheet, rod_negative, or rod_positive")

    # Convert the raw voxel-aligned surface into a smoother, presentation-ready
    # TPMS mesh before it is clipped/translated and written to STL.
    mesh = _postprocess_generated_mesh(mesh, quality=quality)

    payload.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if generation_domain == "boundary":
        # Marching cubes may place surface vertices up to half a voxel outside
        # the sampled grid. Keep browser previews inside the original bounds.
        mesh.vertices = np.clip(
            mesh.vertices,
            np.zeros(3, dtype=np.float64),
            np.array([domain_size_x, domain_size_y, domain_size_z], dtype=np.float64),
        )
        mesh.apply_translation(origin)

    output_file = payload.output_dir / f"{tpms_type}_{structure_type}.stl"

    mesh.export(output_file)

    return ModelGenerationResult(
        output_file=output_file,
        effective_level_set_offset=level_set_offset,
    )
