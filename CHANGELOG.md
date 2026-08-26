# Changelog

## 0.5.0 — unreleased

- Renamed the product and Codex plugin identity to **Mastery Tutor** / `mastery-tutor` while
  preserving the two Skill IDs, `.mastery/` learner workspaces, and legacy registry discovery.
- Promoted `skills/mastery-coach` and `skills/mastery-tool-creator` to the only canonical sources;
  Codex packaging is now a generated adapter with source-drift checks.
- Added evidence-based compatibility labels, host contracts, migration and security guidance, and
  separate English/Chinese repository entry pages.
- Made `VERSION` the release version source and split deterministic artifacts into portable core,
  Codex adapter, and maintainer bundle distributions.
- Added a tag-only release workflow with evaluation evidence gates, cross-platform byte comparison,
  checksums, provenance attestations, and GitHub Release upload.
- Rebuilt beginner teaching around concrete experience, prediction, visible contrast, concept
  naming, guided use, and transfer instead of opening with a taxonomy or glossary.
- Made the classroom learning-first: real accessible choice controls, a compact initial viewport,
  progressive depth, and one immediately visible learner action.
- Added an optional bounded multi-agent preparation protocol for substantial lessons while keeping
  one learner-facing tutor, one state writer, and a complete single-agent fallback.

## Unreleased

- Promoted Mastery Learning from a Codex-only package to one portable two-Skill Agent Skills system:
  added a canonical skill-set manifest, host capability tiers, an AI-readable cross-host install
  contract, and a transactional installer for generic Agent Skills, Claude Code, and GitHub Copilot
  directories. Codex remains the reference adapter, while unrun host behavior stays labeled pending.
- Made generated-tool verification host-neutral without weakening it: new reports bind the observing
  AI and execution boundary, executable checks cannot use a not-applicable boundary, and existing
  Codex schema-v3 reports remain readable for upgrade continuity.
- Moved new workspace registries to the product-owned `~/.mastery-learning` default while retaining
  explicit `MASTERY_HOME`/`CODEX_HOME` support and automatic discovery of existing Codex registries.
- Replaced the contradictory CLI hard stop with a controlled official-recovery state: installers
  now emit machine-readable blocker details, distinguish an unlaunchable WindowsApps candidate from
  a usable CLI, and let an explicitly authorized AI follow current OpenAI CLI documentation before
  rerunning the same verified plugin flow.
- Added a root `AI_INSTALL.md` contract and hardened both platform installers so an AI can complete
  a one-message GitHub install without guessing: legacy standalone Skills stop before mutation,
  the existing Codex CLI is probed before any authorized official recovery, and `codex plugin list`
  verifies the final installation.
- Rewrote the GitHub first impression, plugin metadata, and marketing copy in a direct open-source
  voice that explains the learner workflow before package internals or product claims.
- Replaced optional HTML lesson delivery with a mandatory learner-facing HTML classroom for every
  onboarding, explanation, feedback, review, and close turn; chat now carries only the minimal
  classroom handoff and learner reply.
- Added a deterministic no-script classroom renderer and shared visual system with structured
  prose, callout, process, comparison, annotated-code, concept-map, artifact, and single-action
  blocks; content is escaped, local-only, responsive, dark-mode aware, printable, and not archived
  as a raw learner transcript.
- Added a dedicated no-cache, allowlisted classroom server rooted only at `.mastery/classroom`, so
  profile, plan, evidence, review, registry, and tool files cannot be exposed by the teaching URL.
- Made local servers use OS-assigned loopback ports with exact-process cleanup and closed-port
  verification; fixed-port launches and deceptive launch/cleanup prose now fail validation.
- Hardened generated-tool boundaries: escape objectives, require credential-free HTTPS sources and
  passive links, constrain checks to regular files inside the tool snapshot, and reject traversal,
  symbolic links, Windows junctions, and other reparse points.
- Separated the mutable classroom display layer from verified executable teaching tools, and made
  the Coach internally choose an available loopback port, open the browser, and own server cleanup
  instead of assigning paths, commands, internal Skills, or result-copy chores to learners.
