# Build Studio Integration Contract

EarthForge should provide Build Studio with a building job containing:

- building ID
- project-local footprint
- estimated / measured height evidence
- roof evidence
- facade reference manifest
- neighbor/occlusion context
- scale
- confidence fields

Build Studio should return:

- coarse Minecraft geometry or an intermediate model
- facade opening layout
- roof geometry
- visible material classification
- confidence / unresolved regions
- optional detail suggestions for Astra Microblocks

EarthForge remains responsible for placement in world coordinates.
