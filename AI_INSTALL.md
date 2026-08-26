# AI installation router

Mastery Tutor is a portable two-Skill teaching system, not one root Skill and not a Codex-only
prompt. It always installs both canonical Skills listed in `agent-skill-set.json`:

- `mastery-coach`
- `mastery-tool-creator`

## Route by the current host

Identify the AI host before changing configuration. Do not choose a host from repository marketing
copy or from an executable found on disk.

- **Codex:** read and follow `docs/install/codex.md`. Install the complete generated plugin, not
  standalone Skill copies.
- **Claude Code:** read and follow `docs/install/claude-code.md`.
- **GitHub Copilot:** read and follow `docs/install/github-copilot.md`.
- **OpenCode:** read `docs/install/opencode.md`. It is planned, not verified; do not invent an
  installation procedure.
- **Another Agent Skills host:** read and follow `docs/install/generic-agent.md` only when the host
  documents filesystem-backed Agent Skills.
- **No Agent Skills/filesystem support:** stop. Protocol-only teaching is a reduced mode, not an
  installation of the full product.

## Shared safety boundary

Before replacing anything, show exact existing paths for `mastery-coach`,
`mastery-tool-creator`, the old `mastery-learning` Codex plugin, or a previous `mastery-tutor`
installation. Never silently delete them. Never delete `.mastery/` learner workspaces during an
install, product rename, adapter change, or uninstall.

Use only the selected host's documented installation surface. Do not use `skill-installer` for the
Codex adapter, copy a WindowsApps executable, change package ACLs, or treat a repository clone as an
installed product.

## Shared success condition

Do not claim success until the selected host document's observable checks pass for both Skills.
Report:

1. host and adapter;
2. exact installed paths or plugin identity;
3. version from `VERSION`;
4. post-install verification result;
5. capability level from `COMPATIBILITY.md`;
6. whether host behavior is Verified, Experimental, Planned, or Core only.

File installation proves package integrity. It does not upgrade an Experimental or Planned host to
Verified.
