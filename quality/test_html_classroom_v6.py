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
COACH = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-coach"
CREATOR = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-tool-creator"
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
    return {
        "schema_version": 1,
        "page_id": "ai-landscape-start",
        "kind": "orientation",
        "language": "zh-CN",
        "course": "AI Mastery",
        "progress": "第 0 课 · 建立全景",
        "eyebrow": "从目标开始，而不是从公式开始",
        "title": "人工智能到底在学什么？",
        "lead": "先建立 AI、机器学习、深度学习与大模型之间的地图，再进入代码和数学。",
        "meta": [
            {"label": "当前目标", "value": "AI 全景"},
            {"label": "预计时间", "value": "20 分钟"},
        ],
        "sections": [
            {
                "type": "map",
                "title": "你将走过的四层地图",
                "items": [
                    {"name": "AI", "description": "让机器完成需要判断、规划或生成的任务。"},
                    {"name": "机器学习", "description": "从例子中形成可评价的行为。"},
                    {"name": "深度学习", "description": "用多层神经网络学习表示。"},
                    {"name": "大模型", "description": "在广泛数据上训练并适配多种任务。"},
                ],
            },
            {
                "type": "comparison",
                "title": "规则与学习",
                "headers": ["系统", "行为来源", "检查方式"],
                "rows": [
                    ["规则程序", "开发者写出的条件", "测试规则边界"],
                    ["学习系统", "数据与训练共同形成", "评测代表性行为"],
                ],
            },
            {
                "type": "callout",
                "tone": "insight",
                "title": "为什么不先讲损失",
                "body": ["只有先知道模型在做什么以及为什么需要改进，衡量错误才有意义。"],
            },
        ],
        "action": {
            "title": "先判断一个系统",
            "prompt": "垃圾邮件系统完全由人工写下关键词规则，它更接近规则程序还是机器学习？为什么？",
            "response_hint": "写出你的选择和一句理由",
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
                'data-classroom-block="map"',
                'data-classroom-block="comparison"',
                'data-classroom-block="callout"',
                "script-src 'none'",
                "人工智能到底在学什么？",
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
            self.assertIn('data-classroom-block="choices"', page)
            self.assertIn('data-classroom-block="details"', page)
            self.assertLess(page.index('data-classroom-action="one"'), page.index('data-classroom-block="choices"'))
            self.assertNotIn("Now · one action", page)

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
