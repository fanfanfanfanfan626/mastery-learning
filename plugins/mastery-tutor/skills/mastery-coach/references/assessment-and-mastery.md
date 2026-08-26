# Assessment and mastery protocol

## Evidence dimensions

- `recall`: retrieve facts, definitions, or procedures without cues;
- `conceptual`: explain mechanism, assumptions, and boundaries;
- `application`: use the idea in a representative task;
- `debugging`: diagnose and repair a plausible failure;
- `transfer`: use it when surface details or constraints change;
- `creation`: combine it into a new design, argument, or artifact.

Not every concept requires every dimension. Declare required dimensions in the curriculum or explicit custom-concept definition. Evidence may add observed dimensions but cannot replace or shrink the definition.

## Evidence hierarchy

Recognition and cued recall are weak evidence. Free recall, independent application, debugging, transfer, creation, and delayed performance are progressively stronger. Use weak evidence for diagnosis and feedback, not final mastery.

## Rubric rules

- Publish criteria before a substantial task.
- Score observable features, not writing polish unless communication is the target.
- Use deterministic tests for code outputs, types, invariants, and performance where practical.
- Let the AI judge reasoning only against an explicit rubric and cite the learner's evidence.
- If deterministic checks and AI judgment disagree, report it and do not silently pass.
- Keep confidence separate from score.
- Honor a `no formal checks for now` preference by gathering independent work through natural
  explanations, code reviews, projects, debugging, or teach-backs. If the learner declines all
  independent checks, continue teaching but leave mastery unverified.

## Mastery states

- `unassessed`: no meaningful evidence;
- `emerging`: can recognize or follow;
- `developing`: can perform with support;
- `provisional`: immediate independent success, not yet durable;
- `mastered`: every required dimension has passing independent evidence, plus passing independent delayed retrieval and passing independent transfer/project evidence;
- `fragile`: previously mastered but recent retrieval failed.

Default mastery requires 0.75 in every required dimension, at least three meaningful evidence events, passing independent evidence in every required dimension, a passing independent retrieval at least 12 hours after prior concept evidence, and a separate passing independent transfer or project event that actually carries the `transfer` dimension. Evidence kinds have semantic minimum dimensions; labels alone cannot satisfy durability. Assisted, hinted, unknown-legacy, low-scoring, same-session, or self-reported work cannot satisfy durable evidence. After mastery, any recall/review below 0.75—or any retrieval that needed assistance or hints—changes the state to `fragile`. Assisted success cannot clear `fragile`; require a new passing independent delayed retrieval. Raise the threshold or delay for high-stakes work.

## Question quality audit

Check that every question maps to an outcome, does not leak the answer, cannot pass by guessing alone, avoids irrelevant difficulty, has a defensible rubric, and differs enough from the example to test transfer.

## Review scheduling

Schedule the first review near one day after initial meaningful evidence. Advance through intervals near 1, 3, 7, 14, 30, and 60 days only after independent `recall` or `review` evidence performed on or after the current due time. Same-session explanations, exercises, diagnostics, and early reviews do not advance the interval. Reset or shorten after failure or assisted retrieval.

Choose the review form from the knowledge and error:

- use uncued reconstruction and successive relearning for durable availability;
- use Feynman-style teach-back for a causal explanation, then separately test changed-context use;
- use contrasting cases or interleaving only after the component concepts are individually usable;
- use debugging, design defense, or project review when authentic selection and integration matter;
- vary surface cues without changing the declared concept requirement.

A teach-back can support the `conceptual` or `explain` dimension when it is the learner's own work,
but it cannot by itself satisfy delayed retrieval, transfer, or creation. The bundled engine is
deliberately conservative and simpler than a personalized FSRS optimizer until enough review data
exists. See [method-repertoire.md](method-repertoire.md) for method triggers and stop rules.
