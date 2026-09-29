# EarthForge

EarthForge is a real-world-to-Minecraft reconstruction pipeline.

The project coordinates geographic source data, terrain/road reconstruction,
building reconstruction, Build Studio integration, Astra Microblocks detail,
and Minecraft export.

## First proof of concept

`projects/redfield_sd/` is the first test project.

The first milestone is intentionally small:

1. choose one recognizable Redfield test area,
2. anchor real-world coordinates to Minecraft coordinates,
3. reconstruct terrain, roads, lots, and footprints,
4. reconstruct a small set of buildings from reference imagery,
5. add microblock detail only where normal blocks are insufficient,
6. export a playable Minecraft section,
7. compare the result against the real location and iterate.

## Repository roles

- **EarthForge**: world-scale orchestration and geospatial truth.
- **Build Studio**: building/image reconstruction.
- **Astra Microblocks**: fine geometry and detail.
- **Minecraft exporters**: world / schematic / Litematica output.

See `docs/PIPELINE.md` and `docs/REDFIELD_POC.md`.
