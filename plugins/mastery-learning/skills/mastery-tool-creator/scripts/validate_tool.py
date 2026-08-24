#!/usr/bin/env python3
"""Validate teaching-tool contracts without executing generated code."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shlex
import stat
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from tool_common import (
    IGNORED_SNAPSHOT_FILES, IGNORED_SNAPSHOT_PARTS, safe_tool_root, tool_snapshot,
    update_catalog_rejection, update_catalog_validation,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = 3
TYPES = {"code_lab", "visual_lab", "lesson_lab", "simulation_3d", "blackboard", "notebook", "quiz", "slide_deck", "document", "project_lab"}
MODES = {"coach", "demonstration", "pair", "exam", "review"}
DIMENSIONS = {"recall", "conceptual", "application", "debugging", "transfer", "creation"}
KINDS = {"diagnostic", "recall", "explain", "exercise", "debug", "transfer", "project", "review"}
KIND_DIMENSIONS = {
    "diagnostic": {"conceptual"}, "recall": {"recall"}, "explain": {"conceptual"},
    "exercise": {"application"}, "debug": {"debugging", "application"},
    "transfer": {"transfer", "conceptual"}, "project": {"creation", "application", "transfer"},
    "review": {"recall"},
}
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TEXT_SUFFIXES = {
    ".md", ".html", ".htm", ".py", ".json", ".ipynb", ".js", ".mjs",
    ".jsx", ".ts", ".tsx", ".css", ".txt",
}
RENDER_TYPES = {"visual_lab", "lesson_lab", "simulation_3d", "slide_deck", "document"}
HTML_TOOL_TYPES = {"visual_lab", "lesson_lab", "simulation_3d"}
CANONICAL_HTML_LAUNCH = (
    "Coach-internal: from this tool directory run `<python> -m http.server 0 --bind 127.0.0.1`, "
    "parse the assigned loopback port, open `/index.html`, and stop the exact server session after use; "
    "never hand these steps to the learner."
)
CANONICAL_RENDER_CLEANUP = (
    "Stop the exact loopback server process/session, verify its assigned port is closed, then export learner work if needed; "
    "delete only this tool directory after learner confirmation."
)
JAVASCRIPT_SUFFIXES = {".js", ".mjs", ".jsx", ".ts", ".tsx"}
FORBIDDEN_PYTHON_IMPORTS = {
    "aiohttp", "ctypes", "ftplib", "http", "httpx", "importlib", "paramiko",
    "requests", "runpy", "smtplib", "socket", "subprocess", "urllib", "urllib3",
    "webbrowser", "websockets",
}
FORBIDDEN_PYTHON_CALLS = {
    "__import__", "compile", "eval", "exec",
    "os.execl", "os.execle", "os.execlp", "os.execlpe", "os.execv", "os.execve",
    "os.execvp", "os.execvpe", "os.popen", "os.posix_spawn", "os.posix_spawnp",
    "os.spawnl", "os.spawnle", "os.spawnlp", "os.spawnlpe", "os.spawnv",
    "os.spawnve", "os.spawnvp", "os.spawnvpe", "os.startfile", "os.system",
}
FORBIDDEN_JAVASCRIPT = [
    (re.compile(r"\bimport\s*\("), "dynamic import()"),
    (re.compile(r"\bfetch\s*\("), "fetch()"),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\b(?:WebSocket|EventSource|Worker|SharedWorker)\s*\("), "network/worker constructor"),
    (re.compile(r"\bimportScripts\s*\("), "importScripts()"),
    (re.compile(r"\b(?:navigator\s*\.\s*)?sendBeacon\s*\("), "sendBeacon()"),
    (re.compile(r"\bserviceWorker\s*\.\s*register\s*\("), "service worker registration"),
    (re.compile(r"\b(?:eval|Function)\s*\("), "dynamic code evaluation"),
    (re.compile(r"\bwindow\s*\.\s*open\s*\("), "window.open()"),
    (re.compile(r"\b(?:location\s*\.\s*(?:assign|replace)|document\s*\.\s*write)\s*\("), "dynamic navigation/document write"),
    (re.compile(r"\b(?:(?:window|top|parent)\s*\.\s*)?location(?:\s*\.\s*href)?\s*="), "dynamic navigation assignment"),
    (re.compile(r"\bdocument\s*\.\s*createElement\s*\(\s*['\"](?:script|iframe|link|object|embed)['\"]"), "dynamic executable element creation"),
]
REMOTE_URL_LITERAL = re.compile(r"(?:https?|wss?|ftp):/{2}|(?<!:)//[A-Za-z0-9.-]+", re.IGNORECASE)
MODULE_SPECIFIER = re.compile(
    r"(?:\bimport\s+(?:[^'\";]+?\s+from\s+)?|\bexport\s+[^'\";]+?\s+from\s+|\brequire\s*\()"
    r"['\"]([^'\"]+)['\"]",
)
COMPUTED_REQUIRE = re.compile(r"\brequire\s*\(\s*(?!['\"])")
CSS_IMPORT = re.compile(r"@import\b", re.IGNORECASE)
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
CSP_REQUIRED = {
    "default-src": {"'self'"},
    "connect-src": {"'none'"},
    "img-src": {"'self'", "data:"},
    "media-src": {"'self'"},
    "font-src": {"'self'"},
    "style-src": {"'self'", "'unsafe-inline'"},
    "script-src": {"'self'", "'unsafe-inline'"},
    "object-src": {"'none'"},
    "frame-src": {"'none'"},
    "worker-src": {"'none'"},
    "base-uri": {"'none'"},
    "form-action": {"'none'"},
}


class HTMLSecurityParser(HTMLParser):
    """Collect resources and executable content from static HTML."""

    RESOURCE_ATTRIBUTES = {"action", "data", "formaction", "href", "poster", "src", "srcset", "xlink:href"}
    ACTIVE_TAGS = {"audio", "embed", "iframe", "img", "link", "object", "script", "source", "style", "video"}
    FORBIDDEN_EMBED_TAGS = {"embed", "iframe", "object"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str, str, str]] = []
        self.inline_scripts: list[str] = []
        self.inline_styles: list[str] = []
        self.csp_values: list[str] = []
        self.forbidden_embed_tags: list[str] = []
        self.meta_refresh = False
        self.outbound_ping = False
        self.active_before_csp = False
        self.csp_outside_head = False
        self._seen_csp = False
        self._head_depth = 0
        self._template_depth = 0
        self._capture: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        values = {key.lower(): value for key, value in attrs}
        if lowered == "head":
            self._head_depth += 1
        if lowered == "template":
            self._template_depth += 1
        is_csp = lowered == "meta" and (values.get("http-equiv") or "").strip().lower() == "content-security-policy"
        is_active = lowered in self.ACTIVE_TAGS or any(key.startswith("on") or key == "style" for key in values)
        if is_csp:
            if is_active and not self._seen_csp:
                self.active_before_csp = True
            self._seen_csp = True
            if self._head_depth != 1 or self._template_depth:
                self.csp_outside_head = True
        elif is_active and not self._seen_csp:
            self.active_before_csp = True
        if lowered in self.FORBIDDEN_EMBED_TAGS:
            self.forbidden_embed_tags.append(lowered)
        if lowered == "meta" and (values.get("http-equiv") or "").strip().lower() == "refresh":
            self.meta_refresh = True
        if "ping" in values:
            self.outbound_ping = True
        for attribute in self.RESOURCE_ATTRIBUTES.intersection(values):
            value = values.get(attribute)
            if not isinstance(value, str):
                continue
            candidates = [value]
            if attribute == "srcset":
                candidates = [item.strip().split()[0] for item in value.split(",") if item.strip()]
            relation = values.get("rel") or ""
            self.references.extend((lowered, attribute, candidate, relation) for candidate in candidates)
        for attribute, value in values.items():
            if attribute.startswith("on") and isinstance(value, str):
                self.inline_scripts.append(value)
            if attribute == "style" and isinstance(value, str):
                self.inline_styles.append(value)
        if is_csp:
            if isinstance(values.get("content"), str):
                self.csp_values.append(values["content"] or "")
        if lowered in {"script", "style"} and not values.get("src"):
            self._capture = lowered
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "head" and self._head_depth:
            self._head_depth -= 1
        if tag.lower() == "template" and self._template_depth:
            self._template_depth -= 1
        if self._capture != tag.lower():
            return
        content = "".join(self._buffer)
        (self.inline_scripts if self._capture == "script" else self.inline_styles).append(content)
        self._capture = None
        self._buffer = []


class LessonStructureParser(HTMLParser):
    """Collect real lesson elements so comments and script strings cannot satisfy the contract."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: set[str] = set()
        self.sections: set[str] = set()
        self.roles: set[str] = set()
        self.session_minutes: list[str] = []
        self.progressive_disclosure = False
        self.code_note = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag.lower())
        values = {key.lower(): value for key, value in attrs}
        section = values.get("data-lesson-section")
        if isinstance(section, str):
            self.sections.add(section.strip().lower())
        role = values.get("data-role")
        if isinstance(role, str):
            self.roles.add(role.strip().lower())
        duration = values.get("data-session-minutes")
        if isinstance(duration, str):
            self.session_minutes.append(duration.strip())
        self.progressive_disclosure |= "data-progressive-disclosure" in values
        self.code_note |= "data-code-note" in values


