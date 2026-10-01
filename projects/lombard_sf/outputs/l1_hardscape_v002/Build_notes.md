# Lombard POC 001 ? L1 Terrain + Hardscape v002

This is the **user review gate** before any houses are generated.

Locked source truth carried forward:
- Hyde/Lombard NAVD88 vertical zero
- Leavenworth endpoint drop: **32.85 m**
- OSM crooked centerline: **197.39 m / 157 nodes / 8 detected hairpin extrema**
- DataSF ROW envelope and sidewalk-width context
- NOAA/USGS 2010 class-2 LiDAR 0.5 m terrain grid

v002 adds only evidence-backed hardscape refinement:
- mapped stair handrails where OSM says `handrail=yes`
- mapped ladder/zebra crossing surfaces
- low retaining/planter wall faces only where LiDAR shows adjacent terrain above the road edge
- v001 brick road, curbs, stairs, footways, hedges, Hyde cable-car context and terrain

It still contains **no houses, roofs or interiors**. Building source truth is prepared separately but blocked behind this review gate.

Validation: exact Litematica block map, exact Astra cell/material readback and permanent registration marker all pass.
