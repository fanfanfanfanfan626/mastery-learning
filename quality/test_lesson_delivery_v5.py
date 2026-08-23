from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COACH = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-coach"
CREATOR = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-tool-creator"
SCAFFOLD = CREATOR / "scripts" / "tool_scaffold.py"
VALIDATE = CREATOR / "scripts" / "validate_tool.py"
EVALS = ROOT / "quality" / "evals" / "plugin-evals.json"


def run(script: Path, *arguments: object, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(script), *(str(item) for item in arguments)],
        cwd=ROOT,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode != expect:
        raise AssertionError(
            f"expected {expect}, got {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def finish_scaffold(tool: Path) -> None:
    manifest_path = tool / "tool.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["build_status"] = "complete"
    manifest["interaction"].update({
        "prediction": "Predict how the output changes before moving either parameter control.",
        "learner_action": "Manipulate one parameter, inspect the chart and table, then explain the causal chain.",
        "feedback": "The synchronized chart, numeric table, and status message expose the consequence of each choice.",
        "transfer": "Repeat with a changed target pattern and defend which part of the explanation still transfers.",
    })
    manifest["inspection"]["notes"] = (
        "Inspect the initial, predicted, manipulated, guided-practice, and transfer states at desktop and 390px; "
        "also inspect keyboard focus, reduced motion, console output, and the linked text/table equivalent."
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rubric_path = tool / "rubric.json"
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    rubric["criteria"][0]["description"] = "Explain the causal chain connecting the control, model, and observed output"
    rubric["criteria"][1]["description"] = "Use the changed condition to produce and interpret the target behavior"
    rubric_path.write_text(json.dumps(rubric, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for path in tool.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".html", ".css", ".js", ".json"}:
            path.write_text(
                path.read_text(encoding="utf-8").replace("CUSTOMIZE:", "Lesson detail:"),
                encoding="utf-8",
                newline="\n",
            )


class LessonDeliveryV5Tests(unittest.TestCase):
    def test_skill_routes_rich_lessons_through_a_progressive_contract(self) -> None:
        coach = (COACH / "SKILL.md").read_text(encoding="utf-8")
        delivery = (COACH / "references" / "lesson-delivery.md").read_text(encoding="utf-8")
        creator = (CREATOR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("lesson-delivery.md", coach)
        self.assertIn("lesson_lab", creator)
        for required in [
            "current target", "preview", "20–40", "worked example", "annotated code",
            "progressive disclosure", "do not create", "reuse", "zero-baseline ladder",
            "names and assignment", "before requiring\ncollections, loops, functions",
        ]:
            self.assertIn(required, delivery.lower())

    def test_coach_trigger_metadata_covers_learning_record_lifecycle(self) -> None:
        frontmatter = (COACH / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1].lower()
        for operation in ["inspect", "export", "migrate", "delete"]:
            self.assertIn(operation, frontmatter)

    def test_bundled_scripts_use_codex_python_before_any_runtime_install(self) -> None:
        for skill in [COACH / "SKILL.md", CREATOR / "SKILL.md"]:
            content = skill.read_text(encoding="utf-8").lower()
            self.assertIn("workspace-dependency loader", content)
            self.assertIn("never download or install a python runtime", content)

    def test_conversation_evals_cover_rich_zero_baseline_and_no_spectacle(self) -> None:
        suite = json.loads(EVALS.read_text(encoding="utf-8"))
        cases = {case["id"]: case for case in suite["cases"]}
        rich = cases["follow-up-rich-zero-baseline-first-lesson"]
        self.assertEqual(rich["expected"]["activate"], ["mastery-coach", "mastery-tool-creator"])
        self.assertIn("follow-up-rich-zero-baseline-first-lesson", suite["release_policy"]["critical_case_ids"])
        simple = cases["direct-simple-learning-explanation"]
        self.assertEqual(simple["expected"]["must_not_activate"], ["mastery-tool-creator"])

    def test_lesson_lab_scaffold_has_local_progressive_course_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(
                SCAFFOLD,
                "--workspace", workspace,
                "--id", "line-learning-lesson",
                "--type", "lesson_lab",
                "--concept", "python",
                "--objective", "Trace how parameters change predictions and squared error",
                "--mode", "demonstration",
            )
            tool = workspace / ".mastery" / "tools" / "line-learning-lesson"
            manifest = json.loads((tool / "tool.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["type"], "lesson_lab")
            self.assertTrue(manifest["inspection"]["required"])
            self.assertIn("--bind 127.0.0.1", manifest["launch"])
            self.assertTrue((tool / "styles.css").is_file())
            self.assertTrue((tool / "app.js").is_file())
            self.assertTrue((tool / "accessibility-fallback.html").is_file())
            html = (tool / "index.html").read_text(encoding="utf-8")
            for section in [
                "orientation", "mental-model", "worked-example", "annotated-code",
                "interactive-model", "guided-practice", "transfer", "summary",
            ]:
                self.assertIn(f'data-lesson-section="{section}"', html)
            self.assertIn("data-session-minutes=\"30\"", html)
            self.assertIn("data-code-note", html)
            self.assertIn("accessibility-fallback.html", html)
            self.assertIn("CUSTOMIZE:", html)

    def test_lesson_lab_validation_requires_the_complete_learning_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            run(
                SCAFFOLD,
                "--workspace", workspace,
                "--id", "complete-lesson",
                "--type", "lesson_lab",
                "--concept", "python",
                "--objective", "Trace how parameters change predictions and squared error",
                "--mode", "demonstration",
            )
            tool = workspace / ".mastery" / "tools" / "complete-lesson"
            finish_scaffold(tool)
            report = json.loads(run(VALIDATE, tool).stdout)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["status"], "structurally-valid")

            entry = tool / "index.html"
            content = entry.read_text(encoding="utf-8").replace('data-lesson-section="worked-example"', "")
            entry.write_text(content + '\n<!-- data-lesson-section="worked-example" -->\n', encoding="utf-8")
            rejected = json.loads(run(VALIDATE, tool, expect=1).stdout)
            self.assertIn("worked-example", "\n".join(rejected["errors"]))


if __name__ == "__main__":
    unittest.main()
