# Lombard road joins and paving v021

Both user-circled red shapes are reconstruction artifacts. The v009 road polygon used round segment caps, and v015 protected those cells while adding the cross streets. The inherited red cap and curb survived inside Hyde and Leavenworth. They are not vegetation or LiDAR ground anomalies.

City pavement widths and centerlines define the join limits; the registered aerial and Andrew Napier lower-street reference corroborate continuous asphalt. V021 rebuilds only those overlaps, obsolete cap curbs, a maximum 2m approach blend, and the existing Hyde rail/slot columns. Heights come from the accepted cross-street asphalt, not the old filled terrain grid. Outside those scopes, occupied road/curb geometry stays unchanged. Buildings, pedestrian structures, landscape, registration and review boundaries are preserved.

The red paving now uses a CC0 photograph-sampled palette, narrower area-sampled joints and matching existing slab/riser colors. Geometry outside the road joins is unchanged. Grade steps still shade in Minecraft; this is a color/material step toward realism, not calibrated albedo or a photoreal resource pack. Twenty-by-ten-centimetre paver proportions and mortar color remain provisional.

## Blue building

The v020 blue facade is rejected as an interpretation: its broad glass grid misses discrete framed openings, solid blue panels, bay projections and upper enclosure. It is unchanged in this road-priority pass and must not be copied as reference truth. Rebuild separately from the available photographs before claiming architectural completion.

## Mandatory gates for future passes

- Any road terminating at a cross street must declare the pavement overlap and transition policy. A round centerline cap is not source evidence for a real island.
- Detect red road cells within accepted Hyde/Leavenworth pavement footprints. Require zero undeclared overlap after repair.
- Check the edited surface and its unedited neighbors, solid three-cell support and embedded rail/paint overlays. The independent v021 test checks 148,605 neighbors, including 10,641 across edit boundaries; maximum step is 0.125m.
- Preserve occupancy outside explicit source-justified exceptions and exact Litematica/Astra readback. No review cutoff walls.
- Joint coverage below a microcell must be area-sampled. Do not expand a 6mm joint to a solid dark 62.5mm stripe; also inspect exposed grade risers.
- Run generator, tools/test_lombard_road_finish_v021.py, tools/test_lombard_public_realm_v1.py --road-finish and tools/render_lombard_road_finish_v021.py. Inspect renders before installing.

## Review placement

Same established Lombard placement, rotation 0, mirror none, replace ALL including air. Stop for user flyaround. Review both joins, track crossing, lower road exit and paver appearance. Not auto-pasted into the world.
