# Lombard road truth

This directory contains project-local metric truth generated from the acquired
source snapshot.

Expected generation order:

1. `locked_frame.json`
2. `centerline_local.json`
3. `contours_local.geojson`
4. `elevation_candidates.json`
5. accepted elevation profile
6. measured road corridor
7. generated Minecraft road realization

Do not place stairs, terraces, landscaping, lots, or buildings into the
authoritative pipeline before the road stages are accepted.
