#!/usr/bin/env python3
"""Render one learner-facing Mastery Coach turn into the shared HTML classroom."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import secrets
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from teaching_turn import TeachingTurnError, validate_teaching_turn


SCHEMA_VERSION = 1
KINDS = {"onboarding", "orientation", "lesson", "feedback", "review", "summary"}
TEACHING_KINDS = {"orientation", "lesson", "feedback", "review"}
SECTION_TYPES = {"prose", "callout", "steps", "comparison", "code", "map", "details", "choices", "artifact"}
CALLOUT_TONES = {"concept", "example", "caution", "insight"}
LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
PAGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ARTIFACT_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")
FRAGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_-]*$")
MAX_SPEC_BYTES = 256_000
MAX_SECTIONS = 16
RESPONSE_CONTRACT_FILE = ".response-contract.json"
RESPONSE_PACKET_FILE = ".learner-response.json"
TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "assets" / "classroom-template"
SERVER_SCRIPT = Path(__file__).resolve().parent / "serve_classroom.py"
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
    "script-src 'none'; connect-src 'none'; media-src 'self'; object-src 'none'; "
    "frame-src 'none'; worker-src 'none'; base-uri 'none'; form-action 'self'"
)
INTERNAL_COPY_MARKERS = {
    "teachingturnspec",
    "按照教练规则",
    "学习档案已初始化",
    "学习档案已通过校验",
    "状态引擎已",
    "知识图谱已",
    "证据边界",
    "当前唯一任务",
    "current sole task",
    "according to the coach contract",
    "mastery state validated",
}
UI_TEXT = {
    "en": {
        "skip": "Skip to the lesson",
        "brand_label": "Mastery Tutor classroom",
        "tagline": "Learn one clear step at a time",
        "progress": "Continue from here",
        "action_label": "Your turn",
        "response_prefix": "A helpful way to answer:",
        "submit_note": "Submit here, then return to the conversation and say you are ready to continue.",
        "submit": "Send my answer",
        "feedback_task": "The question we were working on",
        "feedback_response": "What you tried",
        "feedback_error": "Here is where the idea changed direction",
        "feedback_hint": "A small hint",
        "sources": "Sources to verify",
        "rail_label": "A simple rhythm",
        "rail": [
            ("See it first", "Start with the example; the name can come later."),
            ("Try one small step", "Use the box at the end when the idea feels concrete."),
            ("Keep going together", "After you submit, the next explanation follows your answer."),
        ],
        "footer": "This classroom stays on your device, with no analytics or remote trackers.",
        "annotated": "annotated example",
        "choices_label": "Onboarding choices",
        "choices_fallback": "The recommended choices are already selected. Change only what does not fit you.",
        "tone_labels": {"concept": "Key idea", "example": "Example", "caution": "Watch for this", "insight": "What to notice"},
    },
    "zh": {
        "skip": "跳到本节内容",
        "brand_label": "Mastery Tutor 本地课堂",
        "tagline": "陪你一步一步学会",
        "progress": "接着往下学",
        "action_label": "轮到你了",
        "response_prefix": "可以这样回答：",
        "submit_note": "在这里提交后，回到对话说一声“好了”，我会顺着你的回答继续。",
        "submit": "提交给老师看看",
        "feedback_task": "刚才那道题",
        "feedback_response": "你刚才的想法",
        "feedback_error": "问题出在这里",
        "feedback_hint": "给你一个提示",
        "sources": "参考来源",
        "rail_label": "这一小节怎么学",
        "rail": [
            ("先看个例子", "先把这件事看明白，不急着背名字。"),
            ("再自己试试", "页面最后留了一小步给你。"),
            ("然后接着讲", "提交后回到对话，我会顺着你的思路继续。"),
        ],
        "footer": "内容留在你的电脑上，不含统计代码或远程跟踪。",
        "annotated": "带教学注释的示例",
        "choices_label": "入门选择",
        "choices_fallback": "推荐项已经替你选好；不合适的地方再改就行。",
        "tone_labels": {"concept": "关键想法", "example": "举个例子", "caution": "这里容易混", "insight": "值得留意"},
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


def visible_texts(spec: dict[str, Any]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    def walk(value: Any, field: str) -> None:
        if isinstance(value, str):
            result.append((field, value))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{field}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in {"href", "url", "value", "id", "type", "tone", "language"}:
                    continue
                walk(item, f"{field}.{key}")

    for field in ["course", "progress", "eyebrow", "title", "lead", "meta", "sections", "action", "feedback_context"]:
        if field in spec:
            walk(spec[field], field)
    for index, reference in enumerate(spec.get("references", [])):
        if isinstance(reference, dict) and "title" in reference:
            walk(reference["title"], f"references[{index}].title")
    return result


def validate_teacher_voice(spec: dict[str, Any]) -> None:
    for field, value in visible_texts(spec):
        lowered = value.casefold()
        for marker in INTERNAL_COPY_MARKERS:
            if marker.casefold() in lowered:
                fail(f"{field} exposes internal teaching-control language: {marker!r}")


def normalize_options(value: Any, field: str, *, maximum: int = 8) -> list[dict[str, str]]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        fail(f"{field} must contain 1..{maximum} options")
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        if isinstance(raw, str):
            option_value = text(raw, f"{field}[{index}]", maximum=500)
            label = option_value
        elif isinstance(raw, dict) and set(raw) == {"value", "label"}:
            option_value = text(raw.get("value"), f"{field}[{index}].value", maximum=120)
            label = text(raw.get("label"), f"{field}[{index}].label", maximum=420)
        else:
            fail(f"{field}[{index}] must be text or an object with value and label")
        key = option_value.casefold()
        if key in seen:
            fail(f"{field} option values must be unique")
        seen.add(key)
        result.append({"value": option_value, "label": label})
    return result


def collect_choice_fields(sections: list[Any], kind: str) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    for section_index, section in enumerate(sections):
        if not isinstance(section, dict) or section.get("type") != "choices":
            continue
        if kind != "onboarding":
            fail("choices sections are reserved for onboarding; use action.response for teaching answers")
        items = section.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 6:
            fail(f"sections[{section_index}].items must contain 1..6 choice groups")
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                fail(f"sections[{section_index}].items[{item_index}] must be an object")
            item_id = text(item.get("id"), f"sections[{section_index}].items[{item_index}].id", maximum=60)
            if not PAGE_ID_PATTERN.fullmatch(item_id):
                fail(f"sections[{section_index}].items[{item_index}].id must be lowercase hyphen-case")
            name = f"choice.{item_id}"
            if name in fields:
                fail(f"choice id {item_id!r} must be unique across the page")
            options = normalize_options(item.get("options"), f"sections[{section_index}].items[{item_index}].options", maximum=6)
            default = item.get("default", options[0]["value"])
            default = text(default, f"sections[{section_index}].items[{item_index}].default", maximum=500)
            allowed = [option["value"] for option in options]
            if default not in allowed:
                fail(f"sections[{section_index}].items[{item_index}].default must match an option value")
            fields[name] = {
                "type": "choice",
                "required": True,
                "allowed_values": allowed,
                "max_length": max(len(value) for value in allowed),
            }
    return fields


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
            f'<p class="section-index">{label} · {escape(ui["tone_labels"][tone])}</p><h2>{escape(title)}</h2>'
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
            options = normalize_options(
                item.get("options"), f"sections[{index}].items[{item_index}].options", maximum=6
            )
            default = text(
                item.get("default", options[0]["value"]),
                f"sections[{index}].items[{item_index}].default",
                maximum=500,
            )
            if default not in {option["value"] for option in options}:
                fail(f"sections[{index}].items[{item_index}].default must match an option value")
            option_controls: list[str] = []
            group_name = f"choice.{item_id}"
            for option_index, option in enumerate(options):
                control_id = f"choice-{index}-{item_index}-{option_index}"
                checked = " checked" if option["value"] == default else ""
                option_controls.append(
                    f'<label class="choice-option" for="{control_id}">'
                    f'<input id="{control_id}" type="radio" name="{escape(group_name)}" '
                    f'value="{escape(option["value"])}" required{checked}>'
                    f'<span>{escape(option["label"])}</span></label>'
                )
            groups.append(
                f'<fieldset data-choice-group="{escape(item_id)}"><legend>{escape(prompt)}</legend>'
                f'<div class="choice-options">{"".join(option_controls)}</div></fieldset>'
            )
        content = (
            f'<div class="launch-choices" role="group" aria-label="{escape(ui["choices_label"])}">'
            f'{"".join(groups)}</div><p class="choice-fallback">{escape(ui["choices_fallback"])}</p>'
        )
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


def render_feedback_context(value: Any, ui: dict[str, Any]) -> str:
    if not isinstance(value, dict):
        fail("feedback pages require a feedback_context object")
    expected = {
        "attempt_id", "original_task", "learner_response", "earliest_error",
        "hint_level", "hint", "solution_revealed",
    }
    unknown = sorted(set(value) - expected)
    if unknown:
        fail(f"feedback_context has unknown fields: {unknown}")
    attempt_id = text(value.get("attempt_id"), "feedback_context.attempt_id", maximum=96)
    if not PAGE_ID_PATTERN.fullmatch(attempt_id):
        fail("feedback_context.attempt_id must be lowercase hyphen-case")
    original_task = text(value.get("original_task"), "feedback_context.original_task", maximum=2_000)
    learner_response = text(value.get("learner_response"), "feedback_context.learner_response", maximum=2_000)
    earliest_error = text(value.get("earliest_error"), "feedback_context.earliest_error", maximum=1_500)
    hint = text(value.get("hint"), "feedback_context.hint", maximum=1_500)
    hint_level = value.get("hint_level")
    if not isinstance(hint_level, int) or isinstance(hint_level, bool) or not 1 <= hint_level <= 5:
        fail("feedback_context.hint_level must be an integer from 1 to 5")
    solution_revealed = value.get("solution_revealed")
    if not isinstance(solution_revealed, bool):
        fail("feedback_context.solution_revealed must be true or false")
    if solution_revealed and hint_level < 5:
        fail("a revealed full solution must use hint level 5")
    fields = [
        (ui["feedback_task"], original_task),
        (ui["feedback_response"], learner_response),
        (ui["feedback_error"], earliest_error),
        (f'{ui["feedback_hint"]} · {hint_level}/5', hint),
    ]
    return (
        f'<div class="feedback-context" data-attempt-id="{escape(attempt_id)}">'
        + "".join(
            f'<div><strong>{escape(label)}</strong><p>{escape(body)}</p></div>'
            for label, body in fields
        )
        + "</div>"
    )


def render_action_response(
    value: Any,
    *,
    kind: str,
    answer_options: list[str],
    has_choice_fields: bool,
    ui: dict[str, Any],
) -> tuple[str, dict[str, dict[str, Any]], str]:
    if value is None:
        if kind == "onboarding":
            response_type = "submit-only"
            raw: dict[str, Any] = {}
        elif answer_options:
            response_type = "choice"
            raw = {"options": answer_options}
        else:
            response_type = "long-text"
            raw = {}
    elif isinstance(value, dict):
        raw = value
        response_type = raw.get("type")
    else:
        fail("action.response must be an object")
    if response_type not in {"submit-only", "choice", "short-text", "long-text"}:
        fail("action.response.type must be submit-only, choice, short-text, or long-text")

    allowed_keys = {
        "submit-only": {"type", "submit_label"},
        "choice": {"type", "label", "options", "submit_label"},
        "short-text": {"type", "label", "placeholder", "max_length", "submit_label"},
        "long-text": {"type", "label", "placeholder", "max_length", "submit_label"},
    }[response_type]
    unknown = sorted(set(raw) - allowed_keys)
    if unknown:
        fail(f"action.response has unknown fields for {response_type}: {unknown}")
    submit_label = text(raw.get("submit_label", ui["submit"]), "action.response.submit_label", maximum=80)
    fields: dict[str, dict[str, Any]] = {}
    control = ""

    if response_type == "submit-only":
        if kind != "onboarding" or not has_choice_fields:
            fail("submit-only is allowed only for onboarding with choice fields")
    elif response_type == "choice":
        options = normalize_options(raw.get("options", answer_options), "action.response.options")
        values = [option["value"] for option in options]
        if answer_options and set(value.casefold() for value in values) != set(
            value.casefold() for value in answer_options
        ):
            fail("action.response choice values must match teaching_turn.answer_options")
        label = text(raw.get("label", ui["action_label"]), "action.response.label", maximum=120)
        controls = []
        for index, option in enumerate(options):
            control_id = f"answer-option-{index}"
            controls.append(
                f'<label class="answer-option" for="{control_id}">'
                f'<input id="{control_id}" type="radio" name="answer" '
                f'value="{escape(option["value"])}" required><span>{escape(option["label"])}</span></label>'
            )
        control = (
            f'<fieldset class="answer-field"><legend>{escape(label)}</legend>'
            f'<div class="answer-options">{"".join(controls)}</div></fieldset>'
        )
        fields["answer"] = {
            "type": "choice",
            "required": True,
            "allowed_values": values,
            "max_length": max(len(item) for item in values),
        }
    else:
        default_max = 500 if response_type == "short-text" else 2_000
        maximum = raw.get("max_length", default_max)
        if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= default_max:
            fail(f"action.response.max_length must be an integer from 1 to {default_max}")
        label = text(raw.get("label", ui["action_label"]), "action.response.label", maximum=120)
        placeholder = text(
            raw.get("placeholder", "…"), "action.response.placeholder", minimum=0, maximum=240
        )
        if response_type == "short-text":
            control = (
                f'<label class="answer-field"><span>{escape(label)}</span>'
                f'<input type="text" name="answer" maxlength="{maximum}" '
                f'placeholder="{escape(placeholder)}" required></label>'
            )
        else:
            control = (
                f'<label class="answer-field"><span>{escape(label)}</span>'
                f'<textarea name="answer" maxlength="{maximum}" rows="5" '
                f'placeholder="{escape(placeholder)}" required></textarea></label>'
            )
        fields["answer"] = {
            "type": "text",
            "required": True,
            "max_length": maximum,
        }
    return control, fields, submit_label


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


def build_classroom(spec: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if spec.get("schema_version") != SCHEMA_VERSION:
        fail(f"schema_version must equal {SCHEMA_VERSION}")
    page_id = text(spec.get("page_id"), "page_id", maximum=96)
    if not PAGE_ID_PATTERN.fullmatch(page_id):
        fail("page_id must be lowercase hyphen-case")
    kind = spec.get("kind")
    if kind not in KINDS:
        fail(f"kind must be one of {sorted(KINDS)}")
    validate_teacher_voice(spec)
    language = text(spec.get("language", "zh-CN"), "language", maximum=32)
    if not LANGUAGE_PATTERN.fullmatch(language):
        fail("language must be a BCP-47-like language tag")
    ui = interface_text(language)
    eyebrow = text(spec.get("eyebrow"), "eyebrow", maximum=120)
    title = text(spec.get("title"), "title", maximum=220)
    lead = text(spec.get("lead"), "lead", maximum=1_500)
    course = text(spec.get("course", "Mastery Tutor"), "course", maximum=120)
    progress = text(spec.get("progress", ui["progress"]), "progress", maximum=120)

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
    choice_fields = collect_choice_fields(sections, kind)
    rendered_sections = [
        (section.get("type") == "details", render_section(section, index, ui))
        for index, section in enumerate(sections)
    ]
    core_sections_html = "\n".join(html for optional, html in rendered_sections if not optional)
    optional_sections_html = "\n".join(html for optional, html in rendered_sections if optional)

    action = spec.get("action")
    if not isinstance(action, dict):
        fail("action must be an object containing the one current learner task")
    action_title = text(action.get("title"), "action.title", maximum=120)
    action_prompt = text(action.get("prompt"), "action.prompt", maximum=2_000)
    response_hint = text(action.get("response_hint"), "action.response_hint", maximum=500)
    teaching_turn = None
    if kind in TEACHING_KINDS:
        try:
            teaching_turn = validate_teaching_turn(spec.get("teaching_turn"), action_prompt)
        except TeachingTurnError as error:
            fail(str(error))
        if kind in {"orientation", "lesson"} and "learner_promise" in spec["teaching_turn"]:
            promise = teaching_turn["learner_promise"]
            if promise not in title and promise not in lead:
                fail("teaching_turn.learner_promise must appear exactly in the learner-facing title or lead")
    elif spec.get("teaching_turn") is not None:
        fail(f"teaching_turn is required only for {sorted(TEACHING_KINDS)}")
    feedback_html = ""
    if kind == "feedback":
        feedback_html = render_feedback_context(spec.get("feedback_context"), ui)
        assert teaching_turn is not None
        if teaching_turn["feedback_plan"]["first_hint"] != spec["feedback_context"]["hint"].strip():
            fail("feedback_context.hint must exactly match teaching_turn.feedback_plan.first_hint")
        if spec["feedback_context"]["hint_level"] < 5:
            leak_surfaces = {
                "feedback_context.hint": spec["feedback_context"]["hint"],
                "action.response_hint": response_hint,
            }
            raw_response = action.get("response")
            if isinstance(raw_response, dict) and raw_response.get("type") in {"short-text", "long-text"}:
                for key in ["label", "placeholder", "submit_label"]:
                    if isinstance(raw_response.get(key), str):
                        leak_surfaces[f"action.response.{key}"] = raw_response[key]
            for field, surface in leak_surfaces.items():
                for option in teaching_turn["answer_options"]:
                    if option.casefold() in surface.casefold():
                        fail(f"{field} must not reveal answer option {option!r} below hint level 5")
    elif spec.get("feedback_context") is not None:
        fail("feedback_context is allowed only when kind is feedback")

    answer_options = teaching_turn["answer_options"] if teaching_turn is not None else []
    response_control, action_fields, submit_label = render_action_response(
        action.get("response"),
        kind=kind,
        answer_options=answer_options,
        has_choice_fields=bool(choice_fields),
        ui=ui,
    )
    response_fields = {**choice_fields, **action_fields}
    public_contract = {
        "schema_version": 1,
        "page_id": page_id,
        "language": language,
        "fields": response_fields,
    }
    contract_id = hashlib.sha256(
        json.dumps(public_contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    form_token = secrets.token_urlsafe(24)
    response_contract = {
        **public_contract,
        "contract_id": contract_id,
        "form_token": form_token,
    }
    form_hidden = (
        f'<input type="hidden" name="page_id" value="{escape(page_id)}">'
        f'<input type="hidden" name="contract_id" value="{contract_id}">'
        f'<input type="hidden" name="form_token" value="{escape(form_token)}">'
    )
    action_html = f"""
        <section class="current-action" data-classroom-action="one">
          <p class="action-label">{escape(ui["action_label"])}</p>
          <h2>{escape(action_title)}</h2>
          {feedback_html}
          <p>{escape(action_prompt)}</p>
          <p class="response-hint">{escape(ui["response_prefix"])} {escape(response_hint)}</p>
          {response_control}
          <button class="answer-submit" type="submit">{escape(submit_label)}</button>
          <p class="submit-note">{escape(ui["submit_note"])}</p>
        </section>"""
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

    turn_hash = ""
    if teaching_turn is not None:
        turn_hash = hashlib.sha256(
            json.dumps(teaching_turn, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    action_first = kind in {"feedback", "review"}
    intro_class = "turn-intro" if action_first else "turn-intro turn-intro--hero-only"

    response_form_open = (
        f'<form class="classroom-response" method="post" action="/respond" accept-charset="UTF-8">{form_hidden}'
    )
    response_form_close = "</form>"
    if kind == "onboarding":
        intro_action_html = ""
        flow_core_html = response_form_open + core_sections_html + action_html + response_form_close
    elif action_first:
        intro_action_html = response_form_open + action_html + response_form_close
        flow_core_html = core_sections_html
    else:
        intro_action_html = ""
        flow_core_html = core_sections_html + response_form_open + action_html + response_form_close

    page = f"""<!doctype html>
