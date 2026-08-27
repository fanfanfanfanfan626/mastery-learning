#!/usr/bin/env python3
"""Serve only the current classroom page and stylesheet on an assigned loopback port."""

from __future__ import annotations

import argparse
import html
import json
import os
import stat
import sys
import tempfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from render_classroom import CONTENT_SECURITY_POLICY, RESPONSE_CONTRACT_FILE, RESPONSE_PACKET_FILE


ALLOWED_PATHS = {
    "/": "index.html",
    "/index.html": "index.html",
    "/assets/classroom.css": "assets/classroom.css",
}
RESPONSE_PATH = "/respond"
MAX_RESPONSE_BYTES = 32_000

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def is_same_loopback_origin(value: str, port: int) -> bool:
    try:
        parsed = urlsplit(value)
        parsed_port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "http"
        and parsed.hostname == "127.0.0.1"
        and parsed_port == port
        and parsed.username is None
        and parsed.password is None
    )


def fail(message: str) -> None:
    raise SystemExit(message)


def is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def validate_root(value: Path) -> Path:
    root = value.expanduser().resolve()
    if not root.is_dir():
        fail(f"classroom root does not exist: {root}")
    for relative in sorted(set(ALLOWED_PATHS.values())):
        lexical = root / relative
        if is_reparse_point(lexical):
            fail(f"classroom resource must not be a symbolic link or junction: {relative}")
        resolved = lexical.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            fail(f"classroom resource escapes its root: {relative}")
        if not resolved.is_file():
            fail(f"classroom resource is missing: {relative}")
    contract = root / RESPONSE_CONTRACT_FILE
    if is_reparse_point(contract) or not contract.is_file():
        fail("classroom response contract is missing or not a regular file")
    return root


def read_json_object(path: Path, label: str) -> dict[str, object]:
    if is_reparse_point(path) or not path.is_file() or path.stat().st_size > MAX_RESPONSE_BYTES:
        fail(f"{label} is missing, unsafe, or too large")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"cannot read {label}: {error}")
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def atomic_write_json(path: Path, value: dict[str, object]) -> None:
    if path.exists() and (is_reparse_point(path) or not path.is_file()):
        fail("classroom response destination must be a regular file")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def consume_response(root: Path, expected_page_id: str) -> tuple[dict[str, object], bytes]:
    contract = read_json_object(root / RESPONSE_CONTRACT_FILE, "classroom response contract")
    response_path = root / RESPONSE_PACKET_FILE
    if is_reparse_point(response_path) or not response_path.is_file() or response_path.stat().st_size > MAX_RESPONSE_BYTES:
        fail("classroom response is missing, unsafe, or too large")
    try:
        snapshot = response_path.read_bytes()
        response = json.loads(snapshot.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"cannot read classroom response: {error}")
    if not isinstance(response, dict):
        fail("classroom response must be a JSON object")
    if response.get("page_id") != expected_page_id:
        fail("classroom response belongs to a different page")
    if response.get("page_id") != contract.get("page_id") or response.get("contract_id") != contract.get("contract_id"):
        fail("classroom response is stale for the current page")
    return response, snapshot


