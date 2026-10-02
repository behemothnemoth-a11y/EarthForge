#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.terrain.sample_lidar_profile import (
    US_SURVEY_FOOT_TO_M,
    build_sample_points,
    merge_lidar_samples,
)


def close(a: float, b: float, eps: float = 1e-6):
    if abs(a - b) > eps:
        raise AssertionError(f"{a} != {b}")


def centerline():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-122.4196, 37.8020],
                        [-122.4190, 37.8021],
                        [-122.4180, 37.8022],
                    ],
                },
            }
        ],
    }


def test_sampling_includes_vertices_and_endpoints():
    plan = build_sample_points(centerline(), sample_interval_m=20.0)
    assert plan["samples"][0]["station_m"] == 0.0
    close(
        plan["samples"][-1]["station_m"],
        plan["route_length_m"],
    )
    for station in plan["source_vertex_stations_m"]:
        assert any(
            abs(sample["station_m"] - station) <= 1e-6
            for sample in plan["samples"]
        )


def test_merge_and_unit_conversion():
    planned = [
        {"station_m": 0.0, "longitude": -122.4, "latitude": 37.8},
        {"station_m": 1.0, "longitude": -122.39999, "latitude": 37.8},
    ]
    response = {
        "samples": [
            {
                "locationId": 0,
                "value": "281.429992676",
                "rasterId": 33,
                "resolution": 1,
            },
            {
                "locationId": 1,
                "value": "280.429992676",
                "rasterId": 33,
                "resolution": 1,
            },
        ]
    }
    merged = merge_lidar_samples(planned, response)
    close(
        merged[0]["elevation_m_navd88"],
        281.429992676 * US_SURVEY_FOOT_TO_M,
    )
    close(
        merged[0]["raw_grade_to_next_percent"],
        -US_SURVEY_FOOT_TO_M * 100.0,
        eps=1e-4,
    )
    assert merged[-1]["raw_grade_to_next_percent"] is None


def test_missing_sample_fails():
    try:
        merge_lidar_samples(
            [
                {"station_m": 0.0, "longitude": 0.0, "latitude": 0.0},
                {"station_m": 1.0, "longitude": 0.0, "latitude": 0.0},
            ],
            {"samples": [{"locationId": 0, "value": "10"}]},
        )
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("Expected missing LiDAR sample to fail")


if __name__ == "__main__":
    test_sampling_includes_vertices_and_endpoints()
    test_merge_and_unit_conversion()
    test_missing_sample_fails()
    print("EarthForge LiDAR profile tests passed")
