# Redfield, South Dakota — Proof of Concept

Project ID: `redfield_sd`

Milestone: `REDFIELD_POC_001`

## Test area

The first test area is the downtown 600 block of Main Street, approximately
between 6th Avenue and 7th Avenue.

The repository stores a deliberately wider provisional capture window around
that block. Exact working bounds will be tightened after structured map
geometry and visual references are compared.

## Goal

Prove the complete EarthForge chain on one small, recognizable Redfield area
before expanding to the whole town.

## Required sequence

### Gate A — L0 GEO

Build and inspect:

- terrain / grade context;
- roads;
- sidewalks / paths;
- parking / hardscape;
- building footprints;
- simple footprint extrusions where useful.

Do not begin facade reconstruction until this aligns.

### Gate B — L1 BLOCK

Create a playable normal-block Minecraft reconstruction.

This pass uses normal Minecraft blocks only. Astra Microblocks are explicitly
disabled until the L1 version has been inspected in Minecraft.

Required L1 checks:

- road widths and intersections;
- sidewalk / parking spacing;
- lot and building placement;
- building heights;
- roof massing;
- major window / door rhythm where it affects recognition;
- player-scale feel.

### Gate C — L2 DETAIL

Only after L1 acceptance may selected structures receive Microblocks detail.

L2 is not required for the initial proof that EarthForge works.

## Litematica rule

When Litematica export begins, every revision must use the EarthForge
registration-block convention in `docs/LITEMATICA_REGISTRATION.md`.

## POC 001 acceptance

POC 001 is successful when:

1. the selected downtown area is correctly georeferenced;
2. an L0 geographic layout has been reviewed;
3. an L1 normal-block reconstruction has been loaded in Minecraft;
4. placement and scale are repeatable;
5. a subsequent Litematica revision can use the fixed registration convention
   without manual placement hunting.

Microblocks are intentionally outside the first acceptance gate.
