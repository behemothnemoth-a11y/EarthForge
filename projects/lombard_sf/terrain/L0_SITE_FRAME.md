# Lombard SF — L0 Site Frame / Terrain Truth Gate

Status: **ACQUISITION / NOT YET LOCKED**

This gate exists to prevent a Redfield-style bad interpretation from propagating across the site.

## L0 must lock before switchback generation
- Hyde/Lombard and Leavenworth/Lombard intersection controls from authoritative geometry.
- Horizontal CRS transform into the EarthForge metric working frame.
- Vertical datum relationship: San Francisco Elevation Datum vs NAVD88/3DEP.
- Bare-earth grade profile across the full block.
- Road centerline plus both curb lines.
- East/west stair alignments and terrace breaklines.
- Retaining-wall and terrace-band breaklines where terrain changes are structural.

## Visual gate
Produce a top-down plan and at least two longitudinal/cross-section previews with source overlays. No full road rasterization or house propagation until the plan visually agrees with aerial + street imagery.

## Known early evidence
A third-party Hyde/Lombard point reports 37.8020045, -122.4196371 at ~85 m. Treat as provisional only. Public descriptions consistently identify eight tight turns and a steep one-way downhill segment, but published slope/length summaries are not precise enough to drive geometry.

## Next executable artifact
`terrain/l0_truth.json` containing reconciled controls, datum notes, sampled elevation profile, breaklines, and uncertainty per feature; then a generated `.litematic` containing marker + terrain/site-frame only.
