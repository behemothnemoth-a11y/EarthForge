param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $candidate = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    $RepoRoot = $candidate.Path
}

Write-Host "EarthForge check" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"

$required = @(
    "README.md",
    "docs\PIPELINE.md",
    "projects\redfield_sd\project.json",
    "schemas\project.schema.json"
)

$missing = @()
foreach ($rel in $required) {
    $p = Join-Path $RepoRoot $rel
    if (-not (Test-Path $p)) {
        $missing += $rel
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing required files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" }
    exit 1
}

$python = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $python) {
    & py (Join-Path $RepoRoot "tools\validate_json.py")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        & python (Join-Path $RepoRoot "tools\validate_json.py")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        Write-Host "Python not found; skipped JSON validation." -ForegroundColor Yellow
    }
}

Push-Location $RepoRoot
try {
    & git status --short
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

Write-Host "EarthForge structure looks good." -ForegroundColor Green
