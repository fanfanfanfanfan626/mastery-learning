# Install Mastery Learning

> **Package type: Codex plugin marketplace — not a standalone Skill.**
>
> Do not use `skill-installer`, and do not look for `SKILL.md` at the repository root. A standalone
> Skill install would omit the bundled teaching-tool creator and is not supported.

## Let Codex install it

The normal conversational install request is one short sentence:

```text
请把这个仓库作为 Codex 插件（不是独立 Skill）安装：https://github.com/fanfanfanfanfan626/mastery-learning 。按根目录 INSTALL.md 完成并验证。
```

`INSTALL.md` and `AGENTS.md` carry the detailed routing rules, so the learner does not need to put
an implementation checklist in every prompt.

The installer validates both of these identities before changing Codex configuration:

- marketplace: `.agents/plugins/marketplace.json` → `mastery-learning`
- plugin: `plugins/mastery-learning/.codex-plugin/plugin.json` → `mastery-learning`

It does not download code, request credentials, or copy files into the standalone Skills folder.

## Install from a Git clone

Choose a stable parent directory first. Do not clone into an operating-system temporary directory
or a disposable Codex task checkout, because the configured marketplace continues to reference the
clone.

Windows PowerShell:

```powershell
git clone https://github.com/fanfanfanfanfan626/mastery-learning.git
Set-Location .\mastery-learning
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

macOS/Linux:

```bash
git clone https://github.com/fanfanfanfanfan626/mastery-learning.git
cd mastery-learning
sh ./install.sh
```

## Install from a Release ZIP

Download an asset that actually exists on the
[Releases page](https://github.com/fanfanfanfanfan626/mastery-learning/releases), verify its published
SHA-256, and extract the complete archive into a stable directory. Run `install.ps1` or `install.sh`
from the extracted root—the level that contains both `.agents/` and `plugins/`.

## What the installer runs

After validating the repository layout, the platform scripts execute only these Codex operations:

```text
codex plugin marketplace add <absolute-repository-root>
codex plugin add mastery-learning@mastery-learning
```

If either operation fails, the installer stops and prints the failed boundary. It does not silently
fall back to `skill-installer`. After success, open a new Codex task and ask:

```text
我想系统学习机器学习、AI 和大模型。请先诊断我的目标和基础，不要直接给完整课程。
```

## Preflight only

To validate the package without changing Codex configuration:

```powershell
.\install.ps1 -CheckOnly
```

```bash
sh ./install.sh --check-only
```
