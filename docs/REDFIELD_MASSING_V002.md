# Redfield POC 001 — Massing v002

This is the first three-dimensional EarthForge test for Redfield.

It is intentionally **not** the first detailed building pass.

## Goals

1. Preserve the exact v001 project frame and registration reference.
2. Narrow Main Street from the overly broad L0 diagnostic corridor seen in the
   first Minecraft review.
3. Turn selected building footprints into simple normal-block volumes.
4. Keep secondary/rear structures visibly subordinate.
5. Test 1:1-ish player scale before facade reconstruction.

## Road treatment

For v001, Main Street filled almost the full distance between sidewalk
centerlines. In Minecraft that read too wide.

v002 uses:

- Main Street paved half-width: **10 blocks / meters**;
- sidewalk source lines expanded toward the curb, with building footprints
  overwriting any sidewalk overlap;
- the existing provisional 6th/7th Avenue diagnostic geometry;
- the existing alley geometry.

The 20-meter paved Main Street width is a **review value**, not a claimed
survey measurement. It exists so we can inspect the street in Minecraft and
adjust again if needed.

## Building massing

Buildings are classified geometrically:

- `primary_frontage`: footprint reaches the Main Street frontage zone;
- `secondary_rear`: footprint sits substantially behind the Main Street
  frontage.

Initial normal-block heights:

- primary frontage: 5 wall blocks + 1 roof block;
- secondary/rear: 3 wall blocks + 1 roof block.

This is a scale test only. Individual story counts are not claimed yet.

## Materials

Diagnostic materials remain intentionally obvious:

- Main Street: black concrete
- 6th/7th Avenue: gray concrete
- sidewalks: smooth stone
- alleys: polished andesite
- crossings: white concrete
- primary massing: bricks
- secondary massing: stone bricks
- roofs: polished deepslate
- geographic anchor: red concrete
- revision registration marker: yellow concrete

## Registration

The yellow stand-on registration marker remains at the same project reference
as v001.

When loading v002:

1. stand on the yellow marker from v001;
2. set the v002 schematic placement origin to your player-feet block;
3. rotation = 0;
4. mirror = none;
5. paste with replacement enabled so the taller v002 region can replace the
   old flat diagnostic layer cleanly.
