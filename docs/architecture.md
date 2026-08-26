# Architecture

Mastery Tutor has one portable teaching core and generated host adapters. This separation is an
integrity boundary: teaching behavior is authored once, while installation and host integration are
allowed to vary.

## Source layout

```text
skills/                         canonical Agent Skills
  mastery-coach/
  mastery-tool-creator/
adapters/
  codex/                        Codex-only manifest and asset sources
plugins/mastery-tutor/          generated Codex plugin
.agents/plugins/marketplace.json generated Codex marketplace
docs/install/                   host-specific installation contracts
quality/                        validators, tests, evals, and release tooling
```

There is no root `SKILL.md`: the product contains two Skills with different activation boundaries.
`quality/build_adapters.py` copies the canonical Skill trees into a staged Codex package, injects
the value from `VERSION`, rejects links and reparse points, and compares or atomically replaces the
checked-in generated output. CI fails when an adapter drifts from its sources.

## The two-Skill boundary

`mastery-coach` owns:

- goal and scope confirmation;
- curriculum graph and prerequisite selection;
- compact onboarding and teaching-session policy;
- learner profile hypotheses and revisable preferences;
- evidence, mastery, review scheduling, and cross-session state;
- the persistent HTML classroom contract.

`mastery-tool-creator` owns:

- code labs, lesson labs, visual labs, and other reusable artifacts;
- manifest and source-boundary validation;
- external observation/finalization contracts;
- snapshot, stale, rejected, and verified lifecycle states;
- catalog concurrency and evidence handoff.

The Coach may request a tool, but it may not bypass Tool Creator validation or treat page interaction
as mastery evidence. Tool Creator may construct a learning artifact, but it may not change scope or
award mastery.

## State model

Each learner workspace contains a visible `.mastery/` directory. The append-only evidence and
session logs are the durable record; aggregate files are validated projections. State updates use
locks, atomic replacement, stable request IDs, idempotent retries, schema validation, chronological
checks, and migration rules.

The global registry stores only enough information to locate workspaces. New installations use the
portable `~/.mastery-learning` location. Existing `CODEX_HOME/mastery-learning` and
`~/.codex/mastery-learning` registries remain discoverable so the product rename does not orphan
learner data.

Mastery is deliberately stricter than task completion. Independent evidence across required
dimensions, transfer, and delayed retrieval are separate conditions. Assistance is recorded;
failure after mastery can mark a concept fragile; non-retrieval activity cannot postpone an
existing review.

## Classroom model

Every substantive teaching turn updates one learner-facing local HTML classroom. The page carries
one concrete situation, a prediction or choice, an observable reveal, the smallest needed
explanation, a single next action, and progress context. Beginner turns put experience before
terminology and keep the complete field map behind progressive disclosure. Chat acts as a short
handoff, not a second competing lesson.

Static classroom rendering remains available when a host cannot create or inspect a richer tool.
Reusable dynamic artifacts go through Tool Creator. Both surfaces escape learner-controlled text,
avoid remote dependencies, provide a non-script fallback, support narrow screens and reduced motion,
and use loopback HTTP rather than `file://` when a browser is required.

## Optional teaching organization

The core remains fully usable by one agent. A capable host may prepare a substantial lesson through
bounded planning, subject review, classroom production, and independent assurance. These are
temporary work roles, not learner-facing personas. They exchange one `TeachingTurnSpec`; the Coach
remains the integration owner and sole learner-facing voice, and only the state owner may update
`.mastery/`. Ordinary feedback stays single-agent. Failure, timeout, or missing orchestration
capability falls back to the same single-agent contract rather than blocking the lesson.

## Host adapters

The core does not assume Codex task terminology, `CODEX_HOME`, or an app-internal executable.
Adapters map the requirements in [host-contract.md](host-contract.md) to a host:

- discovery and installation directories;
- runtime resolution;
- browser/open-URL behavior;
- safe command observation;
- persistent session recovery;
- process and uninstall lifecycle.

Codex is the current Verified adapter. Other hosts remain Experimental or Core-compatible until the
matrix in [COMPATIBILITY.md](../COMPATIBILITY.md) has recorded results. A directory convention is
not behavioral proof.

## Release model

`VERSION` is the only release version source. The build produces:

- **core**: canonical Skills, portable installer, and shared documentation;
- **codex**: generated Codex marketplace/plugin and Codex installers;
- **bundle**: the complete source/audit distribution used by maintainers.

Archives use fixed timestamps, fixed permissions, stored ZIP entries, sorted paths, and LF-normalized
text. Windows and Linux builds must be byte-identical. Tagged releases are created by the dedicated
release workflow only after version, adapter-drift, test, curriculum, evaluation-evidence, and
archive audits pass.

## Evolution rule

Code may later move from Skill-local scripts into importable `runtime/` modules, but the migration
must preserve standalone Skill installation and extracted-release behavior. Empty directory
reorganization is not architecture. A module is extracted only when it gives a tested ownership
boundary for state, scheduling, registry, classroom, or migrations.
