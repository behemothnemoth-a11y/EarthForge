#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.acquire.lombard_datasf import (
    CONTOURS_DATASET_ID,
    STREETS_DATASET_ID,
    bbox_of_line,
    build_geojson_url,
    expand_wgs84_bbox,
    orient_hyde_to_leavenworth,
    select_crooked_block,
    within_box_where,
)


def feature(from_st: str, to_st: str, cnn: int, active=1):
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
            "coordinates": [
                [-122.4180, 37.8020],
                [-122.4170, 37.8020],
            ],
        },
    }


def test_dataset_ids_and_url():
    assert STREETS_DATASET_ID == "3psu-pn9h"
    assert CONTOURS_DATASET_ID == "6d73-6c4f"
    url = build_geojson_url(
        STREETS_DATASET_ID,
        where="upper(street)='LOMBARD' AND active=1",
        limit=500,
    )
    assert STREETS_DATASET_ID in url
    assert "%24where=" in url
    assert "%24limit=500" in url


def test_select_exact_block_and_orientation():
    selected = select_crooked_block(
        [
            feature("Jones St", "Taylor St", 10),
            feature("Leavenworth St", "Hyde St", 20),
        ]
    )
    assert selected["properties"]["cnn"] == 20

    oriented = orient_hyde_to_leavenworth(selected)
    assert oriented["geometry"]["coordinates"][0] == [-122.4170, 37.8020]
    assert oriented["geometry"]["coordinates"][-1] == [-122.4180, 37.8020]
    assert oriented["properties"]["earthforge_source_direction_reversed"] is True


def test_bbox_expansion_and_query():
    picked = feature("Hyde St", "Leavenworth St", 20)
    bbox = bbox_of_line(picked)
    expanded = expand_wgs84_bbox(bbox, 80.0)
    assert expanded[0] < bbox[0]
    assert expanded[1] < bbox[1]
    assert expanded[2] > bbox[2]
    assert expanded[3] > bbox[3]

    where = within_box_where("the_geom", expanded)
    assert where.startswith("within_box(the_geom,")
    assert where.endswith(")")


def test_ambiguous_selection_fails():
    try:
        select_crooked_block(
            [
                feature("Hyde St", "Leavenworth St", 1),
                feature("Hyde St", "Leavenworth St", 2),
            ]
        )
    except ValueError as exc:
        assert "exactly one" in str(exc)
    else:
        raise AssertionError("Expected ambiguous Lombard source selection to fail")


if __name__ == "__main__":
    test_dataset_ids_and_url()
    test_select_exact_block_and_orientation()
    test_bbox_expansion_and_query()
    test_ambiguous_selection_fails()
    print("EarthForge Lombard acquisition tests passed")
