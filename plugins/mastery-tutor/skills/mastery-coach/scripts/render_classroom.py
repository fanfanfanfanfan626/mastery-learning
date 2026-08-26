#!/usr/bin/env python3
"""Render one learner-facing Mastery Coach turn into the shared HTML classroom."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


SCHEMA_VERSION = 1
KINDS = {"onboarding", "orientation", "lesson", "feedback", "review", "summary"}
SECTION_TYPES = {"prose", "callout", "steps", "comparison", "code", "map", "details", "choices", "artifact"}
CALLOUT_TONES = {"concept", "example", "caution", "insight"}
LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
PAGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ARTIFACT_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
FRAGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_-]*$")
MAX_SPEC_BYTES = 256_000
MAX_SECTIONS = 16
TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "assets" / "classroom-template"
SERVER_SCRIPT = Path(__file__).resolve().parent / "serve_classroom.py"
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
    "script-src 'none'; connect-src 'none'; media-src 'self'; object-src 'none'; "
    "frame-src 'none'; worker-src 'none'; base-uri 'none'; form-action 'none'"
)
UI_TEXT = {
    "en": {
        "skip": "Skip to the lesson",
        "brand_label": "Mastery Tutor classroom",
        "tagline": "AI teaching skill · local classroom",
        "action_label": "Now · one action",
        "response_prefix": "Reply in the AI conversation:",
        "sources": "Sources to verify",
        "rail_label": "How to use this classroom",
        "rail": [
            ("Read the model", "Build the picture before trying to perform."),
            ("Do one action", "The highlighted task is the only required next step."),
            ("Return to the tutor", "The AI checks reasoning; page activity alone is not mastery."),
        ],
        "footer": "Generated locally. No analytics, remote runtime, or hidden mastery claim.",
        "annotated": "annotated example",
    },
    "zh": {
        "skip": "跳到本节内容",
        "brand_label": "Mastery Tutor 本地课堂",
        "tagline": "AI 教学 Skill · 本地课堂",
        "action_label": "现在 · 一个任务",
        "response_prefix": "回到 AI 对话回复：",
        "sources": "参考来源",
        "rail_label": "如何使用这个课堂",
        "rail": [
            ("先建立模型", "理解整体图景后再动手，不要求凭空作答。"),
            ("只做一个任务", "高亮任务是当前唯一必须完成的动作。"),
            ("回到 AI 教练", "AI 检查你的推理；浏览和点击本身不代表掌握。"),
        ],
        "footer": "本地生成；无遥测、无远程运行时，也不会暗中宣称掌握。",
        "annotated": "带教学注释的示例",
    },
}


def fail(message: str) -> None:
    raise SystemExit(message)


def text(value: Any, field: str, *, minimum: int = 1, maximum: int = 8_000) -> str:
    if not isinstance(value, str):
        fail(f"{field} must be text")
    result = value.strip()
    if not minimum <= len(result) <= maximum:
        fail(f"{field} must contain {minimum}..{maximum} characters")
    return result


def text_list(value: Any, field: str, *, minimum: int = 1, maximum: int = 12) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        fail(f"{field} must contain {minimum}..{maximum} text items")
    return [text(item, f"{field}[{index}]", maximum=2_000) for index, item in enumerate(value)]


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def interface_text(language: str) -> dict[str, Any]:
    return UI_TEXT["zh"] if language.lower().split("-", 1)[0] == "zh" else UI_TEXT["en"]


def render_paragraphs(items: list[str]) -> str:
    return "\n".join(f"<p>{escape(item)}</p>" for item in items)


def safe_artifact_href(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    if parsed.query or not FRAGMENT_PATTERN.fullmatch(parsed.fragment):
        return False
    path_text = unquote(parsed.path)
    if "\\" in path_text or "//" in path_text or not ARTIFACT_PATH_PATTERN.fullmatch(path_text.lstrip("/")):
        return False
    parts = PurePosixPath(path_text.lstrip("/")).parts
    if not parts or any(part in {".", ".."} for part in parts):
        return False
    return (
        parsed.scheme == "http"
        and parsed.hostname == "127.0.0.1"
        and parsed.username is None
        and parsed.password is None
        and port is not None
        and 1 <= port <= 65535
    )


def is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def ensure_contained_directory(root: Path, candidate: Path, field: str) -> Path:
    if candidate.exists() and is_reparse_point(candidate):
        fail(f"{field} must not be a symbolic link, junction, or other reparse point")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        fail(f"{field} must remain inside the selected classroom root")
    return resolved


def render_section(section: Any, index: int, ui: dict[str, Any]) -> str:
    if not isinstance(section, dict):
        fail(f"sections[{index}] must be an object")
    section_type = section.get("type")
    if section_type not in SECTION_TYPES:
        fail(f"sections[{index}].type must be one of {sorted(SECTION_TYPES)}")
    title = text(section.get("title"), f"sections[{index}].title", maximum=180)
    label = f"{index + 1:02d}"

    if section_type == "prose":
        body = text_list(section.get("body"), f"sections[{index}].body", maximum=10)
        content = render_paragraphs(body)
    elif section_type == "callout":
        tone = section.get("tone")
        if tone not in CALLOUT_TONES:
            fail(f"sections[{index}].tone must be one of {sorted(CALLOUT_TONES)}")
        body = text_list(section.get("body"), f"sections[{index}].body", maximum=6)
        return (
            f'<section class="classroom-section callout callout--{tone}" data-classroom-block="callout">'
            f'<p class="section-index">{label} · {escape(tone)}</p><h2>{escape(title)}</h2>'
            f"{render_paragraphs(body)}</section>"
        )
    elif section_type == "steps":
        items = section.get("items")
        if not isinstance(items, list) or not 2 <= len(items) <= 8:
            fail(f"sections[{index}].items must contain 2..8 step objects")
        rendered: list[str] = []
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                fail(f"sections[{index}].items[{item_index}] must be an object")
            item_title = text(item.get("title"), f"sections[{index}].items[{item_index}].title", maximum=120)
            item_body = text(item.get("body"), f"sections[{index}].items[{item_index}].body", maximum=1_200)
            rendered.append(
                f'<li><span class="step-number">{item_index + 1}</span><div><strong>{escape(item_title)}</strong>'
                f'<p>{escape(item_body)}</p></div></li>'
            )
        content = f'<ol class="process-steps">{"".join(rendered)}</ol>'
    elif section_type == "comparison":
        headers = text_list(section.get("headers"), f"sections[{index}].headers", minimum=2, maximum=5)
        rows = section.get("rows")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 12:
            fail(f"sections[{index}].rows must contain 1..12 rows")
        rendered_rows: list[str] = []
        for row_index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != len(headers):
                fail(f"sections[{index}].rows[{row_index}] must match the header count")
            cells = [text(cell, f"sections[{index}].rows[{row_index}] cell", maximum=700) for cell in row]
            rendered_rows.append("<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in cells) + "</tr>")
        content = (
            '<div class="table-wrap" tabindex="0"><table><thead><tr>'
            + "".join(f"<th>{escape(header)}</th>" for header in headers)
            + "</tr></thead><tbody>"
            + "".join(rendered_rows)
            + "</tbody></table></div>"
        )
    elif section_type == "code":
        language = text(section.get("language", "text"), f"sections[{index}].language", maximum=40)
        code = text(section.get("code"), f"sections[{index}].code", maximum=20_000)
        notes = text_list(section.get("notes"), f"sections[{index}].notes", minimum=1, maximum=10)
        content = (
            f'<div class="code-frame"><div class="code-header"><span>{escape(language)}</span>'
            f'<span>{escape(ui["annotated"])}</span></div>'
            f'<pre><code>{escape(code)}</code></pre></div><ol class="code-notes">'
            + "".join(f"<li>{escape(note)}</li>" for note in notes)
            + "</ol>"
        )
    elif section_type == "map":
        items = section.get("items")
        if not isinstance(items, list) or not 2 <= len(items) <= 8:
            fail(f"sections[{index}].items must contain 2..8 map objects")
        cards: list[str] = []
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                fail(f"sections[{index}].items[{item_index}] must be an object")
            name = text(item.get("name"), f"sections[{index}].items[{item_index}].name", maximum=100)
            description = text(item.get("description"), f"sections[{index}].items[{item_index}].description", maximum=700)
            cards.append(
                f'<li><span class="map-kicker">{item_index + 1:02d}</span><strong>{escape(name)}</strong>'
                f'<p>{escape(description)}</p></li>'
            )
        content = f'<ol class="concept-map">{"".join(cards)}</ol>'
    elif section_type == "details":
        body = text_list(section.get("body"), f"sections[{index}].body", maximum=10)
        return (
            f'<section class="classroom-section optional-depth" data-classroom-block="details">'
            f'<details><summary><span class="section-index">{label}</span>'
            f'<strong>{escape(title)}</strong></summary><div class="details-body">'
            f'{render_paragraphs(body)}</div></details></section>'
        )
    elif section_type == "choices":
        items = section.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 6:
            fail(f"sections[{index}].items must contain 1..6 choice groups")
        groups: list[str] = []
        seen_ids: set[str] = set()
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                fail(f"sections[{index}].items[{item_index}] must be an object")
            item_id = text(item.get("id"), f"sections[{index}].items[{item_index}].id", maximum=60)
            if not PAGE_ID_PATTERN.fullmatch(item_id) or item_id in seen_ids:
                fail(f"sections[{index}].items[{item_index}].id must be unique lowercase hyphen-case")
            seen_ids.add(item_id)
            prompt = text(item.get("prompt"), f"sections[{index}].items[{item_index}].prompt", maximum=180)
            options = text_list(item.get("options"), f"sections[{index}].items[{item_index}].options", maximum=6)
            groups.append(
                f'<li data-choice-group="{escape(item_id)}"><strong>{escape(prompt)}</strong><ul>'
                + "".join(f"<li>{escape(option)}</li>" for option in options)
                + "</ul></li>"
            )
        content = f'<ol class="launch-choices">{"".join(groups)}</ol>'
    else:
        summary = text(section.get("summary"), f"sections[{index}].summary", maximum=1_200)
        href = text(section.get("href"), f"sections[{index}].href", maximum=500)
        label_text = text(section.get("label"), f"sections[{index}].label", maximum=120)
        if not safe_artifact_href(href):
            fail(f"sections[{index}].href must be an exact assigned loopback URL for a separately served verified tool")
        content = (
            f'<p>{escape(summary)}</p><p><a class="artifact-link" href="{escape(href)}">'
            f'{escape(label_text)} <span aria-hidden="true">→</span></a></p>'
        )

    return (
        f'<section class="classroom-section" data-classroom-block="{escape(section_type)}">'
        f'<p class="section-index">{label}</p><h2>{escape(title)}</h2>{content}</section>'
    )


def validate_references(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 12:
        fail("references must contain at most 12 source objects")
    result: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            fail(f"references[{index}] must be an object")
        title = text(item.get("title"), f"references[{index}].title", maximum=180)
        url = text(item.get("url"), f"references[{index}].url", maximum=1_000)
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            fail(f"references[{index}].url must be an HTTPS source without credentials")
        result.append({"title": title, "url": url})
    return result


def load_spec(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_SPEC_BYTES:
        fail(f"spec must be a regular JSON file no larger than {MAX_SPEC_BYTES} bytes")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"cannot read spec: {error}")
    if not isinstance(value, dict):
        fail("spec root must be an object")
    return value


def render(spec: dict[str, Any]) -> str:
    if spec.get("schema_version") != SCHEMA_VERSION:
        fail(f"schema_version must equal {SCHEMA_VERSION}")
    page_id = text(spec.get("page_id"), "page_id", maximum=96)
    if not PAGE_ID_PATTERN.fullmatch(page_id):
        fail("page_id must be lowercase hyphen-case")
    kind = spec.get("kind")
    if kind not in KINDS:
        fail(f"kind must be one of {sorted(KINDS)}")
    language = text(spec.get("language", "zh-CN"), "language", maximum=32)
    if not LANGUAGE_PATTERN.fullmatch(language):
        fail("language must be a BCP-47-like language tag")
    ui = interface_text(language)
    eyebrow = text(spec.get("eyebrow"), "eyebrow", maximum=120)
    title = text(spec.get("title"), "title", maximum=220)
    lead = text(spec.get("lead"), "lead", maximum=1_500)
    course = text(spec.get("course", "Mastery Tutor"), "course", maximum=120)
    progress = text(spec.get("progress", "Current learning turn"), "progress", maximum=120)

    meta = spec.get("meta", [])
    if not isinstance(meta, list) or len(meta) > 4:
        fail("meta must contain at most four label/value objects")
    meta_html: list[str] = []
    for index, item in enumerate(meta):
        if not isinstance(item, dict):
            fail(f"meta[{index}] must be an object")
        label = text(item.get("label"), f"meta[{index}].label", maximum=60)
        value = text(item.get("value"), f"meta[{index}].value", maximum=180)
        meta_html.append(f"<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>")

    sections = spec.get("sections")
    if not isinstance(sections, list) or not 1 <= len(sections) <= MAX_SECTIONS:
        fail(f"sections must contain 1..{MAX_SECTIONS} section objects")
    minimum_sections = {"orientation": 2, "lesson": 3}.get(kind, 1)
    if len(sections) < minimum_sections:
        fail(f"{kind} pages require at least {minimum_sections} semantic sections")
    section_types = {section.get("type") for section in sections if isinstance(section, dict)}
    if kind == "orientation" and not section_types.intersection({"map", "comparison"}):
        fail("orientation pages require a map or comparison that establishes the field structure")
    if kind == "lesson" and not section_types.intersection({"steps", "comparison", "code", "map"}):
        fail("lesson pages require a worked structure such as steps, comparison, code, or map")
    sections_html = "\n".join(render_section(section, index, ui) for index, section in enumerate(sections))

    action = spec.get("action")
    if not isinstance(action, dict):
        fail("action must be an object containing the one current learner task")
    action_title = text(action.get("title"), "action.title", maximum=120)
    action_prompt = text(action.get("prompt"), "action.prompt", maximum=2_000)
    response_hint = text(action.get("response_hint"), "action.response_hint", maximum=500)
    action_html = f"""
        <section class="current-action" data-classroom-action="one">
          <p class="action-label">{escape(ui["action_label"])}</p>
          <h2>{escape(action_title)}</h2>
          <p>{escape(action_prompt)}</p>
          <p class="response-hint">{escape(ui["response_prefix"])} {escape(response_hint)}</p>
        </section>"""
    flow_html = f"{action_html}\n{sections_html}" if kind == "onboarding" else f"{sections_html}\n{action_html}"

    references = validate_references(spec.get("references"))
    references_html = ""
    if references:
        references_html = (
            f'<section class="sources" aria-labelledby="sources-heading"><h2 id="sources-heading">{escape(ui["sources"])}</h2><ul>'
            + "".join(
                f'<li><a href="{escape(item["url"])}" rel="noopener noreferrer">{escape(item["title"])}</a></li>'
                for item in references
            )
            + "</ul></section>"
        )

    return f"""<!doctype html>
