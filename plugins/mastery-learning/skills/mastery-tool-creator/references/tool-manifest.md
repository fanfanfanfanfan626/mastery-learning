# Teaching-tool manifest

Every generated tool directory contains `tool.json` with this shape:

```json
{
  "schema_version": 3,
  "id": "gradient-landscape",
  "version": "0.1.0",
  "build_status": "complete",
  "type": "lesson_lab",
  "concept": "optimization",
  "objective": "Predict and explain how learning rate changes convergence.",
  "mode": "coach",
  "prerequisites": ["calculus-autodiff"],
  "interaction": {
    "prediction": "Choose converge, oscillate, or diverge before running.",
    "learner_action": "Adjust learning rate and justify the trajectory.",
    "feedback": "Canvas trace plus rubric-based explanation check.",
    "hints": ["Inspect successive loss values."],
    "transfer": "Choose a rate for a narrower loss valley."
  },
  "evidence": {
    "kind": "transfer",
    "dimensions": ["conceptual", "application", "transfer"],
    "rubric": "rubric.json"
  },
  "entrypoint": "index.html",
  "check_command": null,
  "check_expectation": null,
  "accessibility_fallback": "accessibility-fallback.html",
  "launch": "Coach-internal: from this tool directory run `<python> -m http.server 0 --bind 127.0.0.1`, parse the assigned loopback port, open `/index.html`, and stop the exact server session after use; never hand these steps to the learner.",
  "cleanup": "Stop the exact loopback server process/session, verify its assigned port is closed, then export learner work if needed; delete only this tool directory after learner confirmation.",
  "inspection": {
    "required": true,
    "notes": "Render prediction, manipulation, feedback, keyboard flow, and narrow viewport before finalization."
  },
  "sources": [
    {"title": "Primary reference", "url": "https://example.org/reference", "checked_at": "2026-08-22", "license_reuse": "Link and paraphrase only."}
  ],
  "created_at": "2026-08-22T12:00:00+00:00",
  "generator": {"name": "mastery-tool-creator", "version": "0.4.2"}
}
```

## Allowed types

`code_lab`, `visual_lab`, `lesson_lab`, `simulation_3d`, `blackboard`, `notebook`, `quiz`, `slide_deck`, `document`, `project_lab`.

## Required interaction semantics

- `prediction` may be “not applicable” only for a pure retrieval quiz.
- `learner_action` must describe observable production or manipulation.
- `feedback` must name the deterministic signal or explicit rubric.
- `hints` is an ordered array; it may be empty in exam mode.
- `transfer` must change the context or constraints, not repeat the worked example.

## Concept registration

`concept` and `prerequisites` contain lowercase hyphen-case IDs from Mastery Coach `concepts.json`, not human-facing labels. The tool may be scaffolded before state initialization. Before learner evidence is recorded, initialize Mastery Coach and register every custom target or prerequisite with `concept-add`. When `concepts.json` exists, static validation rejects an unregistered ID; when it does not exist, validation returns an explicit registration request.

## Evidence semantics

Evidence dimensions may add detail but must contain the main state engine's semantic minimum:

- `diagnostic` and `explain`: `conceptual`;
- `recall` and `review`: `recall`;
- `exercise`: `application`;
- `debug`: `debugging`, `application`;
- `transfer`: `transfer`, `conceptual`;
- `project`: `creation`, `application`, `transfer`.

## Rubric file

`rubric.json` contains criteria with `id`, `description`, `weight`, and `evidence`. Weights must total 1 within floating-point tolerance. Criteria should score the target capability rather than interface use.

## Catalog entry

`.mastery/tool-catalog.json` stores only compact metadata and path. It is an index, not an activity log. Learner evidence belongs in `.mastery/evidence.jsonl` and is written by the main Skill.

## Static checks, sandbox runs, and inspection

When `check_command` is present, add `check_expectation` with an integer `exit_code` and optional `output_contains` marker. Every declared test or script target must be an existing regular file inside the snapshotted tool directory; discovery roots, parent traversal, arbitrary runner options, cache directories, and external test files are forbidden. Use exit `1` for an intentionally unsolved coach-mode exercise only when its concept-specific tests reach the learner TODO and fail for the declared reason. Never use unconditional failure as a substitute for a test. `validate_tool.py` validates this declaration but never runs it. Codex runs it separately in the available sandbox and `finalize_tool.py` archives the observed exit/output.

Set `inspection.required` for visual labs, guided lesson labs, simulations, slides, and documents. Do not add a self-attested `completed` field. Put the intended inspection scope in the manifest; after rendering, pass actual states/pages, accessibility fallback, and viewport observations to `finalize_tool.py`, with the separate structured `--inspection-result passed` gate. A failed or missing required inspection cannot finalize. Serve HTML only with the scaffolded canonical `<python> -m http.server 0 --bind 127.0.0.1` launch, resolving `<python>` through PATH or the Codex workspace-dependency loader; parse the assigned port, retain the exact process/session identity, inspect the loopback URL, then stop that process and verify the port is closed. Do not rely on `file://`, a fixed port, prose that merely mentions a safe command, or an assumed successful `Ctrl+C`. Every HTML page must carry the exact local-only CSP generated by `tool_scaffold.py`; do not weaken or remove a directive. All executable/resource references must resolve inside the snapshotted tool directory, and junctions/reparse points are forbidden. Put credential-free HTTPS source objects in `sources` or passive credential-free HTTPS anchors with `rel="noopener noreferrer"`, never `http:`, `file:`, `javascript:`, or URLs in scripts, styles, frames, forms, workers, or dynamic loaders. Browser-inspected visual, lesson, and 3D labs use a local HTML fallback linked from the entrypoint; static validation rejects missing local HTML resources and an entrypoint that does not directly link the declared fallback. Text-native tools may use Markdown. A complete slide deck must point to a real `.pptx`; a complete document must point to a real `.docx` or `.pdf`.

Static validation hashes the manifest and every reusable tool file. Finalization refuses bytes that differ from the latest successful static validation, then stores that snapshot in the verification report and catalog. The catalog also stores the complete report's SHA-256; any report-field modification invalidates the verified state. Revalidation preserves `verified` only for the exact verified snapshot and intact report; a valid edit changes status to `stale`, while an invalid edit changes it to `rejected`. Re-run the declared check/inspection and finalize again after any edit. Deliberately untracked runtime files such as `__pycache__`, `.pytest_cache`, `.mypy_cache`, and coverage output are forbidden at validation/finalization; execute checks with the returned no-cache environment so no executable input can escape the snapshot.
