# Changelog

## Unreleased

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
