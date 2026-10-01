# Pipeline

Each stage should accept explicit inputs and write explicit outputs. Avoid
hidden state.

Planned stages:

1. acquire
2. georeference
3. terrain
4. roads
5. footprints
6. reconstruction
7. microblocks
8. export

The project model under `projects/<project_id>/` is the durable source of truth.

Before running or extending a project pipeline, read its project-specific workflow and toolchain manifest when present. Reuse existing codecs, validators, acquisition helpers, and integration contracts before adding parallel implementations.
