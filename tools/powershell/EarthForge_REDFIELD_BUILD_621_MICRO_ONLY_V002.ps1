param(
    [string]$RepoRoot = "",
    [switch]$NoCommit,
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$py = Get-Command py -ErrorAction SilentlyContinue
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $py -and $null -eq $python) {
    throw "Python not found."
}

$script = Join-Path $RepoRoot "pipeline\reconstruction\generate_redfield_621_micro_only_v002.py"

Write-Host ""
Write-Host "EarthForge - 621 Micro-Only v002" -ForegroundColor Cyan
Write-Host "No vanilla building shell. No glass." -ForegroundColor Yellow
Write-Host ""

if ($null -ne $py) { & py $script } else { & python $script }
if ($LASTEXITCODE -ne 0) {
    throw "621 Micro-Only v002 generation failed."
}

$generated = @(
    "projects\redfield_sd\outputs\building_labs\Redfield_621_MicroOnly_v002.litematic",
    "projects\redfield_sd\outputs\building_labs\Redfield_621_MicroOnly_v002.manifest.json",
    "projects\redfield_sd\poc_001\labs\621_micro_only_v002_hosts.json",
    "projects\redfield_sd\validation\redfield_621_micro_only_v002_validation.json"
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
        if ($LASTEXITCODE -ne 0) {
            & git commit -m "Generate 621 Micro-Only v002"
            if ($LASTEXITCODE -ne 0) { throw "git commit failed." }

            if (-not $NoPush.IsPresent) {
                & git push origin HEAD:main
                if ($LASTEXITCODE -ne 0) { throw "push failed." }
            }
        }
        else {
            Write-Host "No generated changes to commit." -ForegroundColor Yellow
        }
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "621 Micro-Only v002 complete." -ForegroundColor Green
