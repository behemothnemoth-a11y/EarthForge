#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
RAW = PROJECT / "downloads" / "osm_poc_001.json"

OUT_BUILDINGS = PROJECT / "buildings" / "osm_buildings_review.geojson"
OUT_ROADS = PROJECT / "roads" / "osm_transport_review.geojson"
OUT_CONTEXT = PROJECT / "terrain" / "osm_surface_context_review.geojson"
OUT_REPORT = PROJECT / "validation" / "osm_poc001_import_report.json"


def feature_collection(features, name):
    return {
        "type": "FeatureCollection",
        "name": name,
        "earthforge_status": "REVIEW_ONLY",
        "features": features,
    }


def props(el):
    tags = dict(el.get("tags", {}))
    return {
        "osm_type": el.get("type"),
        "osm_id": el.get("id"),
        "tags": tags,
        "earthforge_status": "unverified",
    }


def geometry_coords(el):
    geom = el.get("geometry") or []
    return [[float(p["lon"]), float(p["lat"])] for p in geom if "lon" in p and "lat" in p]


def way_feature(el, kind):
    coords = geometry_coords(el)
    if len(coords) < 2:
        return None

    p = props(el)
    p["earthforge_class"] = kind

    if kind in ("building", "surface") and len(coords) >= 4 and coords[0] == coords[-1]:
        geometry = {"type": "Polygon", "coordinates": [coords]}
    else:
        geometry = {"type": "LineString", "coordinates": coords}

    return {
        "type": "Feature",
        "properties": p,
        "geometry": geometry,
    }


def main():
    if not RAW.exists():
        print(f"Missing raw OSM file: {RAW}", file=sys.stderr)
        print("Run tools/powershell/EarthForge_REDFIELD_FETCH_BASE.ps1 first.", file=sys.stderr)
        return 2

    data = json.loads(RAW.read_text(encoding="utf-8"))
    elements = data.get("elements", [])

    buildings = []
    roads = []
    context = []
    ignored = 0

    for el in elements:
        if el.get("type") != "way":
            ignored += 1
            continue

        tags = el.get("tags", {})
        f = None

        if "building" in tags:
            f = way_feature(el, "building")
            if f:
                buildings.append(f)
            continue

        if "highway" in tags:
            f = way_feature(el, "transport")
            if f:
                roads.append(f)
            continue

        if tags.get("amenity") == "parking" or "landuse" in tags or "natural" in tags:
            f = way_feature(el, "surface")
            if f:
                context.append(f)
            continue

        ignored += 1

    for path, obj in [
        (OUT_BUILDINGS, feature_collection(buildings, "redfield_poc001_osm_buildings_review")),
        (OUT_ROADS, feature_collection(roads, "redfield_poc001_osm_transport_review")),
        (OUT_CONTEXT, feature_collection(context, "redfield_poc001_osm_surface_context_review")),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    report = {
        "source": str(RAW.relative_to(ROOT)),
        "status": "review_required",
        "counts": {
            "raw_elements": len(elements),
            "building_features": len(buildings),
            "transport_features": len(roads),
            "surface_context_features": len(context),
            "ignored_or_unsupported_elements": ignored,
        },
        "warnings": [
            "This is not final EarthForge geometry.",
            "OSM relations are not normalized in this first-pass importer.",
            "All features must be compared against official mapping and visual references.",
            "Do not generate the L1 build from this file until L0 review is complete.",
        ],
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("EarthForge Redfield POC 001 OSM normalization complete.")
    print(json.dumps(report["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