def _call_name(node: ast.Call) -> str:
    parts: list[str] = []
    target: ast.AST = node.func
    while isinstance(target, ast.Attribute):
        parts.append(target.attr)
        target = target.value
    if isinstance(target, ast.Name):
        parts.append(target.id)
    return ".".join(reversed(parts))


def is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def validate_python(content: str, relative: str, errors: list[str]) -> None:
    try:
        tree = ast.parse(content, filename=relative)
    except SyntaxError as error:
        errors.append(f"invalid Python syntax in {relative}: line {error.lineno}: {error.msg}")
        return
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            for alias in node.names:
                aliases[alias.asname or alias.name.split(".", 1)[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
            for alias in node.names:
                if alias.name != "*":
                    aliases[alias.asname or alias.name] = f"{node.module or ''}.{alias.name}".strip(".")
        else:
            names = []
        for name in names:
            if name.split(".", 1)[0] in FORBIDDEN_PYTHON_IMPORTS:
                errors.append(f"network/process/dynamic-code import is not allowed in {relative}: {name}")
        if isinstance(node, ast.Call):
            name = _call_name(node)
            first, separator, remainder = name.partition(".")
            if first in aliases:
                name = aliases[first] + (separator + remainder if separator else "")
            if name in FORBIDDEN_PYTHON_CALLS:
                errors.append(f"dynamic code or process launch is not allowed in {relative}: {name}()")
            elif name.rsplit(".", 1)[-1] in {"__import__", "compile", "eval", "exec"}:
                errors.append(f"dynamic code evaluation is not allowed in {relative}: {name}()")
            if name == "getattr" and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                attribute = node.args[1].value
                if isinstance(attribute, str) and any(item.endswith(f".{attribute}") for item in FORBIDDEN_PYTHON_CALLS):
                    errors.append(f"indirect process launch is not allowed in {relative}: getattr(..., {attribute!r})")
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and REMOTE_URL_LITERAL.search(node.value):
            errors.append(f"remote URL literals belong in manifest sources, not executable Python: {relative}")


def _local_reference(root: Path, source: Path, reference: str, errors: list[str], label: str) -> Path | None:
    try:
        parsed = urlsplit(reference)
    except ValueError:
        errors.append(f"invalid {label} in {source.name}: {reference}")
        return None
    if parsed.scheme or parsed.netloc:
        errors.append(f"remote or scheme-bearing {label} is not allowed in {source.name}: {reference}")
        return None
    if not parsed.path:
        return None
    try:
        target = (source.parent / unquote(parsed.path)).resolve()
        target.relative_to(root.resolve())
    except (OSError, ValueError):
        errors.append(f"{label} escapes the tool directory: {reference}")
        return None
    if not target.is_file():
        errors.append(f"{label} does not resolve to a file: {reference}")
        return None
    return target


def validate_javascript(root: Path, source: Path, content: str, errors: list[str]) -> None:
    relative = str(source.relative_to(root)).replace("\\", "/")
    for pattern, capability in FORBIDDEN_JAVASCRIPT:
        if pattern.search(content):
            errors.append(f"{capability} is not allowed in local teaching tool JavaScript: {relative}")
    if COMPUTED_REQUIRE.search(content):
        errors.append(f"computed require() is not allowed in local teaching tool JavaScript: {relative}")
    if REMOTE_URL_LITERAL.search(content):
        errors.append(f"remote URL literals belong in manifest sources or passive anchors, not JavaScript: {relative}")
    for specifier in MODULE_SPECIFIER.findall(content):
        if specifier.startswith("node:") or specifier in {"assert", "assert/strict", "test"}:
            continue
        if not specifier.startswith(("./", "../")):
            errors.append(f"JavaScript module must be a tracked local relative file in {relative}: {specifier}")
            continue
        _local_reference(root, source, specifier, errors, "JavaScript module reference")


def validate_css(root: Path, source: Path, content: str, errors: list[str]) -> None:
    relative = str(source.relative_to(root)).replace("\\", "/")
    if CSS_IMPORT.search(content):
        errors.append(f"CSS @import is not allowed in local teaching tool: {relative}")
    for _, reference in CSS_URL.findall(content):
        value = reference.strip()
        if value.startswith("data:image/"):
            continue
        _local_reference(root, source, value, errors, "CSS resource reference")


def validate_csp(parser: HTMLSecurityParser, entry: Path, errors: list[str]) -> None:
    if len(parser.csp_values) != 1:
        errors.append(f"{entry.name} must contain exactly one Content-Security-Policy meta element")
        return
    directives: dict[str, set[str]] = {}
    for raw in parser.csp_values[0].split(";"):
        tokens = raw.strip().split()
        if not tokens:
            continue
        name, values = tokens[0].lower(), set(tokens[1:])
        if name in directives:
            errors.append(f"duplicate Content-Security-Policy directive in {entry.name}: {name}")
        directives[name] = values
    unknown = sorted(set(directives) - set(CSP_REQUIRED))
    if unknown:
        errors.append(f"unsupported Content-Security-Policy directives in {entry.name}: {unknown}")
    for name, expected in CSP_REQUIRED.items():
        if directives.get(name) != expected:
            errors.append(f"unsafe or missing Content-Security-Policy directive in {entry.name}: {name}")
    if parser.active_before_csp:
        errors.append(f"Content-Security-Policy must appear before active content in {entry.name}")
    if parser.csp_outside_head:
        errors.append(f"Content-Security-Policy must be a direct, effective element inside head in {entry.name}")


def validate_local_html_references(root: Path, entry: Path, content: str, fallback: Path | None, errors: list[str]) -> None:
    parser = HTMLSecurityParser()
    parser.feed(content)
    validate_csp(parser, entry, errors)
    if parser.forbidden_embed_tags:
        errors.append(f"embedded browsing/plugin contexts are not allowed in {entry.name}: {sorted(set(parser.forbidden_embed_tags))}")
    if parser.meta_refresh:
        errors.append(f"meta refresh navigation is not allowed in {entry.name}")
    if parser.outbound_ping:
        errors.append(f"outbound ping attributes are not allowed in {entry.name}")
    linked_fallback = False
    for tag, attribute, reference, relation in parser.references:
        try:
            parsed = urlsplit(reference)
        except ValueError:
            errors.append(f"invalid HTML reference in {entry.name}: {reference}")
            continue
        if parsed.scheme or parsed.netloc:
            if (
                tag == "a"
                and attribute == "href"
                and parsed.scheme == "https"
                and bool(parsed.netloc)
                and parsed.username is None
                and parsed.password is None
            ):
                relation_tokens = set(relation.lower().split())
                if not {"noopener", "noreferrer"}.issubset(relation_tokens):
                    errors.append(f"passive external source link must use rel=\"noopener noreferrer\" in {entry.name}: {reference}")
                continue
            errors.append(f"remote executable or submission resource is not allowed in {entry.name}: {reference}")
            continue
        if reference.startswith("//"):
            errors.append(f"protocol-relative resource is not allowed in {entry.name}: {reference}")
            continue
        target = _local_reference(root, entry, reference, errors, "local HTML reference")
        if target is not None and tag == "script" and target.suffix.lower() not in JAVASCRIPT_SUFFIXES:
            errors.append(f"script resource must use a validated JavaScript/TypeScript suffix in {entry.name}: {reference}")
        if target is not None and tag == "link" and "stylesheet" in relation.lower().split() and target.suffix.lower() != ".css":
            errors.append(f"stylesheet resource must use a validated .css suffix in {entry.name}: {reference}")
        if fallback is not None and target == fallback.resolve():
            linked_fallback = True
    for script in parser.inline_scripts:
        validate_javascript(root, entry, script, errors)
    for style in parser.inline_styles:
        validate_css(root, entry, style, errors)
    if fallback is not None and not linked_fallback:
        errors.append("visual entrypoint must link directly to the declared accessibility_fallback")

def inside(root: Path, relative: str) -> Path | None:
    try:
        lexical = root / relative
        cursor = root
        for part in Path(relative).parts:
            cursor = cursor / part
            if cursor.exists():
                if is_reparse_point(cursor):
                    return None
        path = lexical.resolve()
        tracked = path.relative_to(root.resolve())
        if any(part in IGNORED_SNAPSHOT_PARTS for part in tracked.parts) or path.name in IGNORED_SNAPSHOT_FILES:
            return None
        return path
    except (ValueError, TypeError, OSError):
        return None


def unfinished(value: Any) -> bool:
    if isinstance(value, str):
        return "CUSTOMIZE" in value
    if isinstance(value, list):
        return any(unfinished(item) for item in value)
    if isinstance(value, dict):
        return any(unfinished(item) for item in value.values())
    return False


def read_text(path: Path, errors: list[str]) -> str:
    try:
        if path.stat().st_size > 2_000_000:
            errors.append(f"text artifact is too large to validate safely: {path.name}")
            return ""
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        errors.append(f"cannot read {path.name} as UTF-8: {error}")
        return ""


def validate_manifest(manifest: Any, errors: list[str]) -> None:
    if not isinstance(manifest, dict):
        errors.append("tool.json root must be an object")
        return
    required = [
        "schema_version", "id", "version", "build_status", "type", "concept", "objective", "mode", "prerequisites",
        "interaction", "evidence", "entrypoint", "check_command", "check_expectation",
        "accessibility_fallback", "launch", "cleanup", "inspection", "sources", "created_at", "generator",
    ]
    allowed = set(required) | {"prerequisites", "sources", "created_at"}
    for field in required:
        if field not in manifest:
            errors.append(f"missing manifest field: {field}")
    unknown = sorted(set(manifest) - allowed)
    if unknown:
        errors.append(f"unknown manifest fields: {unknown}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(manifest.get("id"), str) or not ID_PATTERN.fullmatch(manifest.get("id", "")):
        errors.append("id must be lowercase hyphen-case")
    if not isinstance(manifest.get("version"), str) or not manifest.get("version", "").strip():
        errors.append("version must be non-empty")
    if manifest.get("build_status") != "complete":
        errors.append("build_status must be complete after concept-specific customization")
    if manifest.get("type") not in TYPES:
        errors.append("invalid tool type")
    if not isinstance(manifest.get("concept"), str) or not ID_PATTERN.fullmatch(manifest.get("concept", "")):
        errors.append("concept must be a registered lowercase hyphen-case concept ID")
    objective = manifest.get("objective")
    if (
        not isinstance(objective, str)
        or not 12 <= len(objective.strip()) <= 500
        or "\n" in objective
        or "\r" in objective
        or any(ord(character) < 32 for character in objective)
    ):
        errors.append("objective must be an observable outcome of at least 12 characters")
    if manifest.get("mode") not in MODES:
        errors.append("invalid mode")
    prerequisites = manifest.get("prerequisites")
    if not isinstance(prerequisites, list) or any(not isinstance(item, str) or not ID_PATTERN.fullmatch(item) for item in prerequisites):
        errors.append("prerequisites must be an array of lowercase hyphen-case concept IDs")
    elif len(prerequisites) != len(set(prerequisites)) or manifest.get("concept") in prerequisites:
        errors.append("prerequisites must be unique and cannot include the target concept")
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be an array")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict) or not isinstance(source.get("title"), str) or not source["title"].strip():
                errors.append(f"sources[{index}] must contain a non-empty title")
                continue
            unknown_source_fields = set(source) - {"title", "url", "checked_at", "license_reuse"}
            if unknown_source_fields:
                errors.append(f"sources[{index}] contains unknown fields: {sorted(unknown_source_fields)}")
            url = source.get("url")
            try:
                parsed_source = urlsplit(url) if isinstance(url, str) else None
            except ValueError:
                parsed_source = None
            if (
                parsed_source is None
                or parsed_source.scheme != "https"
                or not parsed_source.netloc
                or parsed_source.username is not None
                or parsed_source.password is not None
            ):
                errors.append(f"sources[{index}].url must be HTTPS without embedded credentials")
            for optional in ["checked_at", "license_reuse"]:
                if optional in source and (not isinstance(source[optional], str) or not source[optional].strip()):
                    errors.append(f"sources[{index}].{optional} must be non-empty text when present")
    if not isinstance(manifest.get("created_at"), str) or not manifest.get("created_at", "").strip():
        errors.append("created_at must be non-empty text")
    if not isinstance(manifest.get("launch"), str) or not manifest.get("launch", "").strip():
        errors.append("launch instructions must be non-empty")
    if not isinstance(manifest.get("cleanup"), str) or not manifest.get("cleanup", "").strip():
        errors.append("cleanup instructions must be non-empty")
    generator = manifest.get("generator")
    if not isinstance(generator, dict) or not all(isinstance(generator.get(field), str) and generator[field].strip() for field in ["name", "version"]):
        errors.append("generator must contain non-empty name and version")
    if unfinished(manifest):
        errors.append("tool.json contains unfinished CUSTOMIZE markers")

    interaction = manifest.get("interaction")
    if not isinstance(interaction, dict):
        errors.append("interaction must be an object")
    else:
        for field in ["prediction", "learner_action", "feedback", "hints", "transfer"]:
            if field not in interaction:
                errors.append(f"missing interaction.{field}")
        for field in ["prediction", "learner_action", "feedback", "transfer"]:
            if not isinstance(interaction.get(field), str) or not interaction.get(field, "").strip():
                errors.append(f"interaction.{field} must be non-empty text")
        if not isinstance(interaction.get("hints"), list) or any(not isinstance(item, str) or not item.strip() for item in interaction.get("hints", [])):
            errors.append("interaction.hints must be an array of non-empty strings")
        if manifest.get("mode") == "exam" and interaction.get("hints"):
            errors.append("exam mode must not expose hints")

    evidence = manifest.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be an object")
    else:
        if evidence.get("kind") not in KINDS:
            errors.append("invalid evidence kind")
        dimensions = evidence.get("dimensions")
        if not isinstance(dimensions, list) or not dimensions or set(dimensions) - DIMENSIONS or len(dimensions) != len(set(dimensions)):
            errors.append("invalid or duplicate evidence dimensions")
        elif evidence.get("kind") in KIND_DIMENSIONS and not KIND_DIMENSIONS[evidence["kind"]].issubset(dimensions):
            minimum = sorted(KIND_DIMENSIONS[evidence["kind"]])
            errors.append(f"evidence kind {evidence['kind']} requires semantic minimum dimensions {minimum}")
        if not isinstance(evidence.get("rubric"), str) or not evidence.get("rubric", "").strip():
            errors.append("evidence.rubric must be a relative path")

    inspection = manifest.get("inspection")
    if not isinstance(inspection, dict):
        errors.append("inspection must be an object")
    else:
        expected_required = manifest.get("type") in RENDER_TYPES
        if inspection.get("required") is not expected_required:
            errors.append(f"inspection.required must be {str(expected_required).lower()} for this tool type")
        if not isinstance(inspection.get("notes"), str) or not inspection.get("notes", "").strip():
            errors.append("inspection.notes must describe what Codex must inspect")
        if set(inspection) - {"required", "notes"}:
            errors.append("inspection contains unsupported self-attested fields")


def validate_artifacts(root: Path, manifest: dict[str, Any], errors: list[str], warnings: list[str]) -> dict[str, str]:
    evidence = manifest.get("evidence", {}) if isinstance(manifest.get("evidence"), dict) else {}
    named = [manifest.get("entrypoint"), manifest.get("accessibility_fallback"), evidence.get("rubric")]
    texts: dict[str, str] = {}
    for relative in named:
        path = inside(root, relative) if isinstance(relative, str) else None
        if path is None:
            errors.append(f"unsafe artifact path: {relative}")
        elif not path.exists() or not path.is_file():
            errors.append(f"missing artifact: {relative}")

    for path in root.rglob("*"):
        if is_reparse_point(path):
            errors.append(f"symbolic links, junctions, and reparse points are not allowed in generated tools: {path.relative_to(root)}")
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            relative = str(path.relative_to(root)).replace("\\", "/")
            content = read_text(path, errors)
            texts[relative] = content
            if "CUSTOMIZE" in content:
                errors.append(f"unfinished scaffold marker in {relative}")
            suffix = path.suffix.lower()
            if suffix == ".py":
                validate_python(content, relative, errors)
            elif suffix in JAVASCRIPT_SUFFIXES:
                validate_javascript(root, path, content, errors)
            elif suffix == ".css":
                validate_css(root, path, content, errors)
            elif suffix == ".ipynb":
                try:
                    notebook = json.loads(content)
                    for index, cell in enumerate(notebook.get("cells", [])):
                        if isinstance(cell, dict) and cell.get("cell_type") == "code":
                            source = cell.get("source", [])
                            code = "".join(source) if isinstance(source, list) else str(source)
                            validate_python(code, f"{relative}#cell-{index + 1}", errors)
                except (json.JSONDecodeError, TypeError, AttributeError):
                    pass

    rubric_relative = evidence.get("rubric")
    rubric_path = inside(root, rubric_relative) if isinstance(rubric_relative, str) else None
    if rubric_path and rubric_path.exists():
        try:
            rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
            if rubric.get("schema_version") != 1:
                errors.append("rubric schema_version must be 1")
            criteria = rubric.get("criteria")
            if not isinstance(criteria, list) or not criteria:
                errors.append("rubric has no criteria")
            else:
                identifiers = [item.get("id") for item in criteria if isinstance(item, dict)]
                if len(identifiers) != len(criteria) or len(set(identifiers)) != len(identifiers):
                    errors.append("rubric criterion IDs must be present and unique")
                weight = sum(float(item.get("weight", 0)) for item in criteria)
                if abs(weight - 1.0) > 0.001:
                    errors.append(f"rubric weights total {weight}, expected 1")
                for item in criteria:
                    if not all(isinstance(item.get(field), str) and item[field].strip() for field in ["description", "evidence"]):
                        errors.append("every rubric criterion needs description and evidence")
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            errors.append(f"invalid rubric: {error}")

    fallback = manifest.get("accessibility_fallback")
    if isinstance(fallback, str) and len(texts.get(fallback.replace("\\", "/"), "").strip()) < 80:
        errors.append("accessibility fallback is too short to be a usable equivalent")
    entry_relative = manifest.get("entrypoint")
    entry = inside(root, entry_relative) if isinstance(entry_relative, str) else None
    fallback_path = inside(root, fallback) if isinstance(fallback, str) else None
    requires_link = manifest.get("type") in {"visual_lab", "lesson_lab", "simulation_3d"}
    for relative, content in texts.items():
        if Path(relative).suffix.lower() not in {".html", ".htm"}:
            continue
        html_path = inside(root, relative)
        if html_path is not None:
            required_fallback = fallback_path if requires_link and entry is not None and html_path == entry else None
            validate_local_html_references(root, html_path, content, required_fallback, errors)
    if not manifest.get("sources"):
        warnings.append("no sources recorded; acceptable only for an original or common-knowledge tool")
    return texts


def validate_type(root: Path, manifest: dict[str, Any], texts: dict[str, str], errors: list[str]) -> None:
    tool_type = manifest.get("type")
    entry_relative = manifest.get("entrypoint", "")
    entry = inside(root, entry_relative) if isinstance(entry_relative, str) else None
    entry_text = texts.get(entry_relative.replace("\\", "/"), "") if isinstance(entry_relative, str) else ""
    mode = manifest.get("mode")
    if tool_type == "code_lab":
        if not entry or entry.suffix.lower() != ".py":
            errors.append("code_lab entrypoint must be a Python file")
        test = root / "test_exercise.py"
        if not test.exists():
            errors.append("code_lab requires test_exercise.py")
        else:
            test_content = texts.get("test_exercise.py", read_text(test, errors))
            if "self.fail(" in test_content:
                errors.append("code_lab test contains an unconditional self.fail placeholder")
            assertion = r"\b(?:self\.)?assert(?:Equal|NotEqual|True|False|Is|IsNot|IsNone|IsNotNone|In|NotIn|Raises|RaisesRegex|AlmostEqual|NotAlmostEqual|Greater|GreaterEqual|Less|LessEqual|Regex|NotRegex|CountEqual)\s*\("
            if not re.search(assertion, test_content) and not re.search(r"\bassert\s", test_content):
                errors.append("code_lab test has no deterministic assertion")
        if mode in {"coach", "exam"} and "LEARNER TODO" not in entry_text:
            errors.append("coach/exam code_lab must preserve a visible LEARNER TODO")
    elif tool_type in {"visual_lab", "lesson_lab", "simulation_3d"}:
        if not entry or entry.suffix.lower() not in {".html", ".htm"}:
            errors.append(f"{tool_type} entrypoint must be local HTML")
        executable_text = "\n".join(
            content for relative, content in texts.items()
            if Path(relative).suffix.lower() in JAVASCRIPT_SUFFIXES
        )
        if "addeventlistener" not in f"{entry_text}\n{executable_text}".lower():
            errors.append(f"{tool_type} is missing interactive event handling")
        for token, message in [("prediction", "a prediction control"), ("explanation", "an explanation control")]:
            if token not in entry_text.lower():
                errors.append(f"{tool_type} is missing {message}")
        if tool_type == "lesson_lab":
            required_sections = [
                "orientation", "mental-model", "worked-example", "interactive-model",
                "guided-practice", "transfer", "summary",
            ]
            structure = LessonStructureParser()
            structure.feed(entry_text)
            for section in required_sections:
                if section not in structure.sections:
                    errors.append(f"lesson_lab is missing required lesson section: {section}")
            if structure.tags.intersection({"pre", "code"}):
                if "annotated-code" not in structure.sections:
                    errors.append("lesson_lab containing code is missing the annotated-code section")
                if not structure.code_note:
                    errors.append("lesson_lab containing code needs visible data-code-note annotations")
            for role in ["current-target", "preview"]:
                if role not in structure.roles:
                    errors.append(f"lesson_lab must label the {role} learning boundary")
            durations = [int(value) for value in structure.session_minutes if value.isdigit()]
            if not durations or not any(10 <= value <= 90 for value in durations):
                errors.append("lesson_lab must declare data-session-minutes between 10 and 90")
            if not structure.progressive_disclosure:
                errors.append("lesson_lab needs progressive disclosure for optional depth or hints")
            for asset in ["styles.css", "app.js"]:
                if not (root / asset).is_file():
                    errors.append(f"lesson_lab requires the reusable local asset: {asset}")
            styles = texts.get("styles.css", "").lower()
            for token, message in [
                ("@media (max-width", "a responsive small-screen layout"),
                ("prefers-reduced-motion", "reduced-motion support"),
                (":focus-visible", "visible keyboard focus styles"),
            ]:
                if token not in styles:
                    errors.append(f"lesson_lab styles are missing {message}")
        if tool_type == "simulation_3d" and not any(token in entry_text.lower() for token in ["webgl", "perspective", "z-axis", "z axis"]):
            errors.append("simulation_3d does not encode an inspectable depth variable")
        launch = manifest.get("launch", "")
        if launch != CANONICAL_HTML_LAUNCH:
            errors.append(
                f"{tool_type} launch must equal the canonical coach-internal dynamic-loopback instruction"
            )
        if manifest.get("cleanup") != CANONICAL_RENDER_CLEANUP:
            errors.append(
                f"{tool_type} cleanup must stop the exact server process/session and verify the assigned port is closed"
            )
    elif tool_type == "notebook":
        if not entry or entry.suffix.lower() != ".ipynb":
            errors.append("notebook entrypoint must be .ipynb")
        elif entry.exists():
            try:
                notebook = json.loads(entry.read_text(encoding="utf-8"))
                cells = notebook.get("cells", [])
                code = "\n".join("".join(cell.get("source", [])) for cell in cells if cell.get("cell_type") == "code")
                markdown = "\n".join("".join(cell.get("source", [])) for cell in cells if cell.get("cell_type") == "markdown").lower()
                if notebook.get("nbformat") != 4 or len(cells) < 5:
                    errors.append("notebook needs nbformat 4 and at least five staged cells")
                if "learner todo" not in code.lower() or "assert" not in code:
                    errors.append("notebook needs a learner TODO and deterministic assertion")
                for stage in ["prediction", "transfer", "reflection"]:
                    if stage not in markdown:
                        errors.append(f"notebook is missing a {stage} stage")
            except (json.JSONDecodeError, TypeError) as error:
                errors.append(f"invalid notebook: {error}")
    elif tool_type == "slide_deck":
        if not entry or entry.suffix.lower() != ".pptx" or not entry.exists():
            errors.append("ready slide_deck entrypoint must be an actual .pptx file")
        elif not zipfile.is_zipfile(entry):
            errors.append("slide_deck entrypoint is not a valid PPTX ZIP package")
        else:
            with zipfile.ZipFile(entry) as package:
                names = set(package.namelist())
            if not {"[Content_Types].xml", "ppt/presentation.xml"}.issubset(names):
                errors.append("slide_deck package is missing required PPTX parts")
    elif tool_type == "document":
        if not entry or entry.suffix.lower() not in {".docx", ".pdf"} or not entry.exists():
            errors.append("ready document entrypoint must be an actual .docx or .pdf file")
        elif entry.suffix.lower() == ".docx":
            if not zipfile.is_zipfile(entry):
                errors.append("document entrypoint is not a valid DOCX ZIP package")
            else:
                with zipfile.ZipFile(entry) as package:
                    names = set(package.namelist())
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                    errors.append("document package is missing required DOCX parts")
        else:
            data = entry.read_bytes()
            if not data.startswith(b"%PDF") or b"%%EOF" not in data[-1024:]:
                errors.append("document entrypoint is not a complete-looking PDF")
    elif tool_type in {"blackboard", "quiz", "project_lab"}:
        if len(entry_text.strip()) < 200:
            errors.append(f"{tool_type} entrypoint is too short to contain a complete activity")
    if tool_type in {"code_lab", "notebook", "project_lab"} and not manifest.get("check_command"):
        errors.append(f"{tool_type} requires a deterministic check_command")


def _local_check_target(root: Path, value: str, *, allow_module: bool = False) -> bool:
    if not value or value.startswith("-") or ".." in Path(value).parts or Path(value).is_absolute():
        return False
    file_target = value.split("::", 1)[0]
    if Path(file_target).suffix:
        return inside(root, file_target) is not None
    if allow_module and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", value):
        candidate = root.joinpath(*value.split(".")).with_suffix(".py")
        return candidate.is_file() and inside(root, str(candidate.relative_to(root))) is not None
    return False


def command_args(root: Path, command: str) -> list[str] | None:
    try:
        parts = shlex.split(command, posix=True)
    except ValueError:
        return None
    if not parts:
        return None
    executable = Path(parts[0]).name.lower()
    if executable in {"python", "python3", "python.exe"}:
        if len(parts) >= 4 and parts[1:3] == ["-m", "unittest"]:
            allowed_flags = {"-v", "--verbose", "-q", "--quiet", "-f", "--failfast"}
            targets = [part for part in parts[3:] if part not in allowed_flags]
            if targets and len(targets) + sum(part in allowed_flags for part in parts[3:]) == len(parts[3:]) and all(
                _local_check_target(root, target, allow_module=True) for target in targets
            ):
                return [sys.executable, *parts[1:]]
            return None
        if len(parts) >= 4 and parts[1:3] == ["-m", "pytest"]:
            allowed_flags = {"-q", "--quiet", "-v", "--verbose", "-x"}
            targets = [part for part in parts[3:] if part not in allowed_flags]
            if targets and len(targets) + sum(part in allowed_flags for part in parts[3:]) == len(parts[3:]) and all(
                _local_check_target(root, target) for target in targets
            ):
                return [sys.executable, *parts[1:]]
            return None
        if len(parts) == 2 and parts[1].endswith(".py") and _local_check_target(root, parts[1]):
            return [sys.executable, *parts[1:]]
        return None
    if executable in {"node", "node.exe"}:
        if len(parts) == 2 and _local_check_target(root, parts[1]):
            return parts
        if len(parts) >= 3 and parts[1] == "--test" and all(_local_check_target(root, part) for part in parts[2:]):
            return parts
    return None


def declared_check(root: Path, manifest: dict[str, Any], errors: list[str]) -> dict[str, Any] | None:
    command = manifest.get("check_command")
    expectation = manifest.get("check_expectation")
    if command is None:
        if expectation is not None:
            errors.append("check_expectation must be null when check_command is null")
        return None
    if not isinstance(command, str) or not command.strip():
        errors.append("check_command must be non-empty text or null")
        return None
    if not isinstance(expectation, dict) or not isinstance(expectation.get("exit_code"), int):
        errors.append("check_expectation must declare integer exit_code")
        return None
    expected_text = expectation.get("output_contains")
    if expected_text is not None and (not isinstance(expected_text, str) or not expected_text.strip()):
        errors.append("check_expectation.output_contains must be non-empty text or null")
        return None
    arguments = command_args(root, command)
    if arguments is None:
        errors.append("check_command is outside the allowed Python unittest/pytest, local Python script, or Node test forms")
        return None
    return {
        "command": command, "cwd": str(root), "expected_exit_code": expectation["exit_code"],
        "output_contains": expected_text,
        "environment": {"PYTHONDONTWRITEBYTECODE": "1", "PYTEST_ADDOPTS": "-p no:cacheprovider"},
        "instruction": "Run this command only through Codex's available sandbox, with secrets removed and the declared no-cache environment applied; then pass observed results to finalize_tool.py.",
    }


def validate_concept_registration(root: Path, manifest: dict[str, Any], errors: list[str], warnings: list[str]) -> dict[str, Any]:
    prerequisites = manifest.get("prerequisites")
    prerequisite_items = prerequisites if isinstance(prerequisites, list) else []
    required = list(dict.fromkeys([manifest.get("concept"), *prerequisite_items]))
    required = [item for item in required if isinstance(item, str)]
    concepts_path = root.parent.parent / "concepts.json"
    if not concepts_path.exists():
        warnings.append("learner state is not initialized; register the target and prerequisite concept IDs before recording evidence")
        return {
            "status": "state-unavailable",
            "required_concepts": required,
            "instruction": "Initialize Mastery Coach state, then use its concept-add command for every custom ID before learner evidence is recorded.",
        }
    try:
        value = json.loads(concepts_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"cannot verify concept registration from concepts.json: {error}")
        return {"status": "invalid-state", "required_concepts": required}
    concepts = value.get("concepts") if isinstance(value, dict) else None
    if not isinstance(concepts, dict):
        errors.append("cannot verify concept registration: concepts.json has no concepts object")
        return {"status": "invalid-state", "required_concepts": required}
    missing = [item for item in required if item not in concepts]
    if missing:
        errors.append(f"unregistered concept IDs: {missing}; register them with Mastery Coach concept-add before validation")
        return {"status": "missing", "required_concepts": required, "missing": missing}
    return {"status": "registered", "required_concepts": required}


def update_catalog(root: Path, manifest: dict[str, Any], snapshot: dict[str, Any], errors: list[str]) -> tuple[str | None, str]:
    if root.parent.name != "tools" or root.parent.parent.name != ".mastery":
        errors.append("tool directory must be <workspace>/.mastery/tools/<tool-id>")
        return None, "rejected"
    catalog_path = root.parent.parent / "tool-catalog.json"
    if not catalog_path.exists():
        errors.append("missing .mastery/tool-catalog.json registration")
        return None, "rejected"
    try:
        status = update_catalog_validation(catalog_path, manifest["id"], root, snapshot["sha256"], SCHEMA_VERSION)
    except SystemExit as error:
        errors.append(str(error))
        return None, "rejected"
    return str(catalog_path), status


def main() -> None:
    parser = argparse.ArgumentParser(description="Statically validate a Mastery Learning teaching tool without executing it")
    parser.add_argument("tool_dir", type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    try:
        root = safe_tool_root(args.tool_dir)
    except SystemExit as error:
        print(json.dumps({"ok": False, "errors": [str(error)]}, ensure_ascii=False, indent=2))
        raise SystemExit(1) from error
    manifest_path = root / "tool.json"
    if not manifest_path.exists():
        print(json.dumps({"ok": False, "errors": ["missing tool.json"]}, indent=2))
        raise SystemExit(1)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(json.dumps({"ok": False, "errors": [f"invalid tool.json: {error}"]}, indent=2))
        raise SystemExit(1)

    validate_manifest(manifest, errors)
    texts = validate_artifacts(root, manifest if isinstance(manifest, dict) else {}, errors, warnings)
    validate_type(root, manifest if isinstance(manifest, dict) else {}, texts, errors)
    registration = validate_concept_registration(root, manifest if isinstance(manifest, dict) else {}, errors, warnings)
    check = None if errors else declared_check(root, manifest, errors)
    try:
        snapshot = tool_snapshot(root)
    except (OSError, SystemExit) as error:
        errors.append(str(error))
        snapshot = None
    catalog_path = root.parent.parent / "tool-catalog.json"
    if errors:
        try:
            update_catalog_rejection(catalog_path, root, snapshot.get("sha256") if snapshot else None, errors, SCHEMA_VERSION)
        except SystemExit as error:
            errors.append(str(error))
        catalog, status = None, "rejected"
    else:
        catalog, status = update_catalog(root, manifest, snapshot, errors)
    if errors:
        status = "rejected"
    inspection = manifest.get("inspection", {}) if isinstance(manifest, dict) else {}
    result = {
        "ok": not errors, "status": status, "tool_dir": str(root),
        "errors": errors, "warnings": warnings, "check_request": check,
        "inspection_request": inspection.get("notes") if inspection.get("required") else None,
        "concept_registration": registration, "tool_snapshot": snapshot, "catalog": catalog,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
