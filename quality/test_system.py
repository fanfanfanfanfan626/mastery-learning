from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COACH = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-coach"
CREATOR = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-tool-creator"
STATE = COACH / "scripts" / "mastery.py"
AUDIT = COACH / "scripts" / "curriculum_audit.py"
CURRICULUM = COACH / "assets" / "curricula" / "ml-ai-llm.json"
SCAFFOLD = CREATOR / "scripts" / "tool_scaffold.py"
VALIDATE_TOOL = CREATOR / "scripts" / "validate_tool.py"
FINALIZE_TOOL = CREATOR / "scripts" / "finalize_tool.py"
TEST_RUNTIME = ROOT / "work" / "test-runtime"


def environment() -> dict[str, str]:
    return {**os.environ, "MASTERY_HOME": str(TEST_RUNTIME / "registry"), "PYTHONUTF8": "1"}


def run(*args: str | Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *map(str, args)], cwd=ROOT, text=True, encoding="utf-8",
        capture_output=True, check=False, env=environment(),
    )
    if result.returncode != expect:
        raise AssertionError(f"Expected exit {expect}, got {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


def record(workspace: Path, concept: str, kind: str, score: str, occurred_at: str, dimensions: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return run(
        STATE, "record", "--workspace", workspace, "--concept", concept, "--kind", kind,
        "--score", score, "--occurred-at", occurred_at, "--dimensions", dimensions,
        "--required", "recall,conceptual,application", *extra,
    )


class CurriculumTests(unittest.TestCase):
    def test_builtin_curriculum_has_audited_scope_sources_and_dag(self) -> None:
        report = json.loads(run(AUDIT).stdout)
        self.assertTrue(report["ok"])
        self.assertGreaterEqual(report["concept_count"], 47)
        self.assertGreaterEqual(report["module_count"], 10)
        self.assertGreaterEqual(report["profile_count"], 5)
        self.assertIn("does not prove", report["limitations"][0])

    def test_invalid_schema_source_and_orphan_module_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            broken = json.loads(CURRICULUM.read_text(encoding="utf-8"))
            broken["schema_version"] = 999
            broken["sources"][0]["url"] = "not-a-url"
            broken["sources"].append(dict(broken["sources"][0]))
            broken["concepts"].append({
                "id": "orphan-topic", "module": "orphan-module", "prerequisites": [],
                "outcome": "Demonstrate that an unaffiliated module is rejected.",
                "required_dimensions": ["application"], "sources": ["d2l"],
            })
            target = Path(temporary) / "broken.json"
            target.write_text(json.dumps(broken), encoding="utf-8")
            report = json.loads(run(AUDIT, target, expect=1).stdout)
            combined = "\n".join(report["errors"])
            for marker in ["schema_version", "duplicate source IDs", "canonical URL", "modules not used"]:
                self.assertIn(marker, combined)

    def test_optional_prerequisite_and_stale_official_source_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            broken = json.loads(CURRICULUM.read_text(encoding="utf-8"))
            next(item for item in broken["concepts"] if item["id"] == "python")["optional"] = True
            for source in broken["sources"]:
                if source["type"] == "official-docs":
                    source["checked_at"] = "2020-01-01"
            target = Path(temporary) / "broken.json"
            target.write_text(json.dumps(broken), encoding="utf-8")
            report = json.loads(run(AUDIT, target, expect=1).stdout)
            combined = "\n".join(report["errors"])
            self.assertIn("optional concepts occur", combined)
            self.assertIn("fast-moving source check is stale", combined)


class StateEngineTests(unittest.TestCase):
    def test_registry_finds_workspace_from_unrelated_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "durable-learning"
            workspace.mkdir()
            run(STATE, "init", "--workspace", workspace, "--goal", "Unique registry discovery goal")
            located = json.loads(run(STATE, "locate", "--goal", "registry discovery").stdout)
            self.assertEqual(located["workspaces"][0]["path"], str(workspace.resolve()))

    def test_mastery_requires_fixed_dimensions_transfer_and_real_delay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Explain and apply optimization")
            record(workspace, "optimization", "explain", "0.9", "2026-08-01T09:00:00+00:00", "conceptual")
            record(workspace, "optimization", "exercise", "0.9", "2026-08-01T10:00:00+00:00", "application")
            record(workspace, "optimization", "recall", "0.9", "2026-08-01T11:00:00+00:00", "recall")
            record(workspace, "optimization", "transfer", "0.9", "2026-08-01T12:00:00+00:00", "transfer,conceptual")
            status = json.loads(run(STATE, "status", "--workspace", workspace, "--json").stdout)
            self.assertEqual(status["concepts"][0]["status"], "provisional")
            record(workspace, "optimization", "review", "0.9", "2026-08-02T12:30:00+00:00", "recall", "--delayed")
            status = json.loads(run(STATE, "status", "--workspace", workspace, "--json").stdout)
            self.assertEqual(status["concepts"][0]["status"], "mastered")

    def test_requirements_cannot_shrink_and_kind_semantics_cannot_be_spoofed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Guard mastery semantics")
            record(workspace, "guarded", "explain", "0.9", "2026-08-01T09:00:00+00:00", "conceptual")
            result = run(
                STATE, "record", "--workspace", workspace, "--concept", "guarded", "--kind", "review", "--score", "0.9",
                "--occurred-at", "2026-08-02T09:00:00+00:00", "--dimensions", "recall", "--required", "recall", expect=1,
            )
            self.assertIn("fixed", result.stderr)
            spoof = run(
                STATE, "record", "--workspace", workspace, "--concept", "guarded", "--kind", "transfer", "--score", "0.9",
                "--occurred-at", "2026-08-02T09:00:00+00:00", "--dimensions", "recall", expect=1,
            )
            self.assertIn("requires dimensions", spoof.stderr)

    def test_assisted_review_cannot_clear_fragility(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Recovery requires independent delayed retrieval")
            for kind, score, stamp, dims, extra in [
                ("explain", "0.95", "2026-08-01T09:00:00+00:00", "conceptual", ()),
                ("exercise", "0.95", "2026-08-01T10:00:00+00:00", "application", ()),
                ("transfer", "0.95", "2026-08-01T11:00:00+00:00", "transfer,conceptual", ()),
                ("review", "0.95", "2026-08-02T12:00:00+00:00", "recall", ("--delayed",)),
                ("review", "0.3", "2026-08-03T13:00:00+00:00", "recall", ("--delayed",)),
                ("review", "1.0", "2026-08-03T14:00:00+00:00", "recall", ("--assisted",)),
            ]:
                record(workspace, "recovery", kind, score, stamp, dims, *extra)
            status = json.loads(run(STATE, "status", "--workspace", workspace, "--json").stdout)
            self.assertEqual(status["concepts"][0]["status"], "fragile")

    def test_review_schedule_ignores_zero_diagnostic_and_early_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Conservative scheduling")
            record(workspace, "schedule", "diagnostic", "0", "2026-08-01T08:00:00+00:00", "conceptual")
            reviews = json.loads((workspace / ".mastery" / "reviews.json").read_text(encoding="utf-8"))
            self.assertEqual(reviews["concepts"], {})
            record(workspace, "schedule", "exercise", "0.9", "2026-08-01T09:00:00+00:00", "application")
            first_due = json.loads((workspace / ".mastery" / "reviews.json").read_text(encoding="utf-8"))["concepts"]["schedule"]["due_at"]
            record(workspace, "schedule", "review", "0.9", "2026-08-01T12:00:00+00:00", "recall")
            after_early = json.loads((workspace / ".mastery" / "reviews.json").read_text(encoding="utf-8"))["concepts"]["schedule"]["due_at"]
            self.assertEqual(first_due, after_early)

    def test_validate_handles_wrong_root_and_record_prevalidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Schema safety")
            profile = workspace / ".mastery" / "profile.json"
            profile.write_text("[]", encoding="utf-8")
            before = (workspace / ".mastery" / "evidence.jsonl").read_text(encoding="utf-8")
            result = run(STATE, "validate", "--workspace", workspace, expect=1)
            self.assertNotIn("Traceback", result.stderr)
            run(
                STATE, "record", "--workspace", workspace, "--concept", "safe", "--kind", "exercise", "--score", "0.8",
                "--dimensions", "application", "--required", "application", expect=1,
            )
            self.assertEqual(before, (workspace / ".mastery" / "evidence.jsonl").read_text(encoding="utf-8"))

    def test_set_rejects_wrong_types(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Strict updates")
            result = run(STATE, "set", "--workspace", workspace, "--target", "plan", "--field", "status", "--value", "123", expect=1)
            self.assertIn("plan.status", result.stderr)

    def test_export_and_delete_reject_inside_state_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "learner"
            workspace.mkdir()
            run(STATE, "init", "--workspace", workspace, "--goal", "Own my data")
            inside = workspace / ".mastery" / "backup.zip"
            run(STATE, "export", "--workspace", workspace, "--output", inside, expect=1)
            run(STATE, "delete", "--workspace", workspace, "--backup", inside, "--confirm", "DELETE-MASTERY-DATA", expect=1)
            self.assertTrue((workspace / ".mastery").exists())
            outside = Path(temporary) / "backup.zip"
            run(STATE, "delete", "--workspace", workspace, "--backup", outside, "--confirm", "DELETE-MASTERY-DATA")
            self.assertTrue(outside.exists())
            self.assertFalse((workspace / ".mastery").exists())

    def test_privacy_guard_is_repaired_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Private learning")
            guard = workspace / ".mastery" / ".gitignore"
            guard.write_text("# unsafe\n", encoding="utf-8")
            result = json.loads(run(STATE, "init", "--workspace", workspace, "--goal", "Private learning", "--force").stdout)
            self.assertEqual(guard.read_text(encoding="utf-8"), "*\n!.gitignore\n")
            self.assertTrue(Path(result["privacy_backup"]).exists())

    def test_event_id_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Retry safely")
            args = [
                STATE, "record", "--workspace", workspace, "--event-id", "ev-idempotent123", "--concept", "retry",
                "--kind", "exercise", "--score", "0.8", "--dimensions", "application", "--required", "application",
                "--occurred-at", "2026-08-01T09:00:00+00:00",
            ]
            self.assertFalse(json.loads(run(*args).stdout)["duplicate"])
            self.assertTrue(json.loads(run(*args).stdout)["duplicate"])
            self.assertEqual(len((workspace / ".mastery" / "evidence.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def test_concurrent_records_and_registry_initializations_preserve_all(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            workspaces = [parent / f"ws-{index}" for index in range(12)]
            for workspace in workspaces:
                workspace.mkdir()
            processes = [subprocess.Popen(
                [sys.executable, str(STATE), "init", "--workspace", str(workspace), "--goal", f"Concurrent goal {index}"],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=environment(),
            ) for index, workspace in enumerate(workspaces)]
            results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
            self.assertTrue(all(code == 0 for _, _, code in results), results)
            located = json.loads(run(STATE, "locate", "--goal", "Concurrent goal").stdout)
            self.assertEqual(len(located["workspaces"]), 12)
            workspace = workspaces[0]
            processes = [subprocess.Popen(
                [sys.executable, str(STATE), "record", "--workspace", str(workspace), "--event-id", f"ev-concurrent{index:04d}",
                 "--concept", "concurrency", "--kind", "exercise", "--score", "0.8", "--dimensions", "application",
                 "--required", "application", "--notes", f"event-{index}"],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=environment(),
            ) for index in range(12)]
            results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
            self.assertTrue(all(code == 0 for _, _, code in results), results)
            self.assertEqual(len((workspace / ".mastery" / "evidence.jsonl").read_text(encoding="utf-8").splitlines()), 12)

    def test_v1_migration_backs_up_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "legacy"
            root = workspace / ".mastery"
            root.mkdir(parents=True)
            (root / "profile.json").write_text(json.dumps({"schema_version": 1, "created_at": "2026-08-01T08:00:00+00:00", "goal": "Legacy goal", "hours_per_week": 5, "session_minutes": 45}), encoding="utf-8")
            (root / "plan.json").write_text(json.dumps({"schema_version": 1, "status": "diagnostic", "active_path": [], "excluded_scope": [], "open_questions": []}), encoding="utf-8")
            (root / "sources.json").write_text(json.dumps({"schema_version": 1, "sources": []}), encoding="utf-8")
            (root / "mastery.json").write_text(json.dumps({"schema_version": 1, "concepts": {"legacy-concept": {"title": "Legacy Concept", "required_dimensions": ["application"]}}}), encoding="utf-8")
            (root / "reviews.json").write_text(json.dumps({"schema_version": 1, "concepts": {}}), encoding="utf-8")
            event = {"id": "ev-legacy123456", "timestamp": "2026-08-01T09:00:00+00:00", "concept": "legacy-concept", "kind": "exercise", "score": 0.8, "difficulty": 3, "hints": 0, "independent": True, "delayed": False, "dimensions": ["application"], "notes": "legacy"}
            (root / "evidence.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
            backup = workspace / "migration.zip"
            report = json.loads(run(STATE, "migrate", "--workspace", workspace, "--backup", backup).stdout)
            self.assertTrue(backup.exists())
            self.assertEqual(report["from_schema"], 1)
            self.assertTrue(json.loads(run(STATE, "validate", "--workspace", workspace).stdout)["ok"])

    def test_structured_session_is_available_on_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(STATE, "init", "--workspace", workspace, "--goal", "Session memory")
            run(STATE, "session-close", "--workspace", workspace, "--session-id", "session-structured-0001", "--demonstrated", "Explained one invariant", "--unresolved", "Transfer remains untested", "--next-action", "Solve a changed-context problem")
            status = json.loads(run(STATE, "status", "--workspace", workspace, "--json").stdout)
            self.assertEqual(status["latest_session"]["next_action"], "Solve a changed-context problem")


class ToolCreatorTests(unittest.TestCase):
    def test_scaffold_generator_version_matches_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(
                SCAFFOLD,
                "--workspace", workspace,
                "--id", "version-check-lab",
                "--type", "blackboard",
                "--concept", "testing",
                "--objective", "Explain a deterministic version contract",
            )
            tool = workspace / ".mastery" / "tools" / "version-check-lab" / "tool.json"
            generator = json.loads(tool.read_text(encoding="utf-8"))["generator"]
            plugin = json.loads((ROOT / "plugins" / "mastery-learning" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(generator["version"], plugin["version"])

    def customize_code_lab(self, tool: Path) -> None:
        manifest_path = tool / "tool.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["build_status"] = "complete"
        manifest["interaction"].update({
            "prediction": "Predict the output for positive, zero, and negative inputs before running tests.",
            "learner_action": "Implement learner_solution and explain boundary behavior.",
            "feedback": "The deterministic unittest reports exact mismatches against the contract.",
            "transfer": "Adapt the implementation to reject non-numeric input without changing numeric behavior.",
        })
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        rubric = json.loads((tool / "rubric.json").read_text(encoding="utf-8"))
        rubric["criteria"][0]["description"] = "Explain why doubling preserves sign and zero"
        rubric["criteria"][1]["description"] = "Return twice the numeric input for the tested cases"
        (tool / "rubric.json").write_text(json.dumps(rubric, ensure_ascii=False, indent=2), encoding="utf-8")
        (tool / "accessibility-fallback.md").write_text("# Text equivalent\n\nRead the input/output table, predict each result, implement the function, run the tests, and explain mismatches using the same rubric.\n", encoding="utf-8")
        (tool / "test_exercise.py").write_text(
            "import unittest\nfrom exercise import learner_solution\n\nclass ExerciseTests(unittest.TestCase):\n"
            "    def test_double(self):\n        self.assertEqual(learner_solution(2), 4)\n\nif __name__ == '__main__':\n    unittest.main()\n",
            encoding="utf-8",
        )

    def test_static_validation_never_executes_and_finalize_records_observation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(SCAFFOLD, "--workspace", workspace, "--id", "double-values", "--type", "code_lab", "--concept", "python", "--objective", "Implement and explain a numeric doubling function")
            tool = workspace / ".mastery" / "tools" / "double-values"
            self.customize_code_lab(tool)
            marker = workspace / ".mastery" / "outside-marker.txt"
            test_path = tool / "test_exercise.py"
            test_path.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n" + test_path.read_text(encoding="utf-8"), encoding="utf-8")
            accepted = json.loads(run(VALIDATE_TOOL, tool).stdout)
            self.assertTrue(accepted["ok"])
            self.assertEqual(accepted["status"], "structurally-valid")
            self.assertFalse(marker.exists(), "static validator executed generated code")
            completed = subprocess.run(
                [sys.executable, "-m", "unittest", "test_exercise.py"], cwd=tool,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": "-p no:cacheprovider"},
                text=True, encoding="utf-8", capture_output=True, check=False,
            )
            output = workspace / "observed-output.txt"
            output.write_text(completed.stdout + completed.stderr, encoding="utf-8")
            finalized = json.loads(run(
                FINALIZE_TOOL, tool, "--sandboxed-by", "codex-workspace-sandbox", "--review-notes", "Observed learner TODO failure and rubric-linked feedback.",
                "--observed-exit-code", str(completed.returncode), "--observed-output-file", output,
            ).stdout)
            self.assertEqual(finalized["status"], "verified")
            catalog = json.loads((workspace / ".mastery" / "tool-catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(catalog["tools"][0]["status"], "verified")

    def test_placeholder_and_unknown_manifest_field_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(SCAFFOLD, "--workspace", workspace, "--id", "bad-code-lab", "--type", "code_lab", "--concept", "testing", "--objective", "Implement behavior that deterministic tests verify")
            tool = workspace / ".mastery" / "tools" / "bad-code-lab"
            report = json.loads(run(VALIDATE_TOOL, tool, expect=1).stdout)
            self.assertIn("unconditional self.fail", "\n".join(report["errors"]))
            manifest_path = tool / "tool.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["unexpected"] = "field"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = json.loads(run(VALIDATE_TOOL, tool, expect=1).stdout)
            self.assertIn("unknown manifest fields", "\n".join(report["errors"]))

    def test_concurrent_scaffolds_preserve_catalog_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            processes = [subprocess.Popen(
                [sys.executable, str(SCAFFOLD), "--workspace", str(workspace), "--id", f"lab-{index}", "--type", "blackboard", "--concept", "logic", "--objective", f"Reconstruct a derivation for scenario number {index}"],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=environment(),
            ) for index in range(12)]
            results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
            self.assertTrue(all(code == 0 for _, _, code in results), results)
            catalog = json.loads((workspace / ".mastery" / "tool-catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(len(catalog["tools"]), 12)


class PackageTests(unittest.TestCase):
    def test_plugin_and_skill_structure(self) -> None:
        plugin = json.loads((ROOT / "plugins" / "mastery-learning" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], "mastery-learning")
        self.assertEqual(plugin["version"], "0.4.2")
        self.assertEqual(plugin["skills"], "./skills/")
        for skill in [COACH, CREATOR]:
            content = (skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\nname:"))
            self.assertNotIn("[TODO:", content)
            self.assertTrue((skill / "agents" / "openai.yaml").exists())

    def test_tool_manifest_schema_is_current(self) -> None:
        schema = json.loads((CREATOR / "assets" / "tool-manifest.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], 3)
        self.assertEqual(schema["properties"]["build_status"]["enum"], ["scaffold", "complete"])
        self.assertNotIn("completed", schema["properties"]["inspection"]["properties"])

    def test_release_archive_is_deterministic_and_contains_regressions(self) -> None:
        builder = ROOT / "quality" / "build_release.py"
        with tempfile.TemporaryDirectory() as temporary:
            first, second = Path(temporary) / "first.zip", Path(temporary) / "second.zip"
            run(builder, "--output", first)
            run(builder, "--output", second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                self.assertEqual(names, sorted(names))
                self.assertIn("quality/test_state_regressions_v4.py", names)
                self.assertIn("quality/test_tool_contract_v4.py", names)
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))


if __name__ == "__main__":
    unittest.main()
