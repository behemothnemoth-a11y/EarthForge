# Lombard access + tree realism v024

The v023 landscape density passed visual review, but the user's next flyaround identified three remaining public-realm issues before architecture resumes: several planted cut-throughs appear to be vehicle accesses, the upper/Hyde-side sidewalk is visibly disconnected, and the mapped trees still read as simplified masses.

## Access evidence
The cached OSM source contains eight ways intersecting the Lombard garden/access band with service=driveway: 951848647 and 1011562121 through 1011562127. v024 uses those centerlines as topology, not inferred landscaping. OSM does not supply widths here, so the 2.75 m driveway width is an explicit nominal single-car approximation pending stronger width evidence. Driveway edits remain outside the accepted road and building footprints.

The upper pedestrian network contains mapped ways 691835290 and 691835289 with a 3.6798 m endpoint gap. v024 explicitly connects the nearest mapped endpoints inside existing supported sidewalk/ground context. This is a continuity repair, not a new destination or invented property path.

## Tree realism
Mapped tree positions do not move. Nineteen trees represented in the v023 parent are reshaped inside their existing parent height/radius envelopes. The pass replaces simple trunks/solid crowns with tapered trunks, several branch leaders, overlapping crown lobes, edge thinning and deterministic leaf variation. It makes no species claim. Unsupported tree sites remain absent.

## Validation
The generated candidate passes exact Litematica and Astra readback, access/tree scope checks, road freeze, building-footprint freeze, vanilla preservation, the eight-driveway source count, and the upper-sidewalk continuity gate. The candidate changes only declared driveway/sidewalk access corridors and existing mapped-tree morphology.

Load Projects / Lombard Stress Build / Lombard_Access_And_Tree_Realism_Astra_v024.litematic at the established origin, rotation 0, mirror none, replace ALL including air. Stop for flyaround.
