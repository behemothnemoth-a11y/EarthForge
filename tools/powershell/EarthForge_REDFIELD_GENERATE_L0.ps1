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
    if ($null -ne $py) {
        return "py"
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        return "python"
    }

    throw "Python was not found. Install Python or make py/python available in PATH."
}

$RepoRoot = Resolve-Repo $RepoRoot
$python = Find-Python
$generator = Join-Path $RepoRoot "pipeline\georeference\generate_redfield_poc001_l0.py"

if (-not (Test-Path $generator)) {
    throw "L0 generator not found: $generator"
}

Write-Host ""
Write-Host "EarthForge - Redfield POC 001 L0 generator" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host ""

if ($python -eq "py") {
    & py $generator
}
else {
    & python $generator
}

if ($LASTEXITCODE -ne 0) {
    throw "L0 generator failed with exit code $LASTEXITCODE."
}

$generated = @(
    "projects\redfield_sd\poc_001\locked_frame.json",
    "projects\redfield_sd\poc_001\l0_geometry_local.json",
    "projects\redfield_sd\poc_001\building_match_queue.json",
    "projects\redfield_sd\poc_001\l0_block_plan.csv",
    "projects\redfield_sd\poc_001\l0_preview.svg",
    "projects\redfield_sd\buildings\poc001_buildings_selected.geojson",
    "projects\redfield_sd\roads\poc001_transport_selected.geojson",
    "projects\redfield_sd\validation\poc001_l0_generation_report.json"
)

foreach ($rel in $generated) {
    $path = Join-Path $RepoRoot $rel
    if (-not (Test-Path $path)) {
        throw "Expected generated file is missing: $rel"
    }
}

Push-Location $RepoRoot
try {
    Write-Host ""
    Write-Host "Generated files:" -ForegroundColor Green
    & git status --short -- $generated

    if (-not $NoCommit.IsPresent) {
        & git add -- $generated
        if ($LASTEXITCODE -ne 0) {
            throw "git add failed."
        }

        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "No generated changes to commit." -ForegroundColor Yellow
        }
        else {
            & git commit -m "Generate Redfield POC 001 L0 block frame"
            if ($LASTEXITCODE -ne 0) {
                throw "git commit failed."
            }

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
Write-Host "L0 generation complete." -ForegroundColor Green
