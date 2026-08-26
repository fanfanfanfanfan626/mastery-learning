# HTML classroom delivery contract

The classroom is the learner-facing surface for every active Mastery Coach turn. Chat remains the
transport for learner replies and a minimal “classroom updated/opened” handoff; it must not carry a
second Markdown lesson, setup instructions, internal paths, validation logs, or server commands.

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
   `meta`, 1–16 semantic `sections`, and exactly one `action`.
2. For an agreed learner workspace, render to `<workspace>/.mastery/classroom/index.html`. Before
   workspace selection, render the launch packet to a task-local temporary output directory; do not
   initialize durable learner state merely to display onboarding.
3. Start the bundled `scripts/serve_classroom.py --root <serve_root> --port 0`; do not use a generic
   file server and never serve `.mastery` itself. Read its one-line JSON for the assigned URL, port,
   and PID. The allowlisted server exposes only the classroom page and stylesheet, disables caches,
   and cannot expose profile, evidence, plans, registries, or sibling tools.
4. Open the returned URL with the available browser capability. On later turns update the same page
   and refresh it. At lesson/session close, stop the exact recorded process/session and verify that
   its assigned port is closed. Do not assume that sending `Ctrl+C` succeeded.
5. In chat, say only that the classroom is ready or updated, provide a clickable page link when the
   surface supports it, and ask the learner to respond in chat after the single highlighted action.

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

## Interaction boundary

The HTML page may show the full explanation needed for the present step, but it must highlight
exactly one learner action. The learner replies through the AI conversation unless a verified local
tool has a governed input channel. Never ask the learner to run a server, type a shell command,
stop a process, locate internal files, invoke the sibling Skill, or paste a long auto-generated
“submission summary.”

Page views, scrolling, clicks, and generated summaries are not evidence. The Coach must observe an
attributable learner explanation, calculation, decision, code change, or transfer attempt before
recording evidence.

## Durable-content boundary

The classroom page is a current presentation surface, not a raw transcript archive. Overwrite it as
the lesson advances. Persist only compact evidence/session handoffs and reusable, learner-neutral
lesson or reference artifacts. Do not store the learner's full conversation merely because HTML
rendering makes that easy.
