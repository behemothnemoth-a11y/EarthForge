param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

function Resolve-Repo([string]$Requested) {
    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        return (Resolve-Path $Requested).Path
    }

    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Require-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        throw "Required command not found: $Name"
    }
    return $cmd
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

$curl = Require-Command "curl.exe"
$python = Find-Python

$project = Get-Content $projectPath -Raw | ConvertFrom-Json
$bbox = $project.test_area.capture_bbox_wgs84

$south = [double]$bbox.south
$west  = [double]$bbox.west
$north = [double]$bbox.north
$east  = [double]$bbox.east

$downloads = Join-Path $RepoRoot "projects\redfield_sd\downloads"
New-Item -ItemType Directory -Force -Path $downloads | Out-Null

$rawPath = Join-Path $downloads "osm_poc_001.json"
$queryPath = Join-Path $downloads "osm_poc_001.overpassql"
$tempPath = Join-Path $downloads "osm_poc_001.tmp"

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

$ascii = New-Object System.Text.ASCIIEncoding
[System.IO.File]::WriteAllText($queryPath, $query, $ascii)

Write-Host ""
Write-Host "EarthForge - Redfield POC 001 base acquisition" -ForegroundColor Cyan
Write-Host "BBox : $south,$west,$north,$east"
Write-Host "Query: $queryPath"
Write-Host "Raw  : $rawPath"
Write-Host "HTTP : curl.exe"
Write-Host ""

$endpoints = @(
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
)

$downloaded = $false
$lastEndpoint = ""
$lastExit = -1

foreach ($endpoint in $endpoints) {
    $lastEndpoint = $endpoint

    if (Test-Path $tempPath) {
        Remove-Item $tempPath -Force
    }

    Write-Host "Requesting base geometry from $endpoint"

    $curlArgs = @(
        "--location",
        "--fail",
        "--silent",
        "--show-error",
        "--connect-timeout", "20",
        "--max-time", "150",
        "--retry", "2",
        "--retry-delay", "2",
        "--user-agent", "EarthForge/0.1 (Minecraft reconstruction; GitHub behemothnemoth-a11y/EarthForge)",
        "--header", "Accept: application/json",
        "--output", $tempPath,
        "--data-urlencode", "data@$queryPath",
        $endpoint
    )

    & $curl.Source @curlArgs
    $lastExit = $LASTEXITCODE

    if ($lastExit -eq 0 -and (Test-Path $tempPath)) {
        $length = (Get-Item $tempPath).Length
        if ($length -gt 20) {
            try {
                $probe = Get-Content $tempPath -Raw | ConvertFrom-Json
                if ($null -ne $probe.elements) {
                    Move-Item $tempPath $rawPath -Force
                    $downloaded = $true
                    Write-Host "Download succeeded." -ForegroundColor Green
                    break
                }
                else {
                    Write-Host "Response was JSON but did not contain an elements array." -ForegroundColor Yellow
                }
            }
            catch {
                Write-Host "Response was not valid Overpass JSON." -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "Response file was unexpectedly small." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "curl.exe failed with exit code $lastExit." -ForegroundColor Yellow
    }

    if (Test-Path $tempPath) {
        Remove-Item $tempPath -Force
    }
}

if (-not $downloaded) {
    throw "Unable to download valid Overpass geometry. Last endpoint: $lastEndpoint ; curl exit code: $lastExit"
}

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
