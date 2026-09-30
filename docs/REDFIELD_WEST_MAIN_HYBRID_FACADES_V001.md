> SUPERSEDED / REJECTED AS REDFIELD ARCHITECTURAL EVIDENCE. Preserved as a technical experiment. See REDFIELD_VERIFIED_REFERENCE_CORRECTION.md and the photo-based rebuilds.

# Redfield west Main Street: hybrid facades 617-627

Completed facade-only strip, using the approved generated historic_voxel_main_street_facade.png concept and the accepted 621 RGB/glass v003 geometry. Reviewed the user's September 30, 09:50 Minecraft video for the existing placement and treatment. This is an architectural interpretation of the approved concept, not a surveyed historic reconstruction.

## Composition

- 617-619: seven-block low brown storefront, restrained parapet and stone end piers, display glass, amber transoms, recessed portal and decorative lanterns.
- 621: eight-block approved v003 retained exactly, including its green awning and three windows.
- 623: fifteen-block broad green frontage, five pedimented upper windows, intermediate stone pilasters, stepped central crest, two shop entrances and four display bays.
- 625: eight-block blue-green frontage, three windows with a pediment only over the centre, corner finials and paneled storefront.
- 627: eight-block muted red frontage, three pedimented windows, central crest and corner finials.

All share layered warm stone tones, differentiated shadow courses and edge beads, textured brick, clear shop glass, light-gray upper glass and yellow/amber transoms. Shallow returns only. Entrances remain open for circulation; full door functionality/interiors are outside this facade pass. Decorative micro-lanterns do not emit Minecraft block light. The approved 621 is preserved rather than receiving additional lanterns or door changes.

## Placement

Installed file: Redfield_WestMain_617-627_HybridFacades_v001.litematic in the existing .minecraft/schematics directory. No world has been edited. Previous schematics remain available. No drop ZIP.

Use the same registration as the accepted 621 placement. Latest supplied screenshots/video show origin 513, -53, -1536. Rotation 0, mirror none, Replace ALL including air. Disable old overlapping strip/621 schematic previews. This complete strip already contains the accepted 621.

Inclusive relative bounds: X59..65, Y0..14, Z-130..-85 (7 x 15 x 46). These contain the entire old ReferenceRebuild v003 region (X59..64, Y0..12, same Z range), so Replace ALL clears the previous facade geometry there. Existing structure beyond this shallow region is not rebuilt. Registration platform stays outside the facade patch.

## Validation

1,651 occupied block positions: 200 ordinary full blocks, 21 vanilla slabs and 1,430 Astra hosts. 2,672,254 occupied Astra microcells. Vanilla full blocks and slabs represent 24.39% of occupied volume; conversion to micro hosts is limited to fractional geometry or mixed material positions. This is facade-only accounting, without added building depth to inflate the full-block ratio.

Passed exact exported block-state and reconstructed microcell/material comparison; one connected solid component; all six entrance passages clear to 2.5 blocks tall; exact cell-for-cell match with approved 621 v003; all material names verified against the installed Astra 0.6.0 JAR catalog or native RGB format; independent palette-index bounds checks; installed file SHA verified against source export. Whole-strip in-game lighting, collision and performance remain untested.

Front and individual detail previews use read-back schematic geometry. Vanilla textures are represented by swatches and transparent glass by opaque tint; these are geometry previews, not Minecraft renders. Tiny white diagonal seams in oblique previews are rasterization artifacts.

Editable generator: pipeline/reconstruction/generate_redfield_west_main_hybrid_facades_v001.py. Config: projects/redfield_sd/poc_001/labs/west_main_hybrid_facades_v001.json. It imports the preserved 621 v003 generator and shared EarthForge codecs. Source does not read or preserve old strip geometry.
