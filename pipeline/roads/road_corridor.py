#!/usr/bin/env python3
from __future__ import annotations

from bisect import bisect_right
import argparse
import json
import math
from pathlib import Path
import sys
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.terrain.elevation_profile import ElevationProfile

Point2 = tuple[float, float]


def _point(value: Sequence[float]) -> Point2:
    if len(value) != 2:
        raise ValueError("Centerline points must contain exactly [x, z]")
    x, z = float(value[0]), float(value[1])
    if not math.isfinite(x) or not math.isfinite(z):
        raise ValueError("Centerline coordinates must be finite")
    return (x, z)


def validate_centerline(points: Iterable[Sequence[float]]) -> list[Point2]:
    out = [_point(p) for p in points]
    if len(out) < 2:
        raise ValueError("Road centerline requires at least two points")
    for a, b in zip(out, out[1:]):
        if math.hypot(b[0] - a[0], b[1] - a[1]) <= 1e-9:
            raise ValueError("Road centerline contains a zero-length segment")
    return out


def cumulative_stations(points: Sequence[Point2]) -> list[float]:
    stations = [0.0]
    total = 0.0
    for a, b in zip(points, points[1:]):
        total += math.hypot(b[0] - a[0], b[1] - a[1])
        stations.append(total)
    return stations


def _unit(dx: float, dz: float) -> Point2:
    length = math.hypot(dx, dz)
    if length <= 1e-12:
        raise ValueError("Cannot normalize a zero-length vector")
    return (dx / length, dz / length)


def _segment_tangent(points: Sequence[Point2], i: int) -> Point2:
    a, b = points[i], points[i + 1]
    return _unit(b[0] - a[0], b[1] - a[1])


def point_tangent_at_station(
    points: Sequence[Point2],
    stations: Sequence[float],
    station_m: float,
) -> tuple[Point2, Point2]:
    total = stations[-1]
    if station_m < -1e-9 or station_m > total + 1e-9:
        raise ValueError(f"Station {station_m:.3f} is outside road length 0..{total:.3f}")

    s = min(max(station_m, 0.0), total)

    for vertex_index in range(1, len(stations) - 1):
        if abs(s - stations[vertex_index]) <= 1e-9:
            incoming = _segment_tangent(points, vertex_index - 1)
            outgoing = _segment_tangent(points, vertex_index)
            sx, sz = incoming[0] + outgoing[0], incoming[1] + outgoing[1]
            if math.hypot(sx, sz) > 1e-6:
                tangent = _unit(sx, sz)
            else:
                tangent = outgoing
            return points[vertex_index], tangent

    if s >= total - 1e-9:
        return points[-1], _segment_tangent(points, len(points) - 2)

    i = max(0, bisect_right(stations, s) - 1)
    i = min(i, len(points) - 2)
    a, b = points[i], points[i + 1]
    segment_length = stations[i + 1] - stations[i]
    t = (s - stations[i]) / segment_length
    p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return p, _segment_tangent(points, i)


def sample_stations(total_length_m: float, interval_m: float, vertices: Sequence[float]) -> list[float]:
    if interval_m <= 0 or not math.isfinite(interval_m):
        raise ValueError("sample_interval_m must be a finite number greater than zero")
    samples = {0.0, float(total_length_m), *(float(v) for v in vertices)}
    cursor = interval_m
    while cursor < total_length_m - 1e-9:
        samples.add(round(cursor, 9))
        cursor += interval_m
    return sorted(samples)


def _positive(value: dict, key: str, default: float) -> float:
    raw = float(value.get(key, default))
    if raw < 0 or not math.isfinite(raw):
        raise ValueError(f"{key} must be a finite number >= 0")
    return raw


