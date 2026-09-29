#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects" / "redfield_sd"
POC = PROJECT / "poc_001"

BUILDINGS_IN = PROJECT / "buildings" / "osm_buildings_review.geojson"
ROADS_IN = PROJECT / "roads" / "osm_transport_review.geojson"

FRAME_OUT = POC / "locked_frame.json"
LOCAL_OUT = POC / "l0_geometry_local.json"
QUEUE_OUT = POC / "building_match_queue.json"
CELLS_OUT = POC / "l0_block_plan.csv"
PREVIEW_OUT = POC / "l0_preview.svg"
BUILDINGS_OUT = PROJECT / "buildings" / "poc001_buildings_selected.geojson"
ROADS_OUT = PROJECT / "roads" / "poc001_transport_selected.geojson"
REPORT_OUT = PROJECT / "validation" / "poc001_l0_generation_report.json"

Point = Tuple[float, float]
LocalPoint = Tuple[float, float]


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def outer_coords(feature: dict) -> List[Point]:
    geometry = feature.get("geometry") or {}
    t = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if t == "Polygon":
        return [tuple(p) for p in coords[0]]
    if t == "LineString":
        return [tuple(p) for p in coords]
    return []


def tags(feature: dict) -> dict:
    return (feature.get("properties") or {}).get("tags") or {}


def osm_id(feature: dict):
    return (feature.get("properties") or {}).get("osm_id")


def nearest_pair(a: Sequence[Point], b: Sequence[Point]) -> Tuple[Point, Point, float]:
    best = None
    for pa in a:
        for pb in b:
            dx = pa[0] - pb[0]
            dy = pa[1] - pb[1]
            d2 = dx * dx + dy * dy
            if best is None or d2 < best[2]:
                best = (pa, pb, d2)
    if best is None:
        raise ValueError("Cannot compare empty geometries")
    return best[0], best[1], math.sqrt(best[2])


def midpoint(a: Point, b: Point) -> Point:
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


def find_named_lines(features: Sequence[dict], needle: str) -> List[dict]:
    needle = needle.lower()
    return [
        f for f in features
        if needle in str(tags(f).get("name", "")).lower()
        and (f.get("geometry") or {}).get("type") == "LineString"
    ]


def intersection_from_shared_geometry(main: dict, candidates: Sequence[dict], label: str) -> Point:
    mc = outer_coords(main)
    best = None
    for feature in candidates:
        fc = outer_coords(feature)
        pa, pb, d = nearest_pair(mc, fc)
        if best is None or d < best[0]:
            best = (d, midpoint(pa, pb), osm_id(feature), pa, pb)
    if best is None:
        raise ValueError(f"No candidate geometry for {label}")
    # OSM ways at a junction normally share a node. Allow a small gap because
    # review data can be imperfect; report the gap later.
    return best[1]


def polygon_centroid_simple(coords: Sequence[Point]) -> Point:
    if not coords:
        raise ValueError("Empty polygon")
    pts = list(coords)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    return (
        sum(p[0] for p in pts) / len(pts),
        sum(p[1] for p in pts) / len(pts),
    )


def meters_scales(lat_deg: float) -> Tuple[float, float]:
    lat = math.radians(lat_deg)
    # Good local approximation for a sub-kilometer POC.
    m_per_deg_lon = 111320.0 * math.cos(lat)
    m_per_deg_lat = 110574.0
    return m_per_deg_lon, m_per_deg_lat


class Transform:
    def __init__(self, lon0: float, lat0: float):
        self.lon0 = lon0
        self.lat0 = lat0
        self.m_lon, self.m_lat = meters_scales(lat0)

    def to_local(self, p: Point) -> LocalPoint:
        # Minecraft convention: +X east, +Z south, so north is negative Z.
        x = (p[0] - self.lon0) * self.m_lon
        z = -(p[1] - self.lat0) * self.m_lat
        return (x, z)

    def to_block(self, p: Point) -> Tuple[int, int]:
        x, z = self.to_local(p)
        return (int(round(x)), int(round(z)))


def feature_mean_lon(feature: dict) -> float:
    c = outer_coords(feature)
    return sum(p[0] for p in c) / len(c)


