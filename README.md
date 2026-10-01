# EarthForge

EarthForge is a real-world-to-Minecraft reconstruction pipeline.

The project coordinates geographic source data, terrain/road reconstruction,
building reconstruction, Build Studio integration, Astra Microblocks detail,
and Minecraft export.

## Active projects

EarthForge is now multi-project. Each project owns a durable source-of-truth folder under `projects/<project_id>/` and may add a project-specific workflow document that refines the global pipeline without silently overriding it.

Current projects include:
- `projects/redfield_sd/` — original proof of concept and reconstruction lessons.
- `projects/lombard_sf/` — hard-mode 1:1 real-world reconstruction of the crooked Lombard Street block between Hyde and Leavenworth.

For Lombard, start with `docs/LOMBARD_SF_HARDMODE.md` and `projects/lombard_sf/toolchain.json`.

Historical Redfield stage reference: **REDFIELD_POC_001 / L0 GEO**

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
