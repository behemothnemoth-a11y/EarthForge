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
