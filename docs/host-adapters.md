# Host adapters

Mastery Tutor keeps one canonical pair of Skills under `skills/`. An adapter maps those Skills to a
host without forking teaching behavior. This separates file installation from agent behavior:
successful copying proves packaging; it does not prove activation, classroom delivery, state
recovery, inspection, or cleanup.

| Host | Distribution | Current evidence | Status |
|---|---|---|---|
| Codex | Generated marketplace plugin | Package, installer, engine, classroom, and tool contracts | Engineering-verified; E2 pending |
| Claude Code | Portable two-Skill installer | Layout and byte-preserving installation | Experimental; behavior verification pending |
| GitHub Copilot | Portable two-Skill installer | Layout and byte-preserving installation | Experimental; behavior verification pending |
| Generic Agent Skills | Portable two-Skill installer | Standard Skill structure and custom-target install | Core-compatible; host behavior varies |
| OpenCode | None | No adapter test | Planned |

The machine-readable distribution surface is `agent-skill-set.json`. It names the canonical Skills
and host directory mappings; it does not upgrade a host's status. Status definitions and the full
promotion matrix live in [../COMPATIBILITY.md](../COMPATIBILITY.md). Required host capabilities live
in [host-contract.md](host-contract.md).

Generated Codex output under `plugins/mastery-tutor/` must match the canonical root Skills exactly.
Run `python quality/build_adapters.py --check` to verify that invariant.