<html lang="{escape(language)}">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="{CONTENT_SECURITY_POLICY}">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{escape(title)} · {escape(course)}</title>
  <link rel="stylesheet" href="assets/classroom.css">
</head>
<body data-page-id="{escape(page_id)}" data-turn-kind="{escape(kind)}">
  <a class="skip-link" href="#classroom-main">{escape(ui["skip"])}</a>
  <div class="ambient ambient--one" aria-hidden="true"></div>
  <div class="ambient ambient--two" aria-hidden="true"></div>
  <header class="topbar">
    <a class="brand" href="#classroom-main" aria-label="{escape(ui["brand_label"])}">
      <span class="brand-mark" aria-hidden="true">M</span>
      <span><strong>{escape(course)}</strong><small>{escape(ui["tagline"])}</small></span>
    </a>
    <p class="progress-chip">{escape(progress)}</p>
  </header>
  <main id="classroom-main" class="classroom-shell">
    <header class="lesson-hero">
      <p class="eyebrow">{escape(eyebrow)}</p>
      <h1>{escape(title)}</h1>
      <p class="lead">{escape(lead)}</p>
      <div class="meta-grid">{"".join(meta_html)}</div>
    </header>
    <div class="lesson-grid">
      <article class="lesson-flow">
        {flow_html}
        {references_html}
      </article>
      <aside class="learning-rail" aria-label="{escape(ui["rail_label"])}">
        {''.join(f'<div class="rail-card"><span>{index + 1:02d}</span><strong>{escape(item[0])}</strong><p>{escape(item[1])}</p></div>' for index, item in enumerate(ui["rail"]))}
      </aside>
    </div>
  </main>
  <footer><p>{escape(ui["footer"])}</p></footer>
