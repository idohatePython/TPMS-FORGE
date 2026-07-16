from pathlib import Path

from algorithms.pipeline.slicing_gcode import normalize_gcode_filename


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
