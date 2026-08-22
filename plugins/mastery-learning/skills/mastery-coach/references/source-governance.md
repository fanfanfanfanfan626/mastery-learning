# Curriculum and source governance

## Source policy

Prefer sources in this order:

1. standards, official documentation, specifications, and original papers;
2. maintained open textbooks and university courses;
3. high-quality project documentation and reproducible tutorials;
4. secondary explainers for alternative intuition;
5. AI-generated synthesis, clearly labeled as synthesis.

For fast-moving topics, verify the current version/date. Keep direct quotations short. Link rather than copy restricted material. Confirm the license before redistributing text, images, notebooks, or code.

## Source ledger fields

Record:

- `id`, title, author/organization, canonical URL;
- source type and authority;
- publication/update date or version;
- license/reuse note;
- concepts and outcomes supported;
- known gaps, bias, or assumed prerequisites;
- date checked.

Do not use “widely cited” as a substitute for checking the source.

Add learner-workspace sources through `mastery.py source-add` so incomplete provenance is rejected. For bundled curriculum packs, run `curriculum_audit.py`; schema version, canonical HTTPS URL, duplicate IDs, declared source coverage, target outcomes, scope boundary, orphan modules, optional nodes in required closures, source-check age, and graph integrity are release-blocking checks. The audit is offline: separately verify URL availability, current versions, license terms, and factual fit before release. Recheck fast-moving official documentation/examples at least annually and sooner when a relevant platform changes.

## Curriculum construction

1. Define the target performance and exclusions.
2. Work backward to observable outcomes.
3. Decompose outcomes into prerequisite concepts.
4. Attach required evidence dimensions and mastery criteria.
5. Attach at least one authoritative source to every required concept.
6. Add boundary cases, failure modes, ethics/safety, evaluation, and system constraints where relevant.
7. Audit graph integrity: unique IDs, no missing prerequisites, no cycles, no orphan required nodes.
8. Audit outcome coverage: every target outcome is supported and every required node supports a target.
9. Separate the complete coverage map from the personalized active path.

## Completeness audit questions

- What must the learner already know?
- Can they explain, implement/apply, debug, evaluate, and transfer the target?
- Are data, measurement, uncertainty, and evaluation covered?
- Are security, privacy, ethics, or failure modes material to this goal?
- Are operational constraints such as latency, cost, reproducibility, and maintenance material?
- Does the capstone sample the whole target rather than one happy path?
- Which areas are explicitly out of scope?

## Open-source inspiration used by this product

These projects are architectural references, not bundled dependencies:

- [SkillCoco](https://github.com/skillcoco/skillcoco): local-first mastery loop, knowledge tracing, hands-on labs, and auditable algorithms.
- [OpenTutor](https://github.com/zijinz456/OpenTutor): local learner memory, knowledge graphs, adaptive content, and source-grounded workspaces.
- [Learn FASTER](https://github.com/hluaguo/learn-faster-kit): coding-agent-centered coaching, personalized syllabi, and project practice.
- [FSRS4Anki](https://github.com/open-spaced-repetition/fsrs4anki): data-driven spaced-repetition scheduling and explicit optimizer/scheduler separation.
- [JupyterLite](https://github.com/jupyterlite/jupyterlite): zero-install, browser-based computation and visualization.

Do not copy their prompts, curriculum, UI, or algorithms wholesale. Re-evaluate licenses and current behavior before adopting code.
