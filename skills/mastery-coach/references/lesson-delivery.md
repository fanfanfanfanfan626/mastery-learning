# Guided lesson delivery contract

Use this contract for a substantial first encounter with a concept. The shared HTML classroom is
the learner-facing interface for every turn. A verified lesson artifact may supply executable
interaction, but it never owns planning, feedback, evidence, or mastery.

## Establish the learning boundary

Name exactly one **current target** whose prerequisites are either observed or modeled in this
lesson. Label motivating later ideas as a **preview**. A preview may create orientation and
interest, but it cannot produce evidence for the previewed concept or silently bypass its
prerequisites.

For a learner starting from zero, do not require syntax, notation, or operations that were neither
self-positioned as usable nor modeled first. Self-positioning remains a hypothesis. Use a concrete
domain example early, but keep the recorded target honest. In ML/AI/LLM learning, establish the
AI-to-ML-to-deep-learning-to-LLM landscape and the learner's destination before introducing a
model-and-loss example. Loss answers “how wrong was the prediction?” and is meaningless as an
opening concept before prediction, data, and learned behavior have a purpose.

Use a **zero-baseline ladder** instead of compressing prerequisites into comments. For programming,
establish values, names and assignment, sequential execution, and visible output before requiring
collections, loops, functions, or library syntax, unless the learner has already positioned those
skills as usable. A motivating machine-learning example may appear early, but unfamiliar machinery
must be demonstrated rather than assigned. If the lesson would need more than one hidden rung,
move the current target down and keep the goal-domain idea as a preview.

## Size a complete micro-lesson

Use the learner's session budget. A normal **20–40 minute** lesson should provide enough activity
for orientation, modeling, manipulation, one guided attempt, and a close; do not inflate it with
an arbitrary word count. For shorter sessions, preserve the same causal spine and defer extension.

Use **progressive disclosure** so the core path stays scannable while derivations, terminology,
sources, and optional depth remain available. Introduce no more than 3–5 interacting new elements
before learner action.

## Compose the lesson

Use this sequence flexibly:

1. State the outcome, relevance to the learner's goal, estimated time, current target, and preview.
2. Start from a concrete situation or observable phenomenon.
3. Give the smallest mental model and define new terms.
4. Show one complete **worked example**, including intermediate states rather than only the answer.
5. When code is part of the outcome, provide **annotated code** that explains new syntax and causal
   decisions. Prefer explicit loops and named intermediate values before compact idioms.
6. Expose a synchronized visual, table, trace, or experiment when state changes matter.
7. Complete one step with the learner, then invite one coherent guided action.
8. Give feedback at the earliest causal error and fade support.
9. Add one changed-condition transfer challenge only after the base model is usable.
10. Close with the demonstrated target, unresolved uncertainty, and one next action.

Comments should explain purpose, state change, units, assumptions, and failure boundaries rather
than paraphrasing punctuation. Reduce comments and scaffolding after observed capability improves.

## Add executable interaction only when needed

The classroom is already HTML. Create or **reuse** a verified `lesson_lab` component when at least
one condition holds:

- the concept depends on a dynamic, spatial, stateful, or causal relationship;
- synchronized code, diagram, controls, and numeric state materially reduce hidden mental work;
- the planned lesson is substantial enough that a reusable page improves continuity.

Prefer the classroom's prose, comparison, steps, map, or annotated-code blocks when they are the
smallest adequate instrument. **Do not create** an executable lab for a one-off fact, a single local
correction, a tiny review prompt, or visual polish without a measurable learner action. Do not
rebuild a verified artifact that samples the same outcome and constraints.

When a `lesson_lab` is justified, invoke `$mastery-tool-creator` internally with the current target, preview,
learner starting assumptions, observable outcome, session budget, mode, required interaction, and
evidence boundary. Link it from an `artifact` classroom block. If generation or inspection cannot
complete honestly, continue in the no-script HTML classroom and report the missing interaction
without handing the learner a build command.

## Lesson lab content contract

A lesson lab must contain semantic sections for orientation, mental model, worked example,
interactive model, guided practice, transfer, and summary. Include an annotated-code section when
code appears. It must also provide:

- one prediction gate before reveal;
- 1–3 meaningful controls with visible state and assumptions;
- synchronized visual and text/table output;
- an explanation prompt and progressive hints;
- a changed-condition challenge;
- a linked keyboard-readable text/table equivalent;
- responsive layout, visible focus, reduced-motion support, and no remote runtime dependency.

Opening a page, moving a control, or copying an example is not mastery evidence. Record only an
observed learner explanation, calculation, code change, decision, or transfer attempt, with actual
assistance. Immediate guided success remains provisional.

## Avoid false completeness

Distinguish a full coverage map from the learner's required scope and today's active path. If a
selected profile closure omits a concept from the full pack, label that exclusion or enrichment
instead of calling the smaller route the complete curriculum. Do not call a forward-and-loss trace
a training loop unless gradient computation, parameter update, and repetition are actually shown.