def feature_lat_span(feature: dict) -> float:
    c = outer_coords(feature)
    ys = [p[1] for p in c]
    return max(ys) - min(ys)


def choose_side_alleys(roads: Sequence[dict], main_lon: float, south_lat: float, north_lat: float):
    candidates = []
    for f in roads:
        t = tags(f)
        if t.get("service") != "alley":
            continue
        coords = outer_coords(f)
        if len(coords) < 2:
            continue
        ys = [p[1] for p in coords]
        overlap = max(0.0, min(max(ys), north_lat) - max(min(ys), south_lat))
        if overlap <= 0:
            continue
        lon = feature_mean_lon(f)
        span = feature_lat_span(f)
        candidates.append((f, lon, span, overlap))

    west = [c for c in candidates if c[1] < main_lon and c[2] > 0.0005]
    east = [c for c in candidates if c[1] > main_lon and c[2] > 0.0005]
    if not west or not east:
        raise ValueError("Could not identify both side alleys")

    west_pick = max(west, key=lambda c: c[1])  # closest west
    east_pick = min(east, key=lambda c: c[1])  # closest east
    return west_pick[0], east_pick[0]


def point_inside_rect(p: Point, west: float, south: float, east: float, north: float) -> bool:
    return west <= p[0] <= east and south <= p[1] <= north


def line_bbox(coords: Sequence[Point]):
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    return min(xs), min(ys), max(xs), max(ys)


def bboxes_intersect(a, b) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def wgs84_feature_collection(features: Sequence[dict], name: str) -> dict:
    return {
        "type": "FeatureCollection",
        "name": name,
        "earthforge_status": "POC001_SELECTED_REVIEW",
        "features": list(features),
    }


def line_local(feature: dict, tf: Transform) -> List[LocalPoint]:
    return [tf.to_local(p) for p in outer_coords(feature)]


def polygon_local(feature: dict, tf: Transform) -> List[LocalPoint]:
    return [tf.to_local(p) for p in outer_coords(feature)]


def point_in_polygon(px: float, pz: float, poly: Sequence[LocalPoint]) -> bool:
    inside = False
    n = len(poly)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, zi = poly[i]
        xj, zj = poly[j]
        if ((zi > pz) != (zj > pz)):
            denom = (zj - zi)
            if abs(denom) < 1e-12:
                denom = 1e-12
            x_cross = (xj - xi) * (pz - zi) / denom + xi
            if px < x_cross:
                inside = not inside
        j = i
    return inside


def raster_polygon(poly: Sequence[LocalPoint]) -> set[Tuple[int, int]]:
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    min_x = math.floor(min(xs))
    max_x = math.ceil(max(xs))
    min_z = math.floor(min(zs))
    max_z = math.ceil(max(zs))
    out = set()
    for x in range(min_x, max_x + 1):
        for z in range(min_z, max_z + 1):
            if point_in_polygon(x + 0.5, z + 0.5, poly):
                out.add((x, z))
    return out


def distance_point_segment(px, pz, ax, az, bx, bz):
    vx, vz = bx - ax, bz - az
    wx, wz = px - ax, pz - az
    vv = vx * vx + vz * vz
    if vv <= 1e-12:
        return math.hypot(px - ax, pz - az)
    t = max(0.0, min(1.0, (wx * vx + wz * vz) / vv))
    cx, cz = ax + t * vx, az + t * vz
    return math.hypot(px - cx, pz - cz)


def raster_line(coords: Sequence[LocalPoint], half_width: float, bounds) -> set[Tuple[int, int]]:
    if len(coords) < 2:
        return set()
    min_x, min_z, max_x, max_z = bounds
    out = set()
    for x in range(math.floor(min_x), math.ceil(max_x) + 1):
        for z in range(math.floor(min_z), math.ceil(max_z) + 1):
            px, pz = x + 0.5, z + 0.5
            best = min(
                distance_point_segment(px, pz, *coords[i], *coords[i + 1])
                for i in range(len(coords) - 1)
            )
            if best <= half_width:
                out.add((x, z))
    return out


