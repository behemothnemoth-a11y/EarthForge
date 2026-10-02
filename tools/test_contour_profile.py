#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.terrain.derive_profile_from_contours import derive_profile


def close(a: float, b: float, eps: float = 1e-6):
    if abs(a - b) > eps:
        raise AssertionError(f"{a} != {b}")


def feature(x: float, elevation: float) -> dict:
    return {
        "type": "Feature",
        "properties": {"elev_ft": elevation},
        "geometry": {
            "type": "LineString",
            "coordinates": [[x, -2], [x, 2]],
        },
    }


def test_intersections_and_feet_conversion():
    result = derive_profile(
        [[0, 0], [10, 0]],
        [feature(2, 100), feature(5, 105), feature(8, 110)],
        elevation_field="elev_ft",
        elevation_unit="feet",
        source_id="synthetic_contours",
    )

    assert [row["station_m"] for row in result["controls"]] == [
        2.0,
        5.0,
        8.0,
    ]
    close(result["controls"][0]["elevation_m"], 30.48)
    close(result["controls"][1]["elevation_m"], 32.004)
    close(result["controls"][2]["elevation_m"], 33.528)
    assert not result["covers_start"]
    assert not result["covers_end"]


def test_stationing_through_corner():
    contours = [
        {
            "type": "Feature",
            "properties": {"elev_m": 20},
            "geometry": {
                "type": "LineString",
                "coordinates": [[8, 3], [12, 3]],
            },
        }
    ]

    result = derive_profile(
        [[0, 0], [10, 0], [10, 10]],
        contours,
        elevation_field="elev_m",
    )

    assert len(result["controls"]) == 1
    close(result["controls"][0]["station_m"], 13.0)


def test_duplicate_contour_vertex_is_deduplicated():
    duplicate = {
        "type": "Feature",
        "properties": {"elev_m": 10},
        "geometry": {
            "type": "MultiLineString",
            "coordinates": [
                [[5, -2], [5, 0]],
                [[5, 0], [5, 2]],
            ],
        },
    }

    result = derive_profile(
        [[0, 0], [10, 0]],
        [duplicate],
        elevation_field="elev_m",
    )

    assert result["intersection_count"] == 1
    close(result["controls"][0]["station_m"], 5.0)


def test_cli_direct_launch():
    centerline = {"centerline": [[0, 0], [4, 0]]}
    contours = {
        "type": "FeatureCollection",
        "features": [feature(2, 100)],
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        centerline_path = tmpdir / "centerline.json"
        contours_path = tmpdir / "contours.geojson"
        output_path = tmpdir / "profile.json"

        centerline_path.write_text(
            json.dumps(centerline),
            encoding="utf-8",
        )
        contours_path.write_text(
            json.dumps(contours),
            encoding="utf-8",
        )

        completed = subprocess.run(
            [
                sys.executable,
                str(
                    ROOT
                    / "pipeline"
                    / "terrain"
                    / "derive_profile_from_contours.py"
                ),
                str(centerline_path),
                str(contours_path),
                str(output_path),
                "--elevation-field",
                "elev_ft",
                "--elevation-unit",
                "feet",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        if completed.returncode != 0:
            raise AssertionError(completed.stderr or completed.stdout)

        result = json.loads(
            output_path.read_text(encoding="utf-8")
        )
        assert result["intersection_count"] == 1
        close(result["controls"][0]["station_m"], 2.0)


if __name__ == "__main__":
    test_intersections_and_feet_conversion()
    test_stationing_through_corner()
    test_duplicate_contour_vertex_is_deduplicated()
    test_cli_direct_launch()
    print("EarthForge contour profile tests passed")
