[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [string]$CodexCommand = "codex"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$CliDocumentationUrl = "https://learn.chatgpt.com/docs/codex/cli"

function Get-CodexCandidate {
    param([string]$Command)

    try {
        $CommandInfo = Get-Command -Name $Command -ErrorAction Stop | Select-Object -First 1
        $Candidate = [string]$CommandInfo.Source
        if ([string]::IsNullOrWhiteSpace($Candidate)) {
            $Candidate = [string]$CommandInfo.Definition
        }
        if (-not [string]::IsNullOrWhiteSpace($Candidate)) {
            return $Candidate
        }
    } catch {
        # The structured blocker below still reports the requested command.
    }
    return $Command
}

function New-CliBlockerMessage {
    param(
        [string]$Command,
        [string]$Detail
    )

    $Candidate = Get-CodexCandidate -Command $Command
    $CandidateNote = if ($Candidate -match '(?i)[\\/]WindowsApps[\\/]') {
        "The discovered executable is inside WindowsApps. Treat it as an unavailable app-internal candidate; do not copy it or change package permissions."
    } else {
        "The requested Codex command is missing or could not be launched from this task."
    }

    return @"
MASTERY_INSTALL_STATUS=blocked
MASTERY_BLOCKER=codex-cli-unavailable
MASTERY_CLI_CANDIDATE=$Candidate
MASTERY_RECOVERY=official-cli
MASTERY_CLI_DOCS=$CliDocumentationUrl

$CandidateNote
$Detail

The repository passed preflight, but the plugin is not installed and no Codex configuration was
changed. Follow AI_INSTALL.md's controlled recovery using current official OpenAI CLI documentation,
then rerun this installer. Do not use skill-installer, copy a nested Skill, copy an executable out
of WindowsApps, or change WindowsApps permissions.
"@
}

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot ".")).Path
$MarketplacePath = Join-Path $RepositoryRoot ".agents\plugins\marketplace.json"
$PluginManifestPath = Join-Path $RepositoryRoot "plugins\mastery-tutor\.codex-plugin\plugin.json"
$VersionPath = Join-Path $RepositoryRoot "VERSION"

if (-not (Test-Path -LiteralPath $MarketplacePath -PathType Leaf)) {
    throw "Not a Mastery Tutor marketplace root: missing .agents/plugins/marketplace.json"
}
if (-not (Test-Path -LiteralPath $PluginManifestPath -PathType Leaf)) {
    throw "Incomplete plugin package: missing plugins/mastery-tutor/.codex-plugin/plugin.json"
}
if (-not (Test-Path -LiteralPath $VersionPath -PathType Leaf)) {
    throw "Incomplete plugin package: missing VERSION"
}

$Marketplace = Get-Content -Raw -LiteralPath $MarketplacePath | ConvertFrom-Json
$PluginManifest = Get-Content -Raw -LiteralPath $PluginManifestPath | ConvertFrom-Json
$ReleaseVersion = (Get-Content -Raw -LiteralPath $VersionPath).Trim()
$MarketplacePlugin = @(@($Marketplace.plugins) | Where-Object { $_.name -eq "mastery-tutor" })

if ($Marketplace.name -ne "mastery-tutor" -or $MarketplacePlugin.Count -ne 1) {
    throw "Marketplace identity mismatch: expected exactly one mastery-tutor entry"
}
if ($MarketplacePlugin[0].source.source -ne "local" -or $MarketplacePlugin[0].source.path -ne "./plugins/mastery-tutor") {
    throw "Marketplace source mismatch: expected local path ./plugins/mastery-tutor"
}
if ($PluginManifest.name -ne "mastery-tutor" -or $PluginManifest.skills -ne "./skills/") {
    throw "Plugin identity mismatch: expected mastery-tutor with bundled ./skills/"
}
if ($PluginManifest.version -ne $ReleaseVersion) {
    throw "Plugin version mismatch: generated adapter does not match VERSION"
}

Write-Output "Preflight passed: Mastery Tutor $ReleaseVersion with both bundled Skills."
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
    $CliBlockerMessage = New-CliBlockerMessage -Command $CodexCommand -Detail "Codex CLI launch failed: $($_.Exception.Message)"
    [Console]::Error.WriteLine($CliBlockerMessage)
    exit 1
}
if ($LASTEXITCODE -ne 0) {
    $CliBlockerMessage = New-CliBlockerMessage -Command $CodexCommand -Detail "Codex CLI probe failed with exit code $LASTEXITCODE."
    [Console]::Error.WriteLine($CliBlockerMessage)
    exit 1
}
Write-Output "Codex CLI: $($CodexVersion -join ' ')"

try {
    $ExistingPluginList = @(& $CodexCommand plugin list 2>&1)
} catch {
    throw "Could not inspect existing Codex plugins before installation. No plugin changes were made. $($_.Exception.Message)"
}
if ($LASTEXITCODE -ne 0) {
    throw "Could not inspect existing Codex plugins before installation. No plugin changes were made."
}
$ExistingPluginListText = $ExistingPluginList -join [Environment]::NewLine
if ($ExistingPluginListText -match '(?im)(^|\s)mastery-learning(\s|$)') {
    throw @"
MASTERY_INSTALL_STATUS=blocked
MASTERY_BLOCKER=legacy-plugin-installed

The old 'mastery-learning' Codex plugin is still installed. It was not removed. Follow MIGRATION.md,
confirm that learner workspaces remain intact, remove only the old plugin identity, then rerun this
installer. Never delete .mastery learner data during the product rename.
"@
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
    & $CodexCommand plugin add "mastery-tutor@mastery-tutor"
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
if ($PluginListText -notmatch '(?im)mastery-tutor') {
    throw "Installation verification failed: 'codex plugin list' did not contain mastery-tutor."
}

Write-Output $PluginListText
Write-Output "Installed and verified mastery-tutor as a complete Codex plugin. Open a new Codex task to load both bundled Skills."
