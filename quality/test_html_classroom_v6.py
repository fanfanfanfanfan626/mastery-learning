from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
COACH = ROOT / "skills" / "mastery-coach"
CREATOR = ROOT / "skills" / "mastery-tool-creator"
RENDER = COACH / "scripts" / "render_classroom.py"
SERVER = COACH / "scripts" / "serve_classroom.py"
CURRICULUM = COACH / "assets" / "curricula" / "ml-ai-llm.json"


def run_render(spec: dict[str, object], output_dir: Path, *, expect: int = 0) -> subprocess.CompletedProcess[str]:
    spec_path = output_dir.parent / "classroom-spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(RENDER), "--spec", str(spec_path), "--output-dir", str(output_dir)],
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


def run_workspace_render(
    spec: dict[str, object], workspace: Path, *, expect: int = 0
) -> subprocess.CompletedProcess[str]:
    spec_path = workspace.parent / "workspace-classroom-spec.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(RENDER), "--spec", str(spec_path), "--workspace", str(workspace)],
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


def orientation_spec() -> dict[str, object]:
    action_prompt = "按照‘标题含有中奖才拦截’这条规则，‘限时福利，马上领取’会被拦截还是放行？"
    return {
        "schema_version": 1,
        "page_id": "spam-rule-first-step",
        "kind": "orientation",
        "language": "zh-CN",
        "course": "Mastery Tutor",
        "progress": "第 1 步 · 先看规则会漏掉什么",
        "eyebrow": "先遇到问题，再给它名字",
        "title": "为什么有些垃圾邮件能绕过规则？",
        "lead": "今天只做一件事：看清电脑是在照规则办事，还是能从例子里改变判断。",
        "meta": [
            {"label": "预计时间", "value": "5 分钟"},
            {"label": "新词", "value": "暂时 0 个"},
        ],
        "sections": [
            {
                "type": "callout",
                "tone": "example",
                "title": "一条很简单的拦截规则",
                "body": ["如果邮件标题里出现‘中奖’，系统就拦截；否则放行。电脑只负责照做。"],
            },
            {
                "type": "comparison",
                "title": "把规则放到两个例子上",
                "headers": ["邮件标题", "有没有‘中奖’", "按这条规则会怎样"],
                "rows": [
                    ["恭喜中奖，点击领取", "有", "拦截"],
                    ["限时福利，马上领取", "没有", "等你判断"],
                ],
            },
            {
                "type": "details",
                "title": "完整路线以后再展开",
                "body": ["后面会走到机器学习、深度学习和大模型；现在不需要背这些名字。"],
            },
        ],
        "teaching_turn": {
            "schema_version": 1,
            "learner_problem": "为什么有些垃圾邮件能绕过手写规则？",
            "current_target": "根据一条明确规则追踪系统对新例子的判断。",
            "mental_move": "predict",
            "new_terms": [],
            "answer_options": ["拦截", "放行"],
            "concrete_experience": "比较两封措辞不同但目的相近的邮件。",
            "example": {"case": "标题含有‘中奖’，规则会拦截。", "deciding_feature": "标题是否含有中奖"},
            "counterexample": {"case": "标题不含‘中奖’，规则会放行。", "deciding_feature": "标题是否含有中奖"},
            "visual": {"form": "三列表格显示标题、规则命中和结果。", "deciding_feature": "标题是否含有中奖"},
            "action": action_prompt,
            "evidence_boundary": {
                "can_show": "能否在当前例子上准确执行给定规则。",
                "not_observed": ["不能证明能设计规则。", "不能证明理解机器学习。"],
            },
            "feedback_plan": {
                "earliest_error": "把邮件看起来可疑和规则实际检查的文字混在一起。",
                "first_hint": "只检查标题里有没有‘中奖’两个字。",
                "retry_shape": "保留原邮件和规则，再让学习者只判断拦截或放行。",
            },
        },
        "action": {
            "title": "只判断第二封邮件",
            "prompt": action_prompt,
            "response_hint": "只回复‘拦截’或‘放行’",
        },
        "references": [{"title": "Dive into Deep Learning", "url": "https://d2l.ai/"}],
    }


