# Product specification

## First-principles objective

The final outcome of learning is an independently usable capability. Therefore the product optimizes for evidence of retrieval, explanation, application, debugging, transfer, and creation—not time spent, pages read, answer fluency, or course completion.

## Required product behavior

1. Translate a vague aspiration into an observable capability and proof artifact.
2. Estimate the smallest set of prerequisites that changes the near-term plan from background and skippable self-positioning, then refine it through guided work rather than an entrance exam.
3. Maintain a complete, versioned, sourced coverage graph, a learner-confirmed prerequisite-closed scope, and a short adaptive active path.
4. Teach through active, turn-based interaction rather than monologue. For a beginner, create one
   concrete experience before naming an abstraction, reveal a limitation or contrast, then guide
   one use of the newly named idea. Preserve one complete causal spine while keeping future ideas
   and the full field map optional or labeled as previews.
5. Render every learner-facing turn in one polished, accessible, local HTML classroom. Generate
   executable tools only where they make a relationship or performance observable.
6. Give feedback at the earliest causal error and allow retries.
7. Require independent and durable evidence before mastery.
8. Schedule retrieval and changed-context review.
9. Keep the learner model small, local, inspectable, and revisable.
10. Separate proposed product improvements from automatic session adaptation.
11. Keep teaching behavior host-neutral: host adapters may narrow unavailable tools but may not
    change mastery, privacy, source, answer-leakage, inspection, or deletion rules.
12. Distinguish package conformance, host behavior, and learner outcomes in every support claim.

## Personalization

Personalization starts with one lightweight, revisable experience preset plus optional tone, outside-task, and formal-check overrides. It changes sequence, examples, representations, hint size, difficulty, interaction method, response density, session length, review load, and capstone choice. The AI selects techniques such as worked-example fading, Feynman-style teach-back, contrasting cases, interleaving, or productive failure only when their trigger conditions fit, and keeps a fallback. It is based on observed performance plus user constraints. The system does not assign fixed learning-style labels, make tone change the mastery standard, or infer unrelated sensitive traits.

## Interest and motivation

The system uses meaningful choice, authentic artifacts, visible independence, relevant projects, and frontier-level challenges. Streaks or points may be displayed only as optional information; they do not affect mastery and must not pressure the learner.

## Completeness

Completeness means every target outcome has prerequisite support, sources, boundary/failure cases, and an assessment route. It does not mean every learner must study every node. The complete universe remains auditable; a confirmed target profile and explicit targets derive the required closure. Optional enrichment, unselected concepts, and explicit domain exclusions remain distinct.

For ML/AI/LLM learning, the built-in pack covers computing, mathematics, classical AI search/planning/knowledge representation/sequential decisions, data/experimentation, classical ML, ML production, deep learning, transformers/foundation models, LLM applications, evaluation/safety/production, and research practice. Advanced robotics/control, domain-specialist vision/speech, custom accelerators, and formal certification remain explicit exclusions unless a new target pack adds them.

## Minimum viable user journey

1. Learner states a target to the installed AI tutor.
2. The tutor renders and opens one compact HTML launch card covering the missing goal, time, relevant background, self-positioning, teaching experience, and local-persistence choices.
3. After one reply, the tutor initializes `.mastery/`, stores preferences and self-positioning without calling them evidence, updates the HTML classroom with the provisional short path and coverage boundary, and begins guided orientation without another setup round.
4. Each session retrieves prior or due learning when relevant, models genuinely new material before demanding performance, teaches one frontier capability, and ends with one clear next action.
5. Every explanation, question, feedback turn, review, and close is rendered in the shared classroom. A verified `lesson_lab` or code/visual tool is linked only when executable interaction is justified.
6. Evidence updates mastery and review dates.
7. A capstone and defense verify integrated capability.

For the built-in ML/AI/LLM map, a learner without prior evidence begins inside `ai-landscape`, but
does not receive the whole taxonomy as the first lesson. The first turn starts with one familiar
problem, asks for a prediction, makes the limitation of a hand-written rule visible, and only then
names learning from examples as machine learning. AI, deep learning, foundation models, and LLMs
enter later as an optional roadmap and synthesis. Prediction precedes error, error precedes loss,
and loss precedes optimization. A taxonomy or convenient worksheet must never determine the
conceptual starting point.

## Non-goals for the initial release

- hosted LMS, cohort management, certificates, grades, or surveillance analytics;
- a fixed video/content library;
- a hosted general-purpose website or LMS; the local HTML classroom is a teaching surface owned by the AI session;
- automatic claims of pedagogical effectiveness without learner-outcome evaluation;
- silent self-modification.

The research basis and product-specific claim boundary are documented in [pedagogy-evidence.md](pedagogy-evidence.md). Automated program tests establish engineering behavior, not learner benefit. Conversation evaluations and learner-outcome studies are separate evidence levels; see [evaluation.md](evaluation.md).

## Release acceptance criteria

- both Skills pass Skill Creator validation;
- the generated Codex adapter passes Plugin Creator validation;
- curriculum identity, target closure, source provenance, scope, and DAG audit have no errors;
- state initialization, explicit scope closure, cross-task discovery, serialized writes, interrupted-transaction recovery, derived-state recovery, conservative migration, strict durability transition, failure transition, due-review query, export, and confirmed deletion pass automated tests;
- unfinished generated tools, incomplete lesson sequences, and placeholder checks fail; static validation never executes generated code; only separately observed sandbox/render results can mark a tool verified;
- the deterministic classroom renderer escapes learner content, rejects unsafe links, uses a local-only no-script CSP, exposes exactly one current action, and never requires learner-operated servers or internal Skill commands;
- a beginner classroom puts the concrete problem and current action in the initial viewport, uses
  real accessible controls for choices, introduces no more than three new terms per turn, and does
  not use a glossary or taxonomy dump as the opening lesson;
- the dedicated no-cache classroom server exposes only the current page and shared stylesheet from `.mastery/classroom`; learning profiles, plans, evidence, reviews, registries, and tools are never within its served root;
- all local servers use OS-assigned loopback ports, retain an exact process/session identity, and are considered stopped only after the assigned port is verified closed;
- tool objectives, sources, resource links, paths, and check commands are untrusted: HTML is escaped, remote references are credential-free HTTPS, check targets remain inside the tool snapshot, and links/junctions/reparse points fail closed;
- README and `AGENT_INSTALL.md` classify the distribution as one portable two-Skill system before
  any command runs; the generic installer verifies both canonical trees and the Codex installer
  validates marketplace and plugin identities. Neither path may fall back to a partial install, and
  the exact release archive passes a fresh-clone smoke test before host-specific installation checks;
- at least one cold-start, one single-reply personalized onboarding, and one cross-task resume conversation are manually evaluated for triggering, setup latency, answer leakage, overload, false mastery, preference boundaries, and workspace selection;
- a version-bound conversation-evaluation suite covers direct, indirect, follow-up, negative, and boundary requests; release evidence contains three uniquely identified complete runs, all declared critical cases pass every run, aggregate case pass rate is at least 90%, and each non-critical case passes at least two of three runs;
- any published behavior claim links to the validated release-evidence report and its synthetic transcript evidence; blocked, omitted, duplicate, or below-threshold runs cannot satisfy the tag gate;
- release artifacts are built from canonical LF text, compare byte-for-byte across Windows and Linux, and match canonical bytes from the tagged Git tree.
