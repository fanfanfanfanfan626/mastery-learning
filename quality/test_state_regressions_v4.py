from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COACH = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-coach"
STATE = COACH / "scripts" / "mastery.py"
CURRICULUM = COACH / "assets" / "curricula" / "ml-ai-llm.json"
TEST_RUNTIME = ROOT / "work" / "test-runtime-v4"


def environment() -> dict[str, str]:
    return {**os.environ, "MASTERY_HOME": str(TEST_RUNTIME / "registry"), "PYTHONUTF8": "1"}


def run(*args: str | Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *map(str, args)], cwd=ROOT, text=True, encoding="utf-8",
        capture_output=True, check=False, env=environment(),
    )
    if result.returncode != expect:
        raise AssertionError(
            f"Expected exit {expect}, got {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def record(
    workspace: Path,
    concept: str,
    kind: str,
    score: str,
    occurred_at: str,
    dimensions: str,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return run(
        STATE, "record", "--workspace", workspace, "--concept", concept, "--kind", kind,
        "--score", score, "--occurred-at", occurred_at, "--dimensions", dimensions,
        "--required", "recall,conceptual,application", *extra,
    )


def seed_mastery(workspace: Path, concept: str = "durable") -> None:
    run(STATE, "init", "--workspace", workspace, "--goal", "Durable mastery regression")
    for kind, stamp, dimensions, extra in [
        ("explain", "2026-08-01T09:00:00+00:00", "conceptual", ()),
        ("exercise", "2026-08-01T10:00:00+00:00", "application", ()),
        ("transfer", "2026-08-01T11:00:00+00:00", "transfer,conceptual", ()),
        ("review", "2026-08-02T12:00:00+00:00", "recall", ("--delayed",)),
    ]:
        record(workspace, concept, kind, "0.95", stamp, dimensions, *extra)


def write_legacy_workspace(workspace: Path, events: list[dict[str, object]]) -> Path:
    root = workspace / ".mastery"
    root.mkdir(parents=True)
    (root / "profile.json").write_text(json.dumps({
        "schema_version": 1,
        "created_at": "2026-08-01T08:00:00+00:00",
        "goal": "Legacy migration regression",
        "hours_per_week": 5,
        "session_minutes": 45,
    }), encoding="utf-8")
    (root / "plan.json").write_text(json.dumps({
        "schema_version": 1,
        "status": "diagnostic",
        "active_path": [],
        "excluded_scope": [],
        "open_questions": [],
    }), encoding="utf-8")
    (root / "sources.json").write_text(json.dumps({"schema_version": 1, "sources": []}), encoding="utf-8")
    (root / "mastery.json").write_text(json.dumps({
        "schema_version": 1,
        "concepts": {"legacy-concept": {
            "title": "Legacy Concept",
            "required_dimensions": ["recall", "conceptual", "application"],
        }},
    }), encoding="utf-8")
    (root / "reviews.json").write_text(json.dumps({"schema_version": 1, "concepts": {}}), encoding="utf-8")
    (root / "evidence.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    return root


class StateRegressionV4Tests(unittest.TestCase):
    def test_recent_retrieval_below_pass_threshold_makes_mastery_fragile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            seed_mastery(workspace)
            record(workspace, "durable", "review", "0.70", "2026-08-03T13:00:00+00:00", "recall", "--delayed")
            status = json.loads(run(STATE, "status", "--workspace", workspace, "--json").stdout)
            self.assertEqual(status["concepts"][0]["status"], "fragile")

    def test_force_repair_preserves_omitted_profile_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(
                STATE, "init", "--workspace", workspace, "--goal", "Preserve my plan",
                "--hours-per-week", "2.5", "--session-minutes", "30", "--deadline", "2026-12-31",
            )
            run(STATE, "init", "--workspace", workspace, "--goal", "Preserve my plan", "--force")
            profile = json.loads((workspace / ".mastery" / "profile.json").read_text(encoding="utf-8"))
            self.assertEqual(profile["hours_per_week"], 2.5)
            self.assertEqual(profile["session_minutes"], 30)
            self.assertEqual(profile["deadline"], "2026-12-31")

    def test_legacy_unknown_independence_cannot_create_mastery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "legacy"
            events = [
                {"timestamp": "2026-08-01T09:00:00+00:00", "concept": "legacy-concept", "kind": "explain", "score": 0.95, "difficulty": 3},
                {"timestamp": "2026-08-01T10:00:00+00:00", "concept": "legacy-concept", "kind": "exercise", "score": 0.95, "difficulty": 3},
                {"timestamp": "2026-08-01T11:00:00+00:00", "concept": "legacy-concept", "kind": "transfer", "score": 0.95, "difficulty": 3},
                {"timestamp": "2026-08-02T12:00:00+00:00", "concept": "legacy-concept", "kind": "review", "score": 0.95, "difficulty": 3, "delayed": True},
            ]
            root = write_legacy_workspace(workspace, events)
            run(STATE, "migrate", "--workspace", workspace, "--backup", workspace / "backup.zip")
            migrated = [json.loads(line) for line in (root / "evidence.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all(not event["independent"] for event in migrated))
            status = json.loads(run(STATE, "status", "--workspace", workspace, "--json").stdout)
            self.assertNotEqual(status["concepts"][0]["status"], "mastered")

    def test_migration_rejects_future_events_before_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "legacy"
            root = write_legacy_workspace(workspace, [{
                "timestamp": "2099-01-01T09:00:00+00:00",
                "concept": "legacy-concept",
                "kind": "exercise",
                "score": 0.9,
                "difficulty": 3,
            }])
            run(STATE, "migrate", "--workspace", workspace, "--backup", workspace / "backup.zip", expect=1)
            profile = json.loads((root / "profile.json").read_text(encoding="utf-8"))
            self.assertEqual(profile["schema_version"], 1)

    def test_corrupt_session_log_fails_validation_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Trustworthy resume")
            run(
                STATE, "session-close", "--workspace", workspace, "--session-id", "session-corrupt-log-0001",
                "--demonstrated", "One invariant", "--unresolved", "Transfer",
                "--next-action", "Try a variant",
            )
            with (workspace / ".mastery" / "sessions.jsonl").open("a", encoding="utf-8") as handle:
                handle.write('{"schema_version":1,"id":"session-truncated"')
            validation = json.loads(run(STATE, "validate", "--workspace", workspace, expect=1).stdout)
            self.assertTrue(any("sessions line" in error for error in validation["errors"]))
            resumed = run(STATE, "status", "--workspace", workspace, "--json", expect=1)
            self.assertIn("sessions", resumed.stderr)

    def test_event_id_retry_compares_time_and_delay_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Strict retry identity")
            base = [
                STATE, "record", "--workspace", workspace, "--event-id", "ev-retry-semantics",
                "--concept", "retry", "--kind", "exercise", "--score", "0.8",
                "--dimensions", "application", "--required", "application",
            ]
            run(*base, "--occurred-at", "2026-08-01T09:00:00+00:00")
            changed = run(*base, "--occurred-at", "2026-08-02T09:00:00+00:00", expect=1)
            self.assertIn("different evidence", changed.stderr)

    def test_concept_graph_and_active_path_reject_invalid_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Acyclic plan")
            run(STATE, "concept-add", "--workspace", workspace, "--id", "cycle", "--required", "application")
            cycle = run(
                STATE, "concept-add", "--workspace", workspace, "--id", "cycle",
                "--required", "application", "--prerequisites", "cycle", "--replace", expect=1,
            )
            self.assertIn("cycle", cycle.stderr.lower())
            ghost = run(
                STATE, "set", "--workspace", workspace, "--target", "plan", "--field", "active_path",
                "--value", '["ghost-concept"]', expect=1,
            )
            self.assertIn("undefined", ghost.stderr.lower())

    def test_curriculum_preserves_universe_and_profile_drives_required_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            unselected = parent / "unselected"
            run(STATE, "init", "--workspace", unselected, "--goal", "Explore the field", "--curriculum", "ml-ai-llm")
            unselected_status = json.loads(run(STATE, "status", "--workspace", unselected, "--json").stdout)
            self.assertEqual(unselected_status["coverage"]["scope_status"], "unselected")
            self.assertIsNone(unselected_status["coverage"]["completion_ratio"])
            unselected_plan = json.loads((unselected / ".mastery" / "plan.json").read_text(encoding="utf-8"))
            unselected_concepts = json.loads((unselected / ".mastery" / "concepts.json").read_text(encoding="utf-8"))
            pack = json.loads(CURRICULUM.read_text(encoding="utf-8"))
            self.assertEqual(unselected_plan["excluded_scope"], [])
            self.assertEqual(unselected_concepts["curriculum"]["declared_scope"]["excluded"], pack["scope"]["excluded"])

            workspace = parent / "confirmed"
            run(
                STATE, "init", "--workspace", workspace, "--goal", "Implement a small transformer",
                "--curriculum", "ml-ai-llm", "--target-profile", "llm-engineer",
                "--scope-reason", "Learner confirmed model internals and production operation.",
            )
            by_id = {item["id"]: item for item in pack["concepts"]}
            expected: set[str] = set()

            def visit(concept_id: str) -> None:
                if concept_id in expected:
                    return
                expected.add(concept_id)
                for prerequisite in by_id[concept_id]["prerequisites"]:
                    visit(prerequisite)

            for target in pack["target_profiles"]["llm-engineer"]:
                visit(target)
            concepts = json.loads((workspace / ".mastery" / "concepts.json").read_text(encoding="utf-8"))
            plan = json.loads((workspace / ".mastery" / "plan.json").read_text(encoding="utf-8"))
            sources = json.loads((workspace / ".mastery" / "sources.json").read_text(encoding="utf-8"))
            scope = json.loads(run(STATE, "scope-status", "--workspace", workspace).stdout)
            status = json.loads(run(STATE, "status", "--workspace", workspace, "--json").stdout)
            self.assertEqual(set(concepts["concepts"]), set(by_id))
            self.assertEqual(plan["scope_selection"]["profiles"], ["llm-engineer"])
            self.assertEqual(plan["excluded_scope"], [])
            self.assertEqual(set(scope["required_concepts"]), expected)
            self.assertEqual(status["coverage"]["required"], len(expected))
            self.assertEqual(status["coverage"]["not_selected"], len(by_id) - len(expected))
            self.assertEqual(len(sources["sources"]), len(pack["sources"]))

    def test_windows_style_contention_preserves_all_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Contention safety")
            processes = [subprocess.Popen(
                [
                    sys.executable, str(STATE), "record", "--workspace", str(workspace),
                    "--event-id", f"ev-stress-{index:04d}", "--concept", "concurrency",
                    "--kind", "exercise", "--score", "0.8", "--dimensions", "application",
                    "--required", "application", "--notes", f"event-{index}",
                ],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", env=environment(),
            ) for index in range(32)]
            results = [process.communicate(timeout=45) + (process.returncode,) for process in processes]
            self.assertTrue(all(code == 0 for _, _, code in results), results)
            lines = (workspace / ".mastery" / "evidence.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 32)
            self.assertTrue(json.loads(run(STATE, "validate", "--workspace", workspace).stdout)["ok"])

    def test_scope_change_preserves_evidence_and_derived_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Choose scope safely", "--curriculum", "ml-ai-llm")
            run(
                STATE, "record", "--workspace", workspace, "--concept", "python", "--kind", "diagnostic",
                "--score", "0.6", "--dimensions", "conceptual", "--event-id", "ev-scope-preserve",
            )
            root = workspace / ".mastery"
            before = {name: (root / name).read_bytes() for name in ["evidence.jsonl", "mastery.json", "reviews.json"]}
            applied = json.loads(run(
                STATE, "scope-apply", "--workspace", workspace, "--target-profile", "llm-engineer",
                "--reason", "Learner confirmed model internals and operations.",
            ).stdout)
            self.assertEqual(applied["required_count"], 32)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in before})

    def test_all_builtin_profile_closures_are_stable(self) -> None:
        expected_counts = {
            "llm-application-builder": 31,
            "ml-engineer": 22,
            "ai-systems-builder": 21,
            "llm-engineer": 32,
            "research": 33,
        }
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for profile, expected in expected_counts.items():
                workspace = parent / profile
                result = json.loads(run(
                    STATE, "init", "--workspace", workspace, "--goal", f"Target {profile}",
                    "--curriculum", "ml-ai-llm", "--target-profile", profile,
                    "--scope-reason", "Regression fixture with explicit profile selection.",
                ).stdout)
                self.assertTrue(result["ok"])
                scope = json.loads(run(STATE, "scope-status", "--workspace", workspace).stdout)
                self.assertEqual(scope["required_count"], expected)
                self.assertEqual(scope["required_concepts"][0], "python")

    def test_scope_rejects_unknown_profile_and_outside_active_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Bounded scope", "--curriculum", "ml-ai-llm")
            unknown = run(
                STATE, "scope-apply", "--workspace", workspace, "--target-profile", "imaginary-role",
                "--reason", "Invalid regression input.", expect=1,
            )
            self.assertIn("unknown profiles", unknown.stderr)
            run(
                STATE, "scope-apply", "--workspace", workspace, "--target-profile", "ai-systems-builder",
                "--reason", "Learner confirmed classical AI systems.",
            )
            outside = run(
                STATE, "set", "--workspace", workspace, "--target", "plan", "--field", "active_path",
                "--value", '["transformer"]', expect=1,
            )
            self.assertIn("outside confirmed scope", outside.stderr)

    def test_assisted_retrieval_after_mastery_is_fragile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            seed_mastery(workspace)
            record(workspace, "durable", "review", "1.0", "2026-08-03T13:00:00+00:00", "recall", "--assisted")
            status = json.loads(run(STATE, "status", "--workspace", workspace, "--json").stdout)
            self.assertEqual(status["concepts"][0]["status"], "fragile")

    def test_retry_normalizes_dimension_order_but_rejects_delayed_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Canonical retries")
            base = [
                STATE, "record", "--workspace", workspace, "--event-id", "ev-order-normalized",
                "--concept", "ordering", "--kind", "debug", "--score", "0.8", "--required", "application,debugging",
                "--occurred-at", "2026-08-01T09:00:00+00:00",
            ]
            run(*base, "--dimensions", "debugging,application")
            duplicate = json.loads(run(*base, "--dimensions", "application,debugging").stdout)
            self.assertTrue(duplicate["duplicate"])
            changed = run(*base, "--dimensions", "application,debugging", "--delayed", expect=1)
            self.assertIn("different evidence", changed.stderr)

    def test_tampered_derived_state_is_not_used_by_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Do not trust stale views")
            mastery = workspace / ".mastery" / "mastery.json"
            value = json.loads(mastery.read_text(encoding="utf-8"))
            value["concepts"]["invented"] = {"status": "mastered"}
            mastery.write_text(json.dumps(value), encoding="utf-8")
            result = run(STATE, "status", "--workspace", workspace, "--json", expect=1)
            self.assertIn("Derived state does not match", result.stderr)

    def test_incomplete_transaction_is_recovered_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Recover transactions")
            root = workspace / ".mastery"
            revision = json.loads((root / "state-revision.json").read_text(encoding="utf-8"))["revision"]
            plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
            plan["open_questions"] = ["Recovered from a simulated interrupted commit."]
            plan["updated_at"] = "2026-08-22T12:00:00+00:00"
            content = json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            journal = {
                "journal_schema_version": 1,
                "transaction_id": "tx-simulated-recovery",
                "created_at": "2026-08-22T12:00:00+00:00",
                "base_revision": revision,
                "target_revision": revision + 1,
                "files": {"plan.json": {"content": content, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}},
            }
            (root / "transaction.json").write_text(json.dumps(journal), encoding="utf-8")
            (root / "plan.json").write_text("{}", encoding="utf-8")
            validated = json.loads(run(STATE, "validate", "--workspace", workspace).stdout)
            self.assertTrue(validated["ok"])
            self.assertFalse((root / "transaction.json").exists())
            recovered = json.loads((root / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(recovered["open_questions"], plan["open_questions"])
            self.assertEqual(json.loads((root / "state-revision.json").read_text(encoding="utf-8"))["revision"], revision + 1)

    def test_concept_semantics_are_immutable_after_evidence_but_title_is_correctable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Stable capability definitions")
            run(STATE, "concept-add", "--workspace", workspace, "--id", "foundation", "--required", "conceptual")
            run(
                STATE, "concept-add", "--workspace", workspace, "--id", "target",
                "--title", "Initial title", "--outcome", "Build the target.",
                "--required", "application", "--prerequisites", "foundation",
            )
            run(
                STATE, "record", "--workspace", workspace, "--concept", "foundation",
                "--kind", "explain", "--score", "0.8", "--dimensions", "conceptual",
            )
            evidence = (workspace / ".mastery" / "evidence.jsonl").read_bytes()
            changed_graph = run(
                STATE, "concept-add", "--workspace", workspace, "--id", "target",
                "--required", "application", "--prerequisites", "", "--replace", expect=1,
            )
            self.assertIn("immutable after any evidence", changed_graph.stderr)
            changed_outcome = run(
                STATE, "concept-add", "--workspace", workspace, "--id", "target",
                "--outcome", "A different capability.", "--required", "application", "--replace", expect=1,
            )
            self.assertIn("immutable after any evidence", changed_outcome.stderr)
            run(
                STATE, "concept-add", "--workspace", workspace, "--id", "target",
                "--title", "Corrected title", "--required", "application", "--replace",
            )
            concepts = json.loads((workspace / ".mastery" / "concepts.json").read_text(encoding="utf-8"))
            self.assertEqual(concepts["concepts"]["target"]["title"], "Corrected title")
            self.assertEqual(concepts["concepts"]["target"]["prerequisites"], ["foundation"])
            self.assertEqual((workspace / ".mastery" / "evidence.jsonl").read_bytes(), evidence)

    def test_validate_reports_concept_to_unknown_source_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Source integrity", "--curriculum", "ml-ai-llm")
            concepts_path = workspace / ".mastery" / "concepts.json"
            concepts = json.loads(concepts_path.read_text(encoding="utf-8"))
            concepts["concepts"]["python"]["sources"] = ["missing-source"]
            concepts_path.write_text(json.dumps(concepts), encoding="utf-8")
            result = json.loads(run(STATE, "validate", "--workspace", workspace, expect=1).stdout)
            self.assertTrue(any("references undefined sources" in error for error in result["errors"]))

    def test_custom_curriculum_duplicate_concepts_fail_before_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "workspace"
            curriculum = json.loads(CURRICULUM.read_text(encoding="utf-8"))
            duplicate = dict(curriculum["concepts"][0])
            duplicate["outcome"] = "A duplicate definition must never overwrite the first definition."
            curriculum["concepts"].append(duplicate)
            path = Path(temporary) / "duplicate-curriculum.json"
            path.write_text(json.dumps(curriculum), encoding="utf-8")
            result = run(
                STATE, "init", "--workspace", workspace, "--goal", "Reject duplicate curriculum IDs",
                "--curriculum", path, expect=1,
            )
            self.assertIn("duplicate concept IDs", result.stderr)
            self.assertFalse((workspace / ".mastery" / "profile.json").exists())

    def test_non_retrieval_practice_cannot_postpone_an_overdue_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Monotonic review obligations")
            for stamp in ["2026-08-01T09:00:00+00:00", "2026-08-03T09:00:00+00:00"]:
                run(
                    STATE, "record", "--workspace", workspace, "--concept", "review-me",
                    "--kind", "exercise", "--score", "0.8", "--dimensions", "application",
                    "--required", "application", "--occurred-at", stamp,
                )
            reviews = json.loads((workspace / ".mastery" / "reviews.json").read_text(encoding="utf-8"))
            self.assertEqual(reviews["concepts"]["review-me"]["due_at"], "2026-08-02T09:00:00+00:00")
            self.assertEqual(reviews["concepts"]["review-me"]["last_learning_at"], "2026-08-03T09:00:00+00:00")

    def test_failed_or_assisted_retrieval_never_postpones_an_existing_due_time(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Failed retrieval stays due")
            run(
                STATE, "record", "--workspace", workspace, "--concept", "review-me",
                "--kind", "exercise", "--score", "0.8", "--dimensions", "application",
                "--required", "recall,application", "--occurred-at", "2026-08-01T09:00:00+00:00",
            )
            run(
                STATE, "record", "--workspace", workspace, "--concept", "review-me",
                "--kind", "review", "--score", "0.2", "--dimensions", "recall",
                "--occurred-at", "2026-08-03T09:00:00+00:00", "--assisted",
            )
            reviews = json.loads((workspace / ".mastery" / "reviews.json").read_text(encoding="utf-8"))
            self.assertEqual(reviews["concepts"]["review-me"]["due_at"], "2026-08-02T09:00:00+00:00")

    def test_session_close_requires_a_retry_key_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Idempotent handoffs")
            base = [
                STATE, "session-close", "--workspace", workspace, "--session-id", "session-retry-safe-0001",
                "--demonstrated", "Explained the invariant", "--unresolved", "Transfer remains",
                "--next-action", "Solve a variant",
            ]
            self.assertFalse(json.loads(run(*base).stdout).get("duplicate", False))
            self.assertTrue(json.loads(run(*base).stdout)["duplicate"])
            changed = run(*base[:-1], "Solve a different variant", expect=1)
            self.assertIn("different handoff", changed.stderr)
            self.assertEqual(len((workspace / ".mastery" / "sessions.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def test_concurrent_session_closes_remain_chronological_and_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Concurrent handoffs")
            processes = [subprocess.Popen(
                [
                    sys.executable, str(STATE), "session-close", "--workspace", str(workspace),
                    "--session-id", f"session-concurrent-{index:04d}",
                    "--demonstrated", f"Capability {index}", "--unresolved", "Transfer",
                    "--next-action", f"Variant {index}",
                ],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", env=environment(),
            ) for index in range(24)]
            results = [process.communicate(timeout=45) + (process.returncode,) for process in processes]
            self.assertTrue(all(code == 0 for _, _, code in results), results)
            sessions = [json.loads(line) for line in (workspace / ".mastery" / "sessions.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(sessions), 24)
            self.assertEqual([item["closed_at"] for item in sessions], sorted(item["closed_at"] for item in sessions))
            self.assertTrue(json.loads(run(STATE, "validate", "--workspace", workspace).stdout)["ok"])

    def test_v3_migration_preserves_valid_personalization_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "legacy"
            root = write_legacy_workspace(workspace, [])
            profile_path = root / "profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            profile["schema_version"] = 3
            profile["hypotheses"] = [{
                "observation": "Learner traced shapes accurately.",
                "inference": "Tensor-shape fluency may be strong.",
                "observed_at": "2026-08-01T09:00:00+00:00",
                "confidence": 0.7,
            }]
            profile_path.write_text(json.dumps(profile), encoding="utf-8")
            run(STATE, "migrate", "--workspace", workspace, "--backup", workspace / "backup.zip")
            migrated = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(migrated["hypotheses"], profile["hypotheses"])

    def test_hypothesis_observation_time_is_strictly_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Valid personalization evidence")
            value = json.dumps([{
                "observation": "Observed behavior", "inference": "Tentative inference",
                "observed_at": "not-a-date", "confidence": 0.5,
            }])
            result = run(
                STATE, "set", "--workspace", workspace, "--target", "profile",
                "--field", "hypotheses", "--value", value, expect=1,
            )
            self.assertIn("invalid hypotheses[0].observed_at", result.stderr)

    def test_corrupt_registry_is_reported_instead_of_silently_skipped(self) -> None:
        registry_entry = TEST_RUNTIME / "registry" / "workspaces.d" / "malformed-regression.json"
        registry_entry.parent.mkdir(parents=True, exist_ok=True)
        registry_entry.write_text("{not json", encoding="utf-8")
        try:
            result = run(STATE, "locate", expect=1)
            report = json.loads(result.stdout)
            self.assertFalse(report["ok"])
            self.assertEqual(report["errors"][0]["code"], "invalid-registry-entry")
            self.assertIn("malformed-regression.json", report["errors"][0]["entry"])
        finally:
            registry_entry.unlink(missing_ok=True)

    def test_due_items_remain_visible_but_are_labeled_by_confirmed_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Scoped reviews", "--curriculum", "ml-ai-llm")
            run(
                STATE, "record", "--workspace", workspace, "--concept", "transformer",
                "--kind", "exercise", "--score", "0.8", "--dimensions", "application",
            )
            run(
                STATE, "scope-apply", "--workspace", workspace, "--target-profile", "ai-systems-builder",
                "--reason", "Learner selected classical AI systems.",
            )
            report = json.loads(run(STATE, "due", "--workspace", workspace, "--within-days", "2", "--json").stdout)
            self.assertFalse(any(item["concept"] == "transformer" for item in report["due"]))
            transformer = next(item for item in report["out_of_scope_due"] if item["concept"] == "transformer")
            self.assertEqual(transformer["scope_class"], "not-selected")
            included = json.loads(run(
                STATE, "due", "--workspace", workspace, "--within-days", "2", "--include-nonrequired", "--json",
            ).stdout)
            self.assertTrue(any(item["concept"] == "transformer" for item in included["due"]))

    def test_confirmed_scope_requires_explicit_nonempty_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            init_result = run(
                STATE, "init", "--workspace", parent / "init", "--goal", "No implicit confirmation",
                "--curriculum", "ml-ai-llm", "--target-profile", "llm-engineer", expect=1,
            )
            self.assertIn("non-empty reason", init_result.stderr)
            workspace = parent / "apply"
            run(STATE, "init", "--workspace", workspace, "--goal", "No blank confirmation", "--curriculum", "ml-ai-llm")
            apply_result = run(
                STATE, "scope-apply", "--workspace", workspace, "--target-profile", "llm-engineer",
                "--reason", "", expect=1,
            )
            self.assertIn("non-empty reason", apply_result.stderr)


if __name__ == "__main__":
    unittest.main()
