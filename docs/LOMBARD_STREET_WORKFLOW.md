# Lombard Street Hard-Mode Workflow

Lombard Street between Hyde and Leavenworth is EarthForge's first dedicated steep-road / switchback stress project.

## Rule zero: road outward

Do not use stairs, retaining walls, landscaping, lot edges, or buildings to make an incorrect road look plausible.

Accepted order:

source geometry
-> centerline
-> endpoint controls
-> elevation / grade
-> roadway edges
-> curb edges
-> sidewalks
-> retaining / edge structures
-> stairs
-> terraces / landscaping
-> lot interfaces
-> buildings

A published headline grade is contextual evidence only. It does not define the switchback centerline elevation profile.

DataSF's elevation-contour dataset is a primary candidate source. Exact contour geometry and road centerline must be transformed into the same projected metric frame before profile derivation.

No default road width, curb width, or sidewalk width should be accepted for Lombard. Those dimensions must be sourced or measured for the actual block.
