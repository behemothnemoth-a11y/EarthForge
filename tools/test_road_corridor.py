#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.roads.road_corridor import build_corridor
from pipeline.terrain.elevation_profile import ElevationProfile


def close(a: float, b: float, eps: float = 1e-6):
    if abs(a - b) > eps:
        raise AssertionError(f"{a} != {b}")


def test_elevation_profile():
    profile = ElevationProfile(
        [
            {"station_m": 0, "elevation_m": 100},
            {"station_m": 10, "elevation_m": 102},
            {"station_m": 20, "elevation_m": 101},
        ]
    )
    close(profile.elevation_at(5), 101)
    close(profile.grade_at(5), 0.2)
    close(profile.grade_at(15), -0.1)
    close(profile.summary()["max_abs_grade_percent"], 20.0)


def test_straight_corridor():
    result = build_corridor(
        {
            "road_id": "test_straight",
            "centerline": [[0, 0], [10, 0]],
            "elevation_profile": [
                {"station_m": 0, "elevation_m": 50},
                {"station_m": 10, "elevation_m": 52},
            ],
            "sample_interval_m": 2,
            "cross_section": {
                "roadway_width_m": 6,
                "curb_width_left_m": 0.3,
                "curb_width_right_m": 0.3,
                "sidewalk_width_left_m": 1.5,
                "sidewalk_width_right_m": 1.5,
            },
        }
    )
    close(result["total_length_m"], 10.0)
    assert [row["station_m"] for row in result["samples"]] == [0, 2, 4, 6, 8, 10]
    first = result["samples"][0]
    close(first["road_edge_left"][2], -3.0)
    close(first["road_edge_right"][2], 3.0)
    close(first["sidewalk_outer_left"][2], -4.8)
    close(first["sidewalk_outer_right"][2], 4.8)
    close(first["grade_percent"], 20.0)


def test_corner_preserves_source_vertex():
    result = build_corridor(
        {
            "road_id": "test_corner",
            "centerline": [[0, 0], [10, 0], [10, 10]],
            "elevation_profile": [
                {"station_m": 0, "elevation_m": 0},
                {"station_m": 20, "elevation_m": 2},
            ],
            "sample_interval_m": 6,
        }
    )
    stations = [row["station_m"] for row in result["samples"]]
    assert 10.0 in stations
    corner = next(row for row in result["samples"] if row["station_m"] == 10.0)
    close(corner["center"][0], 10.0)
    close(corner["center"][2], 0.0)
    expected = math.sqrt(0.5)
    close(corner["tangent_xz"][0], expected, 1e-8)
    close(corner["tangent_xz"][1], expected, 1e-8)


def test_cli_direct_launch():
    spec = {
        "road_id": "cli_smoke",
        "centerline": [[0, 0], [4, 0]],
        "elevation_profile": [
            {"station_m": 0, "elevation_m": 10},
            {"station_m": 4, "elevation_m": 11},
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        input_path = tmpdir / "input.json"
        output_path = tmpdir / "output.json"
        input_path.write_text(json.dumps(spec), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "pipeline" / "roads" / "road_corridor.py"),
                str(input_path),
                str(output_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr or completed.stdout)
        result = json.loads(output_path.read_text(encoding="utf-8"))
        assert result["road_id"] == "cli_smoke"
        close(result["total_length_m"], 4.0)


def test_profile_must_cover_road():
    try:
        build_corridor(
            {
                "road_id": "bad_profile",
                "centerline": [[0, 0], [10, 0]],
                "elevation_profile": [
                    {"station_m": 1, "elevation_m": 0},
                    {"station_m": 9, "elevation_m": 1},
                ],
            }
        )
    except ValueError as exc:
        assert "cover the full centerline" in str(exc)
    else:
        raise AssertionError("Expected uncovered elevation profile to fail")


if __name__ == "__main__":
    test_elevation_profile()
    test_straight_corridor()
    test_corner_preserves_source_vertex()
    test_cli_direct_launch()
    test_profile_must_cover_road()
    print("EarthForge road corridor tests passed")
