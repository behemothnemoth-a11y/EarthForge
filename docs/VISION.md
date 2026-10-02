# EarthForge Vision

EarthForge aims to turn the real world into a reproducible, inspectable,
progressively refinable digital world rather than a collection of one-off maps
or handcrafted builds.

The long-term target is **1:1 real-world scale**. The system should be able to
start with coarse public geographic truth, then deepen selected areas with
better terrain, road geometry, architecture, materials, interiors, and
micro-detail as stronger evidence becomes available.

Minecraft is the first proving ground because it gives EarthForge a concrete
place to validate scale, placement, architecture, player-scale readability, and
the Astra Microblocks detail language. It must not become the canonical data
model.

## Separation of concerns

EarthForge separates at least five kinds of truth:

1. **Geospatial truth** — coordinates, elevation, roads, footprints, parcels,
   hydrology, vegetation context, and other mapped geometry.
2. **Reconstruction truth** — inferred or measured building form, facade layout,
   roof form, openings, structural organization, and interior layout.
3. **Material / appearance truth** — color, surface/material identity, texture
   observations, weathering cues, and confidence.
4. **Provenance / confidence truth** — where each fact came from, when it was
   observed, how it may be redistributed, and whether it is measured, observed,
   inferred, or procedural.
5. **Realization** — Minecraft blocks, Astra Microblocks, native engine
   geometry, meshes, collision, or other renderer-specific representations.

EarthForge owns the first four. Realization belongs to adapters.

## Complete buildings

When lawful source data exists, a building may progress from footprint and
massing to complete exterior and interior reconstruction using evidence such as:

- public plans or blueprints;
- floor plans;
- BIM/CAD data;
- surveys or scans;
- photographs and video;
- public records;
- measured in-game/manual corrections.

Observed and measured facts must remain distinguishable from inferred or
procedural fill. Missing data should be represented as uncertainty, not silently
converted into fake certainty.

## World generation and refinement

EarthForge should support uneven fidelity.

A large region may exist first as terrain + transport + footprints while a
single street or building reaches centimeter/microblock-scale detail. Refining
one area must not require rebuilding the entire planet.

That implies:

- deterministic project/tile inputs;
- stable feature IDs;
- explicit source manifests;
- local metric working frames;
- renderer-independent canonical geometry;
- derived outputs that can be regenerated;
- validation at every fidelity level.

## Runtime boundary

EarthForge is not the full game engine.

A future Micrology/native runtime may provide destruction, physics, streaming,
simulation, gameplay, and rendering. EarthForge should provide that runtime
with the reconstructed world, material/structural metadata when known, and
stable spatial identity without absorbing runtime systems into the reconstruction
pipeline.

See `docs/WORLD_SCALE_ARCHITECTURE.md`.
