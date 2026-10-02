# Lombard Stairs and Landings v013

This pass cuts the nine mapped Lombard stair systems into the accepted v012 terrace and retaining geometry instead of laying them on top. The v009 road and curb are immutable. Changes relative to v012 are allowed only inside mapped stair/landing corridors. Each mapped vertex becomes a flat landing at the local smoothed-LiDAR elevation; stair counts use OSM step_count where available and otherwise derive from local vertical drop. No railings, hedges, flowers, buildings, broad terrain, or outer street context are added yet.
