import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.config import settings


class SlicerUnavailableError(RuntimeError):
    pass


class SlicerExecutionError(RuntimeError):
    pass


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

    if settings.slicer_engine == "orca":
        return run_orca_slicer(payload)

    if settings.slicer_engine == "prusa":
        return run_prusa_slicer(payload)

    raise SlicerUnavailableError(f"Unsupported slicer engine: {settings.slicer_engine}")


def resolve_slicer_binary(binary_name: str, display_name: str) -> str:
    binary = Path(binary_name)
    if binary.exists():
        return str(binary)

    found = shutil.which(binary_name)
    if found is None:
        raise SlicerUnavailableError(
            f"{display_name} CLI was not found. Set the slicer path in .env or add it to PATH."
        )

    return found


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


def build_orca_settings_file(payload: SlicingGcodeInput) -> Path:
    profile: dict[str, object] = {}
    if settings.orca_process_profile is not None:
        if not settings.orca_process_profile.exists():
            raise SlicerUnavailableError(
                f"Configured OrcaSlicer process profile does not exist: "
                f"{settings.orca_process_profile}"
            )
        profile.update(json.loads(settings.orca_process_profile.read_text(encoding="utf-8")))

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
    })

    settings_file = payload.output_dir / "tpms_forge_orca_settings.json"
    settings_file.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return settings_file


def build_orca_machine_file(payload: SlicingGcodeInput) -> Path | None:
    if settings.orca_machine_profile is None:
        return None
    if not settings.orca_machine_profile.exists():
        raise SlicerUnavailableError(
            f"Configured OrcaSlicer machine profile does not exist: "
            f"{settings.orca_machine_profile}"
        )

    profile = json.loads(settings.orca_machine_profile.read_text(encoding="utf-8"))
    profile["printer_settings_id"] = profile.get("printer_settings_id") or profile.get("name", "")

    layer_change_gcode = str(profile.get("layer_change_gcode", ""))
    if "G92 E0" not in layer_change_gcode:
        profile["layer_change_gcode"] = f"{layer_change_gcode.rstrip()}\nG92 E0\n"

    machine_file = payload.output_dir / "tpms_forge_orca_machine.json"
    machine_file.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return machine_file


def append_existing_profile(
    command: list[str],
    option: str,
    profile_path: Path | None,
    *,
    for_windows_executable: bool,
) -> None:
    if profile_path is None:
        return
    if not profile_path.exists():
        raise SlicerUnavailableError(
            f"Configured OrcaSlicer profile does not exist: {profile_path}"
        )
    command.extend(
        [
            option,
            to_subprocess_path(profile_path, for_windows_executable=for_windows_executable),
        ]
    )


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


def run_orca_slicer(payload: SlicingGcodeInput) -> SlicingGcodeResult:
    slicer_binary = resolve_slicer_binary(settings.orca_slicer_path, "OrcaSlicer")
    dynamic_machine = build_orca_machine_file(payload)
    dynamic_settings = build_orca_settings_file(payload)
    windows_executable = is_windows_executable(slicer_binary)

    command = [
        slicer_binary,
        "--slice",
        "0",
        "--outputdir",
        to_subprocess_path(payload.output_dir, for_windows_executable=windows_executable),
    ]
    if dynamic_machine is not None:
        command.extend(
            [
                "--load-settings",
                to_subprocess_path(
                    dynamic_machine,
                    for_windows_executable=windows_executable,
                ),
            ]
        )
    command.extend(
        [
            "--load-settings",
            to_subprocess_path(dynamic_settings, for_windows_executable=windows_executable),
        ]
    )
    append_existing_profile(
        command,
        "--load-filaments",
        settings.orca_filament_profile,
        for_windows_executable=windows_executable,
    )
    command.append(
        to_subprocess_path(payload.input_file, for_windows_executable=windows_executable)
    )

    run_slicer_command(command, "OrcaSlicer")
    output_file = find_gcode_file(payload.output_dir, payload.input_file)
    if not output_file.exists():
        raise SlicerExecutionError("OrcaSlicer finished without producing a G-code file.")

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
        message = result.stderr or result.stdout or "Slicer failed without output."
        raise SlicerExecutionError(f"{display_name} failed: {message}")
