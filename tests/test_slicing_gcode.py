from pathlib import Path

from algorithms.pipeline import slicing_gcode
from algorithms.pipeline.slicing_gcode import (
    SlicingGcodeInput,
    normalize_gcode_filename,
    resolve_slicer_binary,
    run_slicing_gcode,
)


def test_normalize_gcode_filename_matches_input_model_stem(tmp_path: Path) -> None:
    input_file = tmp_path / "Phone Holder.stl"
    gcode_file = tmp_path / "plate_1.gcode"
    input_file.write_text("solid phone holder", encoding="utf-8")
    gcode_file.write_text("G1 X1 Y1", encoding="utf-8")

    normalized = normalize_gcode_filename(gcode_file, input_file)

    assert normalized == tmp_path / "Phone Holder.gcode"
    assert normalized.read_text(encoding="utf-8") == "G1 X1 Y1"
    assert not gcode_file.exists()


def test_normalize_gcode_filename_replaces_existing_output(tmp_path: Path) -> None:
    input_file = tmp_path / "part.stl"
    gcode_file = tmp_path / "plate_1.gcode"
    existing_output = tmp_path / "part.gcode"
    input_file.write_text("solid part", encoding="utf-8")
    gcode_file.write_text("new gcode", encoding="utf-8")
    existing_output.write_text("old gcode", encoding="utf-8")

    normalized = normalize_gcode_filename(gcode_file, input_file)

    assert normalized == existing_output
    assert existing_output.read_text(encoding="utf-8") == "new gcode"
    assert not gcode_file.exists()


def test_resolve_slicer_binary_accepts_absolute_path(tmp_path: Path) -> None:
    slicer = tmp_path / "orca-slicer.exe"
    slicer.write_text("", encoding="utf-8")

    assert resolve_slicer_binary(str(slicer), "OrcaSlicer") == str(slicer)


def test_run_vsp_slicer_writes_gcode(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "vsp" / "src" / "vsp_benchmark"
    source_root.mkdir(parents=True)
    (source_root / "__init__.py").write_text("", encoding="utf-8")
    (source_root / "model.py").write_text(
        """
from dataclasses import dataclass
TARGET_MASK_FIELD_MARGIN = 0

@dataclass(frozen=True)
class GridSpec:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    resolution: int

    @property
    def dx(self):
        return (self.x_max - self.x_min) / (self.resolution - 1)

    @property
    def dy(self):
        return (self.y_max - self.y_min) / (self.resolution - 1)

class SliceData:
    def __init__(self, **values):
        self.__dict__.update(values)
""",
        encoding="utf-8",
    )
    (source_root / "paths.py").write_text(
        """
import numpy as np

class ToolPath:
    def __init__(self):
        self.points = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
        self.width = 0.42

def generate_paths(_slice_data, _baseline):
    return [ToolPath()]
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(slicing_gcode.settings, "vsp_slicer_path", tmp_path / "vsp")

    input_file = tmp_path / "part.stl"
    slicing_gcode.trimesh.creation.box(extents=(10.0, 8.0, 2.0)).export(input_file)
    result = run_slicing_gcode(
        SlicingGcodeInput(
            input_file=input_file,
            output_dir=tmp_path / "out",
            params={"slicing_engine": "vsp", "layer_height": 0.2, "line_width": 0.42},
        )
    )

    assert result.gcode_file.name == "part_vsp.gcode"
    gcode = result.gcode_file.read_text(encoding="utf-8")
    assert "TPMS-FORGE VSP in-house toolpath" in gcode
    assert "; VSP placement offset: X125.000 Y125.000" in gcode
    extrusion_moves = [line for line in gcode.splitlines() if line.startswith("G1 ")]
    assert "E0.00378" in extrusion_moves[0]
    assert "E0.00378" in extrusion_moves[1]
