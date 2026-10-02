# Lombard Stairs / Landings / Retaining v004

This pass freezes the v003 road/curb geometry, terrain frame and house massing. It refines only the mapped pedestrian stair system. Each mapped stair run keeps its OSM path and step count where present, adds a flat landing at every mapped vertex/end, and gets LiDAR-backed side retaining faces around the combined stair-and-landing footprint where adjacent garden terrain sits above the constructed stair level. Existing mapped handrails remain tied to the stair lines.

The goal is to make the pedestrian routes read as constructed terrace systems rather than strips laid across the hill.

Next action: Minecraft flyaround and user notes. Do not proceed to house/facade detail until this gate is reviewed.
