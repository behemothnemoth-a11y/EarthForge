#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.georeference.generate_lombard_frame import (
    LocalWGS84Frame,
    build_frame,
)


def close(a: float, b: float, eps: float = 1e-3):
    if abs(a - b) > eps:
        raise AssertionError(f"{a} != {b}")


def centerline_collection():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "street": "Lombard",
                    "earthforge_route_from": "HYDE",
                    "earthforge_route_to": "LEAVENWORTH",
                    "earthforge_route_nodes": [
                        "HYDE",
                        "MONTCLAIR TER",
                        "LEAVENWORTH",
                    ],
                    "earthforge_segment_cnns": [
                        "8449000",
                        "8448000",
                    ],
                    "earthforge_segment_count": 2,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-122.4180, 37.8020],
                        [-122.4170, 37.8020],
                    ],
                },
            }
        ],
    }


def contour_collection():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"elevation": 300},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-122.4175, 37.8010],
                        [-122.4175, 37.8030],
                    ],
                },
            }
        ],
    }


def test_local_axes():
    frame = LocalWGS84Frame(-122.4180, 37.8020)
    east = frame.to_local(-122.4170, 37.8020)
    north = frame.to_local(-122.4180, 37.8030)

    assert east[0] > 80
    close(east[1], 0.0)
    close(north[0], 0.0)
    assert north[1] < -100


def test_build_frame():
    locked, centerline, contours = build_frame(
        centerline_collection(),
        contour_collection(),
    )

    assert locked["anchor_role"] == "Lombard / Hyde centerline endpoint"
    assert locked["source_centerline"]["segment_cnns"] == [
        "8449000",
        "8448000",
    ]
    assert locked["source_centerline"]["segment_count"] == 2
    assert locked["source_centerline"]["route_nodes"] == [
        "HYDE",
        "MONTCLAIR TER",
        "LEAVENWORTH",
    ]
    assert locked["source_centerline"]["station_0"] == "Hyde Street"
    assert locked["source_centerline"]["station_end"] == "Leavenworth Street"
    assert 80 < locked["source_centerline"]["length_m"] < 95

    coords = centerline["features"][0]["geometry"]["coordinates"]
    close(coords[0][0], 0.0)
    close(coords[0][1], 0.0)
    assert coords[-1][0] > 80

    contour_coords = contours["features"][0]["geometry"]["coordinates"]
    assert contour_coords[0][0] > 40
    assert contour_coords[0][1] > 100
    assert contour_coords[1][1] < -100


if __name__ == "__main__":
    test_local_axes()
    test_build_frame()
    print("EarthForge Lombard frame tests passed")
