> SUPERSEDED / REJECTED AS REDFIELD ARCHITECTURAL EVIDENCE. Preserved as a technical experiment. See REDFIELD_VERIFIED_REFERENCE_CORRECTION.md and the photo-based rebuilds.

# 621 native RGB hybrid experiment v002

Built against Astra Microblocks 0.6.0, reviewed at source commit 85a07a8. Installed .minecraft/mods JAR also reports 0.6.0. Sources: Astra README.md, docs/RGB-COLORS.md, HostMaterial.java, and installed materials.json.

The latest approved generated streetscape remains the design reference. This is a concept-based facade, not a measured historical reconstruction. Fort Garry remains deferred.

Changes: three native flat RGB finishes (#D6CEBA trim, #28483B painted green, #3C5B49 inset green); textured vanilla masonry and storefront cores retained; upper openings widened 16 to 20 cells; upper frames brought forward from 24/16 to 5/16 block recess; display frames also brought forward; five-step cornice profile. No glass, roof or full building body added. RGB materials are palette entries inside Astra hosts, never registered standalone block states.

52 ordinary full blocks + 12 vanilla slabs + 254 Astra hosts. Ordinary blocks/slabs represent 33.44% of occupied volume. More hosts than v001 primarily because wider windows intersect previously intact masonry blocks and painted surfaces share hosts with cores. This is an appearance experiment, not a performance improvement claim. Three finish colors avoid per-cell color noise and retain opportunities for coplanar face merging.

Checks passed: exact block-state read-back; exact reconstructed cell geometry/material comparison; one face-connected component; 1.25 x 2.5 block clear entrance; unchanged neighbor slots; no unnecessary homogeneous vanilla cube hosts; each saved material checked against installed JAR catalog or exact native RGB ID syntax. RGB cells: cream 57,831; green 25,074; inset green 2,544. In-game rendering, FPS, and rotation/mirroring of this facade have not been tested. RGB requires Astra 0.6.0 or later supporting this format.

Saved as a separate v002 schematic in .minecraft/schematics, retaining v001. Use the same Redfield registration origin as v001, rotation 0, mirror none, Replace ALL within the schematic region. Region remains X59..65, Y0..14, Z-99..-92 relative to the established origin. No world was edited and no drop ZIP was created.

Preview renders read back the saved geometry. Flat colors are approximate under simulated shading; vanilla textures and Minecraft lighting are not reproduced.

Astra update findings: 0.6.0 adds 24-bit opaque RGB with exact save/sample/copy behavior and bounded color caching. 0.5.0 adds glass and animated materials and distance visibility fixes. 0.4.0 adds schematic rotation/mirror support. Earlier face merging reduces render geometry; documentation explicitly does not guarantee FPS. Flat RGB is not emissive and does not provide arbitrary transparency.
