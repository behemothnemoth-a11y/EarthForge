# Redfield restart: 621 hybrid prototype v001

621 is the independent starting point for a new Redfield authoring approach.
Branch: `codex/redfield-621-hybrid-restart`.
The old 617–627 strip remains available as a reference. This prototype does not
approve a new design for the adjacent buildings.

## What this build contains

- The existing eight-block frontage at Z -99 through -92, facing east (+X).
- Host-aligned brick wall cores, green storefront structure, masonry bands,
  a plinth, shallow returns and short floor strips.
- Astra window reveals and frames, pediments, a sloping awning with connected
  braces and scalloped edging, a bracketed cornice, and parapet ornaments.
- Three upper windows, two open display bays and a walk-through central entry.
- No glass, full building extrusion, roof or interior fit-out.

Geometry is newly authored from continuous 1/16-block primitives. The generator
does not read or copy any earlier schematic. It converts every homogeneous full
cube to its normal Minecraft block, and supported exact half cubes to vanilla
slabs. Only the remaining fractional or mixed-material geometry uses Astra.

The balance is reported both by host count and by occupied volume. Ordinary
blocks and slabs account for approximately 62% of occupied volume, within this
facade study itself; the count is not inflated with a large hidden building body.

## Reference and confidence

Design reference: `projects/redfield_sd/references/generated/historic_voxel_main_street_facade.png`.
The user previously approved this generated streetscape concept. Its three-window
621 storefront is the current visual target. The older single-building image is
context only. Neither generated image is a measured photograph or authoritative
record of Redfield's historic architecture. Ornament, precise heights and facade
depth remain design choices. The existing project supplies the frontage and world
registration. This is an in-game review prototype, not a survey-accurate claim.

## Rebuild

Install Python dependencies from `pipeline/reconstruction/requirements_621_hybrid.txt`.
Run `python pipeline/reconstruction/generate_redfield_621_hybrid_restart_v001.py`.
The optional `--output-dir PATH` puts the results elsewhere. Edit room-independent
parameters and materials in `projects/redfield_sd/poc_001/labs/621_hybrid_restart_v001.json`;
the named construction operations live in the generator's `author` function.
The exported operations JSON is an additional inspectable record, not a substitute
for the editable authoring source.

The outputs include the schematic, a validation report and two previews generated
from the schematic after reading it back. The front preview identifies the block
type at the visible surface. The oblique preview shows depth. Colors are schematic
material swatches, not Minecraft textures or an in-game screenshot.

## Placement

Use the existing **Redfield** registration origin, not the Fort Garry pad.
Set placement origin to the established player-feet location, rotation 0, mirror
none, and Replace Blocks ALL, including air. The patch bounds are inclusive:

`X 59..65, Y 0..14, Z -99..-92` (7 x 15 x 8 blocks).

Air clears the old 621 facade inside those bounds. Adjacent Z slots are outside the
patch. The wider original strip may still be loaded separately; disable its
placement when reviewing this patch to avoid overlapping schematic previews.
This patch contains no registration platform and does not alter the existing one.
It does not remove any older building geometry outside its explicit bounds.

Use the existing Astra-capable Minecraft 26.2 setup. The local Astra package is
0.1.2; the build uses the existing EarthForge `astra_microblocks:test_host` and
`volume_v4` serialization contract. Do not substitute unrelated microblock mods.

## Validation and limits

Automated checks verify all block states, exact reconstructed microcell materials
and positions, a single face-connected solid component, no unnecessary homogeneous
full-cube hosts, a clear 1.25-block-wide / 2.5-block-high entry, and the 621-only
footprint. Exported blocks and block entities are reconstructed into one common
microgrid to check mixed-type joins. These checks do not measure in-game FPS,
lighting, texture mapping, collision behavior implemented by Astra, or paste behavior.
Minecraft testing is still required. The new file has not been pasted into a world.

The branch-specific drop installer applies files locally with no automatic commit
or push. It refuses to overwrite local uncommitted work when switching branches.
The next review should assess street-level proportions, the ordinary-block/micro
seams, recesses and walking through the entry before spreading the approach to 623,
625, 627 and 617–619.
