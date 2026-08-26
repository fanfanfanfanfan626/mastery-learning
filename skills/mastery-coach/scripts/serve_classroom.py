#!/usr/bin/env python3
"""Serve only the current classroom page and stylesheet on an assigned loopback port."""

from __future__ import annotations

import argparse
import json
import os
import stat
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from render_classroom import CONTENT_SECURITY_POLICY


ALLOWED_PATHS = {
    "/": "index.html",
    "/index.html": "index.html",
    "/assets/classroom.css": "assets/classroom.css",
}


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
    return root


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
    args = parser.parse_args()
    if args.port != 0:
        fail("--port must be 0 so the operating system assigns an unshared loopback port")
    root = validate_root(args.root)

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
