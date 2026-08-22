from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CREATOR = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-tool-creator"
COACH = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-coach"
SCAFFOLD = CREATOR / "scripts" / "tool_scaffold.py"
VALIDATE = CREATOR / "scripts" / "validate_tool.py"
FINALIZE = CREATOR / "scripts" / "finalize_tool.py"


def run(script: Path, *arguments: object, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(script), *(str(item) for item in arguments)],
        cwd=ROOT,
        env={**os.environ, "PYTHONUTF8": "1"},
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode != expect:
        raise AssertionError(f"expected {expect}, got {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def check_environment() -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_ADDOPTS": "-p no:cacheprovider",
    }


def customize_code_lab(tool: Path) -> None:
    manifest_path = tool / "tool.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["build_status"] = "complete"
    manifest["interaction"].update({
        "prediction": "Predict outputs for positive, zero, and negative values before running tests.",
        "learner_action": "Implement learner_solution and explain its boundary behavior.",
        "feedback": "Deterministic unittest mismatches identify behavior that violates the rubric.",
        "transfer": "Adapt the implementation to reject non-numeric input without changing numeric behavior.",
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    rubric_path = tool / "rubric.json"
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    rubric["criteria"][0]["description"] = "Explain why doubling preserves sign and zero"
    rubric["criteria"][1]["description"] = "Return twice the numeric input for each tested case"
    rubric_path.write_text(json.dumps(rubric, ensure_ascii=False, indent=2), encoding="utf-8")
    (tool / "accessibility-fallback.md").write_text(
        "# Text equivalent\n\nRead the input/output table, predict each result, implement the function, run the tests, and explain every mismatch using the same rubric.\n",
        encoding="utf-8",
    )
    (tool / "test_exercise.py").write_text(
        "import unittest\nfrom exercise import learner_solution\n\n"
        "class ExerciseTests(unittest.TestCase):\n"
        "    def test_double(self):\n"
        "        self.assertEqual(learner_solution(2), 4)\n\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n",
        encoding="utf-8",
    )


def customize_blackboard(tool: Path) -> None:
    manifest_path = tool / "tool.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["build_status"] = "complete"
    manifest["interaction"].update({
        "prediction": "Predict which invariant is needed before revealing the next derivation step.",
        "learner_action": "Reconstruct each missing step and state why the invariant remains true.",
        "feedback": "Compare the reconstruction with the rubric and the revealed invariant trace.",
        "transfer": "Rebuild the derivation after one assumption is changed.",
    })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    rubric_path = tool / "rubric.json"
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    rubric["criteria"][0]["description"] = "Explain the invariant and every boundary assumption"
    rubric["criteria"][1]["description"] = "Reconstruct all algebraic steps without answer leakage"
    rubric_path.write_text(json.dumps(rubric, ensure_ascii=False, indent=2), encoding="utf-8")
    (tool / "accessibility-fallback.md").write_text(
        "# Text equivalent\n\nUse the numbered derivation below. Predict each missing expression, reveal the reference step, and explain which invariant justifies it before advancing.\n",
        encoding="utf-8",
    )
    (tool / "blackboard.md").write_text(
        "# Invariant reconstruction\n\nFirst define every symbol and assumption. Predict the missing transformation before reading the next paragraph. "
        "For each line, state the equality rule that preserves the invariant and identify any boundary case. Then repeat the derivation after reversing one assumption. "
        "Finish by reconstructing the whole chain from memory and compare each step against the weighted rubric.\n",
        encoding="utf-8",
    )


def customize_visual_lab(tool: Path) -> None:
    manifest_path = tool / "tool.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["build_status"] = "complete"
    manifest["interaction"].update({
        "prediction": "Predict the direction and relative magnitude before revealing the plotted result.",
        "learner_action": "Change one control, run the experiment, and explain the observed causal change.",
        "feedback": "The plotted state and text summary expose the selected input and resulting output.",
        "transfer": "Repeat with a changed constraint and defend whether the original explanation transfers.",
    })
    manifest["inspection"]["notes"] = "Inspect initial and changed states, keyboard controls, text output, and the linked accessibility equivalent."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    rubric_path = tool / "rubric.json"
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    rubric["criteria"][0]["description"] = "Explain the causal mechanism behind the plotted change"
    rubric["criteria"][1]["description"] = "Produce and interpret the expected output in both conditions"
    rubric_path.write_text(json.dumps(rubric, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ["index.html", "accessibility-fallback.html"]:
        path = tool / name
        path.write_text(path.read_text(encoding="utf-8").replace("CUSTOMIZE:", "Activity detail:"), encoding="utf-8")


class ToolContractV4Tests(unittest.TestCase):
    def test_catalog_lock_preserves_all_parallel_scaffolds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            processes = [
                subprocess.Popen(
                    [
                        sys.executable, str(SCAFFOLD), "--workspace", str(workspace),
                        "--id", f"parallel-lab-{index}", "--type", "blackboard",
                        "--concept", "logic", "--objective", f"Reconstruct a derivation for parallel scenario {index}",
                    ],
                    cwd=ROOT,
                    env={**os.environ, "PYTHONUTF8": "1"},
                    text=True,
                    encoding="utf-8",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                for index in range(24)
            ]
            results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
            self.assertTrue(all(code == 0 for _, _, code in results), results)
            catalog = json.loads((workspace / ".mastery" / "tool-catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(len(catalog["tools"]), 24)
            self.assertEqual(len({item["id"] for item in catalog["tools"]}), 24)

    def test_verification_is_bound_to_exact_current_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(SCAFFOLD, "--workspace", workspace, "--id", "hash-bound-lab", "--type", "code_lab", "--concept", "python", "--objective", "Implement and explain a deterministic doubling function")
            tool = workspace / ".mastery" / "tools" / "hash-bound-lab"
            customize_code_lab(tool)
            first = json.loads(run(VALIDATE, tool).stdout)
            self.assertEqual(first["status"], "structurally-valid")

            exercise = tool / "exercise.py"
            original = exercise.read_bytes()
            exercise.write_bytes(original + b"\n# changed after static validation\n")
            precheck = subprocess.run(
                [sys.executable, "-m", "unittest", "test_exercise.py"], cwd=tool,
                text=True, encoding="utf-8", capture_output=True, check=False, env=check_environment(),
            )
            precheck_output = workspace / "precheck-observed.txt"
            precheck_output.write_text(precheck.stdout + precheck.stderr, encoding="utf-8")
            refused = run(
                FINALIZE,
                tool,
                "--sandboxed-by", "codex-workspace-sandbox",
                "--review-notes", "Observed the learner TODO failure after changing content without revalidation.",
                "--observed-exit-code", precheck.returncode,
                "--observed-output-file", precheck_output,
                expect=1,
            )
            self.assertIn("changed after static validation", refused.stderr)
            exercise.write_bytes(original)
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "structurally-valid")

            observed = subprocess.run(
                [sys.executable, "-m", "unittest", "test_exercise.py"],
                cwd=tool,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
                env=check_environment(),
            )
            output = workspace / "observed.txt"
            output.write_text(observed.stdout + observed.stderr, encoding="utf-8")
            finalized = json.loads(run(
                FINALIZE,
                tool,
                "--sandboxed-by", "codex-workspace-sandbox",
                "--review-notes", "Observed the learner TODO failure and the rubric-linked deterministic feedback.",
                "--observed-exit-code", observed.returncode,
                "--observed-output-file", output,
            ).stdout)
            verified_sha = finalized["tool_snapshot"]["sha256"]
            report = json.loads(Path(finalized["report"]).read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], 3)
            self.assertEqual(report["tool_snapshot"]["sha256"], verified_sha)
            self.assertEqual(report["manifest_sha256"], next(item["sha256"] for item in report["tool_snapshot"]["files"] if item["path"] == "tool.json"))
            self.assertEqual(report["inspection"], {"notes": None, "required": False, "result": "not-required"})
            catalog_entry = json.loads((workspace / ".mastery" / "tool-catalog.json").read_text(encoding="utf-8"))["tools"][0]
            self.assertEqual(len(catalog_entry["verification_report_sha256"]), 64)
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "verified")

            report_path = Path(finalized["report"])
            report_bytes = report_path.read_bytes()
            report["tool_snapshot"]["sha256"] = "0" * 64
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            inconsistent = json.loads(run(VALIDATE, tool).stdout)
            self.assertEqual(inconsistent["status"], "stale")
            self.assertIn("verification report", json.loads((workspace / ".mastery" / "tool-catalog.json").read_text(encoding="utf-8"))["tools"][0]["stale_reason"])
            report_path.write_bytes(report_bytes)
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "verified")

            report = json.loads(report_bytes.decode("utf-8"))
            report["review_notes"] = "Tampered review text that was never part of the archived observation."
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "stale")
            report_path.write_bytes(report_bytes)
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "verified")

            exercise.write_bytes(original + b"\n# changed after verification\n")
            stale = json.loads(run(VALIDATE, tool).stdout)
            self.assertEqual(stale["status"], "stale")
            self.assertNotEqual(stale["tool_snapshot"]["sha256"], verified_sha)
            catalog = json.loads((workspace / ".mastery" / "tool-catalog.json").read_text(encoding="utf-8"))["tools"][0]
            self.assertEqual(catalog["status"], "stale")
            self.assertEqual(catalog["verified_tool_sha256"], verified_sha)

            exercise.write_bytes(original)
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "verified")
            exercise.write_bytes(original + b"\n# CUSTOMIZE invalid edit\n")
            rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertEqual(rejected["status"], "rejected")
            catalog = json.loads((workspace / ".mastery" / "tool-catalog.json").read_text(encoding="utf-8"))["tools"][0]
            self.assertEqual(catalog["status"], "rejected")
            exercise.write_bytes(original)
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "verified")
            manifest_path = tool / "tool.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["objective"] += " in a new context"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "stale")

    def test_untracked_runtime_content_can_never_retain_verified_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(SCAFFOLD, "--workspace", workspace, "--id", "cache-bound-lab", "--type", "code_lab", "--concept", "python", "--objective", "Implement and explain a deterministic doubling function")
            tool = workspace / ".mastery" / "tools" / "cache-bound-lab"
            customize_code_lab(tool)
            validated = json.loads(run(VALIDATE, tool).stdout)
            self.assertEqual(validated["check_request"]["environment"]["PYTHONDONTWRITEBYTECODE"], "1")
            observed = subprocess.run(
                [sys.executable, "-m", "unittest", "test_exercise.py"], cwd=tool,
                text=True, encoding="utf-8", capture_output=True, check=False, env=check_environment(),
            )
            output = workspace / "cache-observed.txt"
            output.write_text(observed.stdout + observed.stderr, encoding="utf-8")
            self.assertEqual(json.loads(run(
                FINALIZE, tool, "--sandboxed-by", "codex-workspace-sandbox",
                "--review-notes", "Observed the learner-facing deterministic failure without runtime caches.",
                "--observed-exit-code", observed.returncode, "--observed-output-file", output,
            ).stdout)["status"], "verified")
            cache = tool / "__pycache__"
            cache.mkdir()
            (cache / "mutable_payload.py").write_text("print('changed outside snapshot')\n", encoding="utf-8")
            rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertEqual(rejected["status"], "rejected")
            self.assertTrue(any("Untracked runtime/cache content" in error for error in rejected["errors"]))
            manifest = json.loads((tool / "tool.json").read_text(encoding="utf-8"))
            manifest["check_command"] = "python __pycache__/mutable_payload.py"
            (tool / "tool.json").write_text(json.dumps(manifest), encoding="utf-8")
            command_rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertIn("outside the allowed", "\n".join(command_rejected["errors"]))

    def test_evidence_semantic_minimum_matches_mastery_engine(self) -> None:
        spec = importlib.util.spec_from_file_location("mastery_state_contract", COACH / "scripts" / "mastery.py")
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        sys.path.insert(0, str(CREATOR / "scripts"))
        try:
            import validate_tool
        finally:
            sys.path.pop(0)
        self.assertEqual({key: set(value) for key, value in module.KIND_DIMENSIONS.items()}, validate_tool.KIND_DIMENSIONS)

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(SCAFFOLD, "--workspace", workspace, "--id", "semantic-lab", "--type", "code_lab", "--concept", "python", "--objective", "Implement and explain a deterministic doubling function")
            tool = workspace / ".mastery" / "tools" / "semantic-lab"
            customize_code_lab(tool)
            manifest_path = tool / "tool.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["evidence"] = {"kind": "transfer", "dimensions": ["recall"], "rubric": "rubric.json"}
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertIn("semantic minimum", "\n".join(rejected["errors"]))
            manifest["evidence"] = {"kind": "exercise", "dimensions": ["application"], "rubric": "rubric.json"}
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            (tool / "test_exercise.py").write_text(
                "import unittest\nfrom exercise import learner_solution\n\n"
                "class ExerciseTests(unittest.TestCase):\n"
                "    def test_identity(self):\n"
                "        self.assertIs(learner_solution(None), None)\n",
                encoding="utf-8",
            )
            self.assertTrue(json.loads(run(VALIDATE, tool).stdout)["ok"])

    def test_registered_concept_contract_is_enforced_when_state_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(SCAFFOLD, "--workspace", workspace, "--id", "registered-board", "--type", "blackboard", "--concept", "target-concept", "--prerequisites", "prior-concept", "--objective", "Reconstruct and defend a complete invariant-preserving derivation")
            tool = workspace / ".mastery" / "tools" / "registered-board"
            customize_blackboard(tool)
            concepts_path = workspace / ".mastery" / "concepts.json"
            concepts_path.write_text(json.dumps({"schema_version": 3, "concepts": {"target-concept": {"id": "target-concept"}}}), encoding="utf-8")
            rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertEqual(rejected["concept_registration"]["missing"], ["prior-concept"])
            concepts_path.write_text(json.dumps({"schema_version": 3, "concepts": {
                "target-concept": {"id": "target-concept"},
                "prior-concept": {"id": "prior-concept"},
            }}), encoding="utf-8")
            accepted = json.loads(run(VALIDATE, tool).stdout)
            self.assertEqual(accepted["concept_registration"]["status"], "registered")

    def test_visual_scaffold_uses_loopback_http_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(SCAFFOLD, "--workspace", workspace, "--id", "loopback-lab", "--type", "visual_lab", "--concept", "optimization", "--objective", "Predict and explain convergence under a changed learning rate")
            manifest = json.loads((workspace / ".mastery" / "tools" / "loopback-lab" / "tool.json").read_text(encoding="utf-8"))
            self.assertIn("python -m http.server 8000 --bind 127.0.0.1", manifest["launch"])
            self.assertIn("http://127.0.0.1:8000/index.html", manifest["launch"])
            self.assertNotIn("file://", manifest["launch"])
            self.assertEqual(manifest["accessibility_fallback"], "accessibility-fallback.html")
            fallback = workspace / ".mastery" / "tools" / "loopback-lab" / manifest["accessibility_fallback"]
            self.assertTrue(fallback.exists())
            self.assertIn("text and table equivalent", fallback.read_text(encoding="utf-8").lower())
            self.assertIn("accessibility-fallback.html", (fallback.parent / "index.html").read_text(encoding="utf-8"))

    def test_visual_fallback_and_inspection_are_machine_gated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(SCAFFOLD, "--workspace", workspace, "--id", "inspection-gate-lab", "--type", "visual_lab", "--concept", "optimization", "--objective", "Predict and explain convergence under a changed learning rate")
            tool = workspace / ".mastery" / "tools" / "inspection-gate-lab"
            customize_visual_lab(tool)
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "structurally-valid")

            entry = tool / "index.html"
            good_entry = entry.read_text(encoding="utf-8")
            entry.write_text(good_entry.replace("accessibility-fallback.html", "missing-fallback.html"), encoding="utf-8")
            rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertEqual(rejected["status"], "rejected")
            self.assertTrue(any("does not resolve" in error for error in rejected["errors"]))
            self.assertTrue(any("must link directly" in error for error in rejected["errors"]))

            entry.write_text(good_entry, encoding="utf-8")
            fallback = tool / "accessibility-fallback.html"
            good_fallback = fallback.read_text(encoding="utf-8")
            fallback.write_text(good_fallback.replace("index.html", "missing-entry.html"), encoding="utf-8")
            closure_rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertTrue(any("missing-entry.html" in error and "does not resolve" in error for error in closure_rejected["errors"]))
            fallback.write_text(good_fallback, encoding="utf-8")
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "structurally-valid")
            failed = run(
                FINALIZE, tool, "--sandboxed-by", "codex-workspace-sandbox",
                "--review-notes", "The rendered fallback returned a 404 and the required inspection did not pass.",
                "--inspection-result", "failed",
                "--inspection-notes", "Inspection failed because the required accessibility page returned HTTP 404.",
                expect=1,
            )
            self.assertIn("cannot be verified", failed.stderr)

            finalized = json.loads(run(
                FINALIZE, tool, "--sandboxed-by", "codex-workspace-sandbox",
                "--review-notes", "Observed both interactive states and matching learner-facing text feedback.",
                "--inspection-result", "passed",
                "--inspection-notes", "Rendered initial and changed states, keyboard flow, and the linked text equivalent without missing resources.",
            ).stdout)
            self.assertEqual(finalized["status"], "verified")
            report_path = Path(finalized["report"])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["inspection"]["result"] = "failed"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "stale")

    def test_local_only_policy_is_layered_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(
                SCAFFOLD, "--workspace", workspace, "--id", "local-only-lab",
                "--type", "visual_lab", "--concept", "optimization",
                "--objective", "Predict and explain convergence under a changed learning rate",
            )
            tool = workspace / ".mastery" / "tools" / "local-only-lab"
            customize_visual_lab(tool)
            entry = tool / "index.html"
            clean = entry.read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", clean)
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "structurally-valid")

            entry.write_text(clean.replace('<meta http-equiv="Content-Security-Policy"', '<meta http-equiv="X-Disabled-Policy"', 1), encoding="utf-8")
            missing_csp = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertTrue(any("Content-Security-Policy" in error for error in missing_csp["errors"]))
            policy = re.search(r'<meta http-equiv="Content-Security-Policy"[^>]+>', clean)
            self.assertIsNotNone(policy)
            assert policy
            late_policy = clean.replace(policy.group(0), "", 1).replace("</style>", f"</style>{policy.group(0)}", 1)
            entry.write_text(late_policy, encoding="utf-8")
            late = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertTrue(any("before active content" in error for error in late["errors"]))

            remote_cases = [
                ("</script>", "async function optionalExtension(){ return import('https://example.com/extension.js'); }</script>", "dynamic import"),
                ("</script>", "navigator.sendBeacon('/telemetry', 'x');</script>", "sendBeacon"),
                ("</main>", '<object data="https://example.com/lesson.html"></object></main>', "remote executable"),
                ("</style>", "@import url('https://example.com/theme.css');</style>", "@import"),
            ]
            for marker, replacement, expected in remote_cases:
                entry.write_text(clean.replace(marker, replacement, 1), encoding="utf-8")
                rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
                self.assertIn(expected, "\n".join(rejected["errors"]))

            entry.write_text(clean.replace("</main>", '<p><a href="https://example.com/reference">Reference</a></p></main>'), encoding="utf-8")
            unsafe_link = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertTrue(any("noopener noreferrer" in error for error in unsafe_link["errors"]))
            entry.write_text(clean.replace("</main>", '<p><a href="https://example.com/reference" rel="noopener noreferrer">Reference</a></p></main>'), encoding="utf-8")
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "structurally-valid")

            entry.write_text(clean, encoding="utf-8")
            helper = tool / "helper.js"
            helper.write_text("window.localTeachingHelper = 1;\n", encoding="utf-8")
            entry.write_text(clean.replace("<script>", '<script src="helper.js"></script><script>', 1), encoding="utf-8")
            self.assertEqual(json.loads(run(VALIDATE, tool).stdout)["status"], "structurally-valid")
            helper.write_text("fetch('https://example.com/data.json');\n", encoding="utf-8")
            external_js = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertIn("fetch()", "\n".join(external_js["errors"]))

            inline = re.search(r"<script>(.*?)</script>", clean, flags=re.DOTALL)
            self.assertIsNotNone(inline)
            assert inline
            helper.write_text(inline.group(1).strip() + "\n", encoding="utf-8")
            entry.write_text(clean.replace(inline.group(0), '<script src="helper.js"></script>', 1), encoding="utf-8")
            externalized = json.loads(run(VALIDATE, tool).stdout)
            self.assertEqual(externalized["status"], "structurally-valid")

        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(
                SCAFFOLD, "--workspace", workspace, "--id", "offline-code-lab",
                "--type", "code_lab", "--concept", "python",
                "--objective", "Implement and explain a deterministic doubling function",
            )
            tool = workspace / ".mastery" / "tools" / "offline-code-lab"
            customize_code_lab(tool)
            exercise = tool / "exercise.py"
            clean = exercise.read_text(encoding="utf-8")
            exercise.write_text("import urllib3\nimport subprocess\nimport os as shell\nshell.system('offline-command')\n" + clean, encoding="utf-8")
            rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            joined = "\n".join(rejected["errors"])
            self.assertIn("urllib3", joined)
            self.assertIn("subprocess", joined)
            self.assertIn("os.system", joined)


if __name__ == "__main__":
    unittest.main()
