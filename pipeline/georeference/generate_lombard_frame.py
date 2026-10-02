#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Sequence

WGS84_A = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)


def _line(feature: dict) -> list[list[float]]:
    geometry = feature.get("geometry") or {}
    t = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if t == "LineString":
        return coords
    if t == "MultiLineString" and len(coords) == 1:
        return coords[0]
    raise ValueError(f"Expected a single centerline LineString, got {t}")


class LocalWGS84Frame:
    """Small-area WGS84 tangent frame: +X east, +Z south."""

    def __init__(self, anchor_lon: float, anchor_lat: float):
        self.anchor_lon = float(anchor_lon)
        self.anchor_lat = float(anchor_lat)
        lat = math.radians(self.anchor_lat)
        sin_lat = math.sin(lat)
        denom = math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
        self.prime_vertical_radius_m = WGS84_A / denom
        self.meridional_radius_m = (
            WGS84_A * (1.0 - WGS84_E2) / (denom ** 3)
        )
        self.cos_lat = math.cos(lat)

    def to_local(self, lon: float, lat: float) -> tuple[float, float]:
        dlon = math.radians(float(lon) - self.anchor_lon)
        dlat = math.radians(float(lat) - self.anchor_lat)
        east = dlon * self.prime_vertical_radius_m * self.cos_lat
        north = dlat * self.meridional_radius_m
        return east, -north

    def metadata(self) -> dict:
        return {
            "method": "wgs84_local_tangent_first_order_ellipsoid",
            "source_crs": "EPSG:4326",
            "anchor_lon": self.anchor_lon,
            "anchor_lat": self.anchor_lat,
            "x_positive": "east",
            "z_positive": "south",
            "units": "meters",
            "ellipsoid": "WGS84",
        }


def _transform_coords(coords, frame: LocalWGS84Frame):
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        x, z = frame.to_local(coords[0], coords[1])
        return [round(x, 6), round(z, 6)]
    return [_transform_coords(child, frame) for child in coords]


def transform_geojson_geometry(geometry: dict, frame: LocalWGS84Frame) -> dict:
    t = geometry.get("type")
    if t not in {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    }:
        raise ValueError(f"Unsupported GeoJSON geometry type: {t}")
    return {
        "type": t,
        "coordinates": _transform_coords(geometry.get("coordinates") or [], frame),
    }


def transform_feature_collection(collection: dict, frame: LocalWGS84Frame) -> dict:
    if collection.get("type") != "FeatureCollection":
        raise ValueError("Expected GeoJSON FeatureCollection")
    out_features = []
    for feature in collection.get("features") or []:
        clone = {
            "type": "Feature",
            "properties": feature.get("properties") or {},
            "geometry": transform_geojson_geometry(feature.get("geometry") or {}, frame),
        }
        if "id" in feature:
            clone["id"] = feature["id"]
        out_features.append(clone)
    return {
        "type": "FeatureCollection",
        "coordinate_space": "earthforge_project_local_meters",
        "features": out_features,
    }


def centerline_stations(local_coords: Sequence[Sequence[float]]) -> list[float]:
    if len(local_coords) < 2:
        raise ValueError("Centerline must contain at least two points")
    stations = [0.0]
    total = 0.0
    for a, b in zip(local_coords, local_coords[1:]):
        dx = float(b[0]) - float(a[0])
        dz = float(b[1]) - float(a[1])
        length = math.hypot(dx, dz)
        if length <= 1e-9:
            raise ValueError("Centerline contains a zero-length segment")
        total += length
        stations.append(total)
    return stations


def build_frame(centerline_collection: dict, contours_collection: dict) -> tuple[dict, dict, dict]:
    features = centerline_collection.get("features") or []
    if len(features) != 1:
        raise ValueError("Lombard centerline input must contain exactly one feature")
    source_feature = features[0]
    source_coords = _line(source_feature)
    if len(source_coords) < 2:
        raise ValueError("Lombard centerline must contain at least two vertices")

    anchor_lon = float(source_coords[0][0])
    anchor_lat = float(source_coords[0][1])
    frame = LocalWGS84Frame(anchor_lon, anchor_lat)

    local_centerline_fc = transform_feature_collection(centerline_collection, frame)
    local_contours_fc = transform_feature_collection(contours_collection, frame)

    local_feature = local_centerline_fc["features"][0]
    local_coords = _line(local_feature)
    stations = centerline_stations(local_coords)

    props = source_feature.get("properties") or {}
    lower_props = {str(k).lower(): v for k, v in props.items()}
    segment_cnns = lower_props.get("earthforge_segment_cnns")
    if not segment_cnns:
        cnn = lower_props.get("cnn", lower_props.get("cnntext"))
        segment_cnns = [] if cnn is None else [str(cnn)]
    segment_cnns = [str(value) for value in segment_cnns]

    locked_frame = {
        "schema_version": 1,
        "project_id": "lombard_street_sf",
        "frame_id": "lombard_hyde_anchor_v001",
        "status": "locked_from_acquired_centerline",
        "anchor_role": "Lombard / Hyde centerline endpoint",
        "anchor_wgs84": {
            "longitude": anchor_lon,
            "latitude": anchor_lat,
        },
        "transform": frame.metadata(),
        "axis_convention": {
            "x_positive": "east",
            "z_positive": "south",
            "y_positive": "up",
        },
        "source_centerline": {
            "segment_cnns": segment_cnns,
            "segment_count": len(segment_cnns),
            "route_nodes": lower_props.get("earthforge_route_nodes"),
            "vertex_count": len(local_coords),
            "length_m": round(stations[-1], 6),
            "station_0": "Hyde Street",
            "station_end": "Leavenworth Street",
        },
        "minecraft": {
            "horizontal_scale": "1 meter = 1 block",
            "vertical_scale": "1 meter = 1 block",
            "registration_status": "pending_generated_output_anchor",
        },
    }
    return locked_frame, local_centerline_fc, local_contours_fc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lock Lombard project-local metric frame from acquired WGS84 source geometry."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("projects/lombard_street_sf/acquired"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("projects/lombard_street_sf/road_truth"),
    )
    args = parser.parse_args()

    centerline = json.loads(
        (args.input_dir / "centerline_wgs84.geojson").read_text(encoding="utf-8")
    )
    contours = json.loads(
        (args.input_dir / "contours_wgs84.geojson").read_text(encoding="utf-8")
    )

    locked, local_centerline, local_contours = build_frame(centerline, contours)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "locked_frame.json").write_text(
        json.dumps(locked, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "centerline_local.json").write_text(
        json.dumps(local_centerline, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "contours_local.geojson").write_text(
        json.dumps(local_contours, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Locked {locked['frame_id']} | "
        f"CNNs {','.join(locked['source_centerline']['segment_cnns'])} | "
        f"{locked['source_centerline']['length_m']:.2f} m"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
