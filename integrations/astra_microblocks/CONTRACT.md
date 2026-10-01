# Astra Microblocks Integration Contract

Microblocks are a refinement layer, not the default representation for every
surface.

Good candidates:
- mullions
- cornices
- trim
- railings
- signage
- shaped facade elements
- roof-edge geometry
- small utility details
- curved curbs and curb returns
- sloped transitions
- planter lips / caps
- fine retaining-wall geometry
- evidence-supported stair and terrace corrections

EarthForge should send:
- parent building/object ID
- target local transform
- base Minecraft geometry
- detail specification
- allowed microblock budget / resolution

The returned detail must preserve the parent object's world transform.