</body>
</html>
"""


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Mastery Coach turn into the shared HTML classroom")
    parser.add_argument("--spec", required=True, type=Path)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--workspace", type=Path)
    destination.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    spec = load_spec(args.spec.expanduser().resolve())
    if args.workspace is not None:
        workspace = args.workspace.expanduser().resolve()
        if not workspace.is_dir():
            fail(f"workspace does not exist: {workspace}")
        output_dir = (workspace / ".mastery" / "classroom").resolve()
        if not output_dir.is_relative_to(workspace):
            fail("workspace classroom path must remain inside the selected workspace")
        serve_root = output_dir
        url_path = "/index.html"
    else:
        output_dir = args.output_dir.expanduser().resolve()
        serve_root = output_dir
        url_path = "/index.html"

    stylesheet = TEMPLATE_ROOT / "classroom.css"
    if not stylesheet.is_file():
        fail(f"bundled classroom stylesheet is missing: {stylesheet}")
    if not SERVER_SCRIPT.is_file():
        fail(f"bundled classroom server is missing: {SERVER_SCRIPT}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = ensure_contained_directory(output_dir, output_dir, "classroom output")
    assets_dir = ensure_contained_directory(output_dir, output_dir / "assets", "classroom assets")
    assets_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = ensure_contained_directory(output_dir, assets_dir, "classroom assets")
    atomic_write(assets_dir / "classroom.css", stylesheet.read_text(encoding="utf-8"))
    page = output_dir / "index.html"
    atomic_write(page, render(spec))
    print(json.dumps({
        "ok": True,
        "page": str(page),
        "serve_root": str(serve_root),
        "url_path": url_path,
        "server": {
            "script": str(SERVER_SCRIPT),
            "port": 0,
            "bind": "127.0.0.1",
            "cache": "no-store",
        },
        "next": "Start or reuse the bundled classroom server for serve_root, open url_path, and keep learner-facing teaching out of chat.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
