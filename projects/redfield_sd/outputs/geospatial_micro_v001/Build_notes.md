# Redfield Main Street MicroGrade v001

This is the first EarthForge geospatial surface pass that deliberately uses Astra
Microblocks beyond facade detailing.

Astra 0.7.0 is installed locally. Its chunk-baked renderer removes the old
per-host render bottleneck, so this pass uses 4,266 hosts where sub-block
elevation materially improves source fidelity rather than enforcing the old
host-count cap.

## Scope

- Main Street between the locked Main/7th and Main/6th controls.
- Current EarthForge road-width policy: x -9..9.
- One-block curb bands at x -10 and +10.
- Sidewalk bands out to the mapped storefront edges.
- 1/16-block longitudinal grade from 2012 SDGS LiDAR.
- Subtle one-microcell road crown.
- Two-microcell curb/sidewalk raise.
- Original locked registration marker preserved.

Buildings and accepted photo facades are intentionally not included or moved.

## LiDAR result

The smoothed road profile rises about 0.79 m from Main/7th to Main/6th. The
full profile spans 1.00 m because the street dips slightly south of the middle
of the block before climbing north.

The micrograde changes by at most one microcell between adjacent one-metre
rows, so the result is a continuous shallow grade rather than Minecraft
whole-block stairs.

## Validation

- exact Litematica block-map readback: PASS
- exact Astra cell/material readback: PASS
- Astra hosts: 4,266
- occupied microcells: 8,553,472
- registration marker: PASS
- accepted photo facades changed: NO
- live Minecraft appearance/performance: not yet tested

Horizontal curb/sidewalk placement remains provisional until direct current
Google/Mapillary frontage evidence is captured.
