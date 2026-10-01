param(
    [string]$RepoRoot = "",
    [switch]$Refresh
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

function Download-File([string]$Url, [string]$OutPath) {
    if ((Test-Path $OutPath) -and (-not $Refresh.IsPresent)) {
        Write-Host "SKIP existing: $OutPath"
        return
    }
    Write-Host "GET  $Url"
    $parent = Split-Path $OutPath -Parent
    New-Item -ItemType Directory -Force -Path $parent | Out-Null

    & $script:Curl.Source @(
        "--location",
        "--fail",
        "--silent",
        "--show-error",
        "--connect-timeout", "20",
        "--max-time", "180",
        "--retry", "2",
        "--user-agent", "EarthForge/0.1 (Redfield multisource acquisition)",
        "--output", $OutPath,
        $Url
    )

    if ($LASTEXITCODE -ne 0) {
        throw "Download failed: $Url"
    }
}

$RepoRoot = Resolve-Repo $RepoRoot
$script:Curl = Require-Command "curl.exe"

$Project = Join-Path $RepoRoot "projects\redfield_sd"
$Base = Join-Path $Project "downloads\multisource_v001"
$Sddot = Join-Path $Base "sddot"
$Sanborn = Join-Path $Base "sanborn_1916"
$PrivateRoots = @(
    (Join-Path $Project "references\private\google"),
    (Join-Path $Project "references\private\mapillary"),
    (Join-Path $Project "references\private\kartaview")
)
foreach ($dir in $PrivateRoots) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

Write-Host ""
Write-Host "EarthForge - Redfield multisource acquisition v001" -ForegroundColor Cyan

Download-File "https://dotfiles.sd.gov/cadd/city/pdf/redfield.pdf" (Join-Path $Sddot "redfield.pdf")
Download-File "https://dotfiles.sd.gov/cadd/city/DGN/redfield.dgn" (Join-Path $Sddot "redfield.dgn")
Download-File "https://dotfiles.sd.gov/cadd/city/DWG/redfield.dwg" (Join-Path $Sddot "redfield.dwg")

Download-File "https://www.loc.gov/item/sanborn08259_006/?fo=json" (Join-Path $Sanborn "sanborn08259_006.json")
for ($i = 1; $i -le 7; $i++) {
    $sheet = "{0:D4}" -f $i
    $url = "https://tile.loc.gov/image-services/iiif/service:gmd:gmd418m:g4184m:g4184rm:g082591916:08259_1916-$sheet/full/pct:25/0/default.jpg"
    $out = Join-Path $Sanborn ("08259_1916-$sheet-pct25.jpg")
    Download-File $url $out
}
$items = @()
Get-ChildItem $Base -Recurse -File | Where-Object {
    $_.Name -ne "acquisition_run_v001.json"
} | Sort-Object FullName | ForEach-Object {
    $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $relative = $_.FullName.Substring($Project.Length + 1).Replace("\", "/")
    $items += [ordered]@{
        path = $relative
        bytes = $_.Length
        sha256 = $hash
    }
}

$report = [ordered]@{
    schema_version = 1
    run_date = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    status = "public_sources_acquired"
    files = $items
    deferred = @(
        "Google Street View raw imagery: manual/private only",
        "Mapillary raw imagery: manual/private only",
        "KartaView raw imagery: manual/private only",
        "SDGS LiDAR: select only tiles intersecting the 600 block",
        "NAIP: use SDGS/USDA portal after selecting a block-sized extract"
    )
}

$reportPath = Join-Path $Base "acquisition_run_v001.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8

Write-Host ""
Write-Host "Multisource acquisition complete." -ForegroundColor Green
Write-Host "Public downloads: $Base"
Write-Host "Street-level target plan: projects\redfield_sd\source_manifests\street_level_capture_targets_v001.json"
Write-Host "Raw licensed captures remain private and ignored by Git."
Write-Host ""

Push-Location $RepoRoot
try {
    & git status --short
}
finally {
    Pop-Location
}
