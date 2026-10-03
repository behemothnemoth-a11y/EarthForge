# 1040 Lombard source reset v027

## Decision

The v020, v025 and v026 architectural interpretations are rejected as building geometry. The user explicitly requested that 1040 be removed completely and restarted from references and data in the same real-world-first manner used to harden the Lombard public-realm pipeline.

The next accepted state is **no 1040 building geometry**. The v027 reset generator starts from the accepted v024 public-realm/access context and removes the old neutral envelope plus the v020 blue-facade materials only inside the source-identified 1040 footprint. It does **not** generate replacement ground, slab, foundation, facade, roof or massing. Any cleared footprint/void in the reset artifact is workflow state, not evidence of real terrain.

## What remains valid

- DataSF building ID `201006.0032105`, MBLR `SF0068010`.
- OSM way `262548811` and address match 1040 Lombard Street.
- Source footprint area about 177.21 m² and the registered local coordinate frame.
- The source-mapped driveway/access relationship in v024.
- LiDAR/GIS vertical observations as raw controls only, with vegetation-contamination caution.
- Public-realm geometry already accepted outside the building.

The street-facing facade width, storey subdivisions, bay depths, garage dimensions, terrace depth and pergola geometry from v025/v026 are **not retained as truth** unless independently re-derived.

## Building-specific mandatory order

1040 now follows a building analogue of the Lombard hard-mode gates:

1. **B0 — acquisition/identity truth:** footprint, parcel/address match, raw LiDAR/DEM coverage, full reference registry, camera metadata, historic/current cross-checks.
2. **B1 — site-interface truth:** driveway/garage threshold, visible retaining/ground interfaces, source-supported base elevations. No facade styling.
3. **B2 — outer-volume controls:** total visible envelope, setbacks, roof/terrace zones, and projection depth bounds from multi-view evidence. No windows/timber yet.
4. **B3 — facade measurement:** solve opening bands, bay widths, garage opening, entry, floor lines and projection depths from registered images; every dimension carries provenance/confidence.
5. **B4 — Minecraft massing gate:** only the verified shell/major projections; flyaround.
6. **B5 — openings and structural trim:** windows, garage/door openings and major timber members; flyaround.
7. **B6 — fine Astra detail/material/vegetation:** decorative rails, small timber, vines/bougainvillea and other appearance detail.

A later gate may use prior observations, but it may not inherit rejected v025/v026 geometry.

## Reference/data bundle

The committed source manifest is `projects/lombard_sf/source_manifests/1040_lombard_source_truth_v027.json`. It records the DataSF/OSM identifiers and a dedicated reference sequence from 2008, 2009, two 2013 views, 2014 and 2019. Original-resolution licensed imagery remains private/ignored per source policy.

The image sequence is deliberately multi-year: stable structural features that persist across years can be distinguished from vines, tree occlusion and seasonal planting. Camera coordinates are recorded when Commons metadata provides them. Photo perspective supports correspondence and depth solving; it does not directly supply dimensions.

## Known discrepancy

The existing OSM-derived building record labels the type as apartments, while secondary public/county-record aggregators report a single-family/one-dwelling property, three stories, about 3,680 sq ft and year built 1911. This is logged rather than silently resolved. It is not used to force exterior geometry.

## Next gate

Do **not** generate another 1040 house yet. First produce the B0 source-truth report with:

- registered source footprint and street-facing edge;
- camera/reference map;
- LiDAR/first-return classification around the footprint;
- driveway/garage-threshold evidence;
- common facade control-point table across references;
- plan/elevation/depth diagrams with known, derived and unresolved dimensions visibly separated.

Only after that package is reviewed does B1 site-interface geometry begin.
