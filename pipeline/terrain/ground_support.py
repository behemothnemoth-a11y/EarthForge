"""Ground interpolation with immutable observations and explicit support limits.

Never feed interpolated values back into the observation set. Unsupported
queries remain NaN and must block geometry promotion, not be silently filled.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree


def interpolate_ground(points, elevations, queries, *, max_distance_m=3.0,
                       max_triangle_edge_m=20.0):
    points = np.asarray(points, dtype=float)
    elevations = np.asarray(elevations, dtype=float)
    queries = np.asarray(queries, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) != len(elevations):
        raise ValueError('Expected Nx2 ground coordinates and N elevations')
    if not (np.isfinite(points).all() and np.isfinite(elevations).all()):
        raise ValueError('Ground observations must be finite')
    if max_distance_m <= 0 or max_triangle_edge_m <= 0:
        raise ValueError('Support limits must be positive')
    # Stable aggregation also makes reversed input order produce the same TIN.
    xy, inv = np.unique(points, axis=0, return_inverse=True)
    if len(xy) < 3:
        raise ValueError('At least three distinct ground observations required')
    order = np.argsort(inv, kind='stable')
    starts = np.r_[0, np.flatnonzero(np.diff(inv[order])) + 1]
    heights = np.array([np.median(elevations[group]) for group in np.split(order, starts[1:])])
    tri = Delaunay(xy)
    simplex = tri.find_simplex(queries)
    distance = cKDTree(xy).query(queries)[0]
    vertices = xy[tri.simplices[np.maximum(simplex, 0)]]
    longest_edge = np.max(np.stack([
        np.linalg.norm(vertices[:, i] - vertices[:, j], axis=1)
        for i, j in [(0, 1), (1, 2), (2, 0)]
    ]), axis=0)
    supported = ((simplex >= 0) & (distance <= max_distance_m)
                 & (longest_edge <= max_triangle_edge_m))
    values = np.asarray(LinearNDInterpolator(tri, heights)(queries))
    values[~supported] = np.nan
    return values, {'supported': supported, 'nearest_ground_m': distance,
                    'longest_triangle_edge_m': longest_edge}


def observed_grid(points, elevations, shape, xmin, zmin, resolution):
    """Median only actual returns; leave every unobserved bin NaN."""
    bins = {}
    for (x, z), elevation in zip(points, elevations):
        ix, iz = round((float(x)-xmin)/resolution), round((float(z)-zmin)/resolution)
        if 0 <= iz < shape[0] and 0 <= ix < shape[1]:
            bins.setdefault((iz, ix), []).append(float(elevation))
    result = np.full(shape, np.nan, dtype=float)
    for key, values in bins.items():
        result[key] = np.median(values)
    return result


def check_surface_residual(surface, reference, mask, tolerance_m=.75):
    """Fail closed when a reviewed surface exceeds its independent support."""
    values=np.asarray(surface)[mask]; support=np.asarray(reference)[mask]
    if not len(values) or not np.isfinite(values).all() or not np.isfinite(support).all():
        raise ValueError('Review surface has missing source support')
    residual=values-support
    maximum=float(np.max(np.abs(residual)))
    if maximum>tolerance_m:
        raise ValueError(f'Ground support residual {maximum:.3f} m exceeds {tolerance_m:.3f} m review gate')
    return {'samples':len(values),'max_abs_residual_m':maximum,'tolerance_m':tolerance_m}
