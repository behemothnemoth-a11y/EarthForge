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

$RepoRoot = Resolve-Repo $RepoRoot
$python = Find-Python
$exporter = Join-Path $RepoRoot "pipeline\export\export_redfield_poc001_l0_litematic.py"

if (-not (Test-Path $exporter)) {
    throw "Litematic exporter not found: $exporter"
}

Write-Host ""
Write-Host "EarthForge - Redfield POC 001 L0 Litematic export" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host ""

if ($python -eq "py") {
    & py $exporter
}
else {
    & python $exporter
}

if ($LASTEXITCODE -ne 0) {
    throw "Litematic export or validation failed with exit code $LASTEXITCODE."
}

$generated = @(
    "projects\redfield_sd\outputs\l0\Redfield_POC_001_L0_v001.litematic",
    "projects\redfield_sd\outputs\l0\Redfield_POC_001_L0_v001.manifest.json",
    "projects\redfield_sd\validation\poc001_l0_litematic_validation.json"
)

foreach ($rel in $generated) {
    if (-not (Test-Path (Join-Path $RepoRoot $rel))) {
        throw "Expected generated file is missing: $rel"
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
            & git commit -m "Generate Redfield POC 001 L0 Litematic v001"
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
Write-Host "L0 Litematic export complete." -ForegroundColor Green
