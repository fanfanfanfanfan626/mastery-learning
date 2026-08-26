# Evaluation and learner-outcome plan

## Evidence levels

The project reports five evidence levels separately:

| Level | Question | Evidence |
|---|---|---|
| E0: package | Can a named host discover the complete two-Skill bundle? | Agent Skills validation, adapter manifests, clean installation |
| E1: engine | Are state, scheduling, migration, privacy, and tool invariants correct? | Deterministic automated tests and fault injection |
| E2: conversation | Does a fresh task on a named host activate the right Skills and follow their instructions? | Host-labeled synthetic prompts, transcripts, rubric results, repeated runs |
| E3: usability | Can intended learners complete the workflow without avoidable confusion or overload? | Consenting pilot sessions, observation, abandonment and assistance data |
| E4: outcomes | Does the product improve durable independent capability relative to an explicit comparison? | Predefined outcome study with delayed and transfer measures |

Passing a lower level never implies that a higher level passed. In particular, the Python test count is E1 evidence, not a learning-effect measurement.

E0 is recorded per distribution adapter, and E2 is recorded per host and version. A successful
Claude Code or GitHub Copilot directory installation therefore remains “behavior pending” until
fresh-session runs on that host satisfy the same critical-case and stability policy. Codex results
must not be reused as evidence for another host.

## Conversation evaluation suite

`quality/evals/plugin-evals.json` is the machine-readable E2 suite for the Codex reference adapter.
It covers the request classes in [OpenAI's complete-plugin testing guidance](https://developers.openai.com/plugins/deploy/connect-chatgpt):

- direct requests;
- indirect requests expressing the same goal;
- follow-ups that depend on prior results;
- negative requests that should not activate the plugin;
- intentional boundary cases.

Validate the suite:

```bash
python quality/eval_audit.py suite quality/evals/plugin-evals.json
```

Create a non-overwriting result template for an installed plugin and named Codex/model build:

```bash
python quality/eval_audit.py init-result \
  quality/evals/plugin-evals.json \
  quality/evals/results/<version>/run-001/result.json \
  --run-id run-001 \
  --surface "Codex desktop" \
  --model "exact model identifier" \
  --evaluator "reviewer name or stable pseudonym"
```

Run cases from fresh tasks unless a case contains its own follow-up history. Record the actual activated Skills, criterion evidence, forbidden behavior, and a relative transcript path. Use only the suite's synthetic prompts. Do not put learner state, credentials, personal paths, or unrelated conversation history in committed transcripts.

Validate a completed result:

```bash
python quality/eval_audit.py result \
  quality/evals/plugin-evals.json \
  quality/evals/results/<version>/run-001/result.json
```

The validator requires a complete result by default. Use `--allow-incomplete` only while checking a work-in-progress template. It binds a result to the canonical suite hash, requires every case and criterion, rejects unsafe, repeated, or missing transcript paths, and prevents an activation mismatch or observed forbidden behavior from being labeled `pass`. It does not grade prose automatically; the evidence still needs review.

Version tags are gated by the `release_policy` embedded in the hash-bound suite. For the value in
`VERSION`, collect three independent complete runs with unique run IDs:

```bash
python quality/eval_audit.py release-evidence \
  quality/evals/plugin-evals.json \
  quality/evals/results/<version>
```

The release gate requires all of the following:

- at least three structurally valid runs, each with a unique `run.id`;
- every case recorded as `pass` or evidence-backed `fail`, with no `blocked` or `not-run` result;
- every case listed in `critical_case_ids` passing in every complete run;
- at least a 90% pass rate across all case/run observations;
- every non-critical case passing in at least two thirds of complete runs.

`--minimum-complete-runs` may strengthen the suite policy but cannot lower it. The result root is a closed structure: every direct child must be a non-linked run directory whose name equals its `run.id`, each directory must contain exactly one `result.json` plus the referenced `.md`, `.txt`, `.json`, or `.jsonl` files under `transcripts/`, and unreferenced or renamed files are rejected. Run IDs, timestamps, transcript paths, and whole-run transcript fingerprints must be distinct.

Run each suite instance from fresh tasks and retain failures. These structural checks catch accidental duplication and simple evidence copying, but a repository-local validator cannot observe a run that was never recorded or prove that lightly edited transcripts came from independent execution. Release review must therefore inspect Git history and raw task provenance; stronger publisher claims require externally attested execution.

This gate establishes release-quality E2 evidence, not learner outcomes. A failed case may remain in an otherwise passing aggregate only when it is non-critical and the declared stability thresholds still hold; all failures remain visible in the committed results.

For stability claims beyond the release minimum, add runs rather than selecting only the best. The same policy is evaluated across all complete runs found. Useful aggregate measures include expected-activation recall, negative-case precision, required-criterion pass rate, forbidden-behavior rate, and cross-run disagreement. Report the model, Codex surface/version, plugin version, date, evaluator, failures, and blocked cases.

## Learner pilot

An E3 pilot should test the end-to-end experience before attempting efficacy claims:

1. Recruit consenting learners whose starting level and goal match a declared target profile.
2. Use a pre-task that samples prerequisite knowledge, not only confidence.
3. Observe onboarding, workspace choice, scope confirmation, normal learning, due review, tool use, and cross-task resume.
4. Record only predefined, minimal measures: task completion, time, hints, abandonment, confusion points, and learner-controlled feedback.
5. Keep raw learner data private by default; publish de-identified aggregates and the analysis protocol.

Small pilots are for detecting workflow failures and estimating feasibility. They should not be described as proof of effectiveness.

## Outcome evaluation

Before an E4 study, define the comparison, target capability, scoring rubric, exclusions, missing-data policy, and analysis plan. Prefer outcomes that require independent production:

- immediate application after instruction;
- delayed retrieval after a predefined interval;
- changed-context transfer;
- independent project or debugging performance;
- time and assistance required to reach criterion;
- retention, withdrawal, and adverse-friction rates.

A useful comparison might be the same Codex model with the plugin disabled and a neutral learning prompt. Keep time budget, source access, model, task set, and scoring as comparable as possible. Blind outcome scoring where practical. Report uncertainty, attrition, protocol deviations, and null or negative results. Do not use mastery events generated by the product itself as the sole outcome measure.
