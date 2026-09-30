param(
    [string]$RepoRoot = "",
    [switch]$NoCommit,
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

function Resolve-Repo([string]$Requested) {
    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        return (Resolve-Path $Requested).Path
    }
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $py) { return "py" }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) { return "python" }
    throw "Python was not found. Install Python or make py/python available in PATH."
}

function Run-Python([string]$Python, [string]$Script) {
    if ($Python -eq "py") { & py $Script } else { & python $Script }
    if ($LASTEXITCODE -ne 0) { throw "Failed: $Script" }
}

$RepoRoot = Resolve-Repo $RepoRoot
$python = Find-Python

Write-Host ""
Write-Host "EarthForge - Redfield v006 Microblocks + Interior Foundation" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host ""

Run-Python $python (Join-Path $RepoRoot "pipeline\microblocks\generate_redfield_micro_v006.py")
Run-Python $python (Join-Path $RepoRoot "pipeline\interiors\derive_redfield_interior_seeds.py")
Run-Python $python (Join-Path $RepoRoot "pipeline\integrations\export_redfield_build_studio_jobs.py")
Run-Python $python (Join-Path $RepoRoot "tools\test_astra_microblock_codec.py")

$generated = @(
    "projects\redfield_sd\outputs\l1_micro\Redfield_POC_001_L1_Micro_Alpha_v006.litematic",
    "projects\redfield_sd\outputs\l1_micro\Redfield_POC_001_L1_Micro_Alpha_v006.manifest.json",
    "projects\redfield_sd\outputs\l1_micro\Astra_EarthForge_Compatibility_v001.litematic",
    "projects\redfield_sd\poc_001\micro_v006_hosts.json",
    "projects\redfield_sd\poc_001\interior_seed_v001.json",
    "projects\redfield_sd\poc_001\build_studio_jobs_v001.json",
    "projects\redfield_sd\validation\poc001_l1_micro_alpha_v006_validation.json",
    "projects\redfield_sd\validation\astra_earthforge_compatibility_v001.json",
    "projects\redfield_sd\validation\poc001_interior_readiness_v001.json"
)

foreach ($rel in $generated) {
    if (-not (Test-Path (Join-Path $RepoRoot $rel))) {
        throw "Expected generated file missing: $rel"
    }
}

Push-Location $RepoRoot
try {
    Write-Host ""
    & git status --short -- $generated

    if (-not $NoCommit.IsPresent) {
        & git add -- $generated
        if ($LASTEXITCODE -ne 0) { throw "git add failed." }

        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "No generated changes to commit." -ForegroundColor Yellow
        }
        else {
            & git commit -m "Generate Redfield POC 001 Micro Alpha v006"
            if ($LASTEXITCODE -ne 0) { throw "git commit failed." }
            if (-not $NoPush.IsPresent) {
                & git push origin HEAD:main
                if ($LASTEXITCODE -ne 0) {
                    throw "Commit succeeded but push failed. Changes are safe locally."
                }
            }
        }
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Redfield v006 package generation complete." -ForegroundColor Green
