param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

function Resolve-Repo([string]$Requested) {
    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        return (Resolve-Path $Requested).Path
    }

    $candidate = Resolve-Path (Join-Path $PSScriptRoot "..\..")
    return $candidate.Path
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
$projectPath = Join-Path $RepoRoot "projects\redfield_sd\project.json"

if (-not (Test-Path $projectPath)) {
    throw "EarthForge Redfield project.json not found: $projectPath"
}

$project = Get-Content $projectPath -Raw | ConvertFrom-Json
$bbox = $project.test_area.capture_bbox_wgs84

$south = [double]$bbox.south
$west  = [double]$bbox.west
$north = [double]$bbox.north
$east  = [double]$bbox.east

$downloads = Join-Path $RepoRoot "projects\redfield_sd\downloads"
New-Item -ItemType Directory -Force -Path $downloads | Out-Null

$rawPath = Join-Path $downloads "osm_poc_001.json"

$query = @"
[out:json][timeout:90];
(
  way["building"]($south,$west,$north,$east);
  relation["building"]($south,$west,$north,$east);
  way["highway"]($south,$west,$north,$east);
  way["amenity"="parking"]($south,$west,$north,$east);
  way["landuse"]($south,$west,$north,$east);
  way["natural"]($south,$west,$north,$east);
);
out body geom;
"@

Write-Host ""
Write-Host "EarthForge - Redfield POC 001 base acquisition" -ForegroundColor Cyan
Write-Host "BBox: $south,$west,$north,$east"
Write-Host "Raw : $rawPath"
Write-Host ""

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$endpoints = @(
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
)

$downloaded = $false
$lastError = $null

foreach ($endpoint in $endpoints) {
    try {
        Write-Host "Requesting base geometry from $endpoint"

        $response = Invoke-WebRequest `
            -Uri $endpoint `
            -Method Post `
            -ContentType "application/x-www-form-urlencoded" `
            -Body @{ data = $query } `
            -UseBasicParsing `
            -TimeoutSec 120

        $utf8NoBom = New-Object System.Text.UTF8Encoding -ArgumentList $false
        [System.IO.File]::WriteAllText(
            $rawPath,
            [string]$response.Content,
            $utf8NoBom
        )

        $downloaded = $true
        break
    }
    catch {
        $lastError = $_.Exception.Message
        Write-Host "Endpoint failed; trying fallback." -ForegroundColor Yellow
        Write-Host "  $lastError" -ForegroundColor DarkYellow
    }
}

if (-not $downloaded) {
    throw "Unable to download Overpass geometry. Last error: $lastError"
}

$python = Find-Python
$normalizer = Join-Path $RepoRoot "pipeline\acquire\normalize_osm_poc001.py"

if (-not (Test-Path $normalizer)) {
    throw "Normalizer not found: $normalizer"
}

Write-Host "Normalizing review geometry..."

if ($python -eq "py") {
    & py $normalizer
}
else {
    & python $normalizer
}

if ($LASTEXITCODE -ne 0) {
    throw "OSM normalization failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "Base geometry acquired." -ForegroundColor Green
Write-Host "IMPORTANT: these GeoJSON files are REVIEW geometry, not build-ready truth."
Write-Host ""

Push-Location $RepoRoot
try {
    & git status --short
}
finally {
    Pop-Location
}
