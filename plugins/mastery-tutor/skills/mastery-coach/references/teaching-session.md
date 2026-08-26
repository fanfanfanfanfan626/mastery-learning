# Teaching session protocol

## Choose the next concept

Order candidates by overdue review, blocking prerequisite, value for the target artifact, weak or uncertain mastery, and opportunity for useful interleaving. Do not advance merely because a lesson was consumed.

## Compose a micro-lesson

For a genuinely new concept, begin with a concrete model and gradual release; do not demand
retrieval of content that has not been taught. For prior learning or a due review, retrieve first.
For a substantial first encounter or an explicitly requested interactive lesson, also follow
[lesson-delivery.md](lesson-delivery.md). Name one current evidence target and label any later idea
shown for motivation as a preview; never score the preview as if its prerequisites were complete.
For a novice or an unencountered concept, also apply
[novice-first-teaching.md](novice-first-teaching.md): meet a concrete experience before terminology,
use one mental move, and limit the turn to at most three new terms.
Use this sequence flexibly across several HTML classroom turns:

1. Orientation to one useful outcome.
2. Retrieval from actual prior learning when relevant; otherwise one concrete example, diagram, trace, or experiment.
3. One complete worked example with intermediate state, followed by a shared step with visible decisions.
4. A causal mechanism connecting the observations.
5. The notation or code now needed.
6. One failure case, counterexample, or trade-off.
7. A guided learner attempt.
8. A changed-context independent attempt.
9. One suitable consolidation or transfer move selected from
   [method-repertoire.md](method-repertoire.md), such as a teach-back, contrasting case, debug task,
   or changed-context application.

The explanation before the first learner action should normally fit on one screen.

Fit the whole activity to the stated session budget. A 20–40 minute lesson needs enough modeled,
interactive, and guided work to fill that period; it should not collapse into a paragraph followed
by several worksheet questions. Use progressive disclosure in the classroom or a verified
`lesson_lab` component when dynamic interaction reduces hidden mental work.

Do not display percentage scoring, prohibit tools, or frame ordinary guided work as an exam. Keep
the rubric stable internally and expose detailed criteria for milestone checks, exam mode, or when
the learner needs them to act.

## Feedback model

Classify the response as correct and grounded, correct but fragile, locally incorrect, wrong mental model, missing prerequisite, execution slip, or ambiguous. Then render the earliest useful teaching move and one next action in the updated classroom. Do not narrate routine evidence bookkeeping. If the learner says they do not know, teach the missing model before requesting another attempt. Do not bury the next action under a lecture.

## Multiple representations

Move deliberately among concrete instance, visual model, verbal cause, mathematical notation, executable code, and system trade-off. Ask the learner to translate between at least two. Translation is stronger evidence than recognition inside one representation.
For a new abstraction, the first usable model includes an example, a close counterexample, and a
visual that exposes their deciding difference; all three support the same action.

## Manage cognitive load

- Chunk no more than 3–5 interacting elements before an attempt; for a beginner, at most three of
  them may be new terms.
- Externalize long derivations on a blackboard block and preserve intermediate states.
- Give a worked example only when no usable schema exists; fade steps in the next example.
- Do not require code syntax, notation, or operations that were neither observed as usable nor modeled in the lesson. Expand beginner code and annotate new state changes before introducing compact idioms.
- Reuse terminology consistently and define symbols at first use.
- Switch methods when the learner's errors, energy, or accessibility needs show that the current
  method is not creating a usable model; do not simply make the same task longer.

## End a session

Ask one exit task that samples the target outcome, record the result, then call `session-close` with a stable caller-generated `--session-id`, demonstrated capability, unresolved uncertainty, next action, and any review time. Reuse that ID only for an exact retry. State the same compact handoff to the learner. Do not store a full transcript.
