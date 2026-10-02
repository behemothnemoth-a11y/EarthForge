#!/usr/bin/env python3
from __future__ import annotations

import argparse
from bisect import bisect_right
import json
import math
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.georeference.generate_lombard_frame import LocalWGS84Frame

DWR_LIDAR_SOURCE_ID = "dwr_sfbay_delta_lidar_2025_zone3"
DWR_IMAGE_SERVER = (
    "https://gis.water.ca.gov/arcgisimg/rest/services/elevation/"
    "SFBay_Delta_Zone3_Hydroflattened_2025_LIDAR/ImageServer"
)
US_SURVEY_FOOT_TO_M = 1200.0 / 3937.0


def _line_coordinates(collection: dict) -> list[list[float]]:
    if collection.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection")
    features = collection.get("features") or []
    if len(features) != 1:
        raise ValueError("Lombard centerline collection must contain exactly one feature")
    geometry = features[0].get("geometry") or {}
    if geometry.get("type") != "LineString":
        raise ValueError("Lombard centerline feature must be a LineString")
    coords = geometry.get("coordinates") or []
    if len(coords) < 2:
        raise ValueError("Lombard centerline requires at least two vertices")
    return coords


def _source_stations(
    coords: list[list[float]],
) -> tuple[LocalWGS84Frame, list[float]]:
    anchor_lon, anchor_lat = float(coords[0][0]), float(coords[0][1])
    frame = LocalWGS84Frame(anchor_lon, anchor_lat)
    local = [frame.to_local(float(p[0]), float(p[1])) for p in coords]
    stations = [0.0]
    total = 0.0
    for a, b in zip(local, local[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length <= 1e-9:
            raise ValueError("Centerline contains a zero-length segment")
        total += length
        stations.append(total)
    return frame, stations


def _sample_stations(
    total_length_m: float,
    interval_m: float,
    vertex_stations_m: list[float],
) -> list[float]:
    if interval_m <= 0 or not math.isfinite(interval_m):
        raise ValueError("sample interval must be a finite value greater than zero")
    values = {0.0, total_length_m, *vertex_stations_m}
    cursor = interval_m
    while cursor < total_length_m - 1e-9:
        values.add(round(cursor, 9))
        cursor += interval_m
    return sorted(values)


def _wgs84_at_station(
    coords: list[list[float]],
    vertex_stations_m: list[float],
    station_m: float,
) -> tuple[float, float]:
    total = vertex_stations_m[-1]
    if station_m < -1e-9 or station_m > total + 1e-9:
        raise ValueError(f"Station {station_m:.3f} outside route 0..{total:.3f}")

    station = min(max(float(station_m), 0.0), total)
    if station >= total - 1e-9:
        return float(coords[-1][0]), float(coords[-1][1])

    index = max(0, bisect_right(vertex_stations_m, station) - 1)
    index = min(index, len(coords) - 2)
    span = vertex_stations_m[index + 1] - vertex_stations_m[index]
    t = (station - vertex_stations_m[index]) / span
    a, b = coords[index], coords[index + 1]
    lon = float(a[0]) + (float(b[0]) - float(a[0])) * t
    lat = float(a[1]) + (float(b[1]) - float(a[1])) * t
    return lon, lat


def build_sample_points(
    centerline_collection: dict,
    sample_interval_m: float = 1.0,
) -> dict:
    coords = _line_coordinates(centerline_collection)
    _, vertex_stations = _source_stations(coords)
    stations = _sample_stations(
        vertex_stations[-1],
        sample_interval_m,
        vertex_stations,
    )
    samples = []
    for station in stations:
        lon, lat = _wgs84_at_station(coords, vertex_stations, station)
        samples.append(
            {
                "station_m": round(station, 6),
                "longitude": round(lon, 9),
                "latitude": round(lat, 9),
            }
        )
    return {
        "route_length_m": round(vertex_stations[-1], 6),
        "sample_interval_m": float(sample_interval_m),
        "source_vertex_stations_m": [round(value, 6) for value in vertex_stations],
        "samples": samples,
    }


def _post_get_samples(
    points: list[dict],
    image_server: str = DWR_IMAGE_SERVER,
) -> dict:
    geometry = {
        "points": [
            [point["longitude"], point["latitude"]]
            for point in points
        ],
        "spatialReference": {"wkid": 4326},
    }
    body = urlencode(
        {
            "geometryType": "esriGeometryMultipoint",
            "geometry": json.dumps(geometry, separators=(",", ":")),
            "f": "json",
        }
    ).encode("utf-8")
    request = Request(
        image_server.rstrip("/") + "/getSamples",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "EarthForge/1.0 (+https://github.com/behemothnemoth-a11y/EarthForge)",
        },
        method="POST",
    )
    with urlopen(request, timeout=90) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"DWR ImageServer error: {payload['error']}")
    return payload


