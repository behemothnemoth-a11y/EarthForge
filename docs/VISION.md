# EarthForge Vision

EarthForge aims to turn a real place into a reproducible Minecraft project
rather than a one-off handcrafted map.

The core idea is to separate four concerns:

1. **Geospatial truth** — coordinates, elevation, roads, footprints, parcels.
2. **Reconstruction truth** — inferred building form, facade layout, roof form,
   visible materials, and confidence.
3. **Minecraft realization** — block-scale geometry and palette decisions.
4. **Fine detail** — microblocks for details that normal blocks cannot represent well.

EarthForge owns the project model and coordinate system. It should be possible
to replace any individual acquisition or reconstruction component without
breaking the rest of the pipeline.
