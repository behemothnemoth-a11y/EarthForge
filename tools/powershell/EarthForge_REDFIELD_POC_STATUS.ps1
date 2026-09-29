param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$projectPath = Join-Path $RepoRoot "projects\redfield_sd\project.json"
$rulesPath = Join-Path $RepoRoot "projects\redfield_sd\poc_001\block_pass_rules.json"
$registrationPath = Join-Path $RepoRoot "projects\redfield_sd\poc_001\export_registration.json"
$reportPath = Join-Path $RepoRoot "projects\redfield_sd\validation\osm_poc001_import_report.json"

$project = Get-Content $projectPath -Raw | ConvertFrom-Json
$rules = Get-Content $rulesPath -Raw | ConvertFrom-Json
$registration = Get-Content $registrationPath -Raw | ConvertFrom-Json

Write-Host ""
Write-Host "EarthForge — Redfield POC 001" -ForegroundColor Cyan
Write-Host "Status         : $($project.status)"
Write-Host "Current gate   : $($project.quality_gates.current_target)"
Write-Host "Microblocks    : $($project.quality_gates.microblocks_allowed)"
Write-Host "Test area      : $($project.test_area.label)"
Write-Host "Bounds status  : $($project.test_area.capture_bounds_status)"
Write-Host "Litematic block: $($registration.registration.marker_block)"
Write-Host ""

if (Test-Path $reportPath) {
    $report = Get-Content $reportPath -Raw | ConvertFrom-Json
    Write-Host "OSM review import present:" -ForegroundColor Green
    Write-Host "  Buildings : $($report.counts.building_features)"
    Write-Host "  Transport : $($report.counts.transport_features)"
    Write-Host "  Context   : $($report.counts.surface_context_features)"
} else {
    Write-Host "OSM review import not run yet." -ForegroundColor Yellow
    Write-Host "Run EarthForge_REDFIELD_FETCH_BASE.ps1 next."
}

Write-Host ""
