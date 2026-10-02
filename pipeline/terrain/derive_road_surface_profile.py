#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median
from typing import Sequence


def _load_samples(profile: dict) -> list[dict]:
    samples = profile.get("samples")
    if not isinstance(samples, list) or len(samples) < 3:
        raise ValueError("LiDAR profile must contain at least three samples")

    out = []
    previous_station = None
    for index, sample in enumerate(samples):
        station = float(sample["station_m"])
        elevation = float(sample["elevation_m_navd88"])
        if not math.isfinite(station) or not math.isfinite(elevation):
            raise ValueError(f"Non-finite sample at index {index}")
        if previous_station is not None and station <= previous_station:
            raise ValueError("LiDAR sample stations must be strictly increasing")
        previous_station = station
        out.append(
            {
                "station_m": station,
                "elevation_m": elevation,
                "source_sample": sample,
            }
        )
    return out


def _window_values(
    samples: Sequence[dict],
    index: int,
    radius_m: float,
) -> list[float]:
    station = samples[index]["station_m"]
    return [
        row["elevation_m"]
        for row in samples
        if abs(row["station_m"] - station) <= radius_m + 1e-9
    ]


def _nearest_index(samples: Sequence[dict], target_station: float) -> int:
    return min(
        range(len(samples)),
        key=lambda i: abs(samples[i]["station_m"] - target_station),
    )


def _grade_over_baseline(
    stations: Sequence[float],
    elevations: Sequence[float],
    index: int,
    baseline_m: float,
) -> float | None:
    if baseline_m <= 0:
        raise ValueError("grade_baseline_m must be greater than zero")

    half = baseline_m / 2.0
    center = stations[index]
    left_i = _nearest_index(
        [{"station_m": s} for s in stations],
        max(stations[0], center - half),
    )
    right_i = _nearest_index(
        [{"station_m": s} for s in stations],
        min(stations[-1], center + half),
    )

    if left_i == right_i:
        return None

    run = stations[right_i] - stations[left_i]
    if run <= 1e-9:
        return None
    rise = elevations[right_i] - elevations[left_i]
    return rise / run * 100.0


def derive_road_surface_candidate(
    profile: dict,
    median_radius_m: float = 2.0,
    grade_baseline_m: float = 5.0,
    raw_spike_grade_percent: float = 35.0,
) -> dict:
    """Create a conservative review candidate from dense LiDAR samples.

    This does not lock road truth. The median filter suppresses isolated
    raster/centerline artifacts and the longer-baseline grade is diagnostic.
    Original source samples remain untouched in the source profile.
    """
    if median_radius_m <= 0:
        raise ValueError("median_radius_m must be greater than zero")
    if grade_baseline_m <= 0:
        raise ValueError("grade_baseline_m must be greater than zero")
    if raw_spike_grade_percent <= 0:
        raise ValueError("raw_spike_grade_percent must be greater than zero")

    samples = _load_samples(profile)
    stations = [row["station_m"] for row in samples]

    smoothed = [
        float(median(_window_values(samples, i, median_radius_m)))
        for i in range(len(samples))
    ]

    rows = []
    spike_count = 0
    max_abs_raw_interval_grade = 0.0
    max_abs_candidate_grade = 0.0

    for i, row in enumerate(samples):
        raw_next_grade = None
        if i < len(samples) - 1:
            run = samples[i + 1]["station_m"] - row["station_m"]
            raw_next_grade = (
                samples[i + 1]["elevation_m"] - row["elevation_m"]
            ) / run * 100.0
            max_abs_raw_interval_grade = max(
                max_abs_raw_interval_grade,
                abs(raw_next_grade),
            )

        candidate_grade = _grade_over_baseline(
            stations,
            smoothed,
            i,
            grade_baseline_m,
        )
        if candidate_grade is not None:
            max_abs_candidate_grade = max(
                max_abs_candidate_grade,
                abs(candidate_grade),
            )

        raw_spike = (
            raw_next_grade is not None
            and abs(raw_next_grade) >= raw_spike_grade_percent
        )
        if raw_spike:
            spike_count += 1

        rows.append(
            {
                "station_m": round(row["station_m"], 6),
                "raw_elevation_m_navd88": round(row["elevation_m"], 6),
                "candidate_elevation_m_navd88": round(smoothed[i], 6),
                "raw_interval_grade_to_next_percent": (
                    None
                    if raw_next_grade is None
                    else round(raw_next_grade, 6)
                ),
                "candidate_grade_percent": (
                    None
                    if candidate_grade is None
                    else round(candidate_grade, 6)
                ),
                "raw_spike_flag": raw_spike,
            }
        )

    start = rows[0]
    end = rows[-1]
    net_drop = (
        start["candidate_elevation_m_navd88"]
        - end["candidate_elevation_m_navd88"]
    )

    return {
        "schema_version": 1,
        "project_id": profile.get("project_id", "lombard_street_sf"),
        "source_profile": "road_truth/lidar_profile_navd88.json",
        "source_id": profile.get("source_id"),
        "vertical_datum": "NAVD88",
        "canonical_vertical_unit": "meter",
        "status": "review_candidate_not_locked",
        "method": {
            "elevation_filter": "station_window_median",
            "median_radius_m": median_radius_m,
            "grade_method": "centered_baseline",
            "grade_baseline_m": grade_baseline_m,
            "raw_spike_grade_percent": raw_spike_grade_percent,
        },
        "summary": {
            "sample_count": len(rows),
            "route_length_m": round(stations[-1] - stations[0], 6),
            "candidate_start_elevation_m_navd88": start[
                "candidate_elevation_m_navd88"
            ],
            "candidate_end_elevation_m_navd88": end[
                "candidate_elevation_m_navd88"
            ],
            "candidate_net_drop_m": round(net_drop, 6),
            "raw_spike_interval_count": spike_count,
            "max_abs_raw_interval_grade_percent": round(
                max_abs_raw_interval_grade,
                6,
            ),
            "max_abs_candidate_grade_percent": round(
                max_abs_candidate_grade,
                6,
            ),
        },
        "review_rules": [
            "This file is a candidate surface, not accepted road truth.",
            "Do not erase source LiDAR spikes; keep them in the raw source profile and flag them here.",
            "Review turn stations, endpoints, and suspicious grade changes against reference imagery and source geometry.",
            "Do not generate curbs, stairs, terraces, or buildings from this candidate until elevation_profile_locked is true.",
        ],
        "samples": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a reviewable Lombard road-surface candidate from dense LiDAR samples."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(
            "projects/lombard_street_sf/road_truth/lidar_profile_navd88.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "projects/lombard_street_sf/road_truth/road_surface_candidate_v001.json"
        ),
    )
    parser.add_argument("--median-radius-m", type=float, default=2.0)
    parser.add_argument("--grade-baseline-m", type=float, default=5.0)
    parser.add_argument("--raw-spike-grade-percent", type=float, default=35.0)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    result = derive_road_surface_candidate(
        source,
        median_radius_m=args.median_radius_m,
        grade_baseline_m=args.grade_baseline_m,
        raw_spike_grade_percent=args.raw_spike_grade_percent,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Wrote {args.output} | "
        f"{result['summary']['sample_count']} samples | "
        f"{result['summary']['raw_spike_interval_count']} raw spike intervals | "
        f"candidate max grade "
        f"{result['summary']['max_abs_candidate_grade_percent']:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
