# Install for Claude Code

Status: **Experimental**. Package layout and byte-for-byte installation are tested. Fresh-session
Skill activation, HTML classroom lifecycle, safe code execution, cross-session recovery, and
uninstall have not yet passed the full adapter suite.

User installation:

```text
python install-agent-skills.py --host claude-code --scope user
python install-agent-skills.py --host claude-code --scope user --check
```

Project installation:

```text
python install-agent-skills.py --host claude-code --scope project --project-root <project>
python install-agent-skills.py --host claude-code --scope project --project-root <project> --check
```

Success means both Skill trees match the canonical source and Claude Code is restarted in a fresh
session. It does not mean the adapter is Verified. If local HTML or isolated execution is
unavailable, report the resulting capability level from `COMPATIBILITY.md`.
