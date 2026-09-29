# EarthForge Quality Levels

EarthForge uses explicit quality gates so high-detail systems do not hide
geospatial or block-scale errors.

## L0 — GEO

Purpose: prove placement and scale.

Allowed:
- terrain surface
- road geometry
- sidewalks / paths
- parking / hardscape
- building footprints
- simple diagnostic footprint extrusions

Not required:
- recognizable facades
- detailed roofs
- interiors
- Build Studio reconstruction
- Astra Microblocks

## L1 — BLOCK

Purpose: produce a complete, recognizable Minecraft reconstruction using
normal Minecraft blocks only.

Allowed:
- normal full blocks
- normal slabs, stairs, walls, fences, panes, trapdoors, etc.
- source-informed palettes
- simplified but recognizable roofs
- block-scale windows, doors, signs, curbs, and facade rhythm

Forbidden for the first L1 acceptance pass:
- Astra Microblocks
- custom microblock geometry used to repair bad proportions
- detail that changes the geospatial footprint simply to look better

The Redfield POC must be reviewed in Minecraft at L1 before L2 begins.

## L2 — DETAIL

Purpose: selectively improve details that are genuinely lost at normal-block
resolution.

Possible uses:
- mullions
- cornices
- fine trim
- railings
- shaped facade details
- roof-edge details
- small signage / architectural accents

L2 is optional. A building should remain recognizable and correctly placed
when its L2 detail is removed.