class ClassroomHandler(SimpleHTTPRequestHandler):
    """A no-cache, allowlisted static handler that never exposes sibling learning state."""

    server_version = "MasteryClassroom/1"

    def _allowed_target(self) -> Path | None:
        try:
            path = unquote(urlsplit(self.path).path)
        except ValueError:
            return None
        relative = ALLOWED_PATHS.get(path)
        if relative is None:
            return None
        root = Path(self.directory).resolve()
        lexical = root / relative
        if is_reparse_point(lexical):
            return None
        target = lexical.resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return None
        return target if target.is_file() else None

    def send_head(self):  # type: ignore[no-untyped-def]
        if self._allowed_target() is None:
            self.send_error(404, "Classroom resource not found")
            return None
        for header in ["If-Modified-Since", "If-None-Match"]:
            if header in self.headers:
                del self.headers[header]
        return super().send_head()

    def list_directory(self, path):  # type: ignore[no-untyped-def]
        self.send_error(404, "Directory listing is disabled")
        return None

    def _send_message(self, status: int, title: str, body: str) -> None:
        page = (
            "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{html.escape(title)}</title><link rel=\"stylesheet\" href=\"/assets/classroom.css\"></head>"
            "<body><main class=\"classroom-shell\"><section class=\"classroom-section\">"
            f"<h1>{html.escape(title)}</h1><p>{html.escape(body)}</p>"
            "<p><a href=\"/index.html\">返回课堂</a></p></section></main></body></html>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self) -> None:  # noqa: N802
        try:
            request_path = unquote(urlsplit(self.path).path)
        except ValueError:
            self._send_message(400, "没有提交成功", "这个地址不对，请返回课堂再试一次。")
            return
        if request_path != RESPONSE_PATH:
            self._send_message(404, "没有找到", "这里只接收当前课堂里的回答。")
            return
        origin = self.headers.get("Origin")
        # Sandboxed local browser surfaces may serialize a loopback form origin as "null".
        # The unguessable per-render form token remains mandatory in every accepted case.
        if origin not in {None, "null"} and not is_same_loopback_origin(
            origin, int(self.server.server_address[1])
        ):
            self._send_message(403, "没有提交成功", "请只从刚才打开的课堂页面提交。")
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/x-www-form-urlencoded":
            self._send_message(415, "没有提交成功", "回答格式不对，请返回课堂再试一次。")
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if not 1 <= length <= MAX_RESPONSE_BYTES:
            self._send_message(413, "没有提交成功", "这次回答太长了，请稍微缩短一点。")
            return
        try:
            payload = self.rfile.read(length).decode("utf-8")
            values = parse_qs(payload, keep_blank_values=True, strict_parsing=True, max_num_fields=24)
            root = Path(self.directory).resolve()
            contract = read_json_object(root / RESPONSE_CONTRACT_FILE, "classroom response contract")
        except (UnicodeError, ValueError, SystemExit):
            self._send_message(400, "没有提交成功", "页面内容可能刚刚更新了，请返回课堂刷新后再试。")
            return

        expected_fields = contract.get("fields")
        if not isinstance(expected_fields, dict):
            self._send_message(409, "没有提交成功", "课堂刚刚更新了，请返回后再试一次。")
            return
        control_fields = {"page_id", "contract_id", "form_token"}
        if set(values) != control_fields | set(expected_fields):
            self._send_message(400, "没有提交成功", "回答项目和当前课堂不一致，请刷新后再试。")
            return
        if any(len(item) != 1 for item in values.values()):
            self._send_message(400, "没有提交成功", "每一项只能提交一个回答。")
            return
        if (
            values["page_id"][0] != contract.get("page_id")
            or values["contract_id"][0] != contract.get("contract_id")
            or values["form_token"][0] != contract.get("form_token")
        ):
            self._send_message(409, "没有提交成功", "课堂已经更新，请返回刷新后再提交。")
            return

        submitted: dict[str, str] = {}
        for name, rule in expected_fields.items():
            if not isinstance(name, str) or not isinstance(rule, dict):
                self._send_message(409, "没有提交成功", "课堂刚刚更新了，请返回后再试一次。")
                return
            value = values[name][0].strip()
            maximum = rule.get("max_length")
            if not isinstance(maximum, int) or len(value) > maximum or (rule.get("required") and not value):
                self._send_message(400, "没有提交成功", "有一项还没填好，请返回检查一下。")
                return
            if rule.get("type") == "choice":
                allowed = rule.get("allowed_values")
                if not isinstance(allowed, list) or value not in allowed:
                    self._send_message(400, "没有提交成功", "有一个选择不属于当前页面，请刷新后再试。")
                    return
            elif rule.get("type") != "text":
                self._send_message(409, "没有提交成功", "课堂刚刚更新了，请返回后再试一次。")
                return
            submitted[name] = value

        packet: dict[str, object] = {
            "schema_version": 1,
            "page_id": contract["page_id"],
            "contract_id": contract["contract_id"],
            "submitted_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "fields": submitted,
        }
        try:
            atomic_write_json(root / RESPONSE_PACKET_FILE, packet)
        except SystemExit:
            self._send_message(500, "暂时没有保存", "请返回课堂保留页面，然后在对话里告诉我。")
            return
        language = str(contract.get("language", "zh-CN")).lower()
        if language.startswith("zh"):
            self._send_message(200, "收到啦", "回到刚才的对话说一声“好了”，我们就从这里继续。")
        else:
            self._send_message(200, "Got it", "Return to the conversation and say you are ready to continue.")

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()


class ClassroomServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve one Mastery HTML classroom without exposing learning state")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--consume-response", action="store_true")
    parser.add_argument("--page-id")
    args = parser.parse_args()
    root = validate_root(args.root)
    if args.consume_response:
        if args.port != 0:
            fail("--port is not used with --consume-response")
        if not args.page_id:
            fail("--page-id is required with --consume-response")
        response, snapshot = consume_response(root, args.page_id)
        print(json.dumps({"ok": True, "response": response}, ensure_ascii=False, indent=2))
        sys.stdout.flush()
        response_path = root / RESPONSE_PACKET_FILE
        try:
            if response_path.is_file() and not is_reparse_point(response_path) and response_path.read_bytes() == snapshot:
                response_path.unlink()
        except OSError:
            pass
        return
    if args.page_id:
        fail("--page-id is allowed only with --consume-response")
    if args.port != 0:
        fail("--port must be 0 so the operating system assigns an unshared loopback port")

    def handler(*handler_args, **handler_kwargs):  # type: ignore[no-untyped-def]
        return ClassroomHandler(*handler_args, directory=str(root), **handler_kwargs)

    server = ClassroomServer(("127.0.0.1", args.port), handler)
    port = int(server.server_address[1])
    print(json.dumps({
        "ok": True,
        "url": f"http://127.0.0.1:{port}/index.html",
        "port": port,
        "pid": os.getpid(),
        "root": str(root),
        "cache": "no-store",
        "allowed_paths": sorted(ALLOWED_PATHS),
    }, ensure_ascii=False), flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
