# West Main 617-627: regular-block shells and roofs v001

This extends the approved PhotoFacades v001 with hollow building shells and simple flat roof decks. All 7,009 added blocks are ordinary full vanilla blocks. The existing detailed facade, 1,016 Astra hosts, glazing, empty openings and registration pad are preserved exactly. No additional microblocks, stairs or slabs were used.

The added material counts are 2,960 bricks, 1,927 stone floor/foundation blocks, 784 gray concrete roof blocks, 1,143 light-gray concrete roof blocks, and 195 stone-brick coping blocks. Roof decks sit at relative Y=10; side and rear parapets at Y=11. These are blockout levels fitted below the facade parapets, not measured roof elevations. Interiors remain hollow, with provisional dividing walls following the accepted facade spans; there are no upper-floor slabs or interior layouts.

## Footprint basis and limits

The existing OSM address assignments contradict the approved photographic frontage proportions. This build therefore uses the combined outer outline of ways 1474301419, 1474301430, 1474301428 and 1474301456, without treating their old address labels as correct. The combined outline was visually checked against Esri World Imagery. Overhead imagery shows low-slope roofs, a short northern body, deeper middle/rear areas and a rear recess toward the southern end.

The combined mapped frontage is approximately 45.81 metres. Fitting it uniformly to the accepted 50-block frontage gives approximately 0.916 metres per block in plan. Rasterized depths are 24-50 blocks (about 22-46 metres), including the existing front masonry layer. Dimensions are mapped estimates, not a measured cadastral or architectural survey. The facade itself was previously photo-scaled, so this fit does not establish a surveyed absolute scale for every opening or individual building.

Roof surfaces use light gray and gray concrete to distinguish broad bright and dark areas visible overhead. Flat block decks simplify roof falls. Exact roof materials, drainage, rooftop equipment, roof heights and internal ownership boundaries are not established. The coarse rear walls intentionally omit unverified rear doors/windows.

Sources and attribution: OpenStreetMap contributors (ODbL), existing project GeoJSON, and Esri World Imagery / imagery contributors. The source manifest records way links, imagery tile coordinates, retrieval date and limitations. Raw aerial imagery remains private/ignored by Git. No generated reference images were used.

## Placement

Installed file: Redfield_WestMain_617-627_RegularBlockShells_Roofs_v001.litematic

Use the SAME origin (50,-54,14), rotation 0, mirror none, Replace All. This combined schematic includes the approved facades and pad; disable overlapping older previews. Relative region bounds: X -54..1, Y -1..13, Z -19..30 (56 x 15 x 50 blocks). At the recorded origin this reaches world X -4..51, Y -55..-41, Z -5..44. The expanded region now covers the building bodies behind the fronts. No live world paste was performed.

## Validation

Passed exact full export read-back, preservation of every occupied AND empty position in the original facade region, exact decoded cell/material comparison for all 1,016 existing Astra hosts, zero new hosts, vanilla full-block-only additions, full roof coverage over the new footprint, connected building structure, and hollow interior columns behind all four frontage groups. Installed file checksum was verified. Live-game lighting/collision and appearance have not been tested.

The roof-plan preview is a one-block grid. The axonometric preview simplifies existing microblock hosts as solid cubes to show volume; it does not depict the actual preserved facade detail. Use the prior facade preview or Minecraft to inspect that detail.

Generator: pipeline/massing/generate_redfield_west_main_roof_blockout_v001.py. It reads the saved accepted facade schematic and footprint GeoJSON directly; it does not need private photographs to regenerate the blockout.
