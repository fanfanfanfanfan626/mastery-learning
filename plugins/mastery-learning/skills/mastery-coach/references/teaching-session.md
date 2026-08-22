# Teaching session protocol

## Choose the next concept

Order candidates by overdue review, blocking prerequisite, value for the target artifact, weak or uncertain mastery, and opportunity for useful interleaving. Do not advance merely because a lesson was consumed.

## Compose a micro-lesson

Use this sequence, typically across several chat turns:

1. Retrieval from prior learning or a prerequisite.
2. Prediction about a scenario.
3. One concrete example, diagram, trace, or experiment.
4. A causal mechanism connecting the observations.
5. The notation or code now needed.
6. One failure case, counterexample, or trade-off.
7. A guided learner attempt.
8. A changed-context independent attempt.
9. A teach-back of the mechanism and its boundary.

The explanation before the first learner action should normally fit on one screen.

## Feedback model

Classify the response as correct and grounded, correct but fragile, locally incorrect, wrong mental model, missing prerequisite, execution slip, or ambiguous. Then state what is demonstrated, the earliest gap, one hint or correction, and one retry prompt. Do not bury the next action under a lecture.

## Multiple representations

Move deliberately among concrete instance, visual model, verbal cause, mathematical notation, executable code, and system trade-off. Ask the learner to translate between at least two. Translation is stronger evidence than recognition inside one representation.

## Manage cognitive load

- Chunk no more than 3–5 new interacting elements before an attempt.
- Externalize long derivations on a blackboard block and preserve intermediate states.
- Give a worked example only when no usable schema exists; fade steps in the next example.
- Reuse terminology consistently and define symbols at first use.

## End a session

Ask one exit task that samples the target outcome, record the result, then call `session-close` with a stable caller-generated `--session-id`, demonstrated capability, unresolved uncertainty, next action, and any review time. Reuse that ID only for an exact retry. State the same compact handoff to the learner. Do not store a full transcript.
