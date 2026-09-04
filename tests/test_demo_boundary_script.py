from __future__ import annotations

import subprocess
from pathlib import Path

import trimesh


def test_generate_demo_boundary_script_creates_insole_stls(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/generate-demo-boundary.py",
            "--output-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    open_file = tmp_path / "insole-open-surface.stl"
    solid_file = tmp_path / "insole-solid-boundary.stl"
    open_mesh = trimesh.load_mesh(open_file, process=True)
    solid_mesh = trimesh.load_mesh(solid_file, process=True)

    assert "Open insole surface" in result.stdout
    assert open_file.exists()
    assert solid_file.exists()
    assert not open_mesh.is_watertight
    assert solid_mesh.is_watertight
