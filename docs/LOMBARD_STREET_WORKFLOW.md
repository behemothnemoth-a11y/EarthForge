# Lombard Street Hard-Mode Workflow

Lombard Street between Hyde and Leavenworth is EarthForge's first dedicated steep-road / switchback stress project.

The user's Minecraft Lombard build is generated from this EarthForge project.

## Rule zero: EarthForge remains authoritative

Minecraft is the primary realization and review environment, but it is not a separate source of truth.

If an in-game review shows that a curb, grade, turn, sidewalk, wall, stair, terrace, or building interface needs adjustment:

1. identify the underlying EarthForge input/model error;
2. update EarthForge;
3. regenerate the Minecraft output;
4. review again.

A manual Minecraft correction can be used as an experiment or measurement aid, but it is not accepted until represented in the repo.

## Rule one: road outward

Do not use stairs, retaining walls, landscaping, lot edges, or buildings to make an incorrect road look plausible.

Accepted order:

source geometry
-> centerline
-> endpoint controls
-> elevation / grade
-> roadway edges
-> generated Minecraft road review
-> curb edges
-> generated curb review
-> sidewalks
-> retaining / edge structures
-> stairs
-> terraces / landscaping
-> lot interfaces
-> buildings

A published headline grade is contextual evidence only. It does not define the switchback centerline elevation profile.

DataSF's elevation-contour dataset is a primary candidate source. Exact contour geometry and road centerline must be transformed into the same projected metric frame before profile derivation.

No default road width, curb width, or sidewalk width should be accepted for Lombard. Those dimensions must be sourced or measured for the actual block.

## Acceptance invariant

Every accepted Minecraft Lombard state must be reproducible from a committed EarthForge state. The generated build and the repository must not silently diverge.