- Added `ai-landscape` to every built-in target profile and made its first beginner turn start from
  a familiar problem and the difference between written rules and learning from examples. The full
  AI/ML/DL/foundation-model/LLM map is now a later synthesis rather than the opening glossary.
- Repositioned the project as an **AI Teaching Skill** with a Codex-tested reference adapter,
  expanded teaching/agent/HTML discovery metadata, and kept unverified cross-platform compatibility
  out of the claims.
- Reworked the repository first impression around a clear learner outcome, one-copy install path,
  animated product walkthrough, comparison table, discoverable English summary, contribution guide,
  public roadmap, and structured issue templates.
- Expanded Codex plugin discovery metadata with AI-tutor, machine-learning, LLM, local-first, visual
  identity, website, repository, and screenshot fields while preserving the stable plugin ID.
- Added a guided lesson-delivery contract that starts from an explicit zero-baseline ladder,
  separates the current evidence target from motivating previews, and sizes a complete worked
  micro-lesson to the learner's available session instead of jumping from a short explanation to
  a worksheet.
- Added the `lesson_lab` tool type with a reusable local-only HTML/CSS/JavaScript template for
  annotated code, prediction-gated visual state, guided practice, transfer, progressive hints,
  responsive layout, reduced motion, visible focus, and an equivalent text/table fallback.
- Extended static tool validation, adversarial tests, and synthetic conversation evals so incomplete
  lesson structure, hidden prerequisites, decorative tool use, or post-verification edits cannot be
  presented as a verified lesson.
- Made both Skills resolve Codex's bundled Python through the workspace-dependency loader before
  considering dependencies, preventing fresh tasks from downloading a redundant runtime merely to
  run bundled state or tool scripts; expanded trigger metadata to cover the learning-record
  inspect/export/migrate/delete lifecycle.

## 0.4.2 — 2026-08-23

- Made the repository self-identify as a two-Skill Codex plugin marketplace before installation,
  added platform-native preflight/install scripts, and explicitly rejected partial
  `skill-installer` fallback paths.
- Made release archives checkout-independent by canonicalizing text to LF, using compressor-independent stored ZIP entries, and adding repository-wide `.gitattributes` rules.
- Added a release auditor that compares archive bytes with either the working tree or a Git ref, plus CI builds on Windows and Linux whose artifacts must be byte-for-byte identical.
- Added a 17-case synthetic Codex conversation suite covering direct, indirect, follow-up, negative, and boundary requests, including single-reply personalized onboarding, with a hash-bound result contract that rejects untraceable or falsely passing runs.
- Strengthened the tag gate to require three complete runs with unique IDs, timestamps, and transcript fingerprints; closed evidence directories; zero critical-case failures; an exact 9/10 aggregate threshold; and an exact 2/3 per-case threshold.
- Canonicalized the extensionless `LICENSE` file as release text and added a legacy-Windows-CRLF regression so builds do not depend on an old checkout's line endings.
- Made ZIP installation examples refer only to assets that actually exist on the Releases page instead of assuming an unpublished candidate filename.
- Documented separate package, engine, conversation, usability, and learner-outcome evidence levels, including a conservative pilot and comparison-study plan.
- Added a primary-source pedagogy evidence map and explicit claim boundaries: research-informed rules are not presented as proof that this plugin improves learning.
- Replaced entrance-test onboarding with one compact, skippable launch card and immediate guided teaching; added lightweight experience/tone/task/check preferences plus a governed adaptive repertoire for worked-example fading, Feynman-style teach-back, contrasting cases, interleaving, productive failure, and other conditional methods.
- Prepared tagged builds for GitHub provenance attestation while retaining SHA-256 as an integrity check rather than publisher identity proof.
- Added a state-entrypoint growth budget and invariant-based extraction order so future work must modularize before extending the 2,300-line engine.

## 0.4.1 — 2026-08-22

- Replaced narrow remote-resource regexes with file-type-aware Python, JavaScript, CSS, notebook, and HTML checks that reject network, process-launch, dynamic-code, remote-module, and dynamic-resource paths without executing generated code.
- Required an exact local-only Content Security Policy on every generated HTML page and verified that executable/resource references close over tracked files inside the tool directory; passive HTTPS source links remain allowed.
- Added adversarial regressions for dynamic `import()`, beacons, remote embeds, CSS imports, unsafe Python imports, missing CSP, and modified external local scripts.
- Added a concrete standalone release-ZIP installation path so a user can install the packaged marketplace without an already-published GitHub URL.
- Kept curriculum-pack coverage exclusions in curriculum metadata instead of copying them into an unselected learner plan, preserving the distinction between authored coverage boundaries and learner-confirmed exclusions.

