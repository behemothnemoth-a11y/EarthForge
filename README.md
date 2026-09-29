# EarthForge

EarthForge is a real-world-to-Minecraft reconstruction pipeline.

The project coordinates geographic source data, terrain/road reconstruction,
building reconstruction, Build Studio integration, Astra Microblocks detail,
and Minecraft export.

## First proof of concept

`projects/redfield_sd/` is the first test project.

Current stage: **REDFIELD_POC_001 / L0 GEO**

The selected test area is the downtown Main Street block between 7th Avenue
and 6th Avenue. Drop 0003 derives the exact working frame from imported
geometry, converts it into EarthForge local meters / Minecraft XZ, and produces
a diagnostic normal-block plan plus SVG preview.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\powershell\EarthForge_REDFIELD_GENERATE_L0.ps1
```

The first playable reconstruction remains normal-block-only. Astra Microblocks
stay locked until the L1 block build is reviewed in Minecraft.

## Repository roles

- **EarthForge**: world-scale orchestration and geospatial truth.
- **Build Studio**: building/image reconstruction.
- **Astra Microblocks**: fine geometry and detail after L1 acceptance.
- **Minecraft exporters**: world / schematic / Litematica output.

See `docs/PIPELINE.md`, `docs/REDFIELD_POC.md`, and
`docs/REDFIELD_L0_FRAME.md`.
