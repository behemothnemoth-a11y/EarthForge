# 1040 Building Lab v003 - architectural assemblies and benchmark review

## Why v002 did not meet the user's benchmark
The 09:40:38 video shows that thinner lines were not enough. The front still reads like a diagram on an empty box, with a broad low window grid, largely blank right body, weak construction joints and unfinished window holes. The user explicitly identifies the photo-based Redfield facades and 410 as successful quality references.

Inspected the actual comparator code and artifacts:
- 410 parcel commit 561f70b: connected wall/roof construction, white-framed inset window assemblies and source-specific roof/site controls. Used its construction/validation method, never its house shape.
- Redfield_WestMain_617-627_PhotoFacades_v001 and accepted Simply Charming PhotoStudy v003: feature-by-feature photographic reconstruction, limited appearance palettes, layered reveals/sills/headers, real glazing and read-back previews.
- Older 621 HybridRestart v003 remains rejected as Redfield architectural evidence; its generic greedy-rectangle preview helper is reusable technical code, not source geometry.

The no-glass rule was inherited from an older diagnostic experiment. It was not a user prohibition and conflicts with the later successful photo-based Redfield workflow. v003 uses native gray stained glass, confirmed in the installed Astra 0.7.0 material catalog. The pane is recessed behind the frame; the structure must leave the intended viewing aperture clear.

## Bounded changes
Reauthored the entire front assembly band, not the whole building. Individual casements, thinner muntins, continuous reveals, layered sills/headers, photo-proportioned lower spandrels, narrow timber panel divisions, raised garage panels, inset door leaves and connected side returns replace v002's diagnostic linework. Added the lower right window group visible in the 2009 oblique view. Its obscured lower edge and proposed divisions are explicitly provisional.

The normalized source footprint, registration, body envelope, roof cap, upper pergola and all geometry outside the front band remain unchanged. The main Lombard branch and world are not modified. No vegetation, side/rear window invention, roof fit, interiors or site merge is included.

## Sources and uncertainty
The dedicated July 2008 front, June 2009 oblique, August 2013 close detail and July 2019 photographs remain the source set. The 2008 body-paint sample at review coordinates (737,449)-(754,563) has median RGB 157,176,194; it is an appearance guide under that photograph's lighting, not calibrated albedo. Other restrained finish colors are appearance approximations.

The explicit v003 module sheet records pixel landmarks, proposed window dimensions and confidence. Unrectified pixels establish feature hierarchy, not survey geometry. The low garage height, main proportions, bay depths, terrace dimensions and rear/roof remain source-unresolved. No verified blueprint set or third-party schematic was acquired in this pass; discovery status is unchanged/incomplete. We must not claim v003 is a measured final reconstruction.

## Validation and preview
Exact block and per-host cell/material readback; 3,157 pane rays with zero unintended blockers; one connected opaque structural component; all 256,379 cell changes inside the front construction zone; unchanged source footprint and immutable v002 parent. Shared facade tests and codecs pass. Preview mesh uses the Redfield greedy rectangle utility with a depth buffer, avoiding painter-order artifacts that could hide foreground mullions. Preview glazing is shown as an opaque tint; Minecraft optics still need visual review.

## Placement and next gate
Load Projects / Lombard Stress Build / Building Labs / 1040 Lombard / Lombard_1040_BuildingLab_v003.litematic. Use the isolated lab placement only, rotation 0, mirror none, front facing -Z. Replacing v002 in its scratch area with ALL including air is appropriate; never paste at the full Lombard origin. Stop for a front/three-quarter Minecraft flyaround. Source acceptance and site integration remain blocked.