## 0.4.0 — 2026-08-22

- Upgraded learner state to schema v4 with OS-managed locking, replayable multi-file transactions, strict session validation, complete retry fingerprints, and conservative three-state legacy evidence support.
- Made target profiles operational: the complete curriculum snapshot remains auditable while learner-confirmed profiles derive required and enrichment prerequisite closures, honest completion ratios, and scope-validated active paths.
- Corrected mastery revocation at the 0.75 pass boundary, prevented assisted or unknown legacy evidence from certifying mastery, and made status/due refuse tampered derived views.
- Bound generated-tool verification to exact manifest and tool-tree hashes, rejected all deliberately untracked runtime/cache content so executable inputs cannot escape that snapshot, added stale/rejected lifecycle states, aligned evidence semantics with the state engine, and replaced `file://` visual inspection with loopback HTTP.
- Replaced state and catalog delete-on-release locks with crash-released byte locks and expanded regression coverage for Windows contention, migration, interrupted transactions, sessions, scope changes, tool edits, and cold-start/resume behavior.
- Made review obligations monotonic, separated required/enrichment/out-of-scope due queues, required auditable scope-confirmation reasons, preserved personalization through migration, and made registry corruption visible without hiding healthy discoveries.
- Added idempotent caller-keyed session handoffs with lock-ordered timestamps, authoritative curriculum validation during initialization, browser-renderable HTML fallbacks for visual labs, and deterministic release archives with archive-level regression tests.
- Bound generated-tool trust to the complete verification-report hash, required structured inspection outcomes, and rejected broken local HTML references or unlinked accessibility fallbacks before finalization.

## 0.3.0 — 2026-08-22

- Replaced validator-side code execution with a static-validation and Codex-observed finalization boundary; added stronger DOCX/PPTX/PDF checks and serialized tool-catalog writes.
- Added fixed concept definitions, kind/dimension semantics, idempotent event IDs, conservative fragile-state recovery, and corrected early/overdue review scheduling.
- Added explicit backed-up v1/v2 migration, strict document schemas, structured session handoffs, ownership-checked external locks, and per-workspace registry entries.
- Prevented self-including exports and self-deleting backups, serialized export/delete with recording, and repaired unsafe learner-data gitignore files while preserving a backup.
- Added curriculum optional-closure and source-freshness gates plus an explicit offline-audit limitation.
- Expanded adversarial coverage to 21 tests, including concurrency, malformed state, false mastery, migration, deletion, and non-execution checks.

## 0.2.0 — 2026-08-22

- Made append-only evidence the single source of truth; added locking, consistency validation, deterministic rebuild, cross-task workspace discovery, export, and confirmed deletion.
- Tightened mastery to require independent evidence per required dimension plus separate delayed retrieval and transfer evidence; prevented same-session review inflation.
- Upgraded generated-tool manifests and validation to execute restricted checks, reject placeholder failures and remote executable resources, require render inspection, and update the catalog only after success.
- Expanded curriculum auditing to enforce target prerequisite closure, explicit scope, complete source provenance, and source-to-concept coverage.
- Added classical AI and ML production foundations; the built-in pack now contains 48 concepts across 11 modules.
- Expanded negative, recovery, privacy, concurrency, and cross-task tests.

## 0.1.0 — 2026-08-22

- Added the `mastery-coach` core Skill and evidence-based teaching contract.
- Added local `.mastery/` state, transparent mastery calculation, and review scheduling.
- Added a 43-node ML/AI/LLM curriculum DAG with source and prerequisite audits.
- Added explicit-only `mastery-tool-creator` for code labs, visual/3D labs, blackboards, notebooks, quizzes, decks, documents, and project labs.
- Added negative/positive pedagogical validation for generated tools.
- Added repository CI, system tests, architecture, product, authoring, and acceptance documentation.
