# EarthForge

EarthForge is a **1:1 real-world reconstruction pipeline and canonical world-data
compiler**.

Its job is to turn geographic, architectural, photographic, survey, and other
reference evidence into reproducible world truth. Minecraft is the first
renderer and validation environment, not the architectural ceiling of the
project.

EarthForge coordinates:

- geospatial truth: coordinates, terrain, elevations, roads, parcels, footprints;
- reconstruction truth: building form, facade organization, roofs, interiors;
- material/appearance evidence and confidence;
- source provenance and licensing metadata;
- output adapters for Minecraft, Astra Microblocks, future Micrology/native
  world rendering, and preview/analysis formats.

## Current proof-of-concept state

`projects/redfield_sd/` is the first city-scale test project.

Current Redfield quality level: **L1_MICRO_ALPHA**.

The repository also contains:

- Fort Garry Hotel main-floor interior alpha work;
- the generic Stage 3/4 road + terrain corridor core for measured grades,
  road edges, curbs, and sidewalks;
- Litematica and Astra Microblocks output/compatibility paths.

The Redfield pipeline remains the proving ground for deterministic acquisition,
georeferencing, reconstruction, validation, and export. EarthForge should not
special-case itself into Redfield or Minecraft assumptions as it grows.

## Core rule

**EarthForge owns truth; output adapters own realization.**

Canonical geometry should remain real-world, metric, traceable, and renderer
independent. Minecraft block coordinates, Astra microblocks, meshes, or a
future native engine representation are generated views of that truth.

## Repository roles

- **EarthForge**: world-scale orchestration, geospatial/reconstruction truth,
  provenance, confidence, and reproducible derived data.
- **Build Studio**: building/image reconstruction support.
- **Astra Microblocks**: high-resolution geometry/detail for Minecraft and a
  visual reference for future native rendering.
- **Minecraft exporters**: world / schematic / Litematica realization.
- **Future Micrology/native adapter**: consumes EarthForge world truth; runtime
  physics/destruction remain engine concerns rather than EarthForge concerns.

See:

- `docs/VISION.md`
- `docs/WORLD_SCALE_ARCHITECTURE.md`
- `docs/PIPELINE.md`
- `docs/ROAD_TERRAIN_CORRIDOR.md`
