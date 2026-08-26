# Install for GitHub Copilot

This path is **Experimental**. The portable installer can place both canonical Skills in GitHub
Copilot's documented user or project Skill directory, but the full Mastery Tutor behavior matrix has
not yet been release-gated on a named Copilot version.

```text
python install-agent-skills.py --host github-copilot --scope project --project-root <absolute-project>
python install-agent-skills.py --host github-copilot --scope project --project-root <same-project> --check
```

For user scope, omit `--project-root` and use `--scope user`. Report successful file verification
as Experimental installation, not as a Verified adapter. The host must still provide the
capabilities in [../host-contract.md](../host-contract.md) for the complete product experience.
