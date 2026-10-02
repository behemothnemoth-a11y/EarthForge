#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

STREETS_DATASET_ID = "3psu-pn9h"
CONTOURS_DATASET_ID = "6d73-6c4f"
DATASF_QUERY_ROOT = "https://data.sf.gov/api/v3/views"

HYDE = "HYDE"
LEAVENWORTH = "LEAVENWORTH"
LOMBARD = "LOMBARD"


def normalize_street(value: Any) -> str:
    text = re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()
    suffixes = {"ST", "STREET", "AVE", "AVENUE", "RD", "ROAD", "BLVD", "BOULEVARD"}
    parts = text.split()
    while parts and parts[-1] in suffixes:
        parts.pop()
    return " ".join(parts)


def build_geojson_url(dataset_id: str, *, where: str | None = None, limit: int = 5000) -> str:
    query = "SELECT *"
    if where:
        query += f" WHERE {where}"
    query += f" LIMIT {int(limit)}"
    return f"{DATASF_QUERY_ROOT}/{dataset_id}/query.geojson?{urlencode({'query': query})}"


def fetch_geojson(url: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/geo+json, application/json",
            "User-Agent": "EarthForge/1.0 (+https://github.com/behemothnemoth-a11y/EarthForge)",
        },
    )
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if payload.get("type") != "FeatureCollection":
        raise ValueError(f"Expected GeoJSON FeatureCollection from {url}")
    return payload


def feature_properties(feature: dict) -> dict:
    return feature.get("properties") or {}


def prop(props: dict, *keys: str):
    lower = {str(k).lower(): v for k, v in props.items()}
    for key in keys:
        if key.lower() in lower:
            return lower[key.lower()]
    return None


def _line_coordinates(feature: dict) -> list[list[float]]:
    geometry = feature.get("geometry") or {}
    t = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if t == "LineString":
        return coords
    if t == "MultiLineString" and len(coords) == 1:
        return coords[0]
    raise ValueError(f"Expected one LineString centerline, got {t}")


def is_active_lombard(feature: dict) -> bool:
    props = feature_properties(feature)
    street = normalize_street(prop(props, "street", "streetname", "streetname_gc"))
    active = prop(props, "active")
    if active is None:
        active_ok = True
    else:
        active_ok = str(active).strip().upper() not in {"0", "FALSE", "N", "NO"}
    return street == LOMBARD and active_ok


def _cross_streets(feature: dict) -> tuple[str, str]:
    props = feature_properties(feature)
    return (
        normalize_street(prop(props, "f_st", "from_st", "from_street")),
        normalize_street(prop(props, "t_st", "to_st", "to_street")),
    )


def _reverse_feature_geometry(feature: dict) -> dict:
    clone = json.loads(json.dumps(feature))
    geometry = clone["geometry"]
    if geometry["type"] == "LineString":
        geometry["coordinates"].reverse()
    elif geometry["type"] == "MultiLineString" and len(geometry["coordinates"]) == 1:
        geometry["coordinates"][0].reverse()
    else:
        raise ValueError("Cannot reverse unexpected centerline geometry")
    clone.setdefault("properties", {})["earthforge_source_direction_reversed"] = True
    return clone


def _orient_segment_from(feature: dict, start_node: str) -> tuple[dict, str]:
    from_st, to_st = _cross_streets(feature)
    if from_st == start_node:
        return feature, to_st
    if to_st == start_node:
        return _reverse_feature_geometry(feature), from_st
    raise ValueError(
        f"Segment {_cross_streets(feature)} does not touch route node {start_node!r}"
    )


