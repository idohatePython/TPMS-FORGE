from __future__ import annotations

from typing import cast

import numpy as np
import shapely
import trimesh
from numpy.typing import NDArray

BoolArray = NDArray[np.bool_]
FloatArray = NDArray[np.float64]


def _points_inside_triangles_yz(
    points_yz: FloatArray,
    triangle_yz: FloatArray,
) -> BoolArray:
    a = triangle_yz[0]
    b = triangle_yz[1]
    c = triangle_yz[2]
    v0 = c - a
    v1 = b - a
    v2 = points_yz - a

    dot00 = float(np.dot(v0, v0))
    dot01 = float(np.dot(v0, v1))
    dot11 = float(np.dot(v1, v1))
    dot02 = v2 @ v0
    dot12 = v2 @ v1
    denominator = dot00 * dot11 - dot01 * dot01

    if abs(denominator) < 1e-12:
        return np.zeros(len(points_yz), dtype=np.bool_)

    inv_denominator = 1.0 / denominator
    u = (dot11 * dot02 - dot01 * dot12) * inv_denominator
    v = (dot00 * dot12 - dot01 * dot02) * inv_denominator
    return cast(BoolArray, (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1.0 + 1e-9))


def points_inside_closed_mesh(
    mesh: trimesh.Trimesh,
    points: FloatArray,
    *,
    chunk_size: int = 4096,
) -> BoolArray:
    """Classify points inside a watertight mesh using +X ray parity.

    This intentionally avoids trimesh.contains because the project does not
    currently depend on rtree. It is a conservative first implementation for
    closed STL boundary clipping.
    """

    if not mesh.is_watertight:
        raise ValueError("boundary mesh must be watertight to generate TPMS inside it")

    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    if triangles.size == 0:
        raise ValueError("boundary mesh has no triangles")

    triangle_yz = triangles[:, :, 1:3]
    triangle_yz_min = triangle_yz.min(axis=1)
    triangle_yz_max = triangle_yz.max(axis=1)
    result = np.zeros(len(points), dtype=np.bool_)

    for start in range(0, len(points), chunk_size):
        chunk = points[start : start + chunk_size]
        intersections = np.zeros(len(chunk), dtype=np.int32)
        yz = chunk[:, 1:3]
        x = chunk[:, 0]

        for triangle_index, projected in enumerate(triangle_yz):
            candidate = (
                (yz[:, 0] >= triangle_yz_min[triangle_index, 0] - 1e-9)
                & (yz[:, 0] <= triangle_yz_max[triangle_index, 0] + 1e-9)
                & (yz[:, 1] >= triangle_yz_min[triangle_index, 1] - 1e-9)
                & (yz[:, 1] <= triangle_yz_max[triangle_index, 1] + 1e-9)
            )
            if not np.any(candidate):
                continue

            inside_projection = _points_inside_triangles_yz(
                yz[candidate],
                projected,
            )
            if not np.any(inside_projection):
                continue

            candidate_indices = np.flatnonzero(candidate)[inside_projection]
            tri = triangles[triangle_index]
            normal = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            if abs(normal[0]) < 1e-12:
                continue

            y_values = yz[candidate_indices, 0]
            z_values = yz[candidate_indices, 1]
            intersection_x = (
                np.dot(normal, tri[0]) - normal[1] * y_values - normal[2] * z_values
            ) / normal[0]
            intersections[candidate_indices] += intersection_x > x[candidate_indices] + 1e-9

        result[start : start + chunk_size] = intersections % 2 == 1

    return result


def points_inside_closed_mesh_grid(
    mesh: trimesh.Trimesh,
    x_axis: NDArray[np.floating],
    y_axis: NDArray[np.floating],
    z_axis: NDArray[np.floating],
) -> BoolArray:
    """Classify an axis-aligned sample grid using batched +Z ray parity."""

    if not mesh.is_watertight:
        raise ValueError("boundary mesh must be watertight to generate TPMS inside it")

    triangles = np.asarray(mesh.triangles, dtype=np.float64)
    if triangles.size == 0:
        raise ValueError("boundary mesh has no triangles")

    x_values = np.asarray(x_axis, dtype=np.float64)
    y_values = np.asarray(y_axis, dtype=np.float64)
    z_values = np.asarray(z_axis, dtype=np.float64)
    result = np.zeros((len(x_values), len(y_values), len(z_values)), dtype=np.bool_)

    # A tiny deterministic offset keeps grid samples off shared triangle edges,
    # where two adjacent faces would otherwise count the same crossing twice.
    x_query = x_values + max(float(np.ptp(x_values)), 1.0) * 1e-10
    y_query = y_values + max(float(np.ptp(y_values)), 1.0) * 1.7e-10

    for triangle in triangles:
        projected = triangle[:, :2]
        x_start = int(np.searchsorted(x_query, projected[:, 0].min(), side="left"))
        x_stop = int(np.searchsorted(x_query, projected[:, 0].max(), side="right"))
        y_start = int(np.searchsorted(y_query, projected[:, 1].min(), side="left"))
        y_stop = int(np.searchsorted(y_query, projected[:, 1].max(), side="right"))
        if x_start >= x_stop or y_start >= y_stop:
            continue

        local_x, local_y = np.meshgrid(
            x_query[x_start:x_stop],
            y_query[y_start:y_stop],
            indexing="ij",
        )
        local_points = np.column_stack((local_x.ravel(), local_y.ravel()))
        inside_projection = _points_inside_triangles_yz(local_points, projected)
        if not np.any(inside_projection):
            continue

        edge_a = triangle[1] - triangle[0]
        edge_b = triangle[2] - triangle[0]
        normal = np.cross(edge_a, edge_b)
        if abs(normal[2]) < 1e-12:
            continue

        local_indices = np.flatnonzero(inside_projection)
        local_ix, local_iy = np.unravel_index(
            local_indices,
            (x_stop - x_start, y_stop - y_start),
        )
        query_x = local_points[local_indices, 0]
        query_y = local_points[local_indices, 1]
        intersection_z = (
            np.dot(normal, triangle[0]) - normal[0] * query_x - normal[1] * query_y
        ) / normal[2]

        crossings_below = z_values[None, :] < intersection_z[:, None] - 1e-9
        result[x_start + local_ix, y_start + local_iy, :] ^= crossings_below

    return result


def points_inside_projected_footprint(
    mesh: trimesh.Trimesh,
    points: FloatArray,
    *,
    check_z: bool = True,
) -> BoolArray:
    """Classify points inside the mesh XY convex footprint and Z bounds.

    This relaxed 2.5D boundary mode is intended for open, thin STL surfaces
    such as early insole scans where watertight 3D containment is unavailable.
    """

    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    if vertices.size == 0:
        raise ValueError("boundary mesh has no vertices")

    footprint = shapely.MultiPoint(vertices[:, :2]).convex_hull
    if footprint.is_empty or float(footprint.area) <= 0:
        raise ValueError("boundary mesh footprint could not be computed")

    points_xy = points[:, :2]
    inside_xy = shapely.contains_xy(footprint, points_xy[:, 0], points_xy[:, 1])
    if not check_z:
        return cast(BoolArray, inside_xy)

    z_min = float(vertices[:, 2].min())
    z_max = float(vertices[:, 2].max())
    inside_z = (points[:, 2] >= z_min - 1e-9) & (points[:, 2] <= z_max + 1e-9)
    return cast(BoolArray, inside_xy & inside_z)
