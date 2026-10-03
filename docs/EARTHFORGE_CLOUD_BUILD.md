# EarthForge cloud execution

EarthForge can run its deterministic reconstruction pipeline without Desktop Commander.

## Current cloud layers

### EarthForge Validate
Runs deterministic repository checks on `main` and `codex/**`:
- JSON validation
- stateful Litematic codec tests
- Astra microblock NBT tests
- ground-support regression tests
- architecture self-tests
- Python compilation

### EarthForge Artifact Build
An allowlisted artifact generator. It currently supports `lombard_1040_reset_v027` and:
1. runs the approved generator;
2. requires PASS validation and every individual validation gate to be true;
3. runs codec and ground-support tests;
4. packages the litematic, validation JSON, placement JSON, notes, review images where present, and SHA-256 manifest;
5. uploads the review bundle as a GitHub Actions artifact.

Generator targets must be explicitly added to `tools/ci/build_artifact.py`. Arbitrary workflow input is not executed as a path.

### EarthForge Source Truth Audit
Materializes reproducible public evidence needed by the active source gate. For 1040 it currently:
- caches the canonical NOAA LiDAR ROI;
- resolves and dimension-checks the six canonical Wikimedia Commons originals into a gitignored private cache;
- records hashes/camera metadata without committing the original images;
- performs an observational local-surface roughness classification of LiDAR;
- registers geotagged camera positions into the Lombard local frame;
- enforces a multi-view control-point measurement gate;
- uploads the non-geometry B0 evidence bundle.

A successful Actions job means the audit executed correctly. The audit result itself may still be `BLOCKED`; that is intentional when evidence is incomplete.

## Human gate

Cloud generation never replaces the Minecraft flyaround. The promotion sequence remains:

source/data gate -> deterministic generator -> exact readback -> artifact bundle -> Minecraft paste/flyaround -> user acceptance -> next gate.

## Agentic audit

`.github/workflows/earthforge-source-audit.md` is the source specification for a GitHub Agentic Workflow using the Codex engine. It is intentionally read-only: no `safe-outputs` are declared and its instructions prohibit code/geometry writes.

GitHub Agentic Workflows require the `gh aw` compiler. Before enabling it:
1. install/upgrade `gh` and `github/gh-aw`;
2. configure the repository's `OPENAI_API_KEY` secret for the Codex engine;
3. run `gh aw compile`;
4. review the generated `.lock.yml`;
5. commit both the Markdown source and generated lock file, preferably through a reviewed PR.

Do not add write safe-outputs to the EarthForge source auditor unless the user explicitly chooses an output such as a review issue/comment. Geometry or project-state mutation should remain outside the agentic auditor.