class HtmlClassroomV6Tests(unittest.TestCase):
    def test_renderer_builds_polished_local_only_classroom(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "classroom"
            report = json.loads(run_render(orientation_spec(), output).stdout)
            self.assertTrue(report["ok"])
            self.assertEqual(report["url_path"], "/index.html")
            page = (output / "index.html").read_text(encoding="utf-8")
            css = (output / "assets" / "classroom.css").read_text(encoding="utf-8")
            for marker in [
                'data-turn-kind="orientation"',
                'data-classroom-action="one"',
                'data-classroom-block="comparison"',
                'data-classroom-block="callout"',
                'data-classroom-block="details"',
                "script-src 'none'",
                "为什么有些垃圾邮件能绕过规则？",
            ]:
                self.assertIn(marker, page)
            for marker in [
                "prefers-color-scheme: dark", "prefers-reduced-motion", "@media print",
                "overflow-wrap: anywhere", "min-width: 9rem",
            ]:
                self.assertIn(marker, css)
            self.assertNotIn("<script", page.lower())
            self.assertNotIn("http.server", page)

    def test_renderer_escapes_learner_content_and_rejects_unsafe_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = orientation_spec()
            spec["title"] = '<script>alert("x")</script>'
            run_render(spec, root / "safe")
            page = (root / "safe" / "index.html").read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;", page)
            self.assertNotIn('<script>alert("x")</script>', page)

            unsafe_source = orientation_spec()
            unsafe_source["references"] = [{"title": "bad", "url": "http://example.com/"}]
            failed = run_render(unsafe_source, root / "unsafe-source", expect=1)
            self.assertIn("HTTPS source", failed.stderr)

            unsafe_artifact = orientation_spec()
            unsafe_artifact["sections"].append({
                "type": "artifact", "title": "escape", "summary": "unsafe", "href": "../../secret",
                "label": "open",
            })
            failed = run_render(unsafe_artifact, root / "unsafe-artifact", expect=1)
            self.assertIn("assigned loopback", failed.stderr)

            missing_tool = orientation_spec()
            missing_tool["sections"].append({
                "type": "artifact", "title": "missing", "summary": "not verified",
                "href": "../tools/missing/index.html", "label": "open",
            })
            failed = run_render(missing_tool, root / "missing-tool", expect=1)
            self.assertIn("assigned loopback", failed.stderr)

            loopback_tool = orientation_spec()
            loopback_tool["sections"].append({
                "type": "artifact", "title": "lab", "summary": "verified separately",
                "href": "http://127.0.0.1:49152/index.html", "label": "open",
            })
            run_render(loopback_tool, root / "loopback-tool")

    def test_onboarding_localizes_shell_and_places_action_before_optional_depth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            spec = orientation_spec()
            spec["kind"] = "onboarding"
            spec.pop("teaching_turn")
            spec.pop("progress", None)
            spec["sections"] = [
                {
                    "type": "choices", "title": "一次说清你的偏好", "items": [
                        {"id": "pace", "prompt": "节奏", "options": ["引导式", "项目式"]},
                        {"id": "checks", "prompt": "检测", "options": ["轻量练习", "里程碑测验"]},
                    ],
                },
                {"type": "details", "title": "可选说明", "body": ["这些偏好只是可修改的教学假设。"]},
            ]
            output = Path(temporary) / "classroom"
            run_render(spec, output)
            page = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("AI 教学 Skill · 本地课堂", page)
            self.assertIn("当前学习回合", page)
            self.assertNotIn("Current learning turn", page)
            self.assertIn('data-classroom-block="choices"', page)
            self.assertIn('data-classroom-block="details"', page)
            self.assertLess(page.index('data-classroom-block="choices"'), page.index('data-classroom-action="one"'))
            self.assertLess(page.index('data-classroom-action="one"'), page.index('data-classroom-block="details"'))
            self.assertIn('<fieldset data-choice-group="pace">', page)
            self.assertIn('<legend>节奏</legend>', page)
            self.assertIn('type="radio" name="choice-0-pace"', page)
            self.assertIn('<label class="choice-option" for="choice-0-0-0">', page)
            self.assertIn('class="choice-fallback"', page)
            self.assertNotIn("<form", page.lower())
            self.assertNotIn("Now · one action", page)

    def test_new_material_is_modeled_before_the_single_action(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "classroom"
            run_render(orientation_spec(), output)
            page = (output / "index.html").read_text(encoding="utf-8")
            css = (output / "assets" / "classroom.css").read_text(encoding="utf-8")
            self.assertEqual(page.count('data-classroom-action="one"'), 1)
            self.assertLess(page.index('class="lesson-hero"'), page.index('data-classroom-action="one"'))
            self.assertLess(page.index('data-classroom-block="comparison"'), page.index('data-classroom-action="one"'))
            self.assertIn('class="turn-intro turn-intro--hero-only"', page)
            self.assertIn(".turn-intro {", css)
            self.assertIn(".turn-intro--hero-only { display: block; }", css)

    def test_choices_are_native_no_script_controls_with_escaped_long_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            long_option = "x" * 420 + "<guided>"
            spec = orientation_spec()
            spec["kind"] = "onboarding"
            spec.pop("teaching_turn")
            spec["language"] = "en"
            spec["sections"] = [{
                "type": "choices",
                "title": "Choose a route",
                "items": [{
                    "id": "route",
                    "prompt": "Starting route",
                    "options": [long_option, "Project first"],
                }],
            }]
            output = Path(temporary) / "classroom"
            run_render(spec, output)
            page = (output / "index.html").read_text(encoding="utf-8")
            css = (output / "assets" / "classroom.css").read_text(encoding="utf-8")
            self.assertIn('<div class="launch-choices" role="group" aria-label="Onboarding choices">', page)
            self.assertIn('<fieldset data-choice-group="route">', page)
            self.assertIn('id="choice-0-0-0" type="radio" name="choice-0-route"', page)
            self.assertIn('&lt;guided&gt;', page)
            self.assertNotIn('<guided>', page)
            self.assertIn("Selections are not submitted or saved by this page.", page)
            self.assertIn("form-action 'none'", page)
            self.assertNotIn("<script", page.lower())
            self.assertIn("overflow-wrap: anywhere", css)
            self.assertIn("grid-template-columns: auto minmax(0, 1fr)", css)

    def test_details_use_native_progressive_disclosure_and_matching_styles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            spec = orientation_spec()
            spec["sections"].append({
                "type": "details",
                "title": "Optional derivation",
                "body": ["Hidden until the learner chooses to open it."],
            })
            output = Path(temporary) / "classroom"
            run_render(spec, output)
            page = (output / "index.html").read_text(encoding="utf-8")
            css = (output / "assets" / "classroom.css").read_text(encoding="utf-8")
            self.assertIn("<details><summary>", page)
            self.assertIn('<div class="details-body">', page)
            self.assertNotIn("<details open", page)
            self.assertIn(".optional-depth details[open] summary", css)
            self.assertIn(".details-body", css)

    def test_orientation_and_lesson_require_real_semantic_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            too_small = orientation_spec()
            too_small["sections"] = [{"type": "prose", "title": "short", "body": ["too short"]}]
            failed = run_render(too_small, root / "small", expect=1)
            self.assertIn("at least 2 semantic sections", failed.stderr)

            lesson = orientation_spec()
            lesson["kind"] = "lesson"
            lesson["sections"] = [
                {"type": "prose", "title": "why", "body": ["建立上下文。"]},
                {"type": "steps", "title": "model", "items": [
                    {"title": "观察", "body": "先看输入。"}, {"title": "解释", "body": "再连接机制。"},
                ]},
                {"type": "details", "title": "depth", "body": ["可选推导。"]},
            ]
            run_render(lesson, root / "lesson")

    def test_teaching_turn_is_machine_validated_and_bound_to_rendered_page(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = orientation_spec()
            run_render(valid, root / "valid")
            page = (root / "valid" / "index.html").read_text(encoding="utf-8")
            self.assertRegex(page, r'data-teaching-turn-sha256="[0-9a-f]{64}"')

            too_many_terms = orientation_spec()
            too_many_terms["teaching_turn"]["new_terms"] = [
                {"term": f"term-{index}", "meaning": "meaning"} for index in range(4)
            ]
            failed = run_render(too_many_terms, root / "terms", expect=1)
            self.assertIn("0..3 term objects", failed.stderr)

            mismatched_action = orientation_spec()
            mismatched_action["teaching_turn"]["action"] = "A different hidden task"
            failed = run_render(mismatched_action, root / "action", expect=1)
            self.assertIn("exactly match action.prompt", failed.stderr)

            mismatched_visual = orientation_spec()
            mismatched_visual["teaching_turn"]["visual"]["deciding_feature"] = "邮件长度"
            failed = run_render(mismatched_visual, root / "visual", expect=1)
            self.assertIn("share one deciding_feature", failed.stderr)

    def test_feedback_preserves_attempt_context_and_enforces_hint_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            feedback = orientation_spec()
            feedback["kind"] = "feedback"
            feedback["page_id"] = "spam-rule-first-retry"
            feedback["teaching_turn"]["mental_move"] = "repair"
            feedback["teaching_turn"]["feedback_plan"]["first_hint"] = "只检查标题里有没有‘中奖’两个字。"
            feedback["feedback_context"] = {
                "attempt_id": "spam-attempt-one",
                "original_task": feedback["action"]["prompt"],
                "learner_response": "拦截，因为它看起来很可疑。",
                "earliest_error": "使用了直觉，而不是题目给出的文字规则。",
                "hint_level": 1,
                "hint": "只检查标题里有没有‘中奖’两个字。",
                "solution_revealed": False,
            }
            feedback["action"]["response_hint"] = "格式：结果 + 一行依据"
            run_render(feedback, root / "feedback")
            page = (root / "feedback" / "index.html").read_text(encoding="utf-8")
            css = (root / "feedback" / "assets" / "classroom.css").read_text(encoding="utf-8")
            for marker in ["刚才的任务", "你的回答", "最早需要修正的地方", "本轮提示 · 1/5"]:
                self.assertIn(marker, page)
            self.assertLess(page.index('data-classroom-action="one"'), page.index('class="lesson-hero"'))
            self.assertLess(page.index("刚才的任务"), page.index(feedback["action"]["prompt"]))
            self.assertIn('body[data-turn-kind="feedback"] .turn-intro', css)
            self.assertIn('body[data-turn-kind="feedback"] .feedback-context', css)

            missing = orientation_spec()
            missing["kind"] = "feedback"
            failed = run_render(missing, root / "missing", expect=1)
            self.assertIn("require a feedback_context", failed.stderr)

            leaked = feedback.copy()
            leaked["feedback_context"] = dict(feedback["feedback_context"])
            leaked["feedback_context"]["solution_revealed"] = True
            failed = run_render(leaked, root / "leaked", expect=1)
            self.assertIn("must use hint level 5", failed.stderr)

            leaked_format = orientation_spec()
            leaked_format["kind"] = "feedback"
            leaked_format["page_id"] = "spam-rule-leaked-format"
            leaked_format["teaching_turn"]["mental_move"] = "repair"
            leaked_format["feedback_context"] = dict(feedback["feedback_context"])
            leaked_format["action"]["response_hint"] = "例如：放行，因为……"
            failed = run_render(leaked_format, root / "leaked-format", expect=1)
            self.assertIn("must not reveal answer option", failed.stderr)

    def test_dedicated_server_is_no_cache_and_cannot_expose_learning_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            workspace.mkdir()
            report = json.loads(run_workspace_render(orientation_spec(), workspace).stdout)
            classroom = Path(report["serve_root"])
            fixed = subprocess.run(
                [sys.executable, str(SERVER), "--root", str(classroom), "--port", "8000"],
                cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=False,
            )
            self.assertNotEqual(fixed.returncode, 0)
            self.assertIn("operating system assigns", fixed.stderr)
            profile = workspace / ".mastery" / "profile.json"
            profile.write_text('{"goal":"private learner goal"}', encoding="utf-8")
            process = subprocess.Popen(
                [sys.executable, "-u", str(SERVER), "--root", str(classroom), "--port", "0"],
                cwd=ROOT,
                env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                assert process.stdout is not None
                server = json.loads(process.stdout.readline())
                self.assertEqual(server["pid"], process.pid)
                with urlopen(server["url"], timeout=5) as response:
                    first = response.read().decode("utf-8")
                    self.assertIn("no-store", response.headers["Cache-Control"])
                    modified = response.headers.get("Last-Modified")
                with self.assertRaises(HTTPError) as missing:
                    urlopen(f'http://127.0.0.1:{server["port"]}/../profile.json', timeout=5)
                self.assertEqual(missing.exception.code, 404)

                changed = orientation_spec()
                changed["title"] = "同一秒也必须看到新页面"
                run_workspace_render(changed, workspace)
                request = Request(server["url"], headers={"If-Modified-Since": modified or ""})
                with urlopen(request, timeout=5) as response:
                    current = response.read().decode("utf-8")
                    self.assertEqual(response.status, 200)
                    self.assertIn("同一秒也必须看到新页面", current)
                    self.assertNotEqual(first, current)
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()
            self.assertIsNotNone(process.returncode)
            with socket.socket() as probe:
                probe.settimeout(1)
                self.assertNotEqual(probe.connect_ex(("127.0.0.1", server["port"])), 0)

    def test_workspace_renderer_refuses_a_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = root / "workspace"
            outside = root / "outside"
            workspace.mkdir()
            outside.mkdir()
            try:
                (workspace / ".mastery").symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory symlinks are unavailable: {error}")
            failed = run_workspace_render(orientation_spec(), workspace, expect=1)
            self.assertIn("remain inside", failed.stderr)

    def test_coach_contract_makes_html_a_hard_interface_invariant(self) -> None:
        skill = (COACH / "SKILL.md").read_text(encoding="utf-8").lower()
        classroom = (COACH / "references" / "html-classroom.md").read_text(encoding="utf-8").lower()
        for marker in [
            "html classroom",
            "every learner-facing onboarding, lesson, feedback, review, and close",
            "do not fall back to learner-facing markdown",
            "never ask the learner to invoke an internal skill",
        ]:
            self.assertIn(marker, skill)
        for marker in [
            "every active mastery coach turn",
            "never ask the learner to run a server",
            "do not store the learner's full conversation",
            "exactly one learner action",
        ]:
            self.assertIn(marker, classroom)

    def test_tool_creator_uses_dynamic_internal_loopback_launch(self) -> None:
        creator = (CREATOR / "SKILL.md").read_text(encoding="utf-8")
        scaffold = (CREATOR / "scripts" / "tool_scaffold.py").read_text(encoding="utf-8")
        for content in [creator, scaffold]:
            self.assertIn("http.server 0 --bind 127.0.0.1", content)
            self.assertNotIn("http.server 8000", content)
        self.assertIn("Never ask the learner to run a command", creator)

    def test_every_builtin_target_profile_includes_ai_landscape(self) -> None:
        pack = json.loads(CURRICULUM.read_text(encoding="utf-8"))
        concepts = {item["id"]: item for item in pack["concepts"]}
        self.assertIn("ai-landscape", concepts)
        self.assertEqual(concepts["ai-landscape"]["prerequisites"], [])
        for profile, targets in pack["target_profiles"].items():
            self.assertIn("ai-landscape", targets, profile)


if __name__ == "__main__":
    unittest.main()
