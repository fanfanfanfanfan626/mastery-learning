# Install the Codex adapter

Codex is the verified reference adapter. It installs `mastery-tutor@mastery-tutor` as one complete
plugin containing both canonical Skills. Do not use `skill-installer` or copy either nested Skill.

## Success condition

Do not claim success until all are observed:

1. the repository or Release is in a stable directory;
2. no standalone `mastery-coach` or `mastery-tool-creator` conflict remains under the Codex Skills
   directory;
3. no old `mastery-learning` plugin identity remains installed;
4. `codex plugin add mastery-tutor@mastery-tutor` exits successfully;
5. `codex plugin list` contains `mastery-tutor`;
6. the user is told to start a new Codex task.

The root installer enforces these checks. It never deletes learner workspaces or old Skills.

## Windows

```powershell
Set-Location <stable-repository-or-release-directory>
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

## macOS/Linux

```bash
cd <stable-repository-or-release-directory>
sh ./install.sh
```

The installer validates `.agents/plugins/marketplace.json`, the generated
`plugins/mastery-tutor/.codex-plugin/plugin.json`, and both bundled Skills before it changes Codex
configuration. `-CheckOnly` or `--check-only` performs package preflight without launching Codex.

## If the Codex CLI cannot run

The desktop app and terminal CLI are separate surfaces. A `codex.exe` under WindowsApps may be an
unlaunchable app-internal candidate. Never copy it or change package permissions.

When the installer emits `MASTERY_BLOCKER=codex-cli-unavailable`:

1. keep the repository and all old data unchanged;
2. install or repair only the official CLI using the current
   [OpenAI Codex CLI documentation](https://learn.chatgpt.com/docs/codex/cli), and only when the user
   authorized that machine dependency;
3. verify `codex --version`;
4. if the bare command still resolves to WindowsApps, pass the verified official CLI absolute path
   as `-CodexCommand <path>` or `--codex <path>`;
5. rerun the same root installer.

If the installer emits `MASTERY_BLOCKER=legacy-plugin-installed`, follow `MIGRATION.md`. Remove only
the old plugin identity after confirmation. Never delete `.mastery/` learner directories.