def assemble_crooked_block(features: list[dict]) -> tuple[dict, list[dict]]:
    candidates = [f for f in features if is_active_lombard(f)]
    graph: dict[str, list[tuple[int, str]]] = {}
    for index, feature in enumerate(candidates):
        from_st, to_st = _cross_streets(feature)
        if not from_st or not to_st:
            continue
        graph.setdefault(from_st, []).append((index, to_st))
        graph.setdefault(to_st, []).append((index, from_st))

    queue: list[tuple[str, list[int], set[str]]] = [(HYDE, [], {HYDE})]
    paths: list[list[int]] = []
    while queue:
        node, path, seen_nodes = queue.pop(0)
        if node == LEAVENWORTH:
            paths.append(path)
            continue
        if len(path) >= 12:
            continue
        for segment_index, other in graph.get(node, []):
            if segment_index in path or other in seen_nodes:
                continue
            queue.append((other, path + [segment_index], seen_nodes | {other}))

    if len(paths) != 1:
        diagnostic = [
            {
                "cnn": prop(feature_properties(f), "cnn", "cnntext"),
                "from": _cross_streets(f)[0],
                "to": _cross_streets(f)[1],
            }
            for f in candidates
        ]
        raise ValueError(
            "Expected exactly one active Lombard path from Hyde to Leavenworth; "
            f"found {len(paths)}. Candidates: {diagnostic}"
        )

    current = HYDE
    route_coords: list[list[float]] = []
    oriented_segments: list[dict] = []
    route_nodes = [HYDE]

    for segment_index in paths[0]:
        oriented, next_node = _orient_segment_from(candidates[segment_index], current)
        coords = _line_coordinates(oriented)
        if route_coords:
            ax, ay = route_coords[-1][:2]
            bx, by = coords[0][:2]
            if math.hypot(float(ax) - float(bx), float(ay) - float(by)) > 1e-6:
                raise ValueError(
                    f"Lombard source segments do not meet at {current}: "
                    f"{route_coords[-1]} vs {coords[0]}"
                )
            route_coords.extend(coords[1:])
        else:
            route_coords.extend(coords)
        oriented_segments.append(oriented)
        current = next_node
        route_nodes.append(current)

    if current != LEAVENWORTH:
        raise ValueError(f"Assembled Lombard route ended at {current}, not Leavenworth")

    segment_cnns = [
        str(prop(feature_properties(f), "cnn", "cnntext"))
        for f in oriented_segments
    ]
    assembled = {
        "type": "Feature",
        "properties": {
            "street": "LOMBARD",
            "streetname": "LOMBARD ST",
            "earthforge_route_from": HYDE,
            "earthforge_route_to": LEAVENWORTH,
            "earthforge_route_nodes": route_nodes,
            "earthforge_segment_cnns": segment_cnns,
            "earthforge_segment_count": len(oriented_segments),
        },
        "geometry": {
            "type": "LineString",
            "coordinates": route_coords,
        },
    }
    return assembled, oriented_segments


def bbox_of_line(feature: dict) -> tuple[float, float, float, float]:
    coords = _line_coordinates(feature)
    xs = [float(p[0]) for p in coords]
    ys = [float(p[1]) for p in coords]
    return min(xs), min(ys), max(xs), max(ys)


def expand_wgs84_bbox(
    bbox: tuple[float, float, float, float], margin_m: float
) -> tuple[float, float, float, float]:
    west, south, east, north = bbox
    lat = (south + north) * 0.5
    lat_margin = margin_m / 111_132.0
    lon_scale = max(1e-9, 111_320.0 * math.cos(math.radians(lat)))
    lon_margin = margin_m / lon_scale
    return west - lon_margin, south - lat_margin, east + lon_margin, north + lat_margin


def bbox_intersects_where(
    geometry_field: str, bbox: tuple[float, float, float, float]
) -> str:
    west, south, east, north = bbox
    polygon = (
        f"POLYGON (({west:.8f} {south:.8f}, "
        f"{east:.8f} {south:.8f}, "
        f"{east:.8f} {north:.8f}, "
        f"{west:.8f} {north:.8f}, "
        f"{west:.8f} {south:.8f}))"
    )
    return f"intersects({geometry_field}, '{polygon}')"


