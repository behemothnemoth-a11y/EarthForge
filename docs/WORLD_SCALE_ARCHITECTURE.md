# World-Scale Architecture

This document defines architectural invariants for growing EarthForge from
project-scale proofs of concept into a 1:1 Earth reconstruction system.

## 1. Canonical scale

Canonical EarthForge geometry uses real-world metric units.

`1.0` meter in canonical data means `1.0` real-world meter. A renderer may map
that distance to blocks, voxels, microblocks, mesh units, or another runtime
representation, but the canonical model does not change scale to suit the
renderer.

## 2. Global identity, local precision

Every reconstructable feature should have stable global identity plus geometry
expressed in an appropriate local metric frame.

Keep enough information to recover the relationship:

```text
global/geodetic source position
        ↓
project or tile local metric frame
        ↓
canonical EarthForge geometry
        ↓
renderer/export transform
```

Do not use giant Minecraft/native-engine coordinates as the primary source of
truth.

For very large worlds, runtime origin shifting/rebasing and streaming are
adapter/runtime concerns. EarthForge should preserve stable world identity
across those shifts.

## 3. Horizontal and vertical reference systems are explicit

Every project/tile must record:

- source horizontal CRS;
- local working frame / anchor;
- axis convention;
- horizontal units;
- vertical units;
- elevation source;
- vertical datum when known;
- any transform or approximation used.

Ellipsoidal height, orthometric elevation, assumed local grade, and hand-tuned
Minecraft Y are not interchangeable. Unknown datum information should remain
explicitly unknown.

## 4. Progressive fidelity

EarthForge does not require uniform detail.

A practical world may contain, at the same time:

- continental/regional terrain;
- city road/parcel/footprint truth;
- block-scale architecture;
- facade-level reconstruction;
- complete selected interiors;
- micro-detail on landmarks or active build areas.

Higher fidelity replaces or enriches lower-fidelity derivations for the same
stable feature IDs. It should not create a second unrelated copy of the place.

## 5. Road-first constrained urban reconstruction

For steep, curved, terraced, or tightly constrained streets, road + grade is the
spatial spine. Adjacent curbs, sidewalks, retaining walls, stairs, landscaping,
lots, entrances, and buildings derive outward from accepted road/elevation
truth.

See `docs/ROAD_TERRAIN_CORRIDOR.md`.

## 6. Building truth can deepen independently

A building should have separable layers:

- site/footprint;
- massing;
- exterior architecture;
- materials/appearance;
- structural hints when known;
- floor/interior program;
- interior geometry;
- fixtures/detail;
- renderer-specific realization.

This allows EarthForge to ingest better plans, blueprints, scans, or imagery
later without changing the building's identity or moving the surrounding city.

## 7. Material truth is not a Minecraft palette

Canonical material/appearance data should be capable of representing far more
than the Minecraft block palette.

Where evidence allows, preserve:

- observed color values;
- material category/identity;
- finish/roughness cues;
- transparency/emission where relevant;
- weathering/variation notes;
- source and confidence.

Minecraft/Astra adapters may quantize or approximate this. A future native
renderer can use much richer color/material output without re-acquiring the
world.

## 8. Provenance survives every derived layer

Every important generated fact should be traceable to:

- one or more source records;
- an acquisition date/version;
- a transform/reconstruction step;
- confidence;
- human correction when applicable.

Generated geometry is reproducible output, not an excuse to lose its sources.

## 9. Runtime systems stay outside EarthForge

EarthForge may export metadata useful to physics or destruction, such as known
material or structural classifications.

It should not own the runtime destruction solver, gameplay, AI, simulation
clock, renderer, or streaming implementation. Those systems belong to Micrology
or another consuming engine.

The boundary is intentional: EarthForge reconstructs **what the world is**;
the runtime decides **what happens to it**.

## 10. No planet-wide rebuild requirement

The architecture must permit small deterministic updates.

Changing a curb profile, correcting one building, or adding a newly discovered
floor plan should invalidate the smallest reasonable derived region rather than
forcing a city, country, or planet rebuild.

Project/tile boundaries and cache strategy can evolve, but this incremental
rebuild invariant should remain.
