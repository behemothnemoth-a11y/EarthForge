# EarthForge Single-Building Truth Lab

The whole-block Redfield passes are useful for testing scale and pipeline
integration, but they make it difficult to tell whether a bad result is caused
by:

- source imagery;
- facade inference;
- Minecraft scale;
- ordinary-block geometry;
- microblock geometry;
- roof inference;
- address/footprint matching;
- neighboring-building context.

The Truth Lab isolates **one real building**, wipes the existing EarthForge
version of it, and rebuilds that one building from scratch.

## First target: 621 Main Street — Carpets Plus

Why 621:

- it has a standalone OSM footprint;
- Redfield's current business directory confirms Carpets Plus at 621 N Main;
- the City of Redfield 2023 downtown photograph visibly includes the historic
  storefront group containing Carpets Plus;
- the frontage is narrow enough that 1:1 Minecraft scale stresses the exact
  problem Astra Microblocks is meant to solve;
- it is not a corner building, so the first experiment can focus on facade
  proportion rather than two street elevations.

## Patch behavior

The generated Litematic is a **patch**, not the whole town.

It uses the same global EarthForge schematic origin as every Redfield revision.
The patch region tightly covers 621 and its projecting micro-detail layer.

When pasted with `Replace Blocks: ALL`, the region's implicit air wipes the
old EarthForge 621 reconstruction and replaces it with the Truth Lab version.

Neighboring buildings are outside the patch region.

## Design goal

The test prioritizes the visible Main Street facade:

- red-brick historic upper mass;
- dark green storefront base;
- narrow, tall upper windows;
- sandstone/light trim;
- stronger historic cornice;
- block-scale awning;
- microblock mullions, transoms, sills, pilasters and small cornice ornaments.

The side/rear/roof are plausible reconstructions from footprint/history rather
than photo-verified elevations.

## What this is testing

This is deliberately more detailed than the town-wide generator.

If the facade still fails to resemble the reference at this scale, the gap is
not simply "add more detail." The generated gap report identifies which
pipeline capabilities we need next.