def identify_sidewalks(roads: Sequence[dict], tf: Transform, main_x: float, south_z: float, north_z: float):
    candidates = []
    block_span = abs(north_z - south_z)
    for f in roads:
        t = tags(f)
        if t.get("footway") != "sidewalk":
            continue
        coords = line_local(f, tf)
        if len(coords) < 2:
            continue
        xs = [p[0] for p in coords]
        zs = [p[1] for p in coords]
        z_span = max(zs) - min(zs)
        mean_x = sum(xs) / len(xs)
        if z_span >= block_span * 0.5 and abs(mean_x - main_x) < 40:
            candidates.append((f, mean_x, z_span))
    west = [c for c in candidates if c[1] < main_x]
    east = [c for c in candidates if c[1] > main_x]
    if not west or not east:
        return None, None
    return max(west, key=lambda c: c[1])[0], min(east, key=lambda c: c[1])[0]


def feature_role(feature: dict) -> str:
    t = tags(feature)
    if t.get("service") == "alley":
        return "alley"
    if t.get("footway") == "sidewalk":
        return "sidewalk"
    if t.get("footway") == "crossing":
        return "crossing"
    name = str(t.get("name", ""))
    if name == "Main Street":
        return "main_street"
    if "6th Avenue" in name or "7th Avenue" in name:
        return "avenue"
    if t.get("highway") in ("residential", "tertiary", "trunk"):
        return "road"
    return "transport"


