# REDFIELD_POC_001

Current target: **L0 GEO**

Run the L0 generator after Drop 0003:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\powershell\EarthForge_REDFIELD_GENERATE_L0.ps1
```

Generated files are written under this folder plus the existing
`buildings/`, `roads/`, and `validation/` folders.

The generator can commit and push its outputs automatically. Use `-NoCommit`
or `-NoPush` only when you intentionally want to inspect locally first.
