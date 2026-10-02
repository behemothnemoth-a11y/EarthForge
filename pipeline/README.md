# Pipeline

Each stage should accept explicit inputs and write explicit outputs. Avoid
hidden state.

Stages:

1. acquire
2. georeference
3. terrain
4. roads
5. footprints
6. reconstruction
7. microblocks
8. export

The project model under `projects/<project_id>/` is the durable source of truth.

## Terrain + road foundation

The first generic Stage 3/4 core now lives in:

- `pipeline/terrain/elevation_profile.py`
- `pipeline/roads/road_corridor.py`

It creates a measured project-local station/elevation spine plus road, curb,
and sidewalk offsets while preserving every source centerline vertex. This is
the foundation for steep and curved road reconstruction before adjacent
stairs, retaining walls, landscaping, lots, or buildings are placed.

See `docs/ROAD_TERRAIN_CORRIDOR.md`.
