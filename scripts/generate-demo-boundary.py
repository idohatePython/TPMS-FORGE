from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh


def insole_width(
    y: np.ndarray,
    length: float,
    heel_width: float,
    mid_width: float,
    toe_width: float,
) -> np.ndarray:
    normalized = y / length
    heel_to_mid = heel_width + (mid_width - heel_width) * np.clip(normalized / 0.45, 0, 1)
    mid_to_toe = mid_width + (toe_width - mid_width) * np.clip((normalized - 0.45) / 0.55, 0, 1)
    return np.where(normalized <= 0.45, heel_to_mid, mid_to_toe)


def insole_surface_z(x: np.ndarray, y: np.ndarray, length: float, width: np.ndarray) -> np.ndarray:
    arch = 2.2 * np.exp(-((y - length * 0.42) / (length * 0.17)) ** 2) * np.exp(
        -((x + width * 0.18) / np.maximum(width * 0.28, 1e-6)) ** 2
    )
    toe_lift = 1.2 * np.clip((y - length * 0.78) / (length * 0.22), 0, 1) ** 2
    heel_cup = -0.8 * np.exp(-((y - length * 0.08) / (length * 0.12)) ** 2)
    return arch + toe_lift + heel_cup


def create_open_insole_mesh(
    *,
    length: float = 240.0,
    heel_width: float = 58.0,
    mid_width: float = 74.0,
    toe_width: float = 92.0,
    rows: int = 64,
    columns: int = 18,
) -> trimesh.Trimesh:
    vertices: list[list[float]] = []
    for row in range(rows):
        y = length * row / (rows - 1)
        width = float(insole_width(np.array([y]), length, heel_width, mid_width, toe_width)[0])
        # Rounded heel and toe taper without degenerating to a single point.
        end_taper = 0.22 + 0.78 * (np.sin(np.pi * row / (rows - 1)) ** 0.32)
        row_half_width = width * end_taper / 2.0
        for column in range(columns):
            t = column / (columns - 1)
            x = (t - 0.5) * 2.0 * row_half_width
            edge_rounding = 0.5 + 0.5 * np.cos((t - 0.5) * np.pi)
            z = float(insole_surface_z(np.array([x]), np.array([y]), length, np.array([width]))[0])
            z -= 0.35 * (1.0 - edge_rounding)
            vertices.append([x, y, z])

    faces: list[list[int]] = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            a = row * columns + column
            b = a + 1
            c = a + columns
            d = c + 1
            faces.append([a, c, b])
            faces.append([b, c, d])

    return trimesh.Trimesh(vertices=np.array(vertices), faces=np.array(faces), process=True)


def create_solid_insole_mesh(
    open_mesh: trimesh.Trimesh,
    *,
    thickness: float = 6.0,
) -> trimesh.Trimesh:
    top_vertices = np.asarray(open_mesh.vertices, dtype=np.float64)
    bottom_vertices = top_vertices.copy()
    bottom_vertices[:, 2] -= thickness
    vertices = np.vstack([top_vertices, bottom_vertices])
    top_faces = np.asarray(open_mesh.faces, dtype=np.int64)
    bottom_faces = top_faces[:, ::-1] + len(top_vertices)

    edge_counts: dict[tuple[int, int], int] = {}
    for face in top_faces:
        for start, end in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            key = tuple(sorted((int(start), int(end))))
            edge_counts[key] = edge_counts.get(key, 0) + 1
    boundary_edges = [edge for edge, count in edge_counts.items() if count == 1]
    side_faces: list[list[int]] = []
    for edge_start, edge_end in boundary_edges:
        bottom_start = int(edge_start + len(top_vertices))
        bottom_end = int(edge_end + len(top_vertices))
        side_faces.append([int(edge_start), int(edge_end), bottom_start])
        side_faces.append([int(edge_end), bottom_end, bottom_start])

    faces = np.vstack([top_faces, bottom_faces, np.array(side_faces, dtype=np.int64)])
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate small demo STL boundary models for TPMS-FORGE.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/tpms-forge-demo-boundaries"),
        help="Directory where demo STL files will be written.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    open_mesh = create_open_insole_mesh()
    solid_mesh = create_solid_insole_mesh(open_mesh)

    open_file = args.output_dir / "insole-open-surface.stl"
    solid_file = args.output_dir / "insole-solid-boundary.stl"
    open_mesh.export(open_file)
    solid_mesh.export(solid_file)

    print(f"Open insole surface: {open_file}")
    print(f"Solid insole boundary: {solid_file}")
    print("Use footprint boundary mode for the open surface.")
    print("Use auto or closed boundary mode for the solid boundary.")


if __name__ == "__main__":
    main()
