# Generic Agent Skills installation

Status: **Core only**.

Use this path only when the host documents filesystem-backed Agent Skills compatible with
`SKILL.md`. Determine its exact Skills directory from the host's own documentation, then run:

```text
python install-agent-skills.py --host custom --target <absolute-skills-directory>
python install-agent-skills.py --host custom --target <absolute-skills-directory> --check
```

The check proves that both installed trees match the canonical repository bytes. It does not prove
automatic Skill activation, HTML opening, safe code execution, persistence, resume, or cleanup.
Classify the resulting experience using `COMPATIBILITY.md`; do not call it Verified without the
complete host test suite.
