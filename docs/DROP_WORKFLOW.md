# Large Drop Workflow

EarthForge uses file drops instead of pasting many files into chat.

A drop package contains:

```text
EarthForge_DROP_XXXX/
  drop.json
  payload/
  RUN_EARTHFORGE_DROP.ps1
```

`payload/` mirrors repository-relative paths.

The runner:

1. finds the EarthForge repo;
2. verifies Git;
3. creates safety backups for overwritten files;
4. overlays the payload;
5. shows `git status`;
6. stages files;
7. commits the drop;
8. optionally pushes to `origin main`.

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_EARTHFORGE_DROP.ps1
```

Optional explicit repo path:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_EARTHFORGE_DROP.ps1 `
  -RepoRoot "C:\path\to\EarthForge"
```

Use `-NoPush` when you want the commit locally without pushing it.
