from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "quality" / "evals" / "plugin-evals.json"
if str(ROOT / "quality") not in sys.path:
    sys.path.insert(0, str(ROOT / "quality"))

from eval_audit import (
    audit_release_evidence,
    canonical_suite_hash,
    load_json,
    result_template,
    validate_result,
    validate_suite,
)


class ConversationEvalContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = load_json(EVALS)

    def write_run(
        self,
        root: Path,
        directory: str,
        run_id: str,
        *,
        failed_cases: set[str] | None = None,
        blocked: bool = False,
        transcript_marker: str | None = None,
    ) -> Path:
        failed_cases = failed_cases or set()
        result = result_template(
            self.suite,
            run_id=run_id,
            surface="Codex synthetic release test",
            model="synthetic-model",
            evaluator="automated contract test",
        )
        sequence = sum(1 for entry in root.iterdir() if entry.is_dir())
        result["run"]["recorded_at"] = f"2026-08-23T00:00:{sequence:02d}Z"
        result_path = root / directory / "result.json"
        result_path.parent.mkdir(parents=True)
        transcripts = result_path.parent / "transcripts"
        transcripts.mkdir()
        cases = {case["id"]: case for case in self.suite["cases"]}
        for observed in result["results"]:
            if blocked:
                observed["status"] = "blocked"
                observed["notes"] = "Synthetic environment unavailable"
                continue
            case = cases[observed["case_id"]]
            observed["status"] = "fail" if observed["case_id"] in failed_cases else "pass"
            observed["activated_skills"] = case["expected"]["activate"]
            for index, criterion in enumerate(observed["criteria"]):
                criterion["passed"] = not (observed["status"] == "fail" and index == 0)
                criterion["evidence"] = "Synthetic release-policy evidence"
            transcript = transcripts / f"{observed['case_id']}.md"
            marker = transcript_marker if transcript_marker is not None else directory
            transcript.write_text(
                f"# Synthetic transcript {marker}\n",
                encoding="utf-8",
                newline="\n",
            )
            observed["transcript_path"] = f"transcripts/{transcript.name}"
        result_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return result_path

    def test_suite_covers_official_request_classes(self) -> None:
        self.assertEqual(validate_suite(self.suite), [])
        classes = {case["class"] for case in self.suite["cases"]}
        self.assertEqual(classes, {"direct", "indirect", "follow-up", "negative", "boundary"})
        self.assertGreaterEqual(len(self.suite["cases"]), 15)
        policy = self.suite["release_policy"]
        self.assertEqual(policy["minimum_complete_runs"], 3)
        self.assertEqual(policy["minimum_overall_pass_rate"], {"numerator": 9, "denominator": 10})
        self.assertEqual(policy["minimum_per_case_pass_rate"], {"numerator": 2, "denominator": 3})
        self.assertEqual(
            set(policy["critical_case_ids"]),
            {
                "follow-up-onboarding-one-reply",
                "follow-up-rich-post-orientation-lesson",
                "follow-up-ai-course-starts-with-experience",
                "follow-up-feedback-stays-in-classroom",
                "follow-up-resume-from-another-directory",
                "follow-up-confidence-is-not-mastery",
                "boundary-scope-needs-confirmation",
                "boundary-answer-leakage-request",
                "boundary-multiple-learning-workspaces",
                "boundary-silent-self-modification",
                "boundary-learning-data-deletion",
            },
        )
        manifest = json.loads(
            (ROOT / "plugins" / "mastery-tutor" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.suite["plugin_version"], manifest["version"])

    def test_suite_hash_is_formatting_independent(self) -> None:
        reformatted = json.loads(json.dumps(self.suite, ensure_ascii=False, indent=7))
        self.assertEqual(canonical_suite_hash(self.suite), canonical_suite_hash(reformatted))

    def test_complete_passing_result_requires_traceable_evidence(self) -> None:
        result = result_template(
            self.suite,
            run_id="eval-contract-test",
            surface="Codex test harness",
            model="synthetic-model",
            evaluator="automated contract test",
        )
        with tempfile.TemporaryDirectory() as temporary:
            result_path = Path(temporary) / "result.json"
            transcripts = result_path.parent / "transcripts"
            transcripts.mkdir()
            cases = {case["id"]: case for case in self.suite["cases"]}
            for observed in result["results"]:
                case = cases[observed["case_id"]]
                observed["status"] = "pass"
                observed["activated_skills"] = case["expected"]["activate"]
                for criterion in observed["criteria"]:
                    criterion["passed"] = True
                    criterion["evidence"] = "Synthetic contract evidence"
                transcript = transcripts / f"{observed['case_id']}.md"
                transcript.write_text("# Synthetic transcript\n", encoding="utf-8", newline="\n")
                observed["transcript_path"] = f"transcripts/{transcript.name}"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            errors, counts = validate_result(
                self.suite,
                result,
                result_path=result_path,
                require_complete=True,
            )
        self.assertEqual(errors, [])
        self.assertEqual(counts["pass"], len(self.suite["cases"]))

    def test_false_pass_and_suite_drift_are_rejected(self) -> None:
        result = result_template(
            self.suite,
            run_id="false-pass-test",
            surface="Codex test harness",
            model="synthetic-model",
            evaluator="automated contract test",
        )
        first = result["results"][0]
        first["status"] = "pass"
        first["transcript_path"] = "C:/outside.md"
        errors, _ = validate_result(self.suite, result)
        joined = "\n".join(errors)
        self.assertIn("expected skill activation", joined)
        self.assertIn("safe relative transcript_path", joined)
        self.assertIn("every criterion", joined)

        result["suite_sha256"] = "0" * 64
        errors, _ = validate_result(self.suite, result)
        self.assertIn("suite_sha256 does not match", "\n".join(errors))

    def test_missing_request_class_fails_suite_validation(self) -> None:
        broken = copy.deepcopy(self.suite)
        broken["cases"] = [case for case in broken["cases"] if case["class"] != "negative"]
        self.assertIn("does not cover required request classes", "\n".join(validate_suite(broken)))

    def test_release_policy_schema_is_strict(self) -> None:
        broken = copy.deepcopy(self.suite)
        broken["release_policy"]["minimum_complete_runs"] = 1
        broken["release_policy"]["minimum_overall_pass_rate"] = {"numerator": 1, "denominator": 2}
        broken["release_policy"]["minimum_per_case_pass_rate"] = {"numerator": 1, "denominator": 2}
        broken["release_policy"]["critical_case_ids"].remove("boundary-learning-data-deletion")
        broken["release_policy"]["critical_case_ids"].append("unknown-case")
        joined = "\n".join(validate_suite(broken))
        self.assertIn("integer >= 3", joined)
        self.assertIn("cannot be lower than 9/10", joined)
        self.assertIn("cannot be lower than 2/3", joined)
        self.assertIn("unknown cases", joined)
        self.assertIn("missing required cases", joined)

    def test_release_evidence_gate_rejects_missing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = audit_release_evidence(self.suite, Path(temporary), minimum_complete_runs=1)
        self.assertFalse(report["ok"])
        self.assertIn("need at least 3", "\n".join(report["errors"]))
        self.assertEqual(report["release_policy"]["effective_minimum_complete_runs"], 3)

    def test_release_evidence_gate_rejects_an_all_blocked_template(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_run(root, "blocked-run", "blocked-run", blocked=True)
            report = audit_release_evidence(self.suite, root)
        self.assertFalse(report["ok"])
        self.assertIn("cannot contain blocked", "\n".join(report["errors"]))

    def test_release_evidence_accepts_three_quality_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_run(root, "run-001", "run-001", failed_cases={"direct-broad-learning-goal"})
            self.write_run(root, "run-002", "run-002", failed_cases={"indirect-study-is-not-sticking"})
            self.write_run(root, "run-003", "run-003")
            report = audit_release_evidence(self.suite, root)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["complete_runs"], 3)
        self.assertGreaterEqual(report["overall_pass_rate"], 0.9)

    def test_release_evidence_rejects_a_critical_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.write_run(
                root,
                "run-001",
                "run-001",
                failed_cases={"boundary-learning-data-deletion"},
            )
            self.write_run(root, "run-002", "run-002")
            self.write_run(root, "run-003", "run-003")
            report = audit_release_evidence(self.suite, root)
        self.assertFalse(report["ok"])
        self.assertIn("must pass every complete run", "\n".join(report["errors"]))

    def test_release_evidence_rejects_low_pass_rates(self) -> None:
        all_cases = {case["id"] for case in self.suite["cases"]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(1, 4):
                self.write_run(root, f"run-{index:03d}", f"run-{index:03d}", failed_cases=all_cases)
            report = audit_release_evidence(self.suite, root)
        self.assertFalse(report["ok"])
        self.assertIn("overall case pass rate", "\n".join(report["errors"]))

    def test_release_evidence_uses_exact_nine_tenths_boundary(self) -> None:
        critical = set(self.suite["release_policy"]["critical_case_ids"])
        ordinary = [case["id"] for case in self.suite["cases"] if case["id"] not in critical]
        run_count = 10
        total_observations = len(self.suite["cases"]) * run_count
        self.assertEqual(total_observations % 10, 0)
        exact_failure_count = total_observations // 10

        def report_with_failures(root: Path, failure_count: int) -> dict[str, object]:
            assignments = [set() for _ in range(run_count)]
            for slot in range(failure_count):
                assignments[slot // len(ordinary)].add(ordinary[slot % len(ordinary)])
            for index, assigned in enumerate(assignments):
                self.write_run(
                    root,
                    f"run-{index + 1:03d}",
                    f"run-{index + 1:03d}",
                    failed_cases=assigned,
                )
            return audit_release_evidence(self.suite, root)

        with tempfile.TemporaryDirectory() as exact_temporary:
            exact = report_with_failures(Path(exact_temporary), exact_failure_count)
        with tempfile.TemporaryDirectory() as below_temporary:
            below = report_with_failures(Path(below_temporary), exact_failure_count + 1)
        self.assertTrue(exact["ok"], exact)
        self.assertEqual(exact["overall_pass_rate"], 0.9)
        self.assertFalse(below["ok"])
        self.assertIn("below required 9/10", "\n".join(below["errors"]))

    def test_release_evidence_rejects_duplicate_run_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(1, 4):
                self.write_run(root, f"run-{index:03d}", "duplicate-run")
            report = audit_release_evidence(self.suite, root)
        self.assertFalse(report["ok"])
        self.assertIn("duplicate run.id", "\n".join(report["errors"]))

    def test_release_evidence_rejects_duplicate_transcript_sets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(1, 4):
                self.write_run(
                    root,
                    f"run-{index:03d}",
                    f"run-{index:03d}",
                    transcript_marker="copied-evidence",
                )
            report = audit_release_evidence(self.suite, root)
        self.assertFalse(report["ok"])
        self.assertIn("duplicate transcript evidence fingerprint", "\n".join(report["errors"]))

    def test_release_evidence_rejects_unreferenced_or_renamed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(1, 4):
                self.write_run(root, f"run-{index:03d}", f"run-{index:03d}")
            (root / "run-001" / "attempt.json").write_text("{}\n", encoding="utf-8")
            (root / "ignored").mkdir()
            (root / "ignored" / "attempt.json").write_text("{}\n", encoding="utf-8")
            report = audit_release_evidence(self.suite, root)
        self.assertFalse(report["ok"])
        joined = "\n".join(report["errors"])
        self.assertIn("unreferenced files", joined)
        self.assertIn("must contain a regular result.json", joined)

    def test_result_cli_requires_completeness_by_default(self) -> None:
        result = result_template(
            self.suite,
            run_id="work-in-progress",
            surface="Codex test harness",
            model="synthetic-model",
            evaluator="automated contract test",
        )
        with tempfile.TemporaryDirectory() as temporary:
            result_path = Path(temporary) / "result.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            command = [sys.executable, str(ROOT / "quality" / "eval_audit.py"), "result", str(EVALS), str(result_path)]
            strict = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            incomplete = subprocess.run(
                [*command, "--allow-incomplete"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertEqual(strict.returncode, 1)
        self.assertEqual(incomplete.returncode, 0)

    def test_init_result_enforces_run_directory_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = [
                sys.executable,
                str(ROOT / "quality" / "eval_audit.py"),
                "init-result",
                str(EVALS),
            ]
            options = [
                "--run-id",
                "run-001",
                "--surface",
                "Codex test harness",
                "--model",
                "synthetic-model",
                "--evaluator",
                "automated contract test",
            ]
            invalid = subprocess.run(
                [*base, str(root / "wrong-directory" / "result.json"), *options],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            valid = subprocess.run(
                [*base, str(root / "run-001" / "result.json"), *options],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(valid.returncode, 0)


if __name__ == "__main__":
    unittest.main()
