# Install Mastery Learning

Mastery Learning is a complete Codex plugin marketplace with two bundled Skills. Install the whole
repository. Do not use `skill-installer` and do not copy a nested `SKILL.md`.

## Ask an AI to install it

Send this one message to Codex:

```text
请安装这个完整 Codex 插件：https://github.com/fanfanfanfan626/mastery-learning 。先读取并严格执行仓库根目录的 AI_INSTALL.md；完成其中全部成功条件前，不要宣称安装成功。
```

The machine-readable [AI_INSTALL.md](AI_INSTALL.md) defines the stable-directory rule, legacy-Skill
check, CLI boundary, exact installer entrypoint, and final verification. The user does not need to
repeat those details in the prompt.

## Install it yourself

Keep the repository in a directory that will still exist after the current task ends.

Windows PowerShell:

```powershell
git clone https://github.com/fanfanfanfan626/mastery-learning.git
Set-Location .\mastery-learning
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS/Linux:

```bash
git clone https://github.com/fanfanfanfan626/mastery-learning.git
cd mastery-learning
sh ./install.sh
```

For a Release ZIP, verify its published SHA-256, extract the complete archive into a stable
directory, and run the platform installer from the level containing both `.agents/` and `plugins/`.

## What the installer checks

Before changing Codex configuration, it verifies:

- `.agents/plugins/marketplace.json` identifies the `mastery-learning` marketplace;
- `plugins/mastery-learning/.codex-plugin/plugin.json` identifies the complete plugin;
- no old standalone `mastery-coach` or `mastery-tool-creator` directory can shadow the plugin;
- the existing `codex` command can run.

It then runs:

```text
codex plugin marketplace add <absolute-repository-root>
codex plugin add mastery-learning@mastery-learning
codex plugin list
```

Installation is complete only when the add command succeeds and the list contains
`mastery-learning`. Start a new Codex task afterward so both bundled Skills load.

## If an old standalone Skill is found

The installer stops before changing configuration and prints the exact paths. Review those paths
and decide whether to remove or archive them. Neither the installer nor an AI agent should delete
them without permission.

## If the Codex CLI cannot run

The installer stops and says that the plugin is not installed. It will not download a second Codex
CLI or fall back to a partial Skill install.

Open a normal local terminal where this succeeds:

```text
codex --version
```

Then return to the stable repository and rerun the platform installer. A cloned repository or a
successful package preflight alone is not an installation.

## Package-only preflight

These commands validate repository structure without requiring Codex or changing configuration:

```powershell
.\install.ps1 -CheckOnly
```

```bash
sh ./install.sh --check-only
```

## Why GitHub is one prompt, not a directory button

OpenAI's public Plugins Directory provides the `+` install button. A GitHub repo marketplace is a
separate distribution source and still depends on a local Codex host and CLI. Until this project is
listed in the public directory, the supported GitHub experience is the one-message AI install above.
