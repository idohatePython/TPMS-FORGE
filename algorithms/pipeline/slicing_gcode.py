import json
import math
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import shapely
import trimesh

from backend.app.core.config import settings


class SlicerUnavailableError(RuntimeError):
    pass


class SlicerExecutionError(RuntimeError):
    pass


class VspToolPath(Protocol):
    points: Any
    width: float


WINDOWS_ORCA_CANDIDATES = (
    "/mnt/e/OrcaSlicer/orca-slicer.exe",
    "/mnt/e/OrcaSlicer/OrcaSlicer.exe",
    "/mnt/c/Program Files/OrcaSlicer/OrcaSlicer.exe",
    "/mnt/c/Program Files/Orca-Slicer/OrcaSlicer.exe",
    "/mnt/c/Program Files/OrcaSlicer/orca-slicer.exe",
    "/mnt/c/Program Files (x86)/OrcaSlicer/OrcaSlicer.exe",
    "/mnt/c/Users/sadbread/AppData/Local/OrcaSlicer/OrcaSlicer.exe",
    "/mnt/c/Users/sadbread/AppData/Local/Programs/OrcaSlicer/OrcaSlicer.exe",
)


@dataclass(frozen=True)
class SlicingGcodeInput:
    input_file: Path
    output_dir: Path
    params: dict[str, object]


@dataclass(frozen=True)
class SlicingGcodeResult:
    gcode_file: Path
    preview_file: Path | None = None


def run_slicing_gcode(payload: SlicingGcodeInput) -> SlicingGcodeResult:
    payload.output_dir.mkdir(parents=True, exist_ok=True)

    requested_engine = str(payload.params.get("slicing_engine", settings.slicer_engine))
    if requested_engine == "vsp":
        return run_vsp_slicer(payload)

    if requested_engine == "orca":
        return run_orca_slicer(payload)

    if requested_engine == "prusa":
        return run_prusa_slicer(payload)

    raise SlicerUnavailableError(f"Unsupported slicer engine: {requested_engine}")


def vsp_project_path() -> Path:
    if settings.vsp_slicer_path is not None:
        return settings.vsp_slicer_path
    return Path(
        "/mnt/d/xwechat_files/wxid_gxvvxkt2zxde22_2eb8/msg/file/2026-07/"
        "vsp_benchmark_test2.0(1)"
    )


def ensure_vsp_import_path() -> Path:
    project_path = vsp_project_path()
    source_path = project_path / "src"
    if not source_path.exists():
        raise SlicerUnavailableError(
            f"VSP slicer source was not found. Set VSP_SLICER_PATH in .env. Tried: "
            f"{source_path}"
        )

    source_path_text = str(source_path)
    if source_path_text not in sys.path:
        sys.path.insert(0, source_path_text)
    return project_path


