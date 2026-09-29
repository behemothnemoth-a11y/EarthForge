param(
    [Parameter(Mandatory=$true)]
    [string]$DropRoot,

    [string]$RepoRoot = "",

    [switch]$NoCommit,
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

function Require-Command([string]$Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        throw "Required command '$Name' was not found."
    }
}

function Resolve-EarthForgeRepo([string]$Requested) {
    if (-not [string]::IsNullOrWhiteSpace($Requested)) {
        return (Resolve-Path $Requested).Path
    }

    $candidates = @(
        (Join-Path $env:USERPROFILE "EarthForge"),
        (Join-Path $env:USERPROFILE "source\EarthForge"),
        (Join-Path $env:USERPROFILE "Documents\GitHub\EarthForge")
    )

    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c ".git")) {
            return (Resolve-Path $c).Path
        }
    }

    throw "Could not find the EarthForge repo automatically. Re-run with -RepoRoot `"C:\path\to\EarthForge`"."
}

Require-Command "git"

$DropRoot = (Resolve-Path $DropRoot).Path
$payload = Join-Path $DropRoot "payload"
$manifestPath = Join-Path $DropRoot "drop.json"

if (-not (Test-Path $payload)) {
    throw "Drop payload folder not found: $payload"
}
if (-not (Test-Path $manifestPath)) {
    throw "Drop manifest not found: $manifestPath"
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
$RepoRoot = Resolve-EarthForgeRepo $RepoRoot

Write-Host ""
Write-Host "EarthForge drop $($manifest.drop_id)" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"
Write-Host "Drop: $DropRoot"
Write-Host ""

Push-Location $RepoRoot
try {
    & git rev-parse --is-inside-work-tree | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Target is not a Git repository."
    }

    $branch = (& git branch --show-current)
    if ($LASTEXITCODE -ne 0) { throw "Unable to read current Git branch." }
    if (-not [string]::IsNullOrWhiteSpace($branch) -and $branch.Trim() -ne "main") {
        Write-Host "WARNING: current branch is '$($branch.Trim())', not 'main'." -ForegroundColor Yellow
    }

    $backupRoot = Join-Path $RepoRoot ".earthforge_drop_backups\$($manifest.drop_id)"
    New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

    $items = Get-ChildItem -Path $payload -Recurse -File
    foreach ($item in $items) {
        $relative = $item.FullName.Substring($payload.Length).TrimStart('\','/')
        $dest = Join-Path $RepoRoot $relative
        $destDir = Split-Path $dest -Parent

        if (-not (Test-Path $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }

        if (Test-Path $dest) {
            $backup = Join-Path $backupRoot $relative
            $backupDir = Split-Path $backup -Parent
            if (-not (Test-Path $backupDir)) {
                New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
            }
            Copy-Item $dest $backup -Force
        }

        Copy-Item $item.FullName $dest -Force
        Write-Host "  -> $relative"
    }

    Write-Host ""
    & git status --short

    if (-not $NoCommit) {
        & git add -A
        if ($LASTEXITCODE -ne 0) { throw "git add failed." }

        & git diff --cached --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "No staged changes; nothing to commit." -ForegroundColor Yellow
        } else {
            $message = [string]$manifest.commit_message
            if ([string]::IsNullOrWhiteSpace($message)) {
                $message = "Apply EarthForge drop $($manifest.drop_id)"
            }

            & git commit -m $message
            if ($LASTEXITCODE -ne 0) { throw "git commit failed." }

            if (-not $NoPush) {
                & git push origin HEAD:main
                if ($LASTEXITCODE -ne 0) {
                    throw "Commit succeeded, but git push failed. Your changes are safe locally."
                }
            }
        }
    }

    Write-Host ""
    Write-Host "Drop applied successfully." -ForegroundColor Green
} finally {
    Pop-Location
}