def merge_lidar_samples(
    planned_samples: list[dict],
    response: dict,
) -> list[dict]:
    raw = response.get("samples")
    if not isinstance(raw, list):
        raise ValueError("LiDAR response does not contain a samples list")

    by_id = {}
    for sample in raw:
        location_id = sample.get("locationId")
        if location_id is None:
            raise ValueError("LiDAR sample is missing locationId")
        index = int(location_id)
        if index in by_id:
            raise ValueError(f"Duplicate LiDAR locationId {index}")
        by_id[index] = sample

    expected = set(range(len(planned_samples)))
    actual = set(by_id)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"LiDAR sample IDs do not match request; missing={missing} extra={extra}"
        )

    merged = []
    for index, planned in enumerate(planned_samples):
        source = by_id[index]
        value = str(source.get("value", "")).split(",", 1)[0].strip()
        if not value or value.lower() in {"nodata", "null", "nan"}:
            raise ValueError(
                f"LiDAR returned no elevation at station {planned['station_m']}"
            )
        elevation_ft_us = float(value)
        if not math.isfinite(elevation_ft_us):
            raise ValueError("LiDAR returned a non-finite elevation")

        row = dict(planned)
        row.update(
            {
                "elevation_ft_us_navd88": round(elevation_ft_us, 6),
                "elevation_m_navd88": round(
                    elevation_ft_us * US_SURVEY_FOOT_TO_M,
                    6,
                ),
                "raster_id": source.get("rasterId"),
                "source_resolution_ft_us": source.get("resolution"),
            }
        )
        merged.append(row)

    for index, row in enumerate(merged[:-1]):
        next_row = merged[index + 1]
        run = next_row["station_m"] - row["station_m"]
        rise = next_row["elevation_m_navd88"] - row["elevation_m_navd88"]
        row["raw_grade_to_next_percent"] = round((rise / run) * 100.0, 6)
    if merged:
        merged[-1]["raw_grade_to_next_percent"] = None
    return merged


def acquire_lidar_profile(
    centerline_collection: dict,
    sample_interval_m: float = 1.0,
    image_server: str = DWR_IMAGE_SERVER,
) -> dict:
    plan = build_sample_points(centerline_collection, sample_interval_m)
    response = _post_get_samples(plan["samples"], image_server=image_server)
    samples = merge_lidar_samples(plan["samples"], response)

    elevations = [row["elevation_m_navd88"] for row in samples]
    grades = [
        abs(row["raw_grade_to_next_percent"])
        for row in samples
        if row["raw_grade_to_next_percent"] is not None
    ]
    summary = {
        "sample_count": len(samples),
        "start_elevation_m_navd88": samples[0]["elevation_m_navd88"],
        "end_elevation_m_navd88": samples[-1]["elevation_m_navd88"],
        "start_elevation_ft_us_navd88": samples[0]["elevation_ft_us_navd88"],
        "end_elevation_ft_us_navd88": samples[-1]["elevation_ft_us_navd88"],
        "net_drop_m": round(
            samples[0]["elevation_m_navd88"]
            - samples[-1]["elevation_m_navd88"],
            6,
        ),
        "min_elevation_m_navd88": min(elevations),
        "max_elevation_m_navd88": max(elevations),
        "max_abs_raw_interval_grade_percent": max(grades) if grades else None,
    }

    return {
        "schema_version": 1,
        "project_id": "lombard_street_sf",
        "source_id": DWR_LIDAR_SOURCE_ID,
        "source_url": image_server,
        "source_description": (
            "2025 San Francisco Bay-Delta Quality Level 1 hydro-flattened LiDAR DEM"
        ),
        "horizontal_request_crs": "EPSG:4326",
        "source_horizontal_reference": (
            "NAD83(2011), California State Plane Zone 3, 2025.00 epoch"
        ),
        "source_vertical_datum": "NAVD88",
        "source_vertical_unit": "US survey foot",
        "canonical_vertical_unit": "meter",
        "source_pixel_size_ft_us": 1.0,
        "route_length_m": plan["route_length_m"],
        "sample_interval_m": plan["sample_interval_m"],
        "source_vertex_stations_m": plan["source_vertex_stations_m"],
        "summary": summary,
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sample the 2025 DWR LiDAR DEM along the Lombard EarthForge centerline."
    )
    parser.add_argument(
        "--centerline",
        type=Path,
        default=Path(
            "projects/lombard_street_sf/acquired/centerline_wgs84.geojson"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "projects/lombard_street_sf/road_truth/lidar_profile_navd88.json"
        ),
    )
    parser.add_argument("--interval-m", type=float, default=1.0)
    args = parser.parse_args()

    centerline = json.loads(args.centerline.read_text(encoding="utf-8"))
    result = acquire_lidar_profile(
        centerline,
        sample_interval_m=args.interval_m,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    summary = result["summary"]
    print(
        f"Wrote {args.output} | {summary['sample_count']} LiDAR samples | "
        f"{summary['start_elevation_ft_us_navd88']:.2f} ft -> "
        f"{summary['end_elevation_ft_us_navd88']:.2f} ft NAVD88"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
