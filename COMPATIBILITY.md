# Compatibility

Mastery Tutor separates its portable teaching core from host adapters. A label describes what has
actually been exercised; it is not a promise inferred from a similar directory layout.

| Host | Status | Tested version | HTML classroom | Cross-session resume | Installation |
|---|---|---|---|---|---|
| Codex | **Engineering-verified; E2 pending** | CI and local engineering checks on `main` | Implemented; conversation evidence pending | Engine-tested; conversation evidence pending | Complete plugin |
| Claude Code | Experimental | Not yet release-gated | Manual/open URL pending host test | Pending | Two-Skill installer |
| GitHub Copilot | Experimental | Not yet release-gated | Host behavior pending | Pending | Two-Skill installer |
| Generic Agent Skills host | Core-compatible | Host-specific | Host-dependent | Host-dependent | Two-Skill installer |
| OpenCode | Planned | — | — | — | Not published |

## Status definitions

- **Core-compatible**: both canonical Skills pass structural validation and can be installed without
  changing their bytes. Runtime and interaction behavior remains host-dependent.
- **Experimental**: a named adapter and installation path exist, but the complete release matrix has
  not passed repeatedly on a named host version.
- **Engineering-verified**: packaging, deterministic engines, privacy boundaries, and adapter
  contracts pass automated or fault-injection checks. This is E0/E1 evidence only; it does not
  claim that a fresh host conversation follows the Skills consistently.
- **Verified adapter**: installation, Skill activation, onboarding, HTML classroom, state writes,
  new-session recovery, code/tool boundaries, server cleanup, migration, and uninstall have passed
  the release matrix with recorded evidence.
- **Planned**: no supported installer is shipped. Documentation must not invent one.

## Verification matrix

A host can move to Verified only when all of these are recorded for a named version and operating
system:

1. fresh installation of both Skills as one product;
2. direct, indirect, follow-up, negative, and boundary activation requests;
3. one-reply onboarding without an entrance exam;
4. generated HTML classroom rendering, responsive inspection, fallback, and refresh;
5. `.mastery/` state creation, validation, evidence rules, and new-session recovery;
6. local command/runtime boundaries and answer-leakage protections;
7. loopback server isolation and cleanup;
8. upgrade from the previous identity/version without learner-data loss;
9. clean uninstall that preserves learner workspaces unless deletion is explicitly requested;
10. at least three complete evaluation runs meeting the release policy.

Until all ten items have named, version-bound evidence, describe the adapter by its strongest lower
evidence level and show the missing level explicitly. Do not use a prior version's runs or informal
manual testing to fill a release-evidence directory.

The technical requirements behind this matrix are in [docs/host-contract.md](docs/host-contract.md).
Conversation evidence is governed by [docs/evaluation.md](docs/evaluation.md).
