[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [string]$CodexCommand = "codex"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot ".")).Path
$MarketplacePath = Join-Path $RepositoryRoot ".agents\plugins\marketplace.json"
$PluginManifestPath = Join-Path $RepositoryRoot "plugins\mastery-learning\.codex-plugin\plugin.json"

if (-not (Test-Path -LiteralPath $MarketplacePath -PathType Leaf)) {
    throw "Not a Mastery Learning marketplace root: missing .agents/plugins/marketplace.json"
}
if (-not (Test-Path -LiteralPath $PluginManifestPath -PathType Leaf)) {
    throw "Incomplete plugin package: missing plugins/mastery-learning/.codex-plugin/plugin.json"
}

$Marketplace = Get-Content -Raw -LiteralPath $MarketplacePath | ConvertFrom-Json
$PluginManifest = Get-Content -Raw -LiteralPath $PluginManifestPath | ConvertFrom-Json
$MarketplacePlugin = @(@($Marketplace.plugins) | Where-Object { $_.name -eq "mastery-learning" })

if ($Marketplace.name -ne "mastery-learning" -or $MarketplacePlugin.Count -ne 1) {
    throw "Marketplace identity mismatch: expected exactly one mastery-learning entry"
}
if ($MarketplacePlugin[0].source.source -ne "local" -or $MarketplacePlugin[0].source.path -ne "./plugins/mastery-learning") {
    throw "Marketplace source mismatch: expected local path ./plugins/mastery-learning"
}
if ($PluginManifest.name -ne "mastery-learning" -or $PluginManifest.skills -ne "./skills/") {
    throw "Plugin identity mismatch: expected mastery-learning with bundled ./skills/"
}

Write-Output "Preflight passed: Codex plugin marketplace 'mastery-learning' with bundled Skills."
Write-Output "Repository root: $RepositoryRoot"

if ($CheckOnly) {
    Write-Output "Check-only mode: Codex configuration was not changed."
    exit 0
}

$TemporaryRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\')
if ($RepositoryRoot.StartsWith($TemporaryRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing a temporary install source. Move the complete repository to a stable directory and run again."
}

try {
    & $CodexCommand plugin marketplace add $RepositoryRoot
} catch {
    throw "Could not launch the Codex CLI for marketplace registration. Do not use skill-installer as a fallback. $($_.Exception.Message)"
}
if ($LASTEXITCODE -ne 0) {
    throw "Codex marketplace registration failed with exit code $LASTEXITCODE. The plugin was not installed."
}

try {
    & $CodexCommand plugin add "mastery-learning@mastery-learning"
} catch {
    throw "Could not launch the Codex CLI for plugin installation. Do not copy a nested Skill as a fallback. $($_.Exception.Message)"
}
if ($LASTEXITCODE -ne 0) {
    throw "Codex plugin installation failed with exit code $LASTEXITCODE."
}

Write-Output "Installed mastery-learning as a Codex plugin. Open a new Codex task to load both bundled Skills."
