# Local learner-state schema

The state directory is `<learning-workspace>/.mastery/`. It belongs to the learner and should be readable without this plugin.

The engine also keeps one atomic entry per workspace under `$MASTERY_HOME/workspaces.d/`. When that
override is unset, an explicit `$CODEX_HOME` remains supported for the Codex adapter; otherwise new
installations use `~/.mastery-learning/workspaces.d/`. If the portable directory does not yet exist
but an older `~/.codex/mastery-learning` registry does, the engine keeps using that existing registry
so an upgrade cannot hide prior learning. Current entries store only workspace ID, path, and update
time. Discovery projects every readable entry onto that four-field allowlist before validating it,
so even a damaged legacy entry cannot retain a goal or other learning content. Goal search loads
the workspace's visible `profile.json` instead of duplicating it globally. A new
AI task can still find prior learning without a shared read-modify-write race. Initialization fails
visibly when this registry is not writable, and discovery fails visibly with the exact entry path
when registry data is malformed. `.mastery/.gitignore` is engine-managed and excludes learner
records from Git by default.

## Files

- `profile.json`: explicit goal, stated experience/tone/assignment/assessment constraints, and revisable personalization or method-effectiveness hypotheses. Launch-packet familiarity labels remain hypotheses, never evidence.
- `plan.json`: target artifact, learner-confirmed scope selection/exclusions, and short active path. Curriculum-pack coverage exclusions remain in `concepts.json` and are never copied here as if the learner chose them.
- `concepts.json`: the complete versioned concept universe, prerequisites, outcomes, target profiles, modules, source IDs, and mastery dimensions.
- `mastery.json`: per-concept dimension estimates, evidence counts, and state.
- `reviews.json`: next due date, interval step, and last result per concept. Non-retrieval practice may update `last_learning_at` but never clears or postpones an overdue retrieval obligation.
- `evidence.jsonl`: append-only observed assessment events.
- `sessions.jsonl`: append-only concise session handoffs, not full transcripts.
- `sources.json`: source ledger for learner-added or generated curricula.
- `state-revision.json`: committed aggregate-state revision and transaction ID.
- `transaction.json`: temporary replayable write-ahead journal; normally absent after a successful command.
- `improvement-proposals.md`: proposed teaching-system changes awaiting approval.

## Evidence event

```json
{
  "schema_version": 4,
  "id": "ev-...",
  "timestamp": "2026-08-22T12:00:00+00:00",
  "concept": "gradient-descent",
  "kind": "exercise",
  "score": 0.82,
  "difficulty": 3,
  "hints": 1,
  "assisted": false,
  "independent": false,
  "delayed": false,
  "delay_hours": null,
  "dimensions": ["application"],
  "notes": "Derived update; fixed sign error after one hint",
  "legacy": false,
  "support": "assisted",
  "request_fingerprint": "<sha256 of caller-controlled evidence semantics>"
}
```

## Data rules

- Treat `evidence.jsonl` plus immutable-after-evidence `concepts.json` definitions as the source of truth. Add evidence through the engine; do not rewrite history to improve scores or shrink requirements.
- Treat `mastery.json` and `reviews.json` as replaceable derived views. `validate` compares them with a fresh derivation; `rebuild` restores them after interruption or corruption.
- Treat `support` as the evidence-certification field. `independent` can certify only when support is `independent`; `unknown` is reserved for migrated legacy evidence and cannot satisfy independent, transfer, delayed, or recovery requirements.
- Treat `request_fingerprint` as the complete idempotency boundary. The same event ID with changed time, delay request, dimensions, assistance, score, notes, or custom-concept declaration is a conflict.
- Store concise observations, not private chain-of-thought or full chat transcripts.
- Mark inference and confidence when recording personalization.
- Keep explicit onboarding preferences in `constraints` and self-positioning or inferred method effectiveness in `hypotheses`; neither can certify a concept or create a review obligation.
- A missing score means unassessed, not zero.
- Keep schema version in every JSON root.
- Hold the persistent OS byte lock under the registry lock directory while reading or changing aggregate state. The operating system releases it if a process dies; never delete a live lock file.
- Commit multi-file changes through the write-ahead journal. `state-revision.json` is the commit point; every locked command recovers an interrupted journal before reading state.
- Validate `sessions.jsonl` strictly. A malformed, duplicate, future, or non-chronological session blocks resume instead of silently falling back to an older handoff.
- Keep the full curriculum universe separate from the learner scope. `scope_selection` stores confirmed profiles and explicit targets; required and enrichment closures are derived from the frozen curriculum snapshot. An unselected scope has no completion ratio.
- Back up or commit `.mastery/` only when the learner chooses. Warn before publishing it to a public repository.
- Support export and deletion; never require a hosted account.

The bundled `scripts/mastery.py` owns deterministic updates. Use `scope-apply`, `concept-add`, `set`, `source-add`, and `session-close` for structured writes; use `export` for a ZIP outside `.mastery/` and confirmed `delete` for removal. Use stable event and session IDs for retry safety. `due` retains prior review obligations after a scope change and labels each item `required`, `enrichment`, `not-selected`, or `unselected`; once scope is confirmed, its default action queue contains only required concepts while JSON exposes separate enrichment/out-of-scope buckets and `--include-nonrequired` opts into all. Use `locate` before a cross-task resume. Run explicit `migrate` for schema v1/v2/v3; it creates an outside backup before rewriting, preserves valid personalization hypotheses, quarantines invalid active-path entries, and records unknown legacy support. Direct evidence edits are unsupported.