def normalize_cross_section(spec: dict | None) -> dict:
    spec = spec or {}
    roadway = _positive(spec, "roadway_width_m", 6.0)
    if roadway <= 0:
        raise ValueError("roadway_width_m must be greater than zero")
    return {
        "roadway_width_m": roadway,
        "curb_width_left_m": _positive(spec, "curb_width_left_m", 0.25),
        "curb_width_right_m": _positive(spec, "curb_width_right_m", 0.25),
        "sidewalk_width_left_m": _positive(spec, "sidewalk_width_left_m", 1.5),
        "sidewalk_width_right_m": _positive(spec, "sidewalk_width_right_m", 1.5),
    }


def _offset(point: Point2, normal: Point2, distance_m: float) -> Point2:
    return (point[0] + normal[0] * distance_m, point[1] + normal[1] * distance_m)


def _xyz(point: Point2, elevation_m: float) -> list[float]:
    return [round(point[0], 6), round(elevation_m, 6), round(point[1], 6)]


def build_corridor(spec: dict) -> dict:
    road_id = str(spec.get("road_id") or "").strip()
    if not road_id:
        raise ValueError("road_id is required")

    centerline = validate_centerline(spec["centerline"])
    vertex_stations = cumulative_stations(centerline)
    total_length = vertex_stations[-1]
    profile = ElevationProfile(spec["elevation_profile"])
    if profile.start_station_m > 0.0 + 1e-9 or profile.end_station_m < total_length - 1e-9:
        raise ValueError(
            "elevation_profile must cover the full centerline station range "
            f"0..{total_length:.3f} m"
        )

    cross = normalize_cross_section(spec.get("cross_section"))
    interval = float(spec.get("sample_interval_m", 1.0))
    stations = sample_stations(total_length, interval, vertex_stations)

    half_road = cross["roadway_width_m"] / 2.0
    left_curb_outer = half_road + cross["curb_width_left_m"]
    right_curb_outer = half_road + cross["curb_width_right_m"]
    left_sidewalk_outer = left_curb_outer + cross["sidewalk_width_left_m"]
    right_sidewalk_outer = right_curb_outer + cross["sidewalk_width_right_m"]

    rows = []
    for station in stations:
        point, tangent = point_tangent_at_station(centerline, vertex_stations, station)
        left_normal = (tangent[1], -tangent[0])
        y = profile.elevation_at(station)
        rows.append(
            {
                "station_m": round(station, 6),
                "center": _xyz(point, y),
                "tangent_xz": [round(tangent[0], 9), round(tangent[1], 9)],
                "left_normal_xz": [round(left_normal[0], 9), round(left_normal[1], 9)],
                "grade_percent": round(profile.grade_at(station) * 100.0, 6),
                "road_edge_left": _xyz(_offset(point, left_normal, half_road), y),
                "road_edge_right": _xyz(_offset(point, left_normal, -half_road), y),
                "curb_outer_left": _xyz(_offset(point, left_normal, left_curb_outer), y),
                "curb_outer_right": _xyz(_offset(point, left_normal, -right_curb_outer), y),
                "sidewalk_outer_left": _xyz(_offset(point, left_normal, left_sidewalk_outer), y),
                "sidewalk_outer_right": _xyz(_offset(point, left_normal, -right_sidewalk_outer), y),
            }
        )

    return {
        "schema_version": 1,
        "road_id": road_id,
        "name": spec.get("name"),
        "coordinate_space": "project_local_meters",
        "axis_convention": {
            "x_positive": "east",
            "z_positive": "south",
            "y_positive": "up",
        },
        "total_length_m": round(total_length, 6),
        "sample_interval_m": interval,
        "source_vertex_stations_m": [round(v, 6) for v in vertex_stations],
        "cross_section": cross,
        "elevation_summary": profile.summary(),
        "elevation_segments": profile.segment_grades(),
        "samples": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a measured EarthForge road/grade corridor from local-meter truth."
    )
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()

    spec = json.loads(args.input_json.read_text(encoding="utf-8"))
    result = build_corridor(spec)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {args.output_json} | {result['road_id']} | "
        f"{result['total_length_m']:.2f} m | {len(result['samples'])} samples | "
        f"max grade {result['elevation_summary']['max_abs_grade_percent']:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