def write_vsp_gcode(
    output_file: Path,
    *,
    paths_by_layer: list[tuple[float, list[VspToolPath]]],
    line_width: float,
    layer_height: float,
    print_speed: float,
    travel_speed: float,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
) -> None:
    feed_print = print_speed * 60
    feed_travel = travel_speed * 60
    extrusion_per_mm = max(line_width * layer_height * 0.045, 0.001)
    lines = [
        "; TPMS-FORGE VSP in-house toolpath",
        "; Generated from rasterized cross-sections of the selected STL/OBJ.",
        "; Experimental VSP variable-width centerline toolpath.",
        f"; VSP placement offset: X{offset_x:.3f} Y{offset_y:.3f}",
        "G21 ; units in millimeters",
        "G90 ; absolute coordinates",
        "M83 ; relative extrusion",
        "G92 E0",
    ]

    for layer_index, (z_mm, paths) in enumerate(paths_by_layer):
        lines.append(";LAYER_CHANGE")
        lines.append(f";LAYER:{layer_index}")
        lines.append(f";Z:{z_mm:.3f}")
        lines.append(f";HEIGHT:{layer_height:.3f}")
        lines.append(";TYPE:VSP Toolpath")
        lines.append(f"G0 Z{z_mm:.3f} F{feed_travel:.0f}")
        for path in paths:
            points = path.points
            if len(points) < 2:
                continue
            path_width = float(path.width)
            first_x = float(points[0][0]) + offset_x
            first_y = float(points[0][1]) + offset_y
            lines.append(f"G0 X{first_x:.3f} Y{first_y:.3f} F{feed_travel:.0f}")
            for point in points[1:]:
                x = float(point[0]) + offset_x
                y = float(point[1]) + offset_y
                distance = math.hypot(x - first_x, y - first_y)
                width_ratio = max(path_width / max(line_width, 0.001), 0.25)
                segment_extrusion = distance * extrusion_per_mm * width_ratio
                lines.append(
                    f"G1 X{x:.3f} Y{y:.3f} E{segment_extrusion:.5f} F{feed_print:.0f}"
                )
                first_x, first_y = x, y
        lines.append("G92 E0")

    lines.extend(["M104 S0", "M140 S0", "G0 X0 Y0", "M84", ""])
    output_file.write_text("\n".join(lines), encoding="utf-8")


def float_param(params: dict[str, object], key: str, default: float) -> float:
    value = params.get(key, default)
    if isinstance(value, int | float | str):
        return float(value)
    return default


def vsp_printable_area() -> tuple[float, float, float, float]:
    """Return configured printer bounds as min_x, max_x, min_y, max_y."""

    if settings.orca_machine_profile is None:
        return (0.0, 250.0, 0.0, 250.0)

    try:
        profile = load_orca_profile(settings.orca_machine_profile)
        points = profile.get("printable_area")
        if not isinstance(points, list):
            raise ValueError
        coordinates = [
            tuple(float(value) for value in str(point).lower().split("x", maxsplit=1))
            for point in points
        ]
        if not coordinates or any(len(point) != 2 for point in coordinates):
            raise ValueError
        x_values = [point[0] for point in coordinates]
        y_values = [point[1] for point in coordinates]
        return (min(x_values), max(x_values), min(y_values), max(y_values))
    except (OSError, TypeError, ValueError, json.JSONDecodeError, SlicerUnavailableError):
        return (0.0, 250.0, 0.0, 250.0)


def _rasterize_mesh_section(
    mesh: trimesh.Trimesh,
    *,
    z_mm: float,
    x_mesh: np.ndarray,
    y_mesh: np.ndarray,
) -> np.ndarray:
    section = mesh.section(
        plane_origin=np.array([0.0, 0.0, z_mm]),
        plane_normal=np.array([0.0, 0.0, 1.0]),
    )
    mask = np.zeros(x_mesh.shape, dtype=np.bool_)
    if section is None:
        return mask

    query_x = x_mesh.ravel()
    query_y = y_mesh.ravel()
    close_tolerance = max(float(np.ptp(x_mesh)), float(np.ptp(y_mesh)), 1.0) * 1e-7
    for discrete in section.discrete:
        loop = np.asarray(discrete, dtype=np.float64)
        if len(loop) < 4 or np.linalg.norm(loop[0] - loop[-1]) > close_tolerance:
            continue
        polygon = shapely.Polygon(loop[:, :2])
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if polygon.is_empty:
            continue
        inside = shapely.contains_xy(polygon, query_x, query_y).reshape(mask.shape)
        mask ^= inside
    return mask

