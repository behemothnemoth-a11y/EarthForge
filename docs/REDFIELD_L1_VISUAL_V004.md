# Redfield POC 001 — L1 Visual v004

v004 is EarthForge's first large exterior-fidelity pass.

It stays normal-block-only, but it stops treating every storefront as a
variation of the same procedural facade.

## Major changes from v003

- Block-state-aware Litematica palette support:
  - slabs;
  - stairs;
  - doors;
  - lanterns;
  - leaves/planters;
  - other property-bearing blocks.
- Individual facade profiles for all 20 Main-facing sites.
- Stronger current/reference-informed treatment for:
  - 602 Leo's Good Food;
  - the historic north-end 621/623/625-627 group;
  - 626 City Hall.
- Better two-story window rhythm where historical/current evidence supports a
  taller historic frontage.
- Actual door blocks instead of wooden placeholders.
- Projecting awnings and cornices using slabs/stairs.
- Streetlights and planters based on Redfield downtown streetscape references.
- Parking-stall markings on Main Street.
- Lower, simpler rear additions.
- Same registration marker and horizontal project frame as every prior export.

## Evidence status

EarthForge keeps visual confidence separate from geometry confidence.

`photo_supported` means a facade/profile was informed by a visible exterior
reference found during the v004 research pass.

`history_supported` means the height/form is informed by Redfield's site
history but not fully traced from a current frontal image.

`inferred` means the current exterior still needs Street View/current-photo
verification.

The Redfield Tourism "21 Feet of History" project states that each site is
shown with an old image and a present-day image as of 2024. EarthForge stores
the page URLs as source references but does not redistribute the raw images.

## Still deliberately excluded

- Astra Microblocks;
- full interiors;
- text-bearing signs;
- exact measured elevations;
- exact surveyed story heights.

Those can wait until the block-only exterior is worth keeping.