def acquisition_urls(margin_m: float = 80.0) -> dict:
    street_where = "street='LOMBARD'"
    return {
        "streets": build_geojson_url(
            STREETS_DATASET_ID,
            where=street_where,
            limit=500,
        ),
        "contours_template": (
            f"{DATASF_QUERY_ROOT}/{CONTOURS_DATASET_ID}/query.geojson?"
            "query=SELECT%20*%20WHERE%20within_box(the_geom,N,W,S,E)%20LIMIT%205000"
        ),
        "margin_m": margin_m,
    }


def acquire(output_dir: Path, *, margin_m: float = 80.0) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    urls = acquisition_urls(margin_m)

    streets = fetch_geojson(urls["streets"])
    selected, source_segments = assemble_crooked_block(
        streets.get("features") or []
    )
    selected_collection = {
        "type": "FeatureCollection",
        "name": "lombard_hyde_to_leavenworth_centerline",
        "features": [selected],
    }
    segments_collection = {
        "type": "FeatureCollection",
        "name": "lombard_hyde_to_leavenworth_source_segments",
        "features": source_segments,
    }

    source_bbox = bbox_of_line(selected)
    query_bbox = expand_wgs84_bbox(source_bbox, margin_m)
    contour_where = bbox_intersects_where("the_geom", query_bbox)
    contour_url = build_geojson_url(
        CONTOURS_DATASET_ID,
        where=contour_where,
        limit=5000,
    )
    contours = fetch_geojson(contour_url)

    centerline_path = output_dir / "centerline_wgs84.geojson"
    segments_path = output_dir / "centerline_segments_wgs84.geojson"
    contours_path = output_dir / "contours_wgs84.geojson"
    manifest_path = output_dir / "acquisition.json"

    centerline_path.write_text(
        json.dumps(selected_collection, indent=2) + "\n",
        encoding="utf-8",
    )
    segments_path.write_text(
        json.dumps(segments_collection, indent=2) + "\n",
        encoding="utf-8",
    )
    contours_path.write_text(
        json.dumps(contours, indent=2) + "\n",
        encoding="utf-8",
    )

    props = feature_properties(selected)
    manifest = {
        "schema_version": 1,
        "project_id": "lombard_street_sf",
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "centerline": {
            "dataset_id": STREETS_DATASET_ID,
            "request_url": urls["streets"],
            "selected_cnns": props.get("earthforge_segment_cnns"),
            "segment_count": props.get("earthforge_segment_count"),
            "route_nodes": props.get("earthforge_route_nodes"),
            "route_from": props.get("earthforge_route_from"),
            "route_to": props.get("earthforge_route_to"),
            "source_bbox_wgs84": list(source_bbox),
            "output": centerline_path.name,
            "segments_output": segments_path.name,
        },
        "contours": {
            "dataset_id": CONTOURS_DATASET_ID,
            "request_url": contour_url,
            "query_bbox_wgs84": list(query_bbox),
            "margin_m": margin_m,
            "feature_count": len(contours.get("features") or []),
            "output": contours_path.name,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Acquire source-backed Lombard centerline and local DataSF contour slice."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("projects/lombard_street_sf/acquired"),
    )
    parser.add_argument("--margin-m", type=float, default=80.0)
    parser.add_argument("--print-urls", action="store_true")
    args = parser.parse_args()

    if args.margin_m <= 0:
        raise ValueError("--margin-m must be > 0")

    if args.print_urls:
        print(json.dumps(acquisition_urls(args.margin_m), indent=2))
        return 0

    result = acquire(args.output_dir, margin_m=args.margin_m)
    print(
        f"Wrote Lombard acquisition to {args.output_dir} | "
        f"CNNs {','.join(result['centerline']['selected_cnns'] or [])} | "
        f"{result['contours']['feature_count']} contour features"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
