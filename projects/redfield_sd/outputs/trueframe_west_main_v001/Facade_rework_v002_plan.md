# West Main True-Frame v002 facade rework plan

The v001 distortion came from using **per-address OSM polygon boundaries** even though EarthForge already knew those internal address assignments conflict with the verified modern photographs.

The combined mapped west-Main frontage is still correct and stays locked. Internal facade widths now come from the accepted photo strip proportions, scaled uniformly into the 45.5625 m true frontage.

| Facade | v001 width | v002 target | Result |
|---|---:|---:|---|
| 625-627 | 15.875 m | 14.5625 m | slightly narrower |
| 623 | 14.5625 m | 6.375 m | major correction |
| 621 | 7.875 m | 11.875 m | major correction |
| 617-619 | 7.25 m | 12.75 m | major correction |

The v002 facades must be **re-authored natively**, not scaled as finished voxel images. Window bays, doors, pilasters, sign bands, canopies and marquee sections are snapped as architectural modules at the new microcell widths.

Machine-readable spec: `projects/redfield_sd/poc_001/labs/west_main_trueframe_facade_spec_v002.json`.
