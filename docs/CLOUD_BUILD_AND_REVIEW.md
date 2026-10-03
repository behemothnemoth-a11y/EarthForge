# EarthForge cloud build and review pipeline

EarthForge must not depend on a single developer workstation or remote-control session to generate and validate reconstruction artifacts.

## Roles

### GitHub
GitHub is the control plane and source of record.

It owns:
- repository state and source manifests;
- deterministic validation;
- allowlisted artifact generation;
- exact Litematica/Astra readback checks;
- regression tests;
- review-bundle packaging;
- downloadable Actions artifacts;
- agentic source-audit reports.

### DigitalOcean
DigitalOcean is optional heavy compute.

Use it when a job is too large or too slow for a normal GitHub-hosted runner, for example:
- large LiDAR classification or photogrammetry;
- multi-view camera solving;
- batch reference rendering;
- long regression/stress workloads.

DigitalOcean must not become a second source of truth. Inputs come from a repository commit and outputs must return to GitHub as review artifacts, reports, or deliberate commits.

### Local Minecraft machine
The local Windows machine remains the player-scale review surface.

It is needed for:
- loading the approved .litematic;
- Minecraft flyaround review;
- captures and user notes.

Local review does not replace cloud validation, and cloud validation does not replace the Minecraft flyaround gate.

## Deterministic artifact builds

Workflow: `.github/workflows/earthforge-artifact-build.yml`

The workflow accepts only targets declared in `tools/ci/build_artifact.py`. It does not accept arbitrary Python paths or shell commands.

Current target:
- `lombard_1040_reset_v027`

For an allowed target the workflow:

1. checks out the exact commit;
2. installs declared reconstruction dependencies;
3. compiles the CI wrapper and target generator;
4. runs the generator;
5. requires validation status PASS;
6. requires every named validation gate to be true;
7. runs core Litematic/Astra codec tests;
8. runs the ground-support regression suite;
9. packages the review files;
10. writes SHA-256 hashes for every packaged file;
11. uploads the bundle as a GitHub Actions artifact.

The bundle is transport/review output. It is not automatically accepted geometry.

## Review bundle

Each artifact bundle contains, when available:
- generated `.litematic`;
- validation JSON;
- placement JSON;
- build notes;
- purpose-built reference sheets/images;
- `SHA256_MANIFEST.json`.

GitHub artifacts are retained for 30 days by the current workflow.

## Promotion rule

A successful cloud build means only **technically valid candidate**.

Promotion still requires the project-specific review gate. For Lombard this normally includes:
- source/provenance gate;
- exact readback and regression gates;
- Minecraft placement at the permanent registration origin;
- user flyaround;
- explicit acceptance notes.

No workflow may convert PASS into visual acceptance automatically.

## Adding another generator

Do not expose arbitrary generator paths as workflow input.

Instead:
1. add one entry to `TARGETS` in `tools/ci/build_artifact.py`;
2. declare its exact generator, output directory, expected artifact names and required status;
3. add a workflow input option;
4. add only the necessary push-path triggers;
5. run the cloud build;
6. inspect logs and the uploaded bundle;
7. keep the target blocked from promotion until its human gate passes.

## DigitalOcean escalation

If GitHub-hosted runners become insufficient, move only the compute-heavy stage to a controlled DigitalOcean runner/workspace. Keep the same allowlist, immutable commit input, validation contract and artifact manifest.

Do not make a permanent cloud server a hidden mutable working tree.

## 1040 Lombard current state

1040 is intentionally at source-truth reset v027.

The cloud artifact builder may generate the **reset artifact only**. It must not generate a replacement house until the B0 source-truth package is reviewed and the project state authorizes the next building gate.
