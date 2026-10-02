# EarthForge

EarthForge is a **1:1 real-world reconstruction pipeline and canonical world-data compiler**.

Its job is to turn geographic, architectural, photographic, survey, and other reference evidence into reproducible world truth **and generate the user's Minecraft reconstruction from that truth**.

Minecraft is the current primary realization target. The Minecraft build is not a separate handcrafted project that merely consults EarthForge: it is generated from EarthForge project state and should remain reproducible from the repository.

EarthForge coordinates:

- geospatial truth: coordinates, terrain, elevations, roads, parcels, footprints;
- reconstruction truth: building form, facade organization, roofs, interiors;
- material/appearance evidence and confidence;
- source provenance and licensing metadata;
- deterministic Minecraft realization through normal blocks, Litematica, Astra Microblocks, and related build artifacts;
- future adapters for Micrology/native world rendering and preview/analysis formats.

## Current proof-of-concept state

`projects/redfield_sd/` is the first city-scale test project.

Current Redfield quality level: **L1_MICRO_ALPHA**.

The repository also contains:

- Fort Garry Hotel main-floor interior alpha work;
- Lombard Street road-truth work;
- the generic Stage 3/4 road + terrain corridor core for measured grades, road edges, curbs, and sidewalks;
- Litematica and Astra Microblocks output/compatibility paths.

## Core rule

**EarthForge owns truth and generates the Minecraft build.**

Canonical geometry should remain real-world, metric, traceable, and renderer independent, while Minecraft geometry is a deterministic realization of that state.

Minecraft review is part of the loop:

```text
source evidence
    ↓
EarthForge canonical truth
    ↓
generated Minecraft realization
    ↓
in-game visual / spatial review
    ↓
correction written back into EarthForge
    ↓
regenerated Minecraft realization
```

A manual in-game correction is not considered authoritative until the corresponding correction is represented in EarthForge. The Minecraft world must not become a second source of truth that silently drifts away from the repository.

## Repository roles

- **EarthForge**: authoritative world-scale orchestration, geospatial/reconstruction truth, provenance, confidence, and generation state.
- **Build Studio**: building/image reconstruction support.
- **Astra Microblocks**: high-resolution Minecraft geometry/detail generated as part of the EarthForge realization path.
- **Minecraft exporters**: world / schematic / Litematica realization generated from EarthForge.
- **Future Micrology/native adapter**: consumes the same EarthForge truth; runtime physics/destruction remain engine concerns rather than EarthForge concerns.

See:

- `docs/VISION.md`
- `docs/WORLD_SCALE_ARCHITECTURE.md`
- `docs/PIPELINE.md`
- `docs/ROAD_TERRAIN_CORRIDOR.md`
