# Authoring and extension guide

## Change the main teaching rules

Edit `skills/mastery-coach/SKILL.md` only for routing and universally required behavior. Put detailed protocols in `references/` and link them directly from the relevant route. Keep the frontmatter limited to `name` and `description`.

After any change, run Skill Creator validation and forward-test realistic prompts. Do not add a second source of truth for mastery criteria.

## Extend the HTML classroom

The Coach's learner-facing interface is the shared no-script HTML classroom. Add reusable presentation primitives to `assets/classroom-template/classroom.css` and `scripts/render_classroom.py`; do not hand-author a second page shell inside prompts or curriculum files. Keep content structured, escaped, local-first, responsive, printable, and limited to one current learner action. Executable interactions remain Tool Creator artifacts linked from the classroom, so changing lesson copy does not silently invalidate executable-tool verification.

## Add a curriculum pack

Follow `assets/curricula/ml-ai-llm.json`:

- unique lowercase hyphen IDs;
- acyclic prerequisites;
- observable outcomes;
- one or more required evidence dimensions;
- target profiles expressed as final concept IDs whose prerequisite closure defines coverage;
- a target outcome for every profile and explicit included/excluded scope;
- source IDs that exist in the pack ledger, with organization, authority, version/date, reuse boundary, declared concept coverage, gaps, and check date;
- optional content marked explicitly.

For a broad field, include a prerequisite-free orientation concept in every built-in target profile. It must distinguish the field's major layers, connect them to the learner's goal, and explain the eventual build/evaluate loop before downstream notation or mechanisms. A new machine-learning route, for example, must not open with loss, gradients, tensor shapes, or an exam.

Run `curriculum_audit.py <path>`. It rejects uncovered required concepts, optional nodes hidden inside required closures, stale fast-moving source checks, orphan modules, source-metadata omissions, and mismatched coverage. Also manually verify URLs, licensing, versions, and factual fit; offline structure cannot prove them.

## Add a tool type

Update together:

1. Tool Creator `SKILL.md` behavior;
2. `tool-manifest.schema.json` allowed values;
3. scaffold entrypoint and evidence defaults;
4. validation rules;
5. automated positive and negative tests.

New tool types must still require learner action, feedback, transfer, and evidence. If a type cannot satisfy these, it is content—not a teaching tool—and should not be added.

## Propose self-improvement

Session-level observations belong in the learner workspace's `.mastery/improvement-proposals.md`.
Promote a proposal into the canonical Skill only after reviewing evidence across cases, considering
regressions, updating tests, and changing the single root `VERSION` value. Never
fork teaching rules into a host-specific copy.

## Release

1. Compile the Python sources, audit the curriculum, and run all repository tests on Windows and Linux.
2. Run both Skill Creator validators, portable installation tests, and Codex Plugin Creator validation.
3. Validate `quality/evals/plugin-evals.json`; update it whenever triggering or teaching behavior changes.
4. Update version and changelog, then build twice, audit the archive against the intended Git ref, and compare Windows/Linux artifacts byte-for-byte.
5. Install from the archive in fresh Codex tasks and run the complete Codex conversation suite three
   times with unique run IDs. Critical cases must pass every run, aggregate case pass rate must be at
   least 90%, every non-critical case must pass at least two of three runs, and no case may be blocked
   or omitted. Repeat host-labeled fresh-session evaluations before upgrading any additional adapter
   from behavior-pending.
6. Push to GitHub and publish only artifacts produced from the tagged tree; attach provenance when available.
7. Reinstall the Codex plugin through its configured marketplace, verify portable installation into
   temporary host directories, and start a new task.
8. Publish behavior claims only at the evidence level actually achieved; learner-effect claims require the outcome protocol in `docs/evaluation.md`.
