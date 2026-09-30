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
    throw "Python was not found."
}

$RepoRoot = Resolve-Repo $RepoRoot
$python = Find-Python
$script = Join-Path $RepoRoot "pipeline\reconstruction\generate_redfield_621_truth_lab_v001.py"

Write-Host ""
Write-Host "EarthForge - 621 Carpets Plus Truth Lab v001" -ForegroundColor Cyan
Write-Host "This is a focused PATCH that wipes/rebuilds 621 only." -ForegroundColor Yellow
Write-Host ""

if ($python -eq "py") { & py $script } else { & python $script }
if ($LASTEXITCODE -ne 0) {
    throw "621 Truth Lab generation failed with exit code $LASTEXITCODE."
}

$generated = @(
    "projects\redfield_sd\outputs\building_labs\Redfield_621_CarpetsPlus_TruthLab_v001.litematic",
    "projects\redfield_sd\outputs\building_labs\Redfield_621_CarpetsPlus_TruthLab_v001.manifest.json",
    "projects\redfield_sd\outputs\building_labs\Redfield_621_CarpetsPlus_TruthLab_v001_facade.svg",
    "projects\redfield_sd\validation\redfield_621_truth_lab_v001_validation.json",
    "projects\redfield_sd\validation\redfield_621_truth_lab_v001_gap_report.json"
)

foreach ($rel in $generated) {
    if (-not (Test-Path (Join-Path $RepoRoot $rel))) {
        throw "Expected generated file missing: $rel"
    }
}

Push-Location $RepoRoot
try {
    & git status --short -- $generated

    if (-not $NoCommit.IsPresent) {
        & git add -- $generated
        if ($LASTEXITCODE -ne 0) { throw "git add failed." }

        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "No generated changes to commit." -ForegroundColor Yellow
        }
        else {
            & git commit -m "Generate 621 Carpets Plus Truth Lab v001"
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
Write-Host "621 Truth Lab complete." -ForegroundColor Green
