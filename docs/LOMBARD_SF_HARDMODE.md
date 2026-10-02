# Lombard SF Hard-Mode Reconstruction

## Project-specific rule

Lombard is a **real-world site geometry first** reconstruction.

The final reconstruction target is **1:1 real-world scale in Minecraft**. Use 1 block = 1 meter as the bulk coordinate/grid scale, then use Astra Microblocks 0.7.0 for evidence-supported sub-meter geometry rather than compressing, exaggerating, or beautifying dimensions. Horizontal and vertical proportions must remain tied to measured real-world data. Any unavoidable Minecraft quantization must be recorded as an explicit approximation, not silently absorbed.

The Redfield image-first architectural reset does **not** override the global EarthForge geospatial pipeline for this project. It applies to uncertain architectural interpretation. For Lombard, terrain, road, curb, stair, terrace, retaining-wall and footprint geometry must be established from structured real-world data before Minecraft generation.

## Source authority by feature

Use the strongest source for the feature being solved:

1. **Survey / city GIS / LiDAR / DEM**
   - horizontal control
   - elevation and grade
   - curb / ROW / street geometry where available
   - retaining and terrain breaklines where available
2. **Orthophoto / aerial**
   - switchback plan cross-check
   - roof footprints
   - rear/site context
3. **Street-level imagery**
   - curb construction
   - stair geometry
   - retaining walls
   - planter lips
   - railings
   - landscaping masses
   - garage/entry relationships
   - facade detail
4. **OSM and other volunteered mapping**
   - topology and discovery
   - never final authority where better city/survey data exists

If sources disagree, record the discrepancy. Do not silently select one.

## Mandatory order

### Gate A — acquisition truth
Before any interpreted Minecraft site geometry:
- exact Hyde/Lombard control
- exact Leavenworth/Lombard control
- source CRS and working CRS
- vertical datum reconciliation
- LiDAR/DEM coverage
- city street/ROW geometry
- sidewalk/curb datasets where available
- building footprint dataset
- orthophoto/aerial reference
- street-level reference registry

### Gate B — terrain truth
Derive:
- bare-earth surface
- longitudinal grade
- cross-slope where supported
- structural terrain breaklines
- terrace bands
- stair alignments

Produce plan/profile previews before export.

### Gate C — road truth
Derive:
- road centerline
- actual switchback path
- left/right curb lines
- road width by segment
- turn radii / curvature
- sidewalk edges
- stair paths
- retaining walls
- planter boundaries

No decorative approximation and no generic eight-turn template.

### Gate D — hardscape skeleton
Only after A-C pass:
- road surface
- curbs
- sidewalks
- retaining walls
- stairs
- planter beds
- low walls

### Gate E — landscape massing
Geometry-defining vegetation only.

### Gate F — bordering house massing
Real footprints, garage/entry relationships, roof volumes, and heights. No interiors.

### Gate G — Astra refinement
Astra Microblocks 0.7.0 may refine curved curbs, sloped transitions, stair geometry, wall caps, planter edges, railings, facade trim and other sub-block geometry. Full vanilla blocks remain preferred for bulk mass.

## Minecraft generation rule

The first real Lombard `.litematic` must be generated from reconciled site data.

Diagnostic frames may exist, but they are explicitly non-truth artifacts and must never be used as source geometry.

## Validation

Every promoted revision requires:
- permanent registration marker at schematic `(0,-1,0)`
- player-feet placement origin
- rotation 0
- mirror none
- exact Litematica block readback
- exact Astra block-entity/microcell readback when Astra is present
- source IDs and derivation metadata
- open discrepancy count
- visual gate result

## Anti-propagation rule

No uncertain interpretation may be automatically propagated across the block.

Do **not** try to finish the whole site at once.

The default working unit is the smallest meaningful slice that proves the method:
- one control/elevation slice;
- one switchback turn plus adjacent curb/stair/terrace relationships;
- one retaining-wall/planter condition;
- one bordering-house massing group.

Expand only after that slice passes source, visual, and Minecraft review.

The only permitted whole-site early pass is an explicitly labeled **rough blockout** used to test overall scale, grade, spacing, and relationships. A rough blockout is disposable and must never be promoted to geometry truth without rebuilding from verified source data.

Generate and review in verified stages:
1. terrain
2. switchback/curbs/stairs
3. hardscape
4. landscape massing
5. house massing
6. microblock refinement

A failed or unresolved gate blocks downstream geometry generation.

### Terrain volume rule

Default terrain realization should be a **shallow visible/structural shell**, not a solid mass down to an arbitrary base plane. Preserve enough depth for exposed cuts, retaining conditions, foundations, road support, stairs, and any area the player can see or enter. Omit deep buried fill that contributes nothing to the reconstruction. Full subterranean volume is opt-in only when the real site or gameplay requires it.

