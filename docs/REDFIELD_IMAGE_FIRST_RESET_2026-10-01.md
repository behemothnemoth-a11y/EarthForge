# Redfield Image-First Reset — 2026-10-01

## Decision

The full-block geometry candidates built after the 617-627 proof were useful experiments but are **rejected as reconstruction truth**.

Rejected review candidates:
- `full_block_alpha_v001`
- `full_block_streetscape_v002`
- `full_block_rear_v003`

Reason: the workflow propagated inferred geometry faster than the visual evidence had been reconciled. Facades, roof volumes, and building bodies stopped reading as one believable real building system. Roofs in particular were treated as LiDAR/mapped surfaces without first establishing how each facade, parapet, party wall, side return, and roof mass actually connects.

These outputs stay in Git as learning artifacts. They must not be used as source geometry for the restart.

## New gate

**Images first. No block-scale build generation until the whole block has been visually understood.**

The new sequence is:

1. Build complete current-photo atlases for both sides of Main, south-to-north.
2. Review every facade in context with its neighbors.
3. For each frontage, record:
   - visual width/rhythm relative to neighbors;
   - story count and visible mass;
   - parapet/cornice geometry;
   - upper opening count and spacing;
   - ground-floor storefront/door modules;
   - facade depth/awnings/recesses;
   - visible side-return evidence;
   - what is unknown.
4. Add street-level context imagery where the archive photo is too frontal or cropped.
5. Only after the street-facing image model is approved, reconcile aerial/LiDAR for:
   - true building depth;
   - rear additions;
   - roof plan;
   - roof elevation;
   - parapet-to-roof relationship.
6. Build one building or a very small connected group at a time and review in Minecraft before propagating the method.

## Current image atlas

Machine-readable index:
`projects/redfield_sd/source_manifests/image_first_block_atlas_v001.json`

Private review boards:
- `projects/redfield_sd/references/private/image_first_block_atlas_v001/west_current_facades_south_to_north.jpg`
- `projects/redfield_sd/references/private/image_first_block_atlas_v001/east_current_facades_south_to_north.jpg`

The image boards are intentionally private and ignored by Git.

## What remains valid

Keep:
- locked coordinate frame / registration;
- acquired OSM, SDDOT, aerial, LiDAR, Sanborn and archive evidence;
- MicroGrade as a separate evidence layer, not as permission to auto-build everything;
- Astra Microblocks 0.7.0 rendering capability;
- the accepted lesson that per-address OSM frontage boundaries can be wrong.

Do **not** keep as truth:
- full-block inferred roofs;
- full-block auto-authored facade approximations;
- inferred rear walls/openings;
- automatically propagated streetscape rhythm;
- any assumption that a LiDAR roof return explains how a roof connects to the photographed facade.

## Review discipline

The user needs to be present for the architectural interpretation gates. Automation/repo work can gather references, catalog evidence, make boards, measure sources, and prepare candidate specs. It should not turn uncertain evidence into finished building geometry without review.
