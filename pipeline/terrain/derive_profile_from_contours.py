#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

Point = tuple[float, float]


def _point(value: Sequence[float]) -> Point:
    if len(value) < 2:
        raise ValueError("Coordinate requires at least two values")
    x, z = float(value[0]), float(value[1])
    if not math.isfinite(x) or not math.isfinite(z):
        raise ValueError("Coordinates must be finite")
    return x, z


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _sub(a: Point, b: Point) -> Point:
    return a[0] - b[0], a[1] - b[1]


def _segment_intersection(
    a: Point,
    b: Point,
    c: Point,
    d: Point,
    eps: float = 1e-10,
) -> tuple[float, float, Point] | None:
    """Return t, u, point for AB/CD intersection; collinear overlaps are ignored."""
    r = _sub(b, a)
    s = _sub(d, c)
    denominator = _cross(r, s)
    qmp = _sub(c, a)

    if abs(denominator) <= eps:
        return None

    t = _cross(qmp, s) / denominator
    u = _cross(qmp, r) / denominator
    if -eps <= t <= 1.0 + eps and -eps <= u <= 1.0 + eps:
        t = min(1.0, max(0.0, t))
        u = min(1.0, max(0.0, u))
        point = (a[0] + r[0] * t, a[1] + r[1] * t)
        return t, u, point
    return None


def _centerline(points: Iterable[Sequence[float]]) -> tuple[list[Point], list[float]]:
    parsed = [_point(p) for p in points]
    if len(parsed) < 2:
        raise ValueError("Centerline requires at least two points")

    stations = [0.0]
    total = 0.0
    for a, b in zip(parsed, parsed[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length <= 1e-9:
            raise ValueError("Centerline contains a zero-length segment")
        total += length
        stations.append(total)
    return parsed, stations


def _feature_lines(feature: dict) -> list[list[Point]]:
    geometry = feature.get("geometry") or {}
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates") or []

    if geometry_type == "LineString":
        return [[_point(p) for p in coordinates]]
    if geometry_type == "MultiLineString":
        return [[_point(p) for p in line] for line in coordinates]
    return []


def _elevation_to_meters(value: float, unit: str) -> float:
    if unit == "meters":
        return value
    if unit == "feet":
        return value * 0.3048
    raise ValueError("elevation_unit must be 'meters' or 'feet'")


def derive_profile(
    centerline: Sequence[Sequence[float]],
    contour_features: Sequence[dict],
    elevation_field: str,
    elevation_unit: str = "meters",
    source_id: str | None = None,
) -> dict:
    """Intersect one metric road centerline with contour lines.

    The centerline and contours must already share the same projected metric
    coordinate space. EarthForge intentionally does not guess a CRS or perform
    distance calculations in geographic degrees here.
    """
    road, station_vertices = _centerline(centerline)
    road_length = station_vertices[-1]

    raw = []
    skipped_features = 0

    for feature_index, feature in enumerate(contour_features):
        properties = feature.get("properties") or {}
        if elevation_field not in properties or properties[elevation_field] is None:
            skipped_features += 1
            continue

        elevation_raw = float(properties[elevation_field])
        if not math.isfinite(elevation_raw):
            raise ValueError(
                f"Non-finite contour elevation at feature {feature_index}"
            )
        elevation_m = _elevation_to_meters(elevation_raw, elevation_unit)

        for contour_line in _feature_lines(feature):
            if len(contour_line) < 2:
                continue

            for road_index, (ra, rb) in enumerate(zip(road, road[1:])):
                road_segment_length = (
                    station_vertices[road_index + 1] - station_vertices[road_index]
                )

                for ca, cb in zip(contour_line, contour_line[1:]):
                    hit = _segment_intersection(ra, rb, ca, cb)
                    if hit is None:
                        continue

                    t, _, point = hit
                    station = (
                        station_vertices[road_index]
                        + t * road_segment_length
                    )
                    raw.append(
                        {
                            "station_m": station,
                            "elevation_m": elevation_m,
                            "point_xz_m": point,
                            "feature_index": feature_index,
                        }
                    )

    raw.sort(key=lambda row: (row["station_m"], row["elevation_m"]))

    controls = []
    station_tol = 1e-6
    elevation_tol = 1e-6

    for row in raw:
        if controls and abs(
            row["station_m"] - controls[-1]["station_m"]
        ) <= station_tol:
            if abs(
                row["elevation_m"] - controls[-1]["elevation_m"]
            ) <= elevation_tol:
                continue
            raise ValueError(
                "Conflicting contour elevations intersect the centerline at "
                "the same station: "
                f"{controls[-1]['elevation_m']} vs {row['elevation_m']} m"
            )

        control = {
            "station_m": round(row["station_m"], 6),
            "elevation_m": round(row["elevation_m"], 6),
            "method": "centerline_contour_intersection",
            "point_xz_m": [
                round(row["point_xz_m"][0], 6),
                round(row["point_xz_m"][1], 6),
            ],
        }

        if source_id:
            control["source_id"] = source_id

        controls.append(control)

    return {
        "schema_version": 1,
        "coordinate_requirement": (
            "centerline and contours must share one projected metric coordinate space"
        ),
        "elevation_field": elevation_field,
        "source_elevation_unit": elevation_unit,
        "road_length_m": round(road_length, 6),
        "intersection_count": len(controls),
        "skipped_features_missing_elevation": skipped_features,
        "covers_start": bool(
            controls and abs(controls[0]["station_m"]) <= station_tol
        ),
        "covers_end": bool(
            controls
            and abs(controls[-1]["station_m"] - road_length) <= station_tol
        ),
        "controls": controls,
    }


def _load_centerline(spec: dict) -> list:
    if "centerline" in spec:
        return spec["centerline"]

    if spec.get("type") == "FeatureCollection":
        features = spec.get("features") or []
        if len(features) != 1:
            raise ValueError(
                "Centerline FeatureCollection must contain exactly one feature"
            )
        spec = features[0]

    geometry = spec.get("geometry") or {}
    if geometry.get("type") == "LineString":
        return geometry.get("coordinates") or []

    raise ValueError(
        "Centerline input must contain 'centerline', one LineString Feature, "
        "or a one-feature LineString FeatureCollection"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Derive EarthForge road-station elevation controls "
            "from contour intersections."
        )
    )
    parser.add_argument("centerline_json", type=Path)
    parser.add_argument("contours_geojson", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--elevation-field", required=True)
    parser.add_argument(
        "--elevation-unit",
        choices=("meters", "feet"),
        default="meters",
    )
    parser.add_argument("--source-id")
    args = parser.parse_args()

    centerline_spec = json.loads(
        args.centerline_json.read_text(encoding="utf-8")
    )
    contours = json.loads(
        args.contours_geojson.read_text(encoding="utf-8")
    )

    features = contours.get("features")
    if not isinstance(features, list):
        raise ValueError("Contour input must be a GeoJSON FeatureCollection")

    result = derive_profile(
        _load_centerline(centerline_spec),
        features,
        elevation_field=args.elevation_field,
        elevation_unit=args.elevation_unit,
        source_id=args.source_id,
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Wrote {args.output_json} | "
        f"{result['intersection_count']} contour controls | "
        f"road {result['road_length_m']:.2f} m"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
