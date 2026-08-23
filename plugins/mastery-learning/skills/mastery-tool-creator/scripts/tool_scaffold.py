#!/usr/bin/env python3
"""Create a safe, auditable scaffold for a Mastery Learning teaching tool."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tool_common import register_catalog_entry

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TOOL_TYPES = {
    "code_lab", "visual_lab", "lesson_lab", "simulation_3d", "blackboard", "notebook",
    "quiz", "slide_deck", "document", "project_lab",
}
MODES = {"coach", "demonstration", "pair", "exam", "review"}
ENTRYPOINTS = {
    "code_lab": "exercise.py",
    "visual_lab": "index.html",
    "lesson_lab": "index.html",
    "simulation_3d": "index.html",
    "blackboard": "blackboard.md",
    "notebook": "lab.ipynb",
    "quiz": "quiz.md",
    "slide_deck": "deck-brief.md",
    "document": "document-brief.md",
    "project_lab": "README.md",
}
EVIDENCE = {
    "code_lab": ("exercise", ["application", "debugging"]),
    "visual_lab": ("transfer", ["conceptual", "application", "transfer"]),
    "lesson_lab": ("exercise", ["conceptual", "application"]),
    "simulation_3d": ("transfer", ["conceptual", "application", "transfer"]),
    "blackboard": ("explain", ["recall", "conceptual"]),
    "notebook": ("exercise", ["application", "debugging"]),
    "quiz": ("review", ["recall", "conceptual"]),
    "slide_deck": ("explain", ["conceptual"]),
    "document": ("explain", ["conceptual"]),
    "project_lab": ("project", ["application", "debugging", "transfer", "creation"]),
}
SCHEMA_VERSION = 3
RENDER_TYPES = {"visual_lab", "lesson_lab", "simulation_3d", "slide_deck", "document"}
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; connect-src 'none'; img-src 'self' data:; media-src 'self'; "
    "font-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
    "object-src 'none'; frame-src 'none'; worker-src 'none'; base-uri 'none'; form-action 'none'"
)
LAUNCH = {
    "code_lab": "Run the deterministic check command from this tool directory, then edit exercise.py.",
    "visual_lab": "From this tool directory run `<python> -m http.server 8000 --bind 127.0.0.1`, using Python from PATH or the Codex workspace-dependency loader; inspect `http://127.0.0.1:8000/index.html` in the Codex browser, then stop the server with Ctrl+C.",
    "lesson_lab": "From this tool directory run `<python> -m http.server 8000 --bind 127.0.0.1`, using Python from PATH or the Codex workspace-dependency loader; inspect `http://127.0.0.1:8000/index.html` in the Codex browser, then stop the server with Ctrl+C.",
    "simulation_3d": "From this tool directory run `<python> -m http.server 8000 --bind 127.0.0.1`, using Python from PATH or the Codex workspace-dependency loader; inspect `http://127.0.0.1:8000/index.html` in the Codex browser, then stop the server with Ctrl+C.",
    "blackboard": "Open blackboard.md and reveal one step at a time.",
    "notebook": "Open lab.ipynb in an available local notebook runtime.",
    "quiz": "Open quiz.md and keep any answer material separate until submission.",
    "slide_deck": "Open the completed local .pptx entrypoint after rendering and inspection.",
    "document": "Open the completed local .docx or .pdf entrypoint after rendering and inspection.",
    "project_lab": "Read README.md, then run the manifest check command from this tool directory.",
}
LESSON_TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "assets" / "lesson-lab-template"


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_new(path: Path, text: str) -> None:
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def lesson_template_text(name: str, objective: str, mode: str) -> str:
    path = LESSON_TEMPLATE_ROOT / name
    if not path.is_file():
        raise SystemExit(f"Missing bundled lesson template: {path}")
    return (
        path.read_text(encoding="utf-8")
        .replace("{{CSP}}", CONTENT_SECURITY_POLICY)
        .replace("{{OBJECTIVE}}", objective)
        .replace("{{MODE}}", mode)
    )


def artifact_text(tool_type: str, objective: str, mode: str) -> str:
    if tool_type == "code_lab":
        return (
            '"""Learning exercise. Run: python -m unittest test_exercise.py"""\n\n'
            f'# Objective: {objective}\n'
            f'# Mode: {mode}\n\n'
            'def learner_solution(value):\n'
            '    # LEARNER TODO: replace this line using the stated objective.\n'
            '    raise NotImplementedError("Complete the learner task")\n'
        )
    if tool_type == "lesson_lab":
        return lesson_template_text("index.html", objective, mode)
    if tool_type in {"visual_lab", "simulation_3d"}:
        dimension = "3D" if tool_type == "simulation_3d" else "2D"
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{CONTENT_SECURITY_POLICY}"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Learning lab scaffold</title><style>body{{font:16px system-ui;max-width:880px;margin:40px auto;padding:0 20px}}canvas{{width:100%;border:1px solid #888}}label,button,textarea{{display:block;margin:12px 0}}textarea{{width:100%;min-height:80px}}</style></head>
<body><main><h1>{dimension} learning lab</h1><p>{objective}</p>
<label>Prediction before reveal<textarea id="prediction"></textarea></label>
<button id="reveal">Run experiment</button><canvas id="lab" width="800" height="420"></canvas>
<p id="feedback" aria-live="polite">CUSTOMIZE: connect the control, model, and feedback to the concept.</p>
<label>Explain the result<textarea id="explanation"></textarea></label>
<h2>Transfer challenge</h2><p>CUSTOMIZE: change a causal variable or constraint.</p>
<p><a href="accessibility-fallback.html">Open the text and table equivalent</a></p>
</main><script>document.querySelector('#reveal').addEventListener('click',()=>{{document.querySelector('#feedback').textContent='CUSTOMIZE: render a concept-specific result.'}});</script></body></html>
"""
    if tool_type == "notebook":
        return json.dumps({
            "cells": [
                {"cell_type": "markdown", "metadata": {}, "source": [f"# Objective\n{objective}\n", "Write your prediction before running the next cell."]},
                {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["# LEARNER TODO: implement the experiment\n"]},
                {"cell_type": "markdown", "metadata": {}, "source": ["## Transfer\nCUSTOMIZE: changed-condition challenge."]}
            ],
            "metadata": {}, "nbformat": 4, "nbformat_minor": 5
        }, ensure_ascii=False, indent=2) + "\n"
    title = tool_type.replace("_", " ").title()
    return f"# {title}\n\n## Objective\n\n{objective}\n\n## Learner action\n\nCUSTOMIZE: add the active task.\n\n## Feedback and transfer\n\nCUSTOMIZE: add rubric-linked feedback and a changed-context task.\n"


