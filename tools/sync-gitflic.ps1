# UNO GitFlic non-destructive synchronization, Windows PowerShell 5.1+
# Does not force-push, delete refs, use GitHub Actions, or store credentials.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GitFlicUrl,
    [string]$RepoPath = ".",
    [switch]$Execute
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([string[]]$GitArgs)
    $result = @(& git -C $script:Root @GitArgs 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw ("git " + ($GitArgs -join " ") + " failed: " + ($result -join "`n"))
    }
    return $result
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git executable was not found in PATH."
}
$script:Root = (Resolve-Path -LiteralPath $RepoPath).Path
$top = (Invoke-Git -GitArgs @("rev-parse", "--show-toplevel") | Select-Object -First 1).Trim()
$script:Root = $top
$origin = (Invoke-Git -GitArgs @("remote", "get-url", "origin") | Select-Object -First 1).Trim()
if ($origin -notmatch "github\.com[:/]ivankondral1998-dot/UNO-android-AI-Agent(\.git)?$") {
    throw "Unexpected origin URL. Refusing to mirror a different repository: $origin"
}
if ($GitFlicUrl -notmatch "^(https://gitflic\.ru/|git@gitflic\.ru:)") {
    throw "GitFlicUrl must be a repository HTTPS or SSH URL at gitflic.ru."
}
$existingNames = @(Invoke-Git -GitArgs @("remote"))
$hasRemote = $existingNames -contains "gitflic"
if ($hasRemote) {
    $existingUrl = (Invoke-Git -GitArgs @("remote", "get-url", "gitflic") | Select-Object -First 1).Trim()
    if ($existingUrl -ne $GitFlicUrl) {
        throw "gitflic remote exists with another URL. Refusing to overwrite: $existingUrl"
    }
}

Write-Host "UNO origin: $origin"
Write-Host "GitFlic:    $GitFlicUrl"
if (-not $Execute) {
    Write-Host "DRY RUN: no remotes or repository refs were changed."
    Write-Host "After reviewing the destination, re-run with -Execute."
    exit 0
}
$status = @(Invoke-Git -GitArgs @("status", "--porcelain"))
if ($status.Count -ne 0) {
    throw "Working tree is not clean. Commit/stash local changes before synchronization."
}
if (-not $hasRemote) {
    Invoke-Git -GitArgs @("remote", "add", "gitflic", $GitFlicUrl) | Out-Null
}

Invoke-Git -GitArgs @("fetch", "origin", "--tags") | Out-Null
$heads = @(Invoke-Git -GitArgs @("ls-remote", "--heads", "origin"))
$branches = @()
foreach ($line in $heads) {
    if ($line -notmatch "^([0-9a-f]{40})\s+refs/heads/(.+)$") {
        throw "Unexpected origin branch line: $line"
    }
    $branches += [PSCustomObject]@{ Sha = $Matches[1]; Name = $Matches[2] }
}
if ($branches.Count -lt 1) { throw "Origin has no branches; nothing to mirror." }
foreach ($b in $branches) {
    # Use the fetched remote-tracking ref; push without a force marker.
    $localRef = "refs/remotes/origin/" + $b.Name
    $actual = (Invoke-Git -GitArgs @("rev-parse", $localRef) | Select-Object -First 1).Trim()
    if ($actual -ne $b.Sha) { throw "Local tracking ref mismatch for $($b.Name)" }
    $refspec = $localRef + ":refs/heads/" + $b.Name
    Invoke-Git -GitArgs @("push", "gitflic", $refspec) | Out-Host
}
Invoke-Git -GitArgs @("push", "gitflic", "--tags") | Out-Host

function Read-RemoteRefs {
    param([string]$remote)
    $out = @{}
    $lines = @(Invoke-Git -GitArgs @("ls-remote", "--heads", "--tags", $remote))
    foreach ($line in $lines) {
        if ($line -notmatch "^([0-9a-f]{40})\s+(refs/(heads|tags)/.+)$") {
            throw "Unexpected ref from $remote : $line"
        }
        $ref = $Matches[2]
        $out[$ref] = $Matches[1]
    }
    return ,$out
}
$source = Read-RemoteRefs -remote "origin"
$target = Read-RemoteRefs -remote "gitflic"
$missing = @($source.Keys | Where-Object { -not $target.ContainsKey($_) -or $source[$_] -ne $target[$_] })
$extra = @($target.Keys | Where-Object { -not $source.ContainsKey($_) })
if ($missing.Count -gt 0 -or $extra.Count -gt 0) {
    Write-Warning ("MIRROR NOT IDENTICAL. Missing/different: " + ($missing -join ", "))
    Write-Warning ("Extra refs in GitFlic (not deleted): " + ($extra -join ", "))
    throw "Mirror verification failed. No remote refs were deleted or force-updated."
}
Write-Host ("VERIFIED: GitHub and GitFlic have identical branch/tag refs (" + $source.Count + ").")