def run_vsp_slicer(payload: SlicingGcodeInput) -> SlicingGcodeResult:
    ensure_vsp_import_path()

    from vsp_benchmark.model import GridSpec, SliceData
    from vsp_benchmark.paths import generate_paths

    layer_height = float_param(payload.params, "layer_height", 0.2)
    line_width = float_param(payload.params, "line_width", 0.42)
    print_speed = float_param(payload.params, "print_speed", 60)
    travel_speed = float_param(payload.params, "travel_speed", 150)
    loaded = trimesh.load_mesh(payload.input_file, process=False)
    if isinstance(loaded, trimesh.Scene):
        loaded = loaded.dump(concatenate=True)
    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        raise SlicerExecutionError("VSP could not read the selected STL/OBJ as a mesh.")

    bounds = np.asarray(loaded.bounds, dtype=np.float64)
    model_min = bounds[0]
    model_max = bounds[1]
    model_size = model_max - model_min
    if np.any(model_size <= 0):
        raise SlicerExecutionError("VSP requires a model with positive X, Y, and Z dimensions.")

    xy_span = float(max(model_size[0], model_size[1]))
    grid_spacing = max(line_width / 2.0, 0.1)
    grid_resolution = max(96, min(600, int(math.ceil(xy_span / grid_spacing)) + 1))
    x_center = float((model_min[0] + model_max[0]) / 2.0)
    y_center = float((model_min[1] + model_max[1]) / 2.0)
    half_span = xy_span / 2.0 + grid_spacing
    grid = GridSpec(
        x_min=x_center - half_span,
        x_max=x_center + half_span,
        y_min=y_center - half_span,
        y_max=y_center + half_span,
        resolution=grid_resolution,
    )
    x_values = np.linspace(grid.x_min, grid.x_max, grid.resolution)
    y_values = np.linspace(grid.y_min, grid.y_max, grid.resolution)
    x_mesh, y_mesh = np.meshgrid(x_values, y_values)

    bed_min_x, bed_max_x, bed_min_y, bed_max_y = vsp_printable_area()
    offset_x = (bed_min_x + bed_max_x) / 2.0 - x_center
    offset_y = (bed_min_y + bed_max_y) / 2.0 - y_center
    layer_count = max(1, int(math.ceil(float(model_size[2]) / layer_height)))
    d_values = np.full(x_mesh.shape, line_width / 2.0, dtype=np.float64)
    field_values = np.zeros(x_mesh.shape, dtype=np.float64)
    paths_by_layer: list[tuple[float, list[VspToolPath]]] = []

    for layer_index in range(layer_count):
        z_mm = min(float(model_min[2] + (layer_index + 0.5) * layer_height), float(model_max[2]))
        target_mask = _rasterize_mesh_section(
            loaded,
            z_mm=z_mm,
            x_mesh=x_mesh,
            y_mesh=y_mesh,
        )
        if not np.any(target_mask):
            continue
        slice_data = SliceData(
            case=f"TPMS-FORGE STL layer {layer_index}",
            z=z_mm,
            grid=grid,
            x_values=x_values,
            y_values=y_values,
            x_mesh=x_mesh,
            y_mesh=y_mesh,
            field_values=field_values,
            d_values=d_values,
            target_mask=target_mask,
        )
        paths_by_layer.append((z_mm, cast("list[VspToolPath]", generate_paths(slice_data, "VSP"))))

    if not paths_by_layer or not any(paths for _, paths in paths_by_layer):
        raise SlicerExecutionError("VSP found no printable closed cross-sections in the model.")

    output_file = payload.output_dir / f"{payload.input_file.stem}_vsp.gcode"
    write_vsp_gcode(
        output_file,
        paths_by_layer=paths_by_layer,
        line_width=line_width,
        layer_height=layer_height,
        print_speed=print_speed,
        travel_speed=travel_speed,
        offset_x=offset_x,
        offset_y=offset_y,
    )

    if not output_file.exists():
        raise SlicerExecutionError("VSP slicer finished without producing a G-code file.")
    return SlicingGcodeResult(gcode_file=output_file)


def candidate_slicer_binaries(binary_name: str, display_name: str) -> list[str]:
    candidates = [binary_name]
    if display_name == "OrcaSlicer":
        candidates.extend(
            [
                "OrcaSlicer",
                "orca-slicer.AppImage",
                *WINDOWS_ORCA_CANDIDATES,
            ]
        )
    return candidates


