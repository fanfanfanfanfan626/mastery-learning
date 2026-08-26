# AI install contract

This file is for the AI agent installing Mastery Learning from GitHub.

## Package identity

Mastery Learning is one complete Codex plugin marketplace. It contains two bundled Skills:

- `mastery-coach`
- `mastery-tool-creator`

Do not use `skill-installer`, do not search for a root `SKILL.md`, and do not copy either nested
Skill into the standalone Skills directory.

## Success means all of these are true

1. The complete repository is stored in a stable, learner-owned directory.
2. The root installer passes its package checks.
3. `codex plugin add mastery-learning@mastery-learning` exits successfully.
4. `codex plugin list` contains `mastery-learning`.
5. The learner is told to start a new Codex task before using the bundled Skills.

A clone, a downloaded ZIP, `-CheckOnly`, or a copied `SKILL.md` is not a successful install.
Do not claim success until every condition above has been observed.

## Install procedure

1. Read the repository-root `AGENTS.md` and `INSTALL.md` before changing anything.
2. Resolve a stable install directory. Reuse an existing clean clone only when its `origin` is this
   repository. Do not install from an operating-system temp directory or a disposable task checkout.
3. Check for old standalone copies at `<CODEX_HOME>/skills/mastery-coach` and
   `<CODEX_HOME>/skills/mastery-tool-creator`. If either exists, show the exact paths and ask the
   learner before deleting or moving them. Do not continue around a conflicting copy.
4. Run the root installer for the current platform. The installer performs preflight, probes the
   existing Codex CLI, registers the repository marketplace, installs the complete plugin, and
   verifies the plugin list.
5. Report the repository path, Git commit, and verification result. Ask the learner to start a new
   Codex task.

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS/Linux:

```bash
sh ./install.sh
```

## Hard stop

If `codex --version` cannot run from the current task, stop and report that exact boundary. Do not
download or install another Codex CLI with npm, npx, winget, Homebrew, curl, or a package manager.
Do not fall back to `skill-installer`.

Tell the learner to open a normal local terminal where `codex --version` succeeds, change to the
stable repository directory, and run the root installer shown above. The plugin is not installed
until the success conditions in this file are met.
