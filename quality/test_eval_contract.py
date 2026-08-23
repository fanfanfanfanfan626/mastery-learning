from __future__ import annotations

import copy
import json
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

    def test_suite_covers_official_request_classes(self) -> None:
        self.assertEqual(validate_suite(self.suite), [])
        classes = {case["class"] for case in self.suite["cases"]}
        self.assertEqual(classes, {"direct", "indirect", "follow-up", "negative", "boundary"})
        self.assertGreaterEqual(len(self.suite["cases"]), 15)
        manifest = json.loads(
            (ROOT / "plugins" / "mastery-learning" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
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

    def test_release_evidence_gate_rejects_missing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = audit_release_evidence(self.suite, Path(temporary), minimum_complete_runs=1)
        self.assertFalse(report["ok"])
        self.assertIn("need at least 1", "\n".join(report["errors"]))

    def test_release_evidence_gate_rejects_an_all_blocked_template(self) -> None:
        result = result_template(
            self.suite,
            run_id="blocked-run",
            surface="Codex test harness",
            model="synthetic-model",
            evaluator="automated contract test",
        )
        for observed in result["results"]:
            observed["status"] = "blocked"
            observed["notes"] = "Synthetic environment unavailable"
        with tempfile.TemporaryDirectory() as temporary:
            result_path = Path(temporary) / "run" / "result.json"
            result_path.parent.mkdir()
            result_path.write_text(json.dumps(result), encoding="utf-8")
            report = audit_release_evidence(self.suite, Path(temporary), minimum_complete_runs=1)
        self.assertFalse(report["ok"])
        self.assertIn("cannot contain blocked", "\n".join(report["errors"]))


if __name__ == "__main__":
    unittest.main()