def resolve_slicer_binary(binary_name: str, display_name: str) -> str:
    attempted: list[str] = []

    for candidate in candidate_slicer_binaries(binary_name, display_name):
        attempted.append(candidate)
        binary = Path(candidate)
        if binary.exists():
            return str(binary)

        found = shutil.which(candidate)
        if found is not None:
            return found

    attempted_text = ", ".join(dict.fromkeys(attempted))
    env_name = "ORCA_SLICER_PATH" if display_name == "OrcaSlicer" else "PRUSA_SLICER_PATH"
    raise SlicerUnavailableError(
        f"{display_name} CLI was not found. Set {env_name} in .env to your slicer executable "
        f"path, or add it to PATH. Tried: {attempted_text}"
    )


def resolve_configured_slicer_binary() -> str:
    if settings.slicer_engine == "orca":
        return resolve_slicer_binary(settings.orca_slicer_path, "OrcaSlicer")
    if settings.slicer_engine == "prusa":
        return resolve_slicer_binary(settings.prusa_slicer_path, "PrusaSlicer")
    raise SlicerUnavailableError(f"Unsupported slicer engine: {settings.slicer_engine}")


def is_windows_executable(executable: str) -> bool:
    return executable.lower().endswith(".exe")


def to_subprocess_path(path: Path, *, for_windows_executable: bool) -> str:
    resolved_path = path.resolve()
    if not for_windows_executable:
        return str(resolved_path)

    result = subprocess.run(
        ["wslpath", "-w", str(resolved_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    return str(resolved_path)


def candidate_inherited_profile_paths(profile_path: Path, inherited_name: str) -> list[Path]:
    return [
        profile_path.with_name(f"{inherited_name}.json"),
        profile_path.parent / "base" / f"{inherited_name}.json",
        profile_path.parent.parent / "base" / f"{inherited_name}.json",
    ]


def resolve_inherited_profile_path(profile_path: Path, inherited_name: str) -> Path:
    for candidate in candidate_inherited_profile_paths(profile_path, inherited_name):
        if candidate.exists():
            return candidate

    raise SlicerUnavailableError(
        f"OrcaSlicer profile inheritance could not be resolved: "
        f"{profile_path} inherits {inherited_name}"
    )


def load_orca_profile(profile_path: Path, seen: set[Path] | None = None) -> dict[str, object]:
    if not profile_path.exists():
        raise SlicerUnavailableError(
            f"Configured OrcaSlicer profile does not exist: {profile_path}"
        )

    resolved_path = profile_path.resolve()
    if seen is None:
        seen = set()
    if resolved_path in seen:
        raise SlicerUnavailableError(f"OrcaSlicer profile has circular inheritance: {profile_path}")
    seen.add(resolved_path)

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise SlicerUnavailableError(f"OrcaSlicer profile must be a JSON object: {profile_path}")
    inherited_name = profile.get("inherits")
    if not isinstance(inherited_name, str) or not inherited_name.strip():
        return profile

    parent_path = resolve_inherited_profile_path(profile_path, inherited_name.strip())
    merged = load_orca_profile(parent_path, seen)
    merged.update(profile)
    merged.pop("inherits", None)
    return merged


def build_orca_settings_file(payload: SlicingGcodeInput) -> Path:
    profile: dict[str, object] = {}
    if settings.orca_process_profile is not None:
        profile.update(load_orca_profile(settings.orca_process_profile))

    profile.setdefault("type", "process")
    profile.setdefault("name", "TPMS-FORGE Dynamic Process")
    profile.setdefault("from", "user")
    profile.setdefault("setting_id", "TPMS-FORGE")
    profile.setdefault("instantiation", "true")

    profile.update({
        "layer_height": str(payload.params.get("layer_height", 0.2)),
        "line_width": str(payload.params.get("line_width", 0.42)),
        "wall_loops": str(payload.params.get("wall_loops", 2)),
        "top_shell_layers": str(payload.params.get("top_shell_layers", 4)),
        "bottom_shell_layers": str(payload.params.get("bottom_shell_layers", 3)),
        "sparse_infill_density": f"{payload.params.get('sparse_infill_density', 15)}%",
        "sparse_infill_pattern": str(payload.params.get("sparse_infill_pattern", "gyroid")),
        "enable_support": "1" if payload.params.get("enable_support", False) else "0",
        "support_type": str(payload.params.get("support_type", "normal(auto)")),
        "brim_width": str(payload.params.get("brim_width", 0)),
        "default_speed": str(payload.params.get("print_speed", 60)),
        "travel_speed": str(payload.params.get("travel_speed", 150)),
        "print_settings_id": "TPMS-FORGE Dynamic Process",
    })

    settings_file = payload.output_dir / "tpms_forge_orca_settings.json"
    settings_file.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return settings_file


def build_orca_machine_file(payload: SlicingGcodeInput) -> Path | None:
    if settings.orca_machine_profile is None:
        return None

    profile = load_orca_profile(settings.orca_machine_profile)
    profile["printer_settings_id"] = profile.get("printer_settings_id") or profile.get("name", "")

    layer_change_gcode = str(profile.get("layer_change_gcode", ""))
    if "G92 E0" not in layer_change_gcode:
        profile["layer_change_gcode"] = f"{layer_change_gcode.rstrip()}\nG92 E0\n"

    machine_file = payload.output_dir / "tpms_forge_orca_machine.json"
    machine_file.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return machine_file


def build_orca_filament_file(payload: SlicingGcodeInput) -> Path | None:
    if settings.orca_filament_profile is None:
        return None

    profile = load_orca_profile(settings.orca_filament_profile)
    nozzle_temperature = str(payload.params.get("nozzle_temperature", 220))
    bed_temperature = str(payload.params.get("bed_temperature", 60))
    filament_type = str(payload.params.get("filament_type", "PLA"))
    profile.setdefault("type", "filament")
    profile.setdefault("name", f"TPMS-FORGE {filament_type}")
    profile.update(
        {
            "filament_settings_id": [profile.get("name", f"TPMS-FORGE {filament_type}")],
            "filament_type": [filament_type],
            "nozzle_temperature": [nozzle_temperature],
            "nozzle_temperature_initial_layer": [nozzle_temperature],
            "bed_temperature": [bed_temperature],
            "bed_temperature_initial_layer": [bed_temperature],
            "compatible_printers": [],
        }
    )

    filament_file = payload.output_dir / "tpms_forge_orca_filament.json"
    filament_file.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return filament_file


def find_gcode_file(output_dir: Path, input_file: Path) -> Path:
    candidates = sorted(
        output_dir.glob("*.gcode"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return candidates[0]
    return output_dir / f"{input_file.stem}.gcode"


def normalize_gcode_filename(gcode_file: Path, input_file: Path) -> Path:
    expected_file = gcode_file.with_name(f"{input_file.stem}.gcode")
    if gcode_file == expected_file:
        return gcode_file

    if expected_file.exists():
        expected_file.unlink()
    gcode_file.replace(expected_file)
    return expected_file


def windows_staging_dir(output_dir: Path) -> Path:
    root = settings.orca_windows_work_dir
    if root is None:
        root = Path("/mnt/e/TPMS-FORGE-slicer-cache")

    stage = root / f"slice-{output_dir.name}-{uuid.uuid4().hex[:8]}"
    stage.mkdir(parents=True, exist_ok=True)
    return stage


def copy_result_to_output_dir(gcode_file: Path, output_dir: Path, input_file: Path) -> Path:
    output_file = output_dir / f"{input_file.stem}.gcode"
    if output_file.exists():
        output_file.unlink()
    shutil.copy2(gcode_file, output_file)
    return output_file


def run_orca_slicer(payload: SlicingGcodeInput) -> SlicingGcodeResult:
    slicer_binary = resolve_slicer_binary(settings.orca_slicer_path, "OrcaSlicer")
    windows_executable = is_windows_executable(slicer_binary)
    slicer_payload = payload
    stage_dir: Path | None = None

    if windows_executable:
        stage_dir = windows_staging_dir(payload.output_dir)
        staged_input = stage_dir / payload.input_file.name
        shutil.copy2(payload.input_file, staged_input)
        slicer_payload = SlicingGcodeInput(
            input_file=staged_input,
            output_dir=stage_dir,
            params=payload.params,
        )

    dynamic_machine = build_orca_machine_file(slicer_payload)
    dynamic_settings = build_orca_settings_file(slicer_payload)
    dynamic_filament = build_orca_filament_file(slicer_payload)

    command = [
        slicer_binary,
        "--slice",
        "0",
        "--outputdir",
        to_subprocess_path(slicer_payload.output_dir, for_windows_executable=windows_executable),
    ]
    settings_paths = []
    if dynamic_machine is not None:
        settings_paths.append(
            to_subprocess_path(
                dynamic_machine,
                for_windows_executable=windows_executable,
            )
        )
    settings_paths.append(
        to_subprocess_path(dynamic_settings, for_windows_executable=windows_executable)
    )
    if dynamic_filament is not None:
        settings_paths.append(
            to_subprocess_path(dynamic_filament, for_windows_executable=windows_executable)
        )
    command.extend(["--load-settings", ";".join(settings_paths)])
    command.append(
        to_subprocess_path(slicer_payload.input_file, for_windows_executable=windows_executable)
    )

    run_slicer_command(command, "OrcaSlicer")
    output_file = find_gcode_file(slicer_payload.output_dir, slicer_payload.input_file)
    if not output_file.exists():
        raise SlicerExecutionError("OrcaSlicer finished without producing a G-code file.")

    if stage_dir is not None:
        return SlicingGcodeResult(
            gcode_file=copy_result_to_output_dir(
                output_file,
                payload.output_dir,
                payload.input_file,
            )
        )

    return SlicingGcodeResult(
        gcode_file=normalize_gcode_filename(output_file, payload.input_file)
    )


def run_prusa_slicer(payload: SlicingGcodeInput) -> SlicingGcodeResult:
    slicer_binary = resolve_slicer_binary(settings.prusa_slicer_path, "PrusaSlicer")

    output_file = payload.output_dir / f"{payload.input_file.stem}.gcode"
    command = [
        slicer_binary,
        "--export-gcode",
        "--output",
        str(output_file),
        "--layer-height",
        str(payload.params.get("layer_height", 0.2)),
        "--extrusion-width",
        str(payload.params.get("line_width", 0.42)),
        "--perimeter-speed",
        str(payload.params.get("print_speed", 60)),
        str(payload.input_file),
    ]

    run_slicer_command(command, "PrusaSlicer")

    if not output_file.exists():
        raise SlicerExecutionError("PrusaSlicer finished without producing a G-code file.")

    return SlicingGcodeResult(gcode_file=output_file)


def run_slicer_command(command: list[str], display_name: str) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
        timeout=settings.slicer_timeout_seconds,
    )

    if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        command_text = " ".join(command)
        message_parts = [
            f"{display_name} failed with exit code {result.returncode}.",
            f"Command: {command_text}",
        ]
        if stdout:
            message_parts.append(f"stdout: {stdout}")
        if stderr:
            message_parts.append(f"stderr: {stderr}")
        if not stdout and not stderr:
            message_parts.append("Slicer failed without output.")

        raise SlicerExecutionError(" ".join(message_parts))
