[CmdletBinding()]
param(
    [string]$IntegrationBranch,
    [switch]$AllowDirectPush,
    [switch]$AllowAdminBypass,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

foreach ($command in @("git", "gh")) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $command"
    }
}

git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) { throw "Run this script inside a Git repository." }

gh auth status *> $null
if ($LASTEXITCODE -ne 0) { throw "Authenticate first with: gh auth login" }

$repository = gh repo view --json nameWithOwner,defaultBranchRef | ConvertFrom-Json
$branches = @($repository.defaultBranchRef.name)
if ($IntegrationBranch -and $IntegrationBranch -notin $branches) {
    $branches += $IntegrationBranch
}

Write-Host "Repository: $($repository.nameWithOwner)"
Write-Host "Branches: $($branches -join ', ')"
Write-Host "Required check: Security / required"
Write-Host "Mode: $(if ($Apply) { 'APPLY' } else { 'DRY RUN' })"

foreach ($branch in $branches) {
    gh api "repos/$($repository.nameWithOwner)/branches/$branch" *> $null
    if ($LASTEXITCODE -ne 0) { throw "Remote branch does not exist: $branch" }

    $reviews = if ($AllowDirectPush) {
        $null
    } else {
        @{ required_approving_review_count = 0; dismiss_stale_reviews = $true }
    }
    $payload = @{
        required_status_checks = @{ strict = $true; contexts = @("Security / required") }
        enforce_admins = -not $AllowAdminBypass
        required_pull_request_reviews = $reviews
        restrictions = $null
        allow_force_pushes = $false
        allow_deletions = $false
    } | ConvertTo-Json -Depth 5 -Compress

    if ($Apply) {
        $payload | gh api --method PUT "repos/$($repository.nameWithOwner)/branches/$branch/protection" --input -
        if ($LASTEXITCODE -ne 0) { throw "Failed to protect branch: $branch" }
        Write-Host "Protected: $branch"
    } else {
        Write-Host "Would protect: $branch"
    }
}

if ($Apply) {
    gh api --method PUT "repos/$($repository.nameWithOwner)/vulnerability-alerts"
    if ($LASTEXITCODE -ne 0) { throw "Failed to enable vulnerability alerts." }
    gh api --method PUT "repos/$($repository.nameWithOwner)/automated-security-fixes"
    if ($LASTEXITCODE -ne 0) { throw "Failed to enable automated security fixes." }
    Write-Host "Dependabot alerts and automated security fixes enabled."
} else {
    Write-Host "No remote state changed. Re-run with -Apply after the first green workflow."
}
