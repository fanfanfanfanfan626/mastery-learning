# Personalization protocol

## What to model

Keep the learner model small, explicit, and revisable:

- target capability and deadline;
- time budget and session length;
- verified prerequisite evidence;
- recurring misconceptions;
- effective hint level;
- preferred examples or domains;
- stated visual-density, color-scheme, text-size, or accessibility preference inside the mandatory HTML classroom;
- accessibility and environment constraints;
- engagement signals such as avoidance, flow, or fatigue;
- confidence for each inference and when it was last observed.

Do not infer sensitive traits that are unnecessary for teaching.

During onboarding, ask only relevant background and offer one revisable experience preset:
`guided`, `project`, `rigorous`, or `challenge`. Accept optional overrides for tone, outside-task
load, and formal-check frequency. Infer response depth and hint granularity during teaching unless
the learner explicitly specifies them. This keeps customization useful without turning setup into a
personality inventory. Store explicit choices as preferences or constraints. Store familiarity
labels only as low-confidence hypotheses; they are not evidence.

## What to adapt

- concept order within prerequisite constraints;
- amount of worked example versus independent practice;
- representation: verbal, visual, mathematical, code, or physical analogy;
- delivery medium and artifact reuse when it materially affects friction or comprehension;
- task authenticity and domain;
- difficulty and branching;
- hint granularity;
- session length and review load;
- capstone choice.
- tone and response density without changing factual directness;
- current teaching or review method, chosen from the objective and observed obstacle.

## What not to do

- Do not label a learner as a fixed visual, auditory, or kinesthetic type.
- Do not lower the outcome because performance is temporarily weak.
- Do not optimize for clicks, message count, praise, or streak preservation.
- Do not turn every preference into a permanent rule.
- Do not interpret a visual or layout preference as a fixed learning-style label or as permission to create decorative tools.
- Do not store raw conversation when a compact evidence summary is enough.
- Do not promise to discover one permanently optimal teaching style from a questionnaire.
- Do not confuse a friendly, direct, rigorous, or conversational tone with easier or harder mastery criteria.
- Do not force a named method because the learner selected a preset; presets describe experience, not a pedagogy algorithm.
- Do not equate `no formal exams for now` with verified mastery; teach normally and leave mastery unverified until acceptable independent evidence exists.

## Adaptation decision

For a material change, log:

1. observation;
2. competing explanations;
3. chosen adaptation;
4. confidence from 0 to 1;
5. what future evidence would confirm or reject it.

Example: “Two symbolic derivations failed, while the tensor-shape trace succeeded. Hypothesis: concrete execution traces currently reduce overload (0.65), not a permanent visual preference. Start the next optimizer lesson with an array trace, then retest symbolic transfer.”

## Engagement without manipulation

Use:

- meaningful choices between equivalent projects;
- visible movement from supported to independent performance;
- artifacts the learner owns;
- tasks near the edge of present competence;
- examples connected to the learner's stated goals;
- short sessions with an open loop for next time.

Treat streaks and points as optional displays, never as evidence or pressure.

Revisit onboarding choices after one or two sessions or when performance, fatigue, or engagement
disagrees with them. Honor explicit boundaries such as no homework by moving practice into the
session rather than silently dropping required practice. Select moment-to-moment techniques with
[method-repertoire.md](method-repertoire.md), and treat a failed method choice as a revisable tutor
hypothesis rather than a learner deficit.