def write_svg(path: Path, cells: Dict[Tuple[int, int], Tuple[str, str]], frame: dict):
    # This is a diagnostic map, not an artistic render. Colors are fixed by role
    # solely to make overlapping geometry easy to spot.
    role_color = {
        "building_footprint": "#e67e22",
        "main_street": "#232323",
        "avenue": "#555555",
        "road": "#666666",
        "alley": "#8a8a8a",
        "sidewalk": "#c9c9c9",
        "crossing": "#f4f4f4",
        "project_anchor": "#c0392b",
    }
    xs = [p[0] for p in cells] or [0]
    zs = [p[1] for p in cells] or [0]
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    width = max_x - min_x + 1
    height = max_z - min_z + 1
    scale = 4
    margin = 60
    svg_w = width * scale + margin * 2
    svg_h = height * scale + margin * 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g shape-rendering="crispEdges">'
    ]
    # SVG screen Y grows down. Local Z already grows south, so it maps naturally.
    for (x, z), (role, block) in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        sx = margin + (x - min_x) * scale
        sy = margin + (z - min_z) * scale
        color = role_color.get(role, "#9b59b6")
        parts.append(f'<rect x="{sx}" y="{sy}" width="{scale}" height="{scale}" fill="{color}"/>')
    parts.append('</g>')

    parts.append(f'<text x="{margin}" y="25" font-family="monospace" font-size="16">EarthForge REDFIELD_POC_001 - L0 GEO</text>')
    parts.append(f'<text x="{margin}" y="45" font-family="monospace" font-size="12">+X east | +Z south | 1 block = 1 meter | orange = source building footprint</text>')

    legend = [
        ("building_footprint", "building"),
        ("main_street", "Main St"),
        ("avenue", "6th/7th Ave"),
        ("alley", "alley"),
        ("sidewalk", "sidewalk"),
        ("crossing", "crossing"),
        ("project_anchor", "anchor"),
    ]
    lx = margin
    ly = svg_h - 20
    for role, label in legend:
        color = role_color[role]
        parts.append(f'<rect x="{lx}" y="{ly-10}" width="10" height="10" fill="{color}"/>')
        parts.append(f'<text x="{lx+14}" y="{ly}" font-family="monospace" font-size="11">{label}</text>')
        lx += 90

    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> int:
    buildings_fc = load_json(BUILDINGS_IN)
    roads_fc = load_json(ROADS_IN)
    buildings = buildings_fc.get("features", [])
    roads = roads_fc.get("features", [])

    main_candidates = find_named_lines(roads, "Main Street")
    if not main_candidates:
        raise ValueError("Main Street geometry not found")
    main_street = max(main_candidates, key=lambda f: feature_lat_span(f))

    ave7 = find_named_lines(roads, "7th Avenue")
    ave6 = find_named_lines(roads, "6th Avenue")
    if not ave7 or not ave6:
        raise ValueError("6th/7th Avenue geometry not found")

    p7 = intersection_from_shared_geometry(main_street, ave7, "7th Avenue")
    p6 = intersection_from_shared_geometry(main_street, ave6, "6th Avenue")

    south_lat = min(p7[1], p6[1])
    north_lat = max(p7[1], p6[1])
    if abs(p7[1] - south_lat) > 0.0002:
        raise ValueError("Expected 7th Avenue to be south of 6th Avenue")

    anchor = p7
    tf = Transform(*anchor)
    main_local = line_local(main_street, tf)
    main_x = sum(p[0] for p in main_local) / len(main_local)

    west_alley, east_alley = choose_side_alleys(roads, anchor[0], south_lat, north_lat)
    west_lon = feature_mean_lon(west_alley)
    east_lon = feature_mean_lon(east_alley)

    if west_lon >= anchor[0] or east_lon <= anchor[0]:
        raise ValueError("Alley frame does not bracket Main Street")

    selected_buildings = []
    queue = []
    for f in buildings:
        coords = outer_coords(f)
        if not coords:
            continue
        c = polygon_centroid_simple(coords)
        if point_inside_rect(c, west_lon, south_lat, east_lon, north_lat):
            selected_buildings.append(f)
            lx, lz = tf.to_local(c)
            side = "west" if lx < 0 else "east"
            queue.append({
                "osm_id": osm_id(f),
                "side_of_main": side,
                "centroid_wgs84": {"lon": c[0], "lat": c[1]},
                "centroid_local_m": {"x": round(lx, 3), "z": round(lz, 3)},
                "address": None,
                "match_status": "unmatched",
                "source_name": tags(f).get("name"),
                "building_tag": tags(f).get("building"),
            })

    queue.sort(key=lambda q: (q["side_of_main"], -q["centroid_local_m"]["z"]))

    crop_bbox = (west_lon, south_lat, east_lon, north_lat)
    selected_roads = []
    for f in roads:
        coords = outer_coords(f)
        if not coords:
            continue
        if bboxes_intersect(line_bbox(coords), crop_bbox):
            selected_roads.append(f)

    POC.mkdir(parents=True, exist_ok=True)
    BUILDINGS_OUT.parent.mkdir(parents=True, exist_ok=True)
    ROADS_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)

    BUILDINGS_OUT.write_text(
        json.dumps(wgs84_feature_collection(selected_buildings, "redfield_poc001_buildings_selected"), indent=2) + "\n",
        encoding="utf-8",
    )
    ROADS_OUT.write_text(
        json.dumps(wgs84_feature_collection(selected_roads, "redfield_poc001_transport_selected"), indent=2) + "\n",
        encoding="utf-8",
    )

    p6_local = tf.to_local(p6)
    west_x = tf.to_local((west_lon, anchor[1]))[0]
    east_x = tf.to_local((east_lon, anchor[1]))[0]
    north_z = p6_local[1]
    south_z = 0.0

    # Reserve a little context outside the street/alley frame for the future
    # Litematica registration point and for seeing intersections in preview.
    plan_min_x = math.floor(west_x - 12)
    plan_max_x = math.ceil(east_x + 12)
    plan_min_z = math.floor(north_z - 12)
    plan_max_z = math.ceil(south_z + 12)
    plan_bounds = (plan_min_x, plan_min_z, plan_max_x, plan_max_z)

    registration_local = {
        "player_feet_x": plan_min_x + 3,
        "player_feet_z": plan_max_z - 3,
        "marker_y_offset": -1,
        "status": "reserved_for_future_litematica",
    }

    west_sidewalk, east_sidewalk = identify_sidewalks(roads, tf, main_x, south_z, north_z)
    main_corridor_source = "default_width"
    main_half_width = 12.0
    if west_sidewalk and east_sidewalk:
        wx = sum(p[0] for p in line_local(west_sidewalk, tf)) / len(line_local(west_sidewalk, tf))
        ex = sum(p[0] for p in line_local(east_sidewalk, tf)) / len(line_local(east_sidewalk, tf))
        main_half_width = max(abs(wx - main_x), abs(ex - main_x))
        main_corridor_source = "derived_from_parallel_sidewalk_centerlines"

    cells: Dict[Tuple[int, int], Tuple[str, str]] = {}

    def apply(points: Iterable[Tuple[int, int]], role: str, block: str, overwrite: bool = True):
        for pt in points:
            x, z = pt
            if x < plan_min_x or x > plan_max_x or z < plan_min_z or z > plan_max_z:
                continue
            if overwrite or pt not in cells:
                cells[pt] = (role, block)

    # Roads first.
    main_points = raster_line(line_local(main_street, tf), main_half_width, plan_bounds)
    apply(main_points, "main_street", "minecraft:black_concrete")

    # Avenue corridors are provisional 18 m total width for this first diagnostic pass.
    for f in selected_roads:
        role = feature_role(f)
        if role == "avenue":
            apply(raster_line(line_local(f, tf), 9.0, plan_bounds), "avenue", "minecraft:gray_concrete")

    # Alleys.
    for f in selected_roads:
        if feature_role(f) == "alley":
            apply(raster_line(line_local(f, tf), 2.0, plan_bounds), "alley", "minecraft:polished_andesite")

    # Sidewalks and crossings.
    for f in selected_roads:
        role = feature_role(f)
        if role == "sidewalk":
            apply(raster_line(line_local(f, tf), 1.5, plan_bounds), "sidewalk", "minecraft:smooth_stone")
        elif role == "crossing":
            apply(raster_line(line_local(f, tf), 1.25, plan_bounds), "crossing", "minecraft:white_concrete")

    # Source building footprints always win over diagnostic transport widths.
    building_cell_count = 0
    for f in selected_buildings:
        pts = raster_polygon(polygon_local(f, tf))
        building_cell_count += len(pts)
        apply(pts, "building_footprint", "minecraft:orange_concrete", overwrite=True)

    # Project anchor is a diagnostic cell, not the future Litematica stand block.
    apply({(0, 0)}, "project_anchor", "minecraft:red_concrete", overwrite=True)

    with CELLS_OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["x", "y", "z", "role", "block"])
        for (x, z), (role, block) in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            writer.writerow([x, 0, z, role, block])

    local_model = {
        "schema_version": 1,
        "project_id": "redfield_sd",
        "milestone": "REDFIELD_POC_001",
        "coordinate_frame": {
            "anchor_wgs84": {"lon": anchor[0], "lat": anchor[1]},
            "anchor_description": "Main Street / 7th Avenue centerline intersection",
            "x_positive": "east",
            "z_positive": "south",
            "scale": "1 meter = 1 Minecraft block",
        },
        "frame_local_m": {
            "west_alley_x": round(west_x, 3),
            "east_alley_x": round(east_x, 3),
            "south_7th_z": round(south_z, 3),
            "north_6th_z": round(north_z, 3),
        },
        "buildings": [
            {
                "osm_id": osm_id(f),
                "polygon_xz_m": [[round(x, 3), round(z, 3)] for x, z in polygon_local(f, tf)],
                "tags": tags(f),
            }
            for f in selected_buildings
        ],
        "transport": [
            {
                "osm_id": osm_id(f),
                "role": feature_role(f),
                "line_xz_m": [[round(x, 3), round(z, 3)] for x, z in line_local(f, tf)],
                "tags": tags(f),
            }
            for f in selected_roads
            if (f.get("geometry") or {}).get("type") == "LineString"
        ],
    }
    LOCAL_OUT.write_text(json.dumps(local_model, indent=2) + "\n", encoding="utf-8")

    queue_doc = {
        "schema_version": 1,
        "project_id": "redfield_sd",
        "milestone": "REDFIELD_POC_001",
        "matching_policy": "Do not infer addresses from geometry order alone.",
        "selected_count": len(queue),
        "queue": queue,
    }
    QUEUE_OUT.write_text(json.dumps(queue_doc, indent=2) + "\n", encoding="utf-8")

    frame = {
        "schema_version": 1,
        "project_id": "redfield_sd",
        "milestone": "REDFIELD_POC_001",
        "status": "locked_for_l0_review",
        "anchor": {
            "description": "Main Street / 7th Avenue centerline intersection",
            "wgs84": {"lon": anchor[0], "lat": anchor[1]},
            "minecraft_horizontal": {"x": 0, "z": 0},
        },
        "north_control": {
            "description": "Main Street / 6th Avenue centerline intersection",
            "wgs84": {"lon": p6[0], "lat": p6[1]},
            "local_m": {"x": round(p6_local[0], 3), "z": round(p6_local[1], 3)},
        },
        "orientation": {
            "x_positive": "east",
            "z_positive": "south",
            "minecraft_north": "-Z",
            "rotation_locked": True,
            "mirror": "none",
        },
        "side_boundaries": {
            "west_alley_osm_id": osm_id(west_alley),
            "east_alley_osm_id": osm_id(east_alley),
            "west_alley_lon_mean": west_lon,
            "east_alley_lon_mean": east_lon,
            "west_local_x_m": round(west_x, 3),
            "east_local_x_m": round(east_x, 3),
        },
        "plan_bounds_blocks": {
            "min_x": plan_min_x,
            "min_z": plan_min_z,
            "max_x": plan_max_x,
            "max_z": plan_max_z,
        },
        "future_litematica_registration": registration_local,
        "selected_building_osm_ids": [osm_id(f) for f in selected_buildings],
    }
    FRAME_OUT.write_text(json.dumps(frame, indent=2) + "\n", encoding="utf-8")

    write_svg(PREVIEW_OUT, cells, frame)

    role_counts = {}
    for role, _block in cells.values():
        role_counts[role] = role_counts.get(role, 0) + 1

    report = {
        "schema_version": 1,
        "project_id": "redfield_sd",
        "milestone": "REDFIELD_POC_001",
        "status": "l0_review_required",
        "inputs": {
            "buildings": str(BUILDINGS_IN.relative_to(ROOT)),
            "transport": str(ROADS_IN.relative_to(ROOT)),
        },
        "derived": {
            "anchor_wgs84": {"lon": anchor[0], "lat": anchor[1]},
            "north_intersection_wgs84": {"lon": p6[0], "lat": p6[1]},
            "selected_buildings": len(selected_buildings),
            "selected_transport_features": len(selected_roads),
            "block_cells_total": len(cells),
            "building_cells_before_overlap": building_cell_count,
            "cell_role_counts": role_counts,
            "frame_width_blocks": plan_max_x - plan_min_x + 1,
            "frame_depth_blocks": plan_max_z - plan_min_z + 1,
            "main_corridor_half_width_m": round(main_half_width, 3),
            "main_corridor_width_source": main_corridor_source,
        },
        "validation": {
            "building_count_reasonable": 15 <= len(selected_buildings) <= 30,
            "anchor_is_zero_xz": True,
            "microblocks_used": False,
            "address_assignments_made": False,
            "litematica_generated": False,
        },
        "warnings": [
            "This is an L0 diagnostic block plan, not a finished road model.",
            "6th/7th Avenue diagnostic widths are provisional defaults.",
            "Building footprints are source geometry but still require visual/official-map validation.",
            "The future Litematica registration point is reserved but no Litematica is generated by Drop 0003.",
        ],
    }
    REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("EarthForge Redfield POC 001 L0 frame generated.")
    print(f"  Anchor          : {anchor[1]:.7f}, {anchor[0]:.7f}")
    print(f"  6th intersection: {p6[1]:.7f}, {p6[0]:.7f}")
    print(f"  West alley OSM  : {osm_id(west_alley)}")
    print(f"  East alley OSM  : {osm_id(east_alley)}")
    print(f"  Buildings       : {len(selected_buildings)}")
    print(f"  Transport       : {len(selected_roads)}")
    print(f"  Plan cells      : {len(cells)}")
    print(f"  Frame           : {report['derived']['frame_width_blocks']} x {report['derived']['frame_depth_blocks']} blocks")
    print(f"  Preview         : {PREVIEW_OUT.relative_to(ROOT)}")

    if not report["validation"]["building_count_reasonable"]:
        print("WARNING: selected building count is outside the expected review range.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
