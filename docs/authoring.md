# Authoring and extension guide

## Change the main teaching rules

Edit `plugins/mastery-learning/skills/mastery-coach/SKILL.md` only for routing and universally required behavior. Put detailed protocols in `references/` and link them directly from the relevant route. Keep the frontmatter limited to `name` and `description`.

After any change, run Skill Creator validation and forward-test realistic prompts. Do not add a second source of truth for mastery criteria.

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

Session-level observations belong in the learner workspace's `.mastery/improvement-proposals.md`. Promote a proposal into the Skill only after reviewing evidence across cases, considering regressions, updating tests, and incrementing the plugin version.

## Release

1. Compile the Python sources, audit the curriculum, and run all repository tests on Windows and Linux.
2. Run both Skill Creator validators and Plugin Creator validation.
3. Update version and changelog, then build and smoke-test the exact release archive.
4. Push to GitHub.
5. Reinstall the plugin through its configured marketplace.
6. Start a new Codex task and run cold-start/resume acceptance prompts.