<html lang="{escape(language)}">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="{CONTENT_SECURITY_POLICY}">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>{escape(title)} · {escape(course)}</title>
  <link rel="stylesheet" href="assets/classroom.css">
</head>
<body data-page-id="{escape(page_id)}" data-turn-kind="{escape(kind)}" data-teaching-turn-sha256="{turn_hash}" data-response-contract-sha256="{contract_id}">
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
    <div class="{intro_class}">
      {intro_action_html}
      <header class="lesson-hero">
        <p class="eyebrow">{escape(eyebrow)}</p>
        <h1>{escape(title)}</h1>
        <p class="lead">{escape(lead)}</p>
        <div class="meta-grid">{"".join(meta_html)}</div>
      </header>
    </div>
    <div class="lesson-grid">
      <article class="lesson-flow">
        {flow_core_html}
        {optional_sections_html}
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
    return page, response_contract


def render(spec: dict[str, Any]) -> str:
    return build_classroom(spec)[0]


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


def remove_transient_response(path: Path) -> None:
    if not path.exists():
        return
    if is_reparse_point(path) or not path.is_file():
        fail("existing classroom response must be a regular file")
    path.unlink()


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
    page_html, response_contract = build_classroom(spec)
    response_path = output_dir / RESPONSE_PACKET_FILE
    remove_transient_response(response_path)
    contract_path = output_dir / RESPONSE_CONTRACT_FILE
    if contract_path.exists() and (is_reparse_point(contract_path) or not contract_path.is_file()):
        fail("existing classroom response contract must be a regular file")
    atomic_write(
        contract_path,
        json.dumps(response_contract, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )
    page = output_dir / "index.html"
    atomic_write(page, page_html)
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
