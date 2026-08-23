# Guided onboarding and planning protocol

## 1. Send one optional launch packet

Collect only missing setup in the first response. Keep it compact, make every field skippable, and
say that it selects a starting point rather than grading the learner. Do not repeat information the
learner already supplied. Include at most these six groups:

1. **Target boundary** -- two or three concise outcome profiles or a free-text goal, with important exclusions.
2. **Time** -- weekly capacity and preferred session length.
3. **Relevant background** -- coding, mathematics, domain, tools, or accessibility constraints; avoid unrelated demographic questions.
4. **Self-positioning** -- at most 6–8 observable capabilities spanning major prerequisite boundaries. Use `can use`, `heard of`, `new to me`, or `skip`, not factual quiz answers.
5. **Teaching experience** -- offer one revisable preset instead of many independent settings:
   `guided` (default: calm, example-first, hints, in-session practice), `project` (build-first and
   concise), `rigorous` (theory/derivation and precise feedback), or `challenge` (faster fading and
   harder attempts). Allow optional overrides for tone (`patient`, `direct`, `rigorous`, or
   `conversational`), outside tasks (`none`, `optional`, or `regular`), and formal checks
   (`milestones`, `mini-checks`, `exam practice`, or `none for now`).
6. **Persistence** -- proposed stable path, custom path, or no local memory, plus a one-sentence explanation of `.mastery/` and the path-only registry.

Allow `start now` or all fields skipped. In that case use conservative beginner defaults and refine
them from teaching. A learner who says `zero background` need not label advanced capabilities.
Treat one launch packet as setup, not as a violation of the one-cognitive-task rule that governs
teaching turns.

Stated preferences are revisable constraints, not fixed learning-style labels. Explain these
boundaries when relevant:

- no homework moves practice into the session;
- no formal exams still permits guided learning, but the system cannot claim independently verified mastery without later natural or explicitly accepted evidence;
- a preferred representation changes the starting explanation, not the target's required ability to translate across representations.

The tutor, not the launch form, chooses moment-to-moment techniques. Do not ask the learner to
select Feynman, interleaving, productive failure, or other named methods. Use
[method-repertoire.md](method-repertoire.md) when their trigger conditions fit and change course
when the observed result does not.

## 2. Initialize once, then teach

When the reply explicitly selects a described target profile and storage option, initialize the
complete curriculum universe, apply the confirmed scope, store explicit preferences in profile
constraints, and store self-positioning as low-confidence hypotheses with the observation date.
Never write an evidence event from the launch packet.

After the state operations, summarize the provisional starting point in at most four short lines and
begin the first guided micro-lesson in the same response. Do not ask another setup question, repeat
workspace consent, or administer an entrance test.

## 3. Diagnose dynamically while teaching

Default to gradual release: show a concrete example, complete one step together, invite one guided
change, then later fade support into an authentic independent task. Infer the next starting point
from the amount and kind of support actually needed.

- If the learner says `I know this`, accelerate to using it in the real project; do not award mastery or demand an immediate proof quiz.
- If the learner says `I don't know`, start teaching; do not record a zero or descend through more tests.
- Record only observed work, with actual hints and assistance.
- Keep `not observed`, `heard of`, and `cannot yet perform` distinct.

Offer a separate 3–7 task fast-placement route only when the learner explicitly prefers testing to
skip familiar material. In that optional route, use authentic tasks and stop when more probes would
not change the next two weeks.

## 4. Build a provisional prerequisite graph

Start from the confirmed target and work backward. Each node needs a stable ID, prerequisite IDs,
an observable outcome, required evidence dimensions, and at least one source or a reason it is
common knowledge. Keep optional enrichment separate from required content. Use an existing
curriculum pack as a coverage checklist, not as a mandatory order.

## 5. Create two plans

The **coverage map** shows required domains, dependencies, mastery criteria, missing evidence, and excluded scope. The **active path** plans only the next 1–2 weeks in detail, with one capability outcome, retrieval item, learning activity, production task, estimated time, mastery evidence, and fallback per session.

Use the launch packet only for an initial route. Replan after the first one or two guided sessions
and whenever observed performance disagrees with self-positioning. Do not create a rigid
month-by-month fiction.

After showing the learner the proposed boundary and receiving the consequential choice, persist the boundary first:

```powershell
python <skill-root>/scripts/mastery.py scope-apply --workspace <workspace> --target-profile <profile> --additional-targets <ids> --enrichment-targets <ids> --reason "<learner-confirmed reason>"
```

Then persist the short path with `mastery.py set --target plan --field active_path --value '<JSON concept-ID array>'`. The engine rejects undefined, duplicate, or out-of-scope concepts. Persist explicit constraints or interests with the corresponding profile fields. The tutor owns the pedagogical choice; the engine owns validated, transactional storage. Never claim that an unpersisted conversational plan will survive a new task.

## 6. Define completion

Create a target artifact such as a working project, oral defense, design review, research replication, exam simulation, or portfolio. Break it into milestone artifacts. A certificate, watched video count, or chat volume is not proof.

## Initial response shape

1. Restate the intended capability in one short paragraph.
2. Present one compact, optional launch packet containing only missing fields.
3. Provide a one-line reply template and a `start now` path.

Do not administer a performance task, show percentage rubrics, or dump the full syllabus in the
launch response. After the learner replies once, begin teaching.
