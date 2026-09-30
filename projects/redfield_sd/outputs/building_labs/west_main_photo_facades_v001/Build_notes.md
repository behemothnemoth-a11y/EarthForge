# Redfield west Main Street: photo-based facades 617-627

The completed facade strip replaces the rejected concept interpretation with the modern comparison photographs from Redfield City Tourism's 21 Feet of History archive. Simply Charming is the approved PhotoStudy v003, preserved exactly at its existing coordinates, including its updated sign and awning.

## Facades

- 617-619: three broad pale-blue boarded upper bays, four inserted small windows, air-conditioning unit, recessed brick parapet panels, altered asymmetric ground floor, weathered projecting metal marquee and exposed timber posts.
- 621 Carpets Plus: six boarded upper openings in three pairs, restrained corbelled brick cornice, purple photographed sign band, recessed side door and modern glazed shopfront. Truck-obscured glazing bases are inferred from the visible frame alignment.
- 623 Simply Charming: approved v003 copied without geometry, material or registration changes.
- 625-627: shared upper building with two arched end openings and six rectangular middle openings, opaque upper infill and one boarded opening, a lowered central parapet between raised round-tablet end pavilions, red and peach modern storefronts, photographed Dakota Tan sign and thin shared metal canopy. Street signals obscure some right-hand details; those areas use adjacent visible alignment.

No roof, upper-floor slabs, full building bodies or interiors were added. Door leaves are static facade geometry. No vehicles or street furniture were copied into the architecture. Sub-cell inscriptions, thin aerial wires and tiny signs remain below the useful resolution of this pass.

## Placement

Installed schematic: Redfield_WestMain_617-627_PhotoFacades_v001.litematic

Use the approved Simply Charming origin (50, -54, 14), rotation 0, mirror none, Replace All. This combined strip already includes Simply Charming. Disable overlapping older schematic previews. It uses the same yellow registration block at relative (0,-1,0), with player feet at (0,0,0). The build extends both ways from Simply Charming; it does not reuse the rejected concept strip's incorrect address slots or origin.

Relative bounds: X -5..1, Y -1..13, Z -19..30. World bounding box at the recorded origin: X 45..51, Y -55..-41, Z -5..44. Only this shallow bounded region is included; this is not an automatic cleanup of the old concept build elsewhere. No live Minecraft world was edited.

## Scale and confidence

The frontage is 50 blocks: 14 for 617-619, 13 for 621, 7 for accepted 623, and 16 for the shared 625-627 composition. Heights and widths are photographic estimates anchored to the approved Simply Charming scale, not surveyed measurements. Perspective, occlusion and photograph dates limit metric and current-condition confidence. The modern archive images support opening counts and visible alterations strongly. Exact colors are approximate because photographic lighting and in-game lighting differ. Small lettering remains microcell-resolution limited.

## Primary photographic sources

- [617-619, Bob's Floor Covering](https://tourism.redfield-sd.com/candnw-rr-depot/21-feet-of-history/main-street/p/item/2637/617619-main-street-bobs-floor-covering)
- [621, Carpets Plus](https://tourism.redfield-sd.com/candnw-rr-depot/21-feet-of-history/main-street/p/item/2640/621-main-street-carpets-plus)
- [623, Simply Charming](https://tourism.redfield-sd.com/candnw-rr-depot/21-feet-of-history/main-street/p/item/2642/623-main-street-simply-charming)
- [625, Hair & Company archive page](https://tourism.redfield-sd.com/candnw-rr-depot/21-feet-of-history/main-street/p/item/2643/625-main-street-hair-&-company)
- [627, Youth Center](https://tourism.redfield-sd.com/candnw-rr-depot/21-feet-of-history/main-street/p/item/2646/627-main-street-youth-center)

Use the photographed Dakota Tan appearance at 625; a newer page/business name does not establish that the photograph changed. Source URLs and local reference filenames are recorded in projects/redfield_sd/references/verified_city_archive_sources.json. Crops, palette sizes and source SHA-256 hashes are recorded in the new build configuration. No generated images are architectural evidence.

## Validation

1,262 occupied block positions: 237 ordinary facade blocks, 1,016 Astra hosts and 9 registration-pad blocks. Astra microcells: 1,411,558. Ordinary blocks supply 40.75% of occupied facade volume; this ratio excludes the pad and is a result of the geometry, not a target.

Passed exact block-state and microcell/material export read-back, independent packed-palette bounds validation, supported installed Astra 0.6.0 material IDs, a connected facade, and registration checks. A separate comparison against the previously saved v003 schematic confirms all 149 Simply Charming hosts and its ordinary blocks are unchanged. No live-game lighting, frame-rate or collision test has been performed.

Previews use exported geometry and material color swatches. Glass appears opaque in these previews; the schematic uses native stained-glass materials.

## Reproduction

Run pipeline/reconstruction/generate_redfield_west_main_photo_facades_v001.py with Python, NumPy, Pillow and SciPy. It uses the EarthForge codecs and approved Simply Charming generator. Keep the official photo files under references/private/verified_city_archive, using the manifest filenames; raw photos remain ignored by Git. The installed Astra 0.6.0 JAR is read to validate material compatibility. The generator produces the schematic, complete elevation, four facade detail views, feature inventory, validation report and configuration. The compact feature inventory replaces huge repeated per-cell operation logs.
