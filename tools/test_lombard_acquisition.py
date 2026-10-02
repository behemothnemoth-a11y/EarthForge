#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.acquire.lombard_datasf import (
    CONTOURS_DATASET_ID,
    STREETS_DATASET_ID,
    assemble_crooked_block,
    bbox_intersects_where,
    bbox_of_line,
    build_geojson_url,
    expand_wgs84_bbox,
)


def feature(from_st: str, to_st: str, cnn: int, coords=None, active=1):
    if coords is None:
        coords = [
            [-122.4180, 37.8020],
            [-122.4170, 37.8020],
        ]
    return {
        "type": "Feature",
        "properties": {
            "street": "Lombard",
            "streetname": "Lombard St",
            "active": active,
            "f_st": from_st,
            "t_st": to_st,
            "cnn": cnn,
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
    }


def test_dataset_ids_and_url():
    assert STREETS_DATASET_ID == "3psu-pn9h"
    assert CONTOURS_DATASET_ID == "6d73-6c4f"
    url = build_geojson_url(
        STREETS_DATASET_ID,
        where="street='LOMBARD'",
        limit=500,
    )
    assert STREETS_DATASET_ID in url
    assert "/api/v3/views/" in url
    assert "query=" in url
    assert "LIMIT+500" in url


def test_assemble_two_segment_block_and_orientation():
    montclair = [-122.419003358, 37.802118545]
    hyde = [-122.419613973, 37.801994863]
    leavenworth = [-122.417966229, 37.802201309]

    assembled, segments = assemble_crooked_block(
        [
            feature("Jones St", "Taylor St", 10),
            feature("Leavenworth St", "Montclair Ter", 8448000, [leavenworth, montclair]),
            feature("Montclair Ter", "Hyde St", 8449000, [montclair, hyde]),
        ]
    )

    props = assembled["properties"]
    assert props["earthforge_segment_cnns"] == ["8449000", "8448000"]
    assert props["earthforge_route_nodes"] == [
        "HYDE",
        "MONTCLAIR TER",
        "LEAVENWORTH",
    ]
    assert props["earthforge_segment_count"] == 2
    assert len(segments) == 2
    assert assembled["geometry"]["coordinates"][0] == hyde
    assert assembled["geometry"]["coordinates"][-1] == leavenworth
    assert assembled["geometry"]["coordinates"].count(montclair) == 1


def test_bbox_expansion_and_query():
    picked = feature("Hyde St", "Leavenworth St", 20)
    bbox = bbox_of_line(picked)
    expanded = expand_wgs84_bbox(bbox, 80.0)
    assert expanded[0] < bbox[0]
    assert expanded[1] < bbox[1]
    assert expanded[2] > bbox[2]
    assert expanded[3] > bbox[3]

    where = bbox_intersects_where("the_geom", expanded)
    assert where.startswith("intersects(the_geom, 'POLYGON ((")
    assert where.endswith("))')")


def test_ambiguous_selection_fails():
    try:
        assemble_crooked_block(
            [
                feature("Hyde St", "Montclair Ter", 1),
                feature("Hyde St", "Montclair Ter", 2),
                feature("Montclair Ter", "Leavenworth St", 3),
            ]
        )
    except ValueError as exc:
        assert "exactly one" in str(exc)
    else:
        raise AssertionError("Expected ambiguous Lombard route selection to fail")


if __name__ == "__main__":
    test_dataset_ids_and_url()
    test_assemble_two_segment_block_and_orientation()
    test_bbox_expansion_and_query()
    test_ambiguous_selection_fails()
    print("EarthForge Lombard acquisition tests passed")
