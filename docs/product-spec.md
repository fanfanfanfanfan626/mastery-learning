# Product specification

## First-principles objective

The final outcome of learning is an independently usable capability. Therefore the product optimizes for evidence of retrieval, explanation, application, debugging, transfer, and creation—not time spent, pages read, answer fluency, or course completion.

## Required product behavior

1. Translate a vague aspiration into an observable capability and proof artifact.
2. Estimate the smallest set of prerequisites that changes the near-term plan from background and skippable self-positioning, then refine it through guided work rather than an entrance exam.
3. Maintain a complete, versioned, sourced coverage graph, a learner-confirmed prerequisite-closed scope, and a short adaptive active path.
4. Teach through active, turn-based interaction rather than monologue; for a substantial new
   concept, preserve one complete causal spine from orientation and modeling through guided action
   and close, while keeping future ideas labeled as previews.
5. Generate tools only where they make a relationship or performance observable.
6. Give feedback at the earliest causal error and allow retries.
7. Require independent and durable evidence before mastery.
8. Schedule retrieval and changed-context review.
9. Keep the learner model small, local, inspectable, and revisable.
10. Separate proposed product improvements from automatic session adaptation.

## Personalization

Personalization starts with one lightweight, revisable experience preset plus optional tone, outside-task, and formal-check overrides. It changes sequence, examples, representations, hint size, difficulty, interaction method, response density, session length, review load, and capstone choice. The AI selects techniques such as worked-example fading, Feynman-style teach-back, contrasting cases, interleaving, or productive failure only when their trigger conditions fit, and keeps a fallback. It is based on observed performance plus user constraints. The system does not assign fixed learning-style labels, make tone change the mastery standard, or infer unrelated sensitive traits.

## Interest and motivation

The system uses meaningful choice, authentic artifacts, visible independence, relevant projects, and frontier-level challenges. Streaks or points may be displayed only as optional information; they do not affect mastery and must not pressure the learner.

## Completeness

Completeness means every target outcome has prerequisite support, sources, boundary/failure cases, and an assessment route. It does not mean every learner must study every node. The complete universe remains auditable; a confirmed target profile and explicit targets derive the required closure. Optional enrichment, unselected concepts, and explicit domain exclusions remain distinct.

For ML/AI/LLM learning, the built-in pack covers computing, mathematics, classical AI search/planning/knowledge representation/sequential decisions, data/experimentation, classical ML, ML production, deep learning, transformers/foundation models, LLM applications, evaluation/safety/production, and research practice. Advanced robotics/control, domain-specialist vision/speech, custom accelerators, and formal certification remain explicit exclusions unless a new target pack adds them.

## Minimum viable user journey

1. Learner states a target in Codex.
2. Codex presents one compact, skippable launch packet covering the missing goal, time, relevant background, self-positioning, teaching experience, and local-persistence choices.
3. After one reply, Codex initializes `.mastery/`, stores preferences and self-positioning without calling them evidence, shows the provisional short path and coverage boundary, and begins a guided micro-lesson without another setup round.
4. Each session retrieves prior or due learning when relevant, models genuinely new material before demanding performance, teaches one frontier capability, and ends with one clear next action.
5. Code or interactive tools are generated only when justified; a reusable guided lesson may use
   a verified `lesson_lab`, while simple explanations and small corrections stay in conversation.
6. Evidence updates mastery and review dates.
7. A capstone and defense verify integrated capability.

## Non-goals for the initial release

- hosted LMS, cohort management, certificates, grades, or surveillance analytics;
- a fixed video/content library;
- a general-purpose website as the main interface;
- automatic claims of pedagogical effectiveness without learner-outcome evaluation;
- silent self-modification.

The research basis and product-specific claim boundary are documented in [pedagogy-evidence.md](pedagogy-evidence.md). Automated program tests establish engineering behavior, not learner benefit. Conversation evaluations and learner-outcome studies are separate evidence levels; see [evaluation.md](evaluation.md).

## Release acceptance criteria

- both Skills pass Skill Creator validation;
- the plugin passes Plugin Creator validation;
- curriculum identity, target closure, source provenance, scope, and DAG audit have no errors;
- state initialization, explicit scope closure, cross-task discovery, serialized writes, interrupted-transaction recovery, derived-state recovery, conservative migration, strict durability transition, failure transition, due-review query, export, and confirmed deletion pass automated tests;
- unfinished generated tools, incomplete lesson sequences, and placeholder checks fail; static validation never executes generated code; only separately observed sandbox/render results can mark a tool verified;
- README and `INSTALL.md` classify the distribution as one two-Skill plugin before any command runs;
  platform installers validate both marketplace and plugin identities, never fall back to a partial
  standalone-Skill install, and the exact release archive passes a fresh-clone smoke test before a
  separate Codex installation check;
- at least one cold-start, one single-reply personalized onboarding, and one cross-task resume conversation are manually evaluated for triggering, setup latency, answer leakage, overload, false mastery, preference boundaries, and workspace selection;
- a version-bound conversation-evaluation suite covers direct, indirect, follow-up, negative, and boundary requests; release evidence contains three uniquely identified complete runs, all declared critical cases pass every run, aggregate case pass rate is at least 90%, and each non-critical case passes at least two of three runs;
- any published behavior claim links to the validated release-evidence report and its synthetic transcript evidence; blocked, omitted, duplicate, or below-threshold runs cannot satisfy the tag gate;
- release artifacts are built from canonical LF text, compare byte-for-byte across Windows and Linux, and match canonical bytes from the tagged Git tree.
