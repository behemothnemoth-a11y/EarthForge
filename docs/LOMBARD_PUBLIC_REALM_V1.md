# Lombard complete no-house v1 — v017

The user authorized completion of the whole crooked public corridor and the two already present 50m endpoint streets. This replaces the interim v016 stop with a single assembled-v1 flyaround. Houses remain excluded.

## Contents and evidence

- Accepted v009 crooked road/curb and v015 endpoint pavement: all 1,876,518 occupied microcells retained exactly.
- Full supporting public ground rebuilt from original 2010 class-2 LiDAR observations with bounded TIN support and the existing 1.5m smoothing. The recursive-fill defect established in v016 is not used. The 2025 DWR DEM remains independent corroboration, not an inserted height layer.
- Hyde and Leavenworth sidewalks use DataSF recorded widths (4.572m and 3.6576m), with long-side curbs, lowered crossing entries and no road-end curb caps. Intersection aprons stop within the already scoped street-and-sidewalk strip. Outgoing Lombard widths are measured from city ROW cross-sections minus recorded sidewalks; grade ties to accepted endpoint pavement and original ground slope.
- Nine OSM stair runs with supported shells, endpoint landings and paired handrails where tagged. Tagged step counts are retained; untagged counts are inferred from measured drop at a nominal 0.18m. Width 1.45m and landing depth 0.7m are explicit v1 approximations.
- Some source stair alignments intersect the accepted road. Conflicting sections move outward to 1m centerline clearance, with source/modeled traces and maximum offsets recorded per run. This is a reconstruction reconciliation, not a claim that OSM surveyed those adjusted positions. The independent audit checks decoded walking surfaces and samples the resulting centerlines for support and obstacles.
- Fifteen mapped hedge features, low planted beds, eighteen mapped trees, eight crossings and two Hyde cable-car tracks. Rail pairs use source 1.067m gauge. Markings and rails overlay the pavement by one microcell to preserve the accepted occupied cells.
- Mapped hydrant and stop-sign massing, with any short sidewalk placement adjustment or unresolved source conflict recorded. No invented house or street-light massing.

## Source provenance and confidence

Geometry inputs remain the current project's `poc_001/l0_city_layers_v001.json`, `l0_crooked_centerline_v001.json`, source truth, hardscape extraction and cached OSM map. Original ground input is `downloads/raw/lombard_poc001_lidar_roi_v001.npz`; its hash and parent artifact hash are in validation. Source authority and licenses remain in the project's existing manifests. The site frame stays local X east, Z south from EPSG:3717; 1 block = 1m, cells = 1/16m.

Public reference character was checked against Andrew Napier's Lombard Street photograph (CC BY 2.0, https://commons.wikimedia.org/wiki/File:Lombard_Street_(10064478253).jpg), the cached CC0 Crooked Section photograph, and private cached aerial imagery. No private imagery is redistributed in this v1 bundle. Plant colors, individual flower placement and crown shapes are illustrative. Tree p90 non-ground heights may include neighboring structure returns and remain candidate massing. Curbs, crossfall, ramps, signs and stair details need visual review; this is a complete assembled v1, not a survey certification.

The circled lower shapes were interpolation artifacts; see `LOMBARD_TERRAIN_REPAIR_V016.md` and its frame/source comparisons. Original-point ground and the order-invariance regression guard carry that fix forward throughout the full corridor. Building footprints reserve sites only; no houses are extruded. Temporary scope edges never become walls, caps or terrain faces.

## Reproduce and validate

Run `python pipeline/reconstruction/generate_lombard_public_realm_v1.py`, then `python tools/test_lombard_public_realm_v1.py` and `python tools/render_lombard_public_realm_v1.py [output-directory]`. Run `python -m pytest tests/test_ground_support.py -q` for ground gap-fill regressions. The renderer currently uses Windows Segoe UI; preview display sampling is 0.25m while schematic geometry remains 1/16m.

The generator validates exact Litematica blocks, exact Astra host sets, every microcell and original material, the permanent registration marker, every accepted occupied road cell, and original-ground support. The independent audit rejects missing pedestrian top cells, foliage below 2.25m over pedestrian surfaces, unsupported sampled stair centerlines and sampled head-height obstacles. Its limits are explicit: it is not an in-game collision or walking test. Render manifests record the schematic SHA-256 so previews cannot silently represent an older generation.

## Placement and next gate

Load `Projects / Lombard Stress Build / Lombard_Complete_No_Houses_V1_Astra_v017.litematic` at the same v015/v016 origin. Rotation 0, mirror none, replace ALL, including air. Preserve the yellow registration marker at local (0,-1,0). User flyaround remains required; do not automatically mark visual acceptance. Inspect lower terrain A/B/C, long stair continuity and curb clearances, endpoint sidewalk connections, canopy clearance, rail/crossing overlays and thin surfaces at scene edges.
