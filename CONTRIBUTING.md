# Contributing to Mastery Learning

Thanks for helping make AI-assisted learning more honest, useful, and accessible.

## Good first contributions

- improve a confusing installation or first-session instruction;
- add a small synthetic conversation case with explicit pass/fail criteria;
- improve keyboard, narrow-screen, or text-fallback behavior in a lesson template;
- document a reproducible teaching failure without including private learner data;
- add a curriculum source only when its scope, provenance, and covered concepts are explicit.

Look for issues labeled [`good first issue`](https://github.com/fanfanfanfanfan626/mastery-learning/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

## Development setup

Use Python 3.10 or newer. The core project has no runtime package installer; Codex supplies the AI interface and the repository scripts use the standard library unless a validation tool states otherwise.

```bash
python plugins/mastery-learning/skills/mastery-coach/scripts/curriculum_audit.py
python quality/eval_audit.py suite quality/evals/plugin-evals.json
python -m unittest discover -s quality -p "test_*.py" -v
```

Before changing plugin or Skill metadata, also run the current Codex `plugin-creator` and `skill-creator` validators. Do not weaken an evidence, privacy, deletion, inspection, or answer-leakage boundary merely to make a test pass.

## Pull requests

Keep each pull request focused. Explain:

1. the learner or maintainer problem;
2. the invariant that should hold;
3. how the change was tested;
4. any claim, privacy, or migration boundary affected.

Do not commit `.mastery/` data, real learner transcripts, credentials, generated caches, or unreviewed copyrighted course content.

## Teaching changes

A teaching change should define the intended learner action and the evidence it can produce. A more beautiful explanation is not automatically a better lesson; preserve learner agency, productive struggle, accessible fallbacks, and honest uncertainty.

## Community

Be specific, patient, and kind. Early users are helping uncover product failures, not taking an exam. Critique behavior and artifacts rather than people.
