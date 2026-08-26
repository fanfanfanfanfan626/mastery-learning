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

$CodexHome = if ($env:CODEX_HOME) {
    [System.IO.Path]::GetFullPath($env:CODEX_HOME)
} else {
    Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex'
}
$StandaloneSkillsRoot = Join-Path $CodexHome 'skills'
$LegacySkills = @(
    @(
        'mastery-coach',
        'mastery-tool-creator'
    ) | ForEach-Object {
        Join-Path $StandaloneSkillsRoot $_
    } | Where-Object {
        Test-Path -LiteralPath $_ -PathType Container
    }
)

if ($LegacySkills.Count -gt 0) {
    $LegacyList = $LegacySkills -join [Environment]::NewLine
    throw @"
Legacy standalone Mastery Skills were found:
$LegacyList

No Codex configuration was changed. These copies can shadow the complete plugin. Show the paths to
the user and ask before removing or moving them, then rerun this installer. Do not delete them
silently and do not install around them.
"@
}

try {
    $CodexVersion = @(& $CodexCommand --version 2>&1)
} catch {
    throw @"
Could not launch the Codex CLI: $($_.Exception.Message)

The repository passed preflight, but the plugin is not installed. Do not download another Codex
CLI, use skill-installer, or copy a nested Skill. Open a normal local terminal where
'codex --version' succeeds, return to this stable repository, and run install.ps1 again.
"@
}
if ($LASTEXITCODE -ne 0) {
    throw @"
The Codex CLI probe failed with exit code $LASTEXITCODE.

The plugin is not installed. Do not download another Codex CLI or use skill-installer. Open a normal
local terminal where 'codex --version' succeeds and rerun this installer.
"@
}
Write-Output "Codex CLI: $($CodexVersion -join ' ')"

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

try {
    $PluginList = @(& $CodexCommand plugin list 2>&1)
} catch {
    throw "The plugin command completed, but installation verification could not run. $($_.Exception.Message)"
}
if ($LASTEXITCODE -ne 0) {
    throw "The plugin command completed, but 'codex plugin list' failed with exit code $LASTEXITCODE."
}
$PluginListText = $PluginList -join [Environment]::NewLine
if ($PluginListText -notmatch '(?im)mastery-learning') {
    throw "Installation verification failed: 'codex plugin list' did not contain mastery-learning."
}

Write-Output $PluginListText
Write-Output "Installed and verified mastery-learning as a complete Codex plugin. Open a new Codex task to load both bundled Skills."
