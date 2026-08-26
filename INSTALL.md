# Install Mastery Tutor

Mastery Tutor contains two canonical Agent Skills. Choose the host you are actually using:

| Host | Status | Instructions |
|---|---|---|
| Codex | Engineering-verified; E2 conversation evidence pending | [docs/install/codex.md](docs/install/codex.md) |
| Claude Code | Experimental | [docs/install/claude-code.md](docs/install/claude-code.md) |
| GitHub Copilot | Experimental | [docs/install/github-copilot.md](docs/install/github-copilot.md) |
| OpenCode | Planned | [docs/install/opencode.md](docs/install/opencode.md) |
| Other Agent Skills host | Core only | [docs/install/generic-agent.md](docs/install/generic-agent.md) |

## Ask an AI to install it

Send this message to the AI host you want to use:

```text
请安装 Mastery Tutor：https://github.com/fanfanfanfan626/mastery-tutor 。先读取并严格执行仓库根目录的 AI_INSTALL.md，识别当前 AI 宿主并安装完整的两个 Skill；发现旧版本先告诉我，不要直接覆盖或删除任何 .mastery 学习数据。若当前宿主是 Codex 且 codex --version 不可用，我允许你仅按 OpenAI 官方 Codex CLI 文档安装或修复正式 CLI；禁止复制 WindowsApps 内部程序、修改其权限、使用 skill-installer 或拆装嵌套 Skill。完成对应宿主的全部成功条件前不要宣称安装成功。
```

The AI-readable router is [AI_INSTALL.md](AI_INSTALL.md). Package status and feature limits are in
[COMPATIBILITY.md](COMPATIBILITY.md). Existing `mastery-learning` users must read
[MIGRATION.md](MIGRATION.md) before replacing the old Codex plugin identity.

## Portable manual install

Python 3.10 or newer is required for the local state engine and deterministic HTML classroom.

```text
python install-agent-skills.py --host <agent-skills|claude-code|github-copilot> --scope <user|project>
python install-agent-skills.py --host <same-host> --scope <same-scope> --check
```

Use `--project-root <absolute-path>` for another project or `--host custom --target
<absolute-skills-directory>` for a documented compatible host. Existing differing Skill directories
produce a conflict. Use `--replace` only after reviewing the paths; replacement keeps a recoverable
sibling backup.
