#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.terrain.derive_road_surface_profile import (
    derive_road_surface_candidate,
)


def synthetic_profile() -> dict:
    samples = []
    for i in range(11):
        elevation = 100.0 - 0.2 * i
        if i == 5:
            elevation += 2.0
        samples.append(
            {
                "station_m": float(i),
                "elevation_m_navd88": elevation,
            }
        )
    return {
        "project_id": "lombard_street_sf",
        "source_id": "synthetic_lidar",
        "samples": samples,
    }


def test_spike_is_flagged_and_median_suppressed():
    result = derive_road_surface_candidate(
        synthetic_profile(),
        median_radius_m=1.1,
        grade_baseline_m=4.0,
        raw_spike_grade_percent=35.0,
    )

    assert result["status"] == "review_candidate_not_locked"
    assert result["summary"]["raw_spike_interval_count"] >= 1

    row = result["samples"][5]
    assert row["raw_elevation_m_navd88"] > row["candidate_elevation_m_navd88"]
    assert abs(row["candidate_elevation_m_navd88"] - 99.0) < 0.25


def test_candidate_retains_expected_slope():
    result = derive_road_surface_candidate(
        synthetic_profile(),
        median_radius_m=1.1,
        grade_baseline_m=4.0,
        raw_spike_grade_percent=35.0,
    )

    mid = result["samples"][4]["candidate_grade_percent"]
    assert mid is not None
    assert -25.0 < mid < -15.0


def test_cli_direct_launch():
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        input_path = tmpdir / "profile.json"
        output_path = tmpdir / "candidate.json"
        input_path.write_text(
            json.dumps(synthetic_profile()),
            encoding="utf-8",
        )

        completed = subprocess.run(
            [
                sys.executable,
                str(
                    ROOT
                    / "pipeline"
                    / "terrain"
                    / "derive_road_surface_profile.py"
                ),
                "--input",
                str(input_path),
                "--output",
                str(output_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        if completed.returncode != 0:
            raise AssertionError(completed.stderr or completed.stdout)

        result = json.loads(output_path.read_text(encoding="utf-8"))
        assert result["status"] == "review_candidate_not_locked"
        assert len(result["samples"]) == 11


if __name__ == "__main__":
    test_spike_is_flagged_and_median_suppressed()
    test_candidate_retains_expected_slope()
    test_cli_direct_launch()
    print("EarthForge road-surface profile tests passed")
