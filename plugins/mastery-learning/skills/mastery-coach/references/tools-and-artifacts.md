# Teaching tools and artifact protocol

## Coding exercises

Before writing files, state the learning mode.

- In **coach mode**, create a minimal scaffold, TODOs, fixtures, tests, and rubric. Do not fill the target implementation.
- In **demonstration mode**, implement one complete example while narrating decisions, then create a different learner task.
- In **pair mode**, let the learner choose architecture and invariants; Codex may perform repetitive edits.
- In **exam mode**, create the task and checks, then withhold hints until submission.

For each code exercise:

1. Name the capability and constraints.
2. Ask for a prediction or plan.
3. Create the smallest safe workspace.
4. Provide a deterministic command that checks the result.
5. Inspect the learner's diff, output, and explanation.
6. Diagnose the earliest conceptual error before editing.
7. Record evidence only for work attributable to the learner.

Never run untrusted code outside the available sandbox. Static manifest validation does not make code safe: execute the check in a separate Codex sandbox call with secrets removed, then archive only observed exit/output through the Tool Creator finalization gate. Do not expose secrets in examples, logs, fixtures, or screenshots.

Before every reuse of an existing generated tool, rerun `mastery-tool-creator/scripts/validate_tool.py` against its current directory. `verified` is valid only when the current tool-tree and manifest SHA-256 match the archived verification report. Treat `stale`, `rejected`, a missing report, or a hash mismatch as unverified; rerun the external check/render and finalization after any edit.

## Visual laboratory

Use the conversation-native visualization capability when available. Otherwise create a local HTML/canvas, SVG, notebook, plot, or diagram. Serve verified local HTML from its own tool directory with the manifest's exact dynamic-port loopback launch; do not assume a fixed port, share the classroom server, or rely on `file://` access. The Coach records the exact process/session and assigned port, opens the lab, then stops that process and verifies its port is closed; the learner never receives lifecycle commands. Link the running verified lab into the classroom only by its exact assigned loopback URL. A lab must include:

- a question and prediction before reveal;
- 1–3 meaningful controls;
- a visible outcome tied to the concept;
- an explanation prompt after manipulation;
- a changed-condition challenge;
- a way to capture evidence.

Do not create decorative animation and call it a lab. Keep variables, units, scales, and assumptions visible. For 3D, use it only when the extra spatial dimension encodes a real relationship.

## Guided lesson lab

Use [lesson-delivery.md](lesson-delivery.md) and invoke `$mastery-tool-creator` with type
`lesson_lab` when one substantial concept encounter needs executable synchronized visualization,
guided practice, and transfer beyond the classroom's no-script blocks. This is especially
appropriate for a dynamic causal relationship such as parameter-to-output, algorithm state, tensor
shape, probability, optimization, or attention.

Reuse an exact verified lesson that samples the same target and assumptions. Do not create a lesson
lab for a one-off fact, one local correction, tiny review, or decorative polish. If generation or
inspection fails, preserve the teaching sequence in the HTML classroom rather than blocking the
learner. Page interaction is not evidence until the tutor observes attributable learner reasoning
or production.

## Blackboard

Use persistent classroom steps, comparison, code, or map blocks for derivations, traces, or evolving system state. Preserve earlier lines, highlight the current step, define symbols, and ask the learner to supply the next step. For algorithms, a table of iteration/state is often clearer than prose.

## Slides and documents

Generate slides when the learner needs a reusable mini-lesson, presentation rehearsal, or visual recap. Use a document/PDF when layout or offline study matters. Keep active-recall prompts outside the answer-facing slide or on a separate reveal. The HTML classroom remains the default teaching surface.

## Notebooks

Prefer a notebook for experiments with data, models, plots, and narrative. Separate cells into prediction, setup, learner TODO, deterministic check, visualization, and reflection. Pin dependencies or state versions. If JupyterLite/Pyodide is available, it can provide a zero-install browser lab; otherwise use the learner's normal Python environment.

## Repository or paper study

- Start from an architecture map or claim map.
- Select one execution path, experiment, or theorem to trace deeply.
- Ask the learner to predict before opening the implementation or result.
- Distinguish quoted/source content, paraphrase, and tutor inference.
- Turn reading into an artifact: annotated trace, reproduction, test, diagram, critique, or ablation.
