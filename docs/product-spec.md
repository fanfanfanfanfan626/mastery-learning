# Product specification

## First-principles objective

The final outcome of learning is an independently usable capability. Therefore the product optimizes for evidence of retrieval, explanation, application, debugging, transfer, and creation—not time spent, pages read, answer fluency, or course completion.

## Required product behavior

1. Translate a vague aspiration into an observable capability and proof artifact.
2. Diagnose the smallest set of prerequisites that changes the near-term plan.
3. Maintain a complete, versioned, sourced coverage graph, a learner-confirmed prerequisite-closed scope, and a short adaptive active path.
4. Teach through active, turn-based interaction rather than monologue.
5. Generate tools only where they make a relationship or performance observable.
6. Give feedback at the earliest causal error and allow retries.
7. Require independent and durable evidence before mastery.
8. Schedule retrieval and changed-context review.
9. Keep the learner model small, local, inspectable, and revisable.
10. Separate proposed product improvements from automatic session adaptation.

## Personalization

Personalization changes sequence, examples, representations, hint size, difficulty, session length, review load, and capstone choice. It is based on observed performance plus user constraints. The system does not assign fixed learning-style labels or infer unrelated sensitive traits.

## Interest and motivation

The system uses meaningful choice, authentic artifacts, visible independence, relevant projects, and frontier-level challenges. Streaks or points may be displayed only as optional information; they do not affect mastery and must not pressure the learner.

## Completeness

Completeness means every target outcome has prerequisite support, sources, boundary/failure cases, and an assessment route. It does not mean every learner must study every node. The complete universe remains auditable; a confirmed target profile and explicit targets derive the required closure. Optional enrichment, unselected concepts, and explicit domain exclusions remain distinct.

For ML/AI/LLM learning, the built-in pack covers computing, mathematics, classical AI search/planning/knowledge representation/sequential decisions, data/experimentation, classical ML, ML production, deep learning, transformers/foundation models, LLM applications, evaluation/safety/production, and research practice. Advanced robotics/control, domain-specialist vision/speech, custom accelerators, and formal certification remain explicit exclusions unless a new target pack adds them.

## Minimum viable user journey

1. Learner states a target in Codex.
2. Codex resolves the goal boundary, explains local persistence, and agrees on a stable learner-owned workspace.
3. Codex initializes `.mastery/`, then asks and records diagnostic tasks before showing the short path plus coverage boundary.
4. Each session starts with retrieval, teaches one frontier capability, and ends with an exit task.
5. Code or interactive tools are generated only when justified.
6. Evidence updates mastery and review dates.
7. A capstone and defense verify integrated capability.

## Non-goals for the initial release

- hosted LMS, cohort management, certificates, grades, or surveillance analytics;
- a fixed video/content library;
- a general-purpose website as the main interface;
- automatic claims of pedagogical effectiveness without learner-outcome evaluation;
- silent self-modification.

## Release acceptance criteria

- both Skills pass Skill Creator validation;
- the plugin passes Plugin Creator validation;
- curriculum identity, target closure, source provenance, scope, and DAG audit have no errors;
- state initialization, explicit scope closure, cross-task discovery, serialized writes, interrupted-transaction recovery, derived-state recovery, conservative migration, strict durability transition, failure transition, due-review query, export, and confirmed deletion pass automated tests;
- unfinished generated tools and placeholder checks fail; static validation never executes generated code; only separately observed sandbox/render results can mark a tool verified;
- README installation commands match the bundled Plugin Creator installation contract, and the exact release archive passes a fresh-clone smoke test before a separate Codex installation check;
- at least one cold-start and one cross-task resume conversation are manually evaluated for triggering, answer leakage, overload, false mastery, and workspace selection.
