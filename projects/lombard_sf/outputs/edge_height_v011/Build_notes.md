# Lombard Local Edge Height v011

Local edge-height correction pass on approved v010. Every occupied v010 road, curb, and terrace-base cell is locked and validated unchanged. Only low planter-edge corrections are added where the smoothed LiDAR terrace surface rises 0.125-0.50 m above the standard curb. Anything above 0.50 m is deliberately left for the next retaining-wall pass instead of being misrepresented as a tall curb. No stairs, hedges/flowers, buildings, broad terrain, or outer street context are added.
