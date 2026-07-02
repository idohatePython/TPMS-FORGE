from dataclasses import dataclass
from pathlib import Path


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
    raise NotImplementedError("Slicing and G-code pipeline is not implemented yet.")

