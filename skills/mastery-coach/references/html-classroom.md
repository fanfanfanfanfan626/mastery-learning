# HTML classroom delivery contract

The classroom is the learner-facing surface for every active Mastery Coach turn. Its local form is
the primary input surface; chat carries only a minimal “classroom updated/opened” handoff and a
short return signal after submission. Chat must not carry a second Markdown lesson, setup
instructions, internal paths, validation logs, or server commands.

Read [teacher-voice.md](teacher-voice.md) before composing visible copy. Internal teaching and state
objects are not learner-facing prose.

## Separate display from executable teaching tools

Use the bundled `scripts/render_classroom.py` for ordinary onboarding, orientation, explanation,
feedback, review, and session-close pages. It renders a strict structured JSON specification into a
shared, no-script HTML shell with local CSS. The current page may change on every turn without
claiming that a generated executable tool remains verified.

Use `$mastery-tool-creator` only for an interaction whose causal behavior needs JavaScript, code,
simulation, a notebook, or another executable/reusable artifact. Link that verified artifact from
an `artifact` classroom block. Tool verification and learner evidence remain separate from classroom
rendering.

## Render every teaching turn

Before sending learner-facing teaching content:

1. Build one JSON spec with `schema_version`, `page_id`, `kind`, `eyebrow`, `title`, `lead`, optional
   `meta`, 1–16 semantic `sections`, and exactly one `action`. Orientation, lesson, feedback, and
   review pages must embed the current machine-readable `TeachingTurnSpec` as `teaching_turn`; the
   renderer validates its term budget, single mental move, shared deciding feature, evidence limits,
   feedback plan, and exact binding to `action.prompt`, then binds its hash into the HTML.
   A `feedback` page must also include `feedback_context` with the original task, attributable
   learner response, earliest causal error, current hint and level, and whether a full solution was
   revealed. The renderer rejects feedback that drops this context or claims a revealed solution
   below hint level 5. Give onboarding choice groups one recommended default each. Add
   `action.response` when the inferred control is not appropriate; use `submit-only` for onboarding
   choices, `choice` for a finite answer, and `short-text` or `long-text` for learner-produced
   reasoning.
2. For an agreed learner workspace, render to `<workspace>/.mastery/classroom/index.html`. Before
   workspace selection, render the launch packet to a task-local temporary output directory; do not
   initialize durable learner state merely to display onboarding.
3. Start the bundled `scripts/serve_classroom.py --root <serve_root> --port 0`; do not use a generic
   file server and never serve `.mastery` itself. Read its one-line JSON for the assigned URL, port,
   and PID. The allowlisted server exposes only the classroom page and stylesheet, disables caches,
   accepts one nonce-bound same-origin form at `/respond`, and cannot expose profile, evidence,
   plans, registries, response files, or sibling tools.
4. Open the returned URL with the available browser capability. On later turns update the same page
   and refresh it. At lesson/session close, stop the exact recorded process/session and verify that
   its assigned port is closed. Do not assume that sending `Ctrl+C` succeeded.
5. After the learner submits and returns, run `serve_classroom.py --root <serve_root>
   --consume-response --page-id <page_id>`. Interpret only a response whose page and contract match;
   consumption deletes the transient packet. In chat, use one natural sentence with the classroom
   link or open status and ask the learner to return after submitting. Do not narrate rendering,
   validation, state writes, server lifecycle, or Skill routing.

If automatic browser control is unavailable, still generate the HTML and provide its clickable
local file or loopback link. Do not replace the learning content with Markdown. If neither local
file creation nor an HTML-capable surface exists, report the platform limitation before teaching;
do not claim the HTML-first experience was delivered.

## Page composition

Make the page visually consistent rather than designing a new theme each turn. Use the bundled
classroom stylesheet and the renderer's semantic blocks:

- `prose` for short connected explanations;
- `callout` for one concept, example, caution, or insight;
- `steps` for a causal or procedural sequence;
- `comparison` for exact mappings and distinctions;
- `code` for an annotated complete example;
- `map` for orientation, hierarchy, or a learning journey;
- `choices` for a compact, single-response onboarding form;
- `details` for optional depth that should not push the current action below the fold;
- `artifact` for a verified local lab or lesson component served separately on its own assigned
  loopback port. Link its exact verified `http://127.0.0.1:<port>/...` URL, never a `../tools` path.

Keep a strong hierarchy, generous whitespace, readable line length, responsive layout, dark-mode
support, visible focus, reduced motion, printable output, and a strict local-only CSP. Do not add
decorative animation, remote fonts, trackers, or visual density that competes with the current task.

Order the page by teaching state. Onboarding shows its choices before the unified reply action.
Orientation and lesson pages show the concrete model, example, close counterexample, and visual
distinction before the action. Feedback keeps the preserved attempt and current hint at the top;
review may put the retrieval prompt first because the model is intentionally withheld. Optional
`details` follow the action so extra depth cannot turn a guided attempt back into a lecture.

## Interaction boundary

The HTML page may show the full explanation needed for the present step, but it must highlight
exactly one learner action. The shared classroom posts bounded radio/text fields to its loopback
server without JavaScript. The learner then gives only a short return signal in the AI conversation;
the Coach consumes the bound packet and never guesses from an ambiguous “done”. A separately
verified tool may use its own governed input channel. Never ask the learner to run a server, type a shell command,
stop a process, locate internal files, invoke the sibling Skill, or paste a long auto-generated
“submission summary.”

Page views, scrolling, and default selections are not evidence. Submitted self-positioning remains
a preference or hypothesis. A submitted teaching response is attributable learner work, but the
Coach must inspect its explanation, calculation, decision, code change, or transfer attempt before
recording evidence.

Feedback must be self-contained. Never replace the original situation with an ordinal reference
such as “retry step 1” or “fix the second part.” Preserve the exact task and learner response beside
the smallest useful hint, then ask one complete retry question. Hint levels 1–4 must leave the
target production to the learner; level 5 may explain a full solution only after failed retries or
an explicit request, and must be labeled as assisted learning rather than independent evidence.
When the `TeachingTurnSpec` declares finite `answer_options`, the renderer rejects those values in
feedback hints and response-format examples below level 5.

## Durable-content boundary

The classroom page is a current presentation surface, not a raw transcript archive. Overwrite it as
the lesson advances. Persist only compact evidence/session handoffs and reusable, learner-neutral
lesson or reference artifacts. The server stores at most one size-bounded transient response packet;
consume and delete it before updating the page. Do not store the learner's full conversation merely
because HTML rendering makes that easy.
