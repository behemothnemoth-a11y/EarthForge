# Road / Terrain Corridor Core

EarthForge builds difficult streets **from the road outward**.

For steep, curved, switchback, terraced, or otherwise constrained streets, the
road corridor is the geometric spine. Curbs, sidewalks, retaining walls,
stairs, landscaping, parcels, and buildings should not be independently
eyeballed into place.

## Truth order

1. lock the project-local centerline vertices in meters;
2. lock measured elevation controls along that centerline;
3. generate a station/elevation profile and inspect grade changes;
4. generate roadway edges, curb outers, and sidewalk outers from the same spine;
5. validate the corridor against source data and reference imagery;
6. only then build adjacent retaining walls, stairs, terraces, planting, and lots;
7. buildings come after the street/lot relationship is accepted.

A source centerline vertex is always preserved as a sample station. Regular
sampling is added between vertices; it never replaces them.

## Coordinate convention

The corridor core uses EarthForge project-local meters:

- `+X` = east
- `+Z` = south
- `+Y` = up

Minecraft coordinates remain an output representation. The road model should
stay metric until realization/export.

## Elevation profile

`pipeline/terrain/elevation_profile.py` provides a piecewise-linear measured
profile along road station.

Each control contains:

```json
{
  "station_m": 12.5,
  "elevation_m": 104.82,
  "source_id": "survey/control/12",
  "confidence": 0.98
}
```

Controls must be strictly increasing by station and must cover the full road
corridor. EarthForge does not silently extrapolate beyond measured truth.

## Corridor generator

`pipeline/roads/road_corridor.py` consumes a local-meter specification:

```json
{
  "road_id": "example_road",
  "name": "Example Road",
  "centerline": [[0, 0], [8, 0], [12, 4]],
  "elevation_profile": [
    {"station_m": 0, "elevation_m": 100},
    {"station_m": 13.656854, "elevation_m": 102.2}
  ],
  "sample_interval_m": 1.0,
  "cross_section": {
    "roadway_width_m": 6.0,
    "curb_width_left_m": 0.25,
    "curb_width_right_m": 0.25,
    "sidewalk_width_left_m": 1.5,
    "sidewalk_width_right_m": 1.5
  }
}
```

Run from the repository root:

```powershell
python .\pipeline\roads\road_corridor.py input.json output.json
```

The output records centerline elevation, grade, tangent, left normal, road
edges, curb outers, and sidewalk outers for every station. It is deliberately a
truth model, not yet a Minecraft block-placement algorithm.

## Why this comes before stairs or buildings

On a steep road, a small centerline or grade error propagates outward into the
curbs, sidewalks, stairs, walls, terraces, entrances, and building elevations.
Fixing the street after those systems exist creates cascading rework.

The corridor therefore becomes an acceptance gate: **do not advance outward
until the road geometry and elevation profile are judged correct enough for the
current quality level.**
