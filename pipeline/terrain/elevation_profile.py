#!/usr/bin/env python3
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class ElevationControl:
    station_m: float
    elevation_m: float
    source_id: str | None = None
    confidence: float | None = None

    @classmethod
    def from_mapping(cls, value: dict) -> "ElevationControl":
        return cls(
            station_m=float(value["station_m"]),
            elevation_m=float(value["elevation_m"]),
            source_id=value.get("source_id"),
            confidence=(
                None if value.get("confidence") is None
                else float(value["confidence"])
            ),
        )


class ElevationProfile:
    """Piecewise-linear elevation truth along a road station axis.

    Stations are measured in project-local meters from the start of the
    centerline. The profile intentionally does not hide extrapolation: callers
    must provide controls that cover the corridor they want to build.
    """

    def __init__(self, controls: Iterable[ElevationControl | dict]):
        parsed = [
            c if isinstance(c, ElevationControl) else ElevationControl.from_mapping(c)
            for c in controls
        ]
        if len(parsed) < 2:
            raise ValueError("ElevationProfile requires at least two controls")

        previous_station = None
        for control in parsed:
            if not math.isfinite(control.station_m) or not math.isfinite(control.elevation_m):
                raise ValueError("Elevation controls must contain finite numbers")
            if control.confidence is not None and not 0.0 <= control.confidence <= 1.0:
                raise ValueError("Elevation control confidence must be between 0 and 1")
            if previous_station is not None and control.station_m <= previous_station:
                raise ValueError("Elevation control stations must be strictly increasing")
            previous_station = control.station_m

        self._controls = tuple(parsed)
        self._stations = tuple(c.station_m for c in parsed)

    @property
    def controls(self) -> tuple[ElevationControl, ...]:
        return self._controls

    @property
    def start_station_m(self) -> float:
        return self._controls[0].station_m

    @property
    def end_station_m(self) -> float:
        return self._controls[-1].station_m

    def _segment_index(self, station_m: float) -> int:
        if station_m < self.start_station_m - 1e-9 or station_m > self.end_station_m + 1e-9:
            raise ValueError(
                f"Station {station_m:.3f} m is outside elevation profile "
                f"[{self.start_station_m:.3f}, {self.end_station_m:.3f}]"
            )
        if station_m >= self.end_station_m - 1e-9:
            return len(self._controls) - 2
        return max(0, bisect_right(self._stations, station_m) - 1)

    def elevation_at(self, station_m: float) -> float:
        i = self._segment_index(float(station_m))
        a = self._controls[i]
        b = self._controls[i + 1]
        span = b.station_m - a.station_m
        t = (station_m - a.station_m) / span
        return a.elevation_m + (b.elevation_m - a.elevation_m) * t

    def grade_at(self, station_m: float) -> float:
        """Return local grade as rise/run (0.20 == 20%)."""
        i = self._segment_index(float(station_m))
        a = self._controls[i]
        b = self._controls[i + 1]
        return (b.elevation_m - a.elevation_m) / (b.station_m - a.station_m)

    def segment_grades(self) -> list[dict]:
        out = []
        for a, b in zip(self._controls, self._controls[1:]):
            grade = (b.elevation_m - a.elevation_m) / (b.station_m - a.station_m)
            out.append(
                {
                    "start_station_m": a.station_m,
                    "end_station_m": b.station_m,
                    "grade": grade,
                    "grade_percent": grade * 100.0,
                }
            )
        return out

    def summary(self) -> dict:
        grades = [row["grade_percent"] for row in self.segment_grades()]
        return {
            "control_count": len(self._controls),
            "start_station_m": self.start_station_m,
            "end_station_m": self.end_station_m,
            "min_elevation_m": min(c.elevation_m for c in self._controls),
            "max_elevation_m": max(c.elevation_m for c in self._controls),
            "max_uphill_percent": max(grades),
            "max_downhill_percent": min(grades),
            "max_abs_grade_percent": max(abs(g) for g in grades),
        }
