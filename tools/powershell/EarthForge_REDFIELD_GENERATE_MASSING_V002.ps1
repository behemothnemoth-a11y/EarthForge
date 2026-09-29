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
$script = Join-Path $RepoRoot "pipeline\massing\generate_redfield_poc001_massing_v002.py"

if (-not (Test-Path $script)) {
    throw "Massing generator not found: $script"
}

Write-Host ""
Write-Host "EarthForge - Redfield POC 001 Massing v002" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host ""

if ($python -eq "py") {
    & py $script
}
else {
    & python $script
}

if ($LASTEXITCODE -ne 0) {
    throw "Massing v002 generation failed with exit code $LASTEXITCODE."
}

$generated = @(
    "projects\redfield_sd\outputs\massing\Redfield_POC_001_Massing_v002.litematic",
    "projects\redfield_sd\outputs\massing\Redfield_POC_001_Massing_v002.manifest.json",
    "projects\redfield_sd\poc_001\massing_v002_building_classes.json",
    "projects\redfield_sd\validation\poc001_massing_v002_validation.json"
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
            & git commit -m "Generate Redfield POC 001 Massing v002"
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
Write-Host "Massing v002 complete." -ForegroundColor Green