## Stress-build review loop

Lombard is also the EarthForge workflow stress build. Do not skip ahead simply because the next pipeline stage is technically possible.

For every meaningful reconstruction slice:
1. gather/derive only the data needed for that slice;
2. generate only that slice into a pasteable Minecraft artifact;
3. paste it into the test world using the permanent registration convention;
4. perform a player-scale flyaround / visual review;
5. collect the user's notes;
6. revise the slice until accepted;
7. write the resulting lesson/rule back into EarthForge;
8. only then proceed to the next slice.

The purpose is to train and harden the pipeline through observed Minecraft results. Confidence to generate larger areas in one pass must be earned from repeated accepted slices, not assumed.

Do not pre-build downstream geometry, even as hidden candidate output, unless the user explicitly asks for a rough whole-site blockout.

## Core-corridor isolation rule

When a whole-site rough blockout begins to obscure review of the section currently being refined, temporarily remove outer context instead of trying to repair everything at once.

For the active Lombard core-review phase, keep only:
- the complete crooked road between Hyde and Leavenworth;
- immediate curb / planter / terrace structure;
- mapped stairs, landings, handrails, footways and retaining conditions that directly serve the crooked block;
- hedges / planting masses that define those terraces;
- the shallow terrain shell required to support and visually explain those features;
- minimal endpoint tie-ins and the permanent registration pad.

Temporarily exclude:
- bordering house / building massing;
- broad Hyde and Leavenworth street extensions;
- unrelated cross-street context;
- outer terrain shelves not needed to support the core corridor;
- peripheral scenery / context that is not part of the current review gate.

Reintroduce outer context only after the crooked-road core passes its own flyaround gates. Context returns in deliberate layers and must not be allowed to hide unresolved core geometry.

## Road-first rebuild rule

The active Lombard reconstruction is reset to **road first**.

Until the road itself passes player-scale review, the active review artifact must contain only:
- the Hyde-to-Leavenworth crooked roadway;
- the permanent registration pad.

Everything else is downstream and must stay out:
- curbs;
- sidewalks;
- terrain;
- stairs and landings;
- retaining walls;
- planter edges;
- hedges / landscaping;
- buildings;
- cross-street context;
- cable-car context.

Road truth has two independent parts that must both pass:
1. **plan geometry** — centerline, width, turn flare, curve shape, endpoint tie-ins;
2. **vertical geometry** — downhill grade, smoothness, transition behavior and endpoint drop.

The road surface should be generated into **air-backed Astra hosts**. Do not use terrain-backed or stone-filled host defaults for road-only review.

Reintroduce layers only after road acceptance, one layer at a time. The intended sequence after road approval is:
1. curb / road-edge construction;
2. immediate terrain / planter terrace structure;
3. stairs / landings / retaining walls;
4. landscape massing;
5. building massing;
6. architecture and fine detail.

A downstream layer may not silently alter previously accepted road geometry.

## Review reference bundle rule

Every Minecraft flyaround gate must include a small, purpose-built reference bundle so the user can judge reconstruction fidelity against the real site while reviewing the schematic.

For each review artifact, prepare:
- **1 aerial / plan reference** showing the feature in site context;
- **1 street-level overview** showing how the feature reads at human scale;
- **1–3 close detail references** focused on the exact layer being reviewed;
- a short note saying what each image is meant to verify.

The reference bundle should be selected for the current gate only. Do not flood the review with unrelated imagery.

Examples:
- road pass → aerial alignment + street-level road view + close paver detail;
- curb pass → curb/road-edge close views + one wider hairpin view;
- stairs pass → stair runs, landings, railings, retaining interfaces;
- landscape pass → hedge/planter/terrace massing and spacing;
- house pass → frontage, garage relationships, roofline and setback views.

When possible, pair the Minecraft flyaround with the corresponding reference views side-by-side or in a compact comparison sheet.

Raw licensed imagery remains private/ignored; committed review bundles should use redistributable references or metadata/pointers where required.

## Physical expansion rule

EarthForge must expand the reconstruction **physically outward from already accepted geometry**. A source feature is not permission to build that feature early.

For Lombard:
- accepted road/curb/hardscape establishes the current built footprint;
- each new pass may expand that footprint only by the explicitly reviewed band or layer;
- stairs, paths, landscaping, buildings, and other source-known features may be generated only where the accepted ground/hardscape footprint has reached them;
- a feature that continues beyond the current footprint must stop at the review boundary and retain its source continuation for a later expansion pass;
- no floating or unsupported feature may be created simply because its complete real-world source geometry is available.

Rejected v013 is the canonical failure case: complete mapped stair ways were generated before surrounding terrain had been built far enough outward.
