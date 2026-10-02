# Lombard Acquisition and Georeferencing

This is the first executable stage of the Lombard Minecraft generation chain.

## Sources

EarthForge uses:

- DataSF / San Francisco Public Works `Streets – Active and Retired` (`3psu-pn9h`) for the official basemap centerline.
- DataSF `Elevation Contours` (`6d73-6c4f`) for five-foot contours based on the San Francisco Elevation Datum.

The acquisition code does not accept a hand-clicked replacement for the official centerline.

## 1. Inspect the requests

From the repository root:

```powershell
python .\pipeline\acquire\lombard_datasf.py --print-urls
```

This does not download anything. It shows the current source endpoints EarthForge will use.

## 2. Acquire the local source snapshot

```powershell
python .\pipeline\acquire\lombard_datasf.py
```

EarthForge:

1. requests active Lombard centerlines;
2. finds the single segment whose cross streets are Hyde and Leavenworth;
3. rejects zero or multiple exact matches;
4. orients the feature from Hyde to Leavenworth;
5. calculates a tight source bounding box;
6. expands it by the configured local margin;
7. requests only the matching elevation-contour slice;
8. writes the source snapshot plus an acquisition manifest.

Outputs:

- `projects/lombard_street_sf/acquired/centerline_wgs84.geojson`
- `projects/lombard_street_sf/acquired/contours_wgs84.geojson`
- `projects/lombard_street_sf/acquired/acquisition.json`

The acquisition manifest records the exact request URLs, selected CNN, bounds,
time, and contour count.

## 3. Lock the EarthForge local metric frame

```powershell
python .\pipeline\georeference\generate_lombard_frame.py
```

The selected Hyde endpoint becomes station zero / project origin.

The frame is:

- `+X` east
- `+Z` south
- metric
- WGS84-ellipsoid local tangent approximation
- intended only for this small local corridor, not as a planet-wide coordinate system

Outputs:

- `road_truth/locked_frame.json`
- `road_truth/centerline_local.json`
- `road_truth/contours_local.geojson`

## 4. Derive elevation controls

After source acquisition and frame generation:

```powershell
python .\pipeline\terrain\derive_profile_from_contours.py .\projects\lombard_street_sf\road_truth\centerline_local.json .\projects\lombard_street_sf\road_truth\contours_local.geojson .\projects\lombard_street_sf\road_truth\elevation_candidates.json --elevation-field elevation --elevation-unit feet --source-id datasf_elevation_contours_2026
```

Contour intersections are candidate controls. They still need endpoint
elevations and review before the elevation profile is accepted.

## Minecraft relationship

These files are upstream inputs to the Minecraft generator.

Do not fix a generated Lombard alignment error only in Minecraft. Correct the
acquisition/frame/truth layer that caused it, regenerate, then review the new
Minecraft output.