def test_text() -> str:
    return """import unittest

from exercise import learner_solution


class ExerciseTests(unittest.TestCase):
    def test_customized_behavior(self):
        self.fail("CUSTOMIZE: replace with a deterministic concept-specific test")


if __name__ == "__main__":
    unittest.main()
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a Mastery Learning teaching tool")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--id", required=True)
    parser.add_argument("--type", required=True, choices=sorted(TOOL_TYPES))
    parser.add_argument("--concept", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--mode", default="coach", choices=sorted(MODES))
    parser.add_argument("--prerequisites", default="")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.id):
        raise SystemExit("--id must be lowercase hyphen-case")
    if len(args.objective.strip()) < 12:
        raise SystemExit("--objective must be an observable outcome, not a short topic label")

    workspace = Path(args.workspace).expanduser().resolve()
    tool_dir = workspace / ".mastery" / "tools" / args.id
    if tool_dir.exists():
        raise SystemExit(f"Tool already exists: {tool_dir}")
    tools_root = tool_dir.parent
    tools_root.mkdir(parents=True, exist_ok=True)
    catalog_path = workspace / ".mastery" / "tool-catalog.json"
    temporary_dir = Path(tempfile.mkdtemp(prefix=f".{args.id}.", dir=str(tools_root)))
    entrypoint = ENTRYPOINTS[args.type]
    fallback = "accessibility-fallback.html" if args.type in {"visual_lab", "lesson_lab", "simulation_3d"} else "accessibility-fallback.md"
    kind, dimensions = EVIDENCE[args.type]
    hints = [] if args.mode == "exam" else ["Restate the target observation.", "Name the governing principle.", "Show one analogous case."]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "id": args.id,
        "version": "0.1.0",
        "build_status": "scaffold",
        "type": args.type,
        "concept": args.concept,
        "objective": args.objective.strip(),
        "mode": args.mode,
        "prerequisites": [item.strip() for item in args.prerequisites.split(",") if item.strip()],
        "interaction": {
            "prediction": "CUSTOMIZE: prompt a prediction before revealing the outcome.",
            "learner_action": "CUSTOMIZE: state the learner's observable action.",
            "feedback": "CUSTOMIZE: connect deterministic output or rubric criteria.",
            "hints": hints,
            "transfer": "CUSTOMIZE: change the context, data, or constraints.",
        },
        "evidence": {"kind": kind, "dimensions": dimensions, "rubric": "rubric.json"},
        "entrypoint": entrypoint,
        "check_command": "python -m unittest test_exercise.py" if args.type == "code_lab" else None,
        "check_expectation": {"exit_code": 1, "output_contains": "NotImplementedError"} if args.type == "code_lab" else None,
        "accessibility_fallback": fallback,
        "launch": LAUNCH[args.type],
        "cleanup": "Export learner work if needed, then delete only this tool directory after learner confirmation.",
        "inspection": {
            "required": args.type in RENDER_TYPES,
            "notes": "CUSTOMIZE: state what Codex must render and inspect." if args.type in RENDER_TYPES else "Rendering is not required for this text/code scaffold.",
        },
        "sources": [],
        "created_at": timestamp(),
        "generator": {"name": "mastery-tool-creator", "version": "0.4.2"},
    }
    rubric = {
        "schema_version": 1,
        "objective": args.objective.strip(),
        "criteria": [
            {"id": "mechanism", "description": "CUSTOMIZE: explain the causal mechanism", "weight": 0.5, "evidence": "learner explanation"},
            {"id": "performance", "description": "CUSTOMIZE: produce the target behavior", "weight": 0.5, "evidence": "artifact output or deterministic check"},
        ],
    }
    try:
        atomic_json(temporary_dir / "tool.json", manifest)
        atomic_json(temporary_dir / "rubric.json", rubric)
        write_new(temporary_dir / entrypoint, artifact_text(args.type, args.objective.strip(), args.mode))
        if args.type == "lesson_lab":
            write_new(temporary_dir / "styles.css", lesson_template_text("styles.css", args.objective.strip(), args.mode))
            write_new(temporary_dir / "app.js", lesson_template_text("app.js", args.objective.strip(), args.mode))
            fallback_text = lesson_template_text("accessibility-fallback.html", args.objective.strip(), args.mode)
        elif fallback.endswith(".html"):
            fallback_text = (
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<meta http-equiv="Content-Security-Policy" content="{CONTENT_SECURITY_POLICY}">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Accessible learning lab equivalent</title></head><body><main>'
                '<h1>Text and table equivalent</h1>'
                f'<p>CUSTOMIZE: provide a keyboard-readable text and table equivalent for {args.objective.strip()}.</p>'
                '<p>Include the same prediction, observable state, feedback, explanation prompt, and changed-condition challenge as the visual lab.</p>'
                '<p><a href="index.html">Return to the interactive lab</a></p></main></body></html>\n'
            )
        else:
            fallback_text = f"# Accessibility fallback\n\nCUSTOMIZE: provide a text/table equivalent for **{args.objective.strip()}**.\n"
        write_new(temporary_dir / fallback, fallback_text)
        if args.type == "code_lab":
            write_new(temporary_dir / "test_exercise.py", test_text())
        os.replace(temporary_dir, tool_dir)
        register_catalog_entry(catalog_path, {
            "id": args.id, "type": args.type, "concept": args.concept,
            "objective": args.objective.strip(), "path": str(tool_dir), "status": "scaffold",
        }, SCHEMA_VERSION)
    except BaseException:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
        if tool_dir.exists():
            shutil.rmtree(tool_dir)
        raise
    print(json.dumps({"ok": True, "tool_dir": str(tool_dir), "next": "Customize files, set build_status to complete, then run static validate_tool.py."}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
