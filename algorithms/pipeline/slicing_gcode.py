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

    if settings.slicer_engine != "prusa":
        raise SlicerUnavailableError(f"Unsupported slicer engine: {settings.slicer_engine}")

    slicer_binary = shutil.which(settings.prusa_slicer_path)
    if slicer_binary is None:
        raise SlicerUnavailableError(
            "PrusaSlicer CLI was not found. Install PrusaSlicer and make `prusa-slicer` "
            "available in PATH, or set PRUSA_SLICER_PATH."
        )

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

    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
        timeout=settings.slicer_timeout_seconds,
    )

    if result.returncode != 0 or not output_file.exists():
        message = result.stderr or result.stdout or "Slicer failed without output."
        raise SlicerExecutionError(message)

    return SlicingGcodeResult(gcode_file=output_file)
