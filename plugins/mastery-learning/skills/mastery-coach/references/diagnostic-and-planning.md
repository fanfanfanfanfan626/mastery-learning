# Diagnostic and planning protocol

## 1. Convert the request into a capability target

Capture target performance, context, time horizon, weekly capacity, constraints, and the artifact or performance that will prove completion. If the goal is vague, ask the single question that most changes the path. Prefer “What would you like to be able to build or explain?” over “What is your learning style?”

## 2. Build a provisional prerequisite graph

Start from the target and work backward. Each node needs a stable ID, prerequisite IDs, an observable outcome, required evidence dimensions, and at least one source or a reason it is common knowledge. Keep optional enrichment separate from required content.

Use an existing curriculum pack as a coverage checklist when available. Do not assume its order fits the learner.

Initialize the complete curriculum universe without pretending every node is required. After diagnostic evidence, recommend one or more target profiles plus any explicit goal concepts. Show the resulting prerequisite closure, important exclusions, and target artifact; ask for confirmation before persisting it with `scope-apply`. Do not infer or confirm a target profile from keywords alone.

## 3. Sample diagnostic evidence

After the goal boundary and durable workspace are agreed, explain the local files and initialize state before administering diagnostic tasks that should persist. If the learner declines persistence, diagnose conversationally and do not claim cross-task memory. Record each observed diagnostic after the response; never invent backfilled performance.

Use 3–7 short tasks spanning the graph. Prefer tasks that discriminate multiple levels:

- explain a mechanism in the learner's own words;
- predict a result before running code;
- repair a small bug;
- solve a representative calculation;
- compare two approaches and choose under constraints;
- sketch a small system or experiment.

Stop when additional questions are unlikely to change the first two weeks. Record uncertainty; “not tested” differs from “does not know.”

## 4. Create two plans

The **coverage map** shows required domains, dependencies, mastery criteria, missing evidence, and excluded scope. The **active path** plans only the next 1–2 weeks in detail, with one capability outcome, retrieval item, learning activity, production task, estimated time, mastery evidence, and fallback per session.

Replan after new evidence. Do not create a rigid month-by-month fiction.

After showing the learner the proposed boundary and receiving the consequential choice, persist the boundary first:

```powershell
python <skill-root>/scripts/mastery.py scope-apply --workspace <workspace> --target-profile <profile> --additional-targets <ids> --enrichment-targets <ids> --reason "<learner-confirmed reason>"
```

Then persist the short path with `mastery.py set --target plan --field active_path --value '<JSON concept-ID array>'`. The engine rejects undefined, duplicate, or out-of-scope concepts. Persist explicit constraints or interests with the corresponding profile fields. The tutor owns the pedagogical choice; the engine owns validated, transactional storage. Never claim that an unpersisted conversational plan will survive a new task.

## 5. Define completion

Create a target artifact such as a working project, oral defense, design review, research replication, exam simulation, or portfolio. Break it into milestone artifacts. A certificate, watched video count, or chat volume is not proof.

## Initial response shape

1. Restate the inferred capability target.
2. Name the key uncertainty.
3. Ask one diagnostic task.

Do not show the entire syllabus until the first evidence is available unless the learner explicitly requests it.
