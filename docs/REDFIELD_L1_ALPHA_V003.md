# Redfield POC 001 — L1 Alpha v003

This is intentionally a much larger jump than the earlier EarthForge review
passes.

v003 moves from generic massing toward recognizable block-only downtown
architecture while keeping uncertainty explicit.

## What changes

- Main Street and 6th/7th Avenue widths are rebuilt from the source centerlines
  using tighter review widths.
- The 20 primary storefront footprints are assigned inferred Main Street
  addresses from parity + south-to-north order.
- Three rear structures are attached to their nearest inferred storefront
  parent.
- Buildings become hollow shells instead of solid masses.
- Main-facing facades receive:
  - storefront glazing;
  - doorway placeholders;
  - sign bands;
  - structural columns;
  - upper windows on taller profiles;
  - varied parapets.
- Four corner/landmark facades receive extra treatment:
  - 602 Leo's Good Food;
  - 603 New York Life;
  - 625/627 paired historic frontage;
  - 626 City Hall.
- City Hall gets a distinct civic facade treatment.
- Known current/historical facts influence several height profiles, but v003
  still does **not** claim surveyed heights.
- The same yellow stand-on registration point is preserved.

## Important address-matching caveat

The source OSM footprints do not contain Main Street addresses.

EarthForge's v003 mapping uses:

1. the Redfield "21 Feet of History" address sequence;
2. even addresses on the east side / odd addresses on the west side;
3. the exact south-to-north order of the 20 Main-facing source footprints;
4. known merged sites, including 604 absorbing the older 606/608 numbering;
5. a paired 625/627 interpretation of the northernmost west-side footprint.

This is marked `inferred_sequence`, not `survey_verified`.

It is strong enough for an L1-alpha architecture test, but Street View/current
photo review can still change an assignment.

## No Microblocks

v003 remains normal Minecraft blocks only.

Microblocks stay locked until the normal-block reconstruction is accepted.
