# Lombard Street - Hyde to Leavenworth

This EarthForge project is the steep-street / constrained-urban stress case and the generator source for the user's Minecraft Lombard build.

## Generation rule

The Minecraft Lombard reconstruction is generated from this project.

In-game review is expected and important, but a correction discovered in Minecraft must be written back into EarthForge and regenerated. Do not allow a manual world edit to become the only copy of accepted geometry.

## Locked scope

The current target is the famous crooked block of Lombard Street between Hyde Street and Leavenworth Street in San Francisco.

The build order is intentionally strict:

1. source-backed centerline and endpoint control points
2. source-backed elevation controls / grade profile
3. roadway surface and switchback geometry
4. curb geometry
5. sidewalks
6. retaining walls and edge structures
7. stairs
8. terraces / planting beds / landscaping
9. lots and building interfaces
10. bordering buildings

Do not advance outward while the road / grade spine is still changing.

## Current phase

ROAD_TRUTH_ACQUISITION

No approximate centerline coordinates, endpoint elevations, turn radii, curb heights, sidewalk widths, stairs, or building offsets are locked in this project yet.

The repository contains source manifests for the official SFCTA Lombard study and DataSF elevation contours. Exact geometry should be imported or measured from structured source data before generation.

## Truth / generation loop

official / structured source geometry
-> project-local metric frame
-> centerline stationing
-> contour / elevation intersections
-> accepted elevation controls
-> road corridor
-> generated Minecraft road
-> in-game review
-> corrections written back to EarthForge
-> regeneration
-> curbs + sidewalks
-> everything outward
