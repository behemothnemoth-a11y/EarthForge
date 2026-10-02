# Lombard neighborhood blockout v018

The user explicitly requested surrounding building and site blockout, while deferring photoreal textures. This supersedes the v017 no-houses restriction for this new candidate. Redfield remains a separate image-first exterior-evidence effort.

## Source-led scope

Use the existing 29 DataSF frontage components plus other DataSF footprints within 8m of the v017 public-corridor scope. Components are dataset polygons, not a count of distinct houses. Retain complete selected footprints except explicit public walking/road clearance clipping. Record each footprint ID, source and modeled areas, and clipping amount.

Building caps use the city's absolute median first-return elevation. The base is its minimum ground elevation. This avoids adding a median relative height to the minimum ground value on a slope. Flat caps are height envelopes, not evidence of flat roofs. Fine roof shapes, facade colors, windows, garage openings, entrances, patios and awnings are not inferred. Large height variance or vegetation contamination remains a review uncertainty; statistics alone are insufficient to establish architecture.

Surrounding ground is a shallow neutral shell from original class-2 ground returns. Sample only within a 3m neighborhood of selected footprints, excluding every mapped building and the existing public scope. The sampling distance is not a property boundary. Use 5m nearest-observation and 20m triangle-edge limits; unsupported samples remain absent and are counted. No generated fences, perimeter walls, cut-end caps or claims of surveyed patios follow from this mask.

## Preservation and checks

Every occupied v017 microcell and vanilla block is preserved, including the entire road, landscape, stairs, rails and registration. New shells avoid buffered public road/pedestrian footprints. Source conflicts and rejected writes are logged instead of silently modifying the public corridor. Exact Litematica/Astra readback is required. Run the pedestrian audit against the new artifact using v017 walking surfaces as controls to detect new overhead obstruction.

Commands:

- `python pipeline/reconstruction/generate_lombard_neighborhood_v018.py`
- `python tools/test_lombard_public_realm_v1.py --blockout`
- `python tools/render_lombard_public_realm_v1.py OUTPUT_DIRECTORY --blockout`

Next review: building proportions and heights, amount of setback space, relationship to stairs, and ground support near each footprint. Resolve image identity and roof/entrance detail one building or a small connected group at a time. Preserve original source traces and record adjustments. No photoreal texturing in this pass.

Place at the same origin as v017, rotation 0, mirror none, replace ALL including air. Stop for a flyaround before architectural detail propagation.
