# Redfield Multisource Acquisition v001

EarthForge should not treat Google Street View as the only truth source.
The 600 block reconstruction now uses a layered evidence stack.

## Evidence roles

Use each source for the thing it is best at:

1. SDDOT CADD: road/intersection geometry and official city mapping.
2. OpenStreetMap: machine-readable building, road, alley and topology seed.
3. Aerial / orthophoto: roofs, rear additions, setbacks, parking and alleys.
4. LiDAR: grade, elevation and height cross-checks where returns are useful.
5. Google Street View: current facade depth, sidewalks, curbs, poles, signs,
   entrances, side walls and street furniture.
6. Mapillary / KartaView: alternate street-level dates and angles when covered.
7. Redfield 21 Feet of History: current archive facades plus historical change.
8. Library of Congress Sanborn maps: historic lots, party walls, footprints
   and construction/use history.

Geometry sources outrank imagery for coordinates unless a documented mismatch
shows the structured source is wrong or stale.
## Acquired on 2026-10-01

The ignored local acquisition folder now contains:

- SDDOT Redfield city map PDF.
- SDDOT Redfield DGN.
- SDDOT Redfield DWG.
- Library of Congress 1916 Redfield Sanborn item metadata.
- Seven 25-percent JPEG sheets from the 1916 Sanborn set.

Existing private evidence already includes:

- verified Redfield 21 Feet of History storefront captures;
- Esri World Imagery roof/rear mosaic and OSM overlay.

The 1916 Sanborn collection is public domain according to the Library of
Congress. The working downloads remain ignored anyway so that the repository
stays lightweight.

## Deferred large or licensed sources

Do not bulk-download these automatically:

- Google Street View imagery;
- Mapillary imagery;
- KartaView imagery;
- an entire county of LiDAR;
- an entire county NAIP package.

For street-level services, record IDs, dates, headings, URLs and confidence.
Keep screenshots/captures under ignored private reference folders.
For LiDAR/NAIP, select only the tiles or extracts that intersect the POC.
## Reproduce the public-source pull

From the EarthForge repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\powershell\EarthForge_REDFIELD_FETCH_MULTISOURCE.ps1
```

Use `-Refresh` to re-download the public files.

The script intentionally does not automate Google, Mapillary or KartaView
image downloads.

## Street-level capture pass

Use:

- `projects/redfield_sd/source_manifests/street_level_capture_targets_v001.json`
- `projects/redfield_sd/source_manifests/street_level_capture_targets_v001.csv`

For each target, collect a straight-on view plus north/south obliques where
possible. Record panorama/image/sequence ID, source date, heading, pitch,
occlusions, confidence and what the view proves.

The first capture pass covers storefronts 617-627, the opposite east curb,
Main/6th, Main/7th, the west alley and an overall block traversal.
## Next geometry gate

Before altering the accepted photo-based facades:

1. compare SDDOT CADD against the locked EarthForge frame;
2. verify curb and sidewalk placement from street-level imagery;
3. compare OSM footprint/rear geometry against aerial and LiDAR;
4. locate the 600 block on the 1916 Sanborn sheets;
5. build a discrepancy ledger;
6. change geometry only where two or more evidence layers justify it, or where
   one clearly higher-authority source resolves the conflict.

Source registry:
`projects/redfield_sd/source_manifests/redfield_multisource_acquisition_v001.json`.

## Discrepancy ledger

Cross-source conflicts are tracked in:

- `projects/redfield_sd/poc_001/multisource_discrepancy_ledger_v001.json`
- `projects/redfield_sd/poc_001/multisource_discrepancy_ledger_v001.csv`

The first entries preserve the known OSM/photo frontage conflict, provisional
roof-height uncertainty, and pending curb/rear verification instead of silently
choosing one source.
