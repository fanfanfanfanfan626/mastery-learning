#!/usr/bin/env python3
"""Shared atomic catalog operations for teaching-tool scripts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


SNAPSHOT_ALGORITHM = "sha256-tree-v1"
IGNORED_SNAPSHOT_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_SNAPSHOT_FILES = {".coverage", ".DS_Store", "Thumbs.db"}
REPORT_OBSERVERS = {"codex", "claude-code", "github-copilot", "generic-agent"}
EXECUTION_BOUNDARIES = {"host-sandbox", "isolated-container", "learner-authorized-local", "not-applicable"}


def is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def safe_tool_root(value: Path) -> Path:
    """Resolve a canonical tool root only after rejecting linked lifecycle boundaries."""
    requested = value.expanduser().absolute()
    if requested.parent.name != "tools" or requested.parent.parent.name != ".mastery":
        raise SystemExit("tool directory must be <workspace>/.mastery/tools/<tool-id>")
    for boundary in [requested.parent.parent, requested.parent, requested]:
        if boundary.exists() and is_reparse_point(boundary):
            raise SystemExit(f"tool path must not traverse a symbolic link, junction, or reparse point: {boundary}")
    return requested.resolve()


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def tool_snapshot(root: Path) -> dict[str, Any]:
    """Hash every reusable tool input and reject untracked runtime/cache content."""
    root = root.resolve()
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        try:
            is_reparse = is_reparse_point(path)
            resolved = path.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError) as error:
            raise SystemExit(f"Cannot snapshot escaping or unreadable path: {relative.as_posix()}: {error}") from error
        if is_reparse:
            raise SystemExit(f"Cannot snapshot symbolic link, junction, or reparse point: {relative.as_posix()}")
        if any(part in IGNORED_SNAPSHOT_PARTS for part in relative.parts) or path.name in IGNORED_SNAPSHOT_FILES:
            raise SystemExit(
                f"Untracked runtime/cache content is forbidden in a verifiable tool: {relative.as_posix()}. "
                "Remove it and run checks with bytecode/cache creation disabled."
            )
        if not path.is_file():
            continue
        data = path.read_bytes()
        records.append({
            "path": relative.as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    if not records:
        raise SystemExit("Cannot snapshot an empty tool directory")
    canonical = json.dumps(records, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {
        "algorithm": SNAPSHOT_ALGORITHM,
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "files": records,
    }


def _verification_report_matches(catalog_path: Path, entry: dict[str, Any], tool_id: str, digest: str) -> bool:
    report_value = entry.get("verification_report")
    if not isinstance(report_value, str) or not report_value:
        return False
    try:
        report_path = Path(report_value).resolve()
        expected_path = (catalog_path.parent / "verification-reports" / f"{tool_id}.json").resolve()
        if report_path != expected_path:
            return False
    except (OSError, ValueError):
        return False
    try:
        report_bytes = report_path.read_bytes()
        report = json.loads(report_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    report_sha256 = entry.get("verification_report_sha256")
    if not isinstance(report_sha256, str) or hashlib.sha256(report_bytes).hexdigest() != report_sha256:
        return False
    schema_version = report.get("schema_version") if isinstance(report, dict) else None
    shared_keys = {
        "schema_version", "tool_id", "tool_version", "verified_at", "review_notes", "check",
        "inspection", "concept_registration", "manifest_sha256", "tool_snapshot", "warning",
    }
    if schema_version == 3:
        required_keys = shared_keys | {"sandboxed_by"}
        provenance_valid = report.get("sandboxed_by") == "codex-workspace-sandbox"
    elif schema_version == 4:
        required_keys = shared_keys | {"observer", "execution_boundary"}
        provenance_valid = (
            report.get("observer") in REPORT_OBSERVERS
            and report.get("execution_boundary") in EXECUTION_BOUNDARIES
            and (report.get("check") is None or report.get("execution_boundary") != "not-applicable")
        )
    else:
        return False
    if (
        not isinstance(report, dict)
        or set(report) != required_keys
        or report.get("tool_id") != tool_id
        or not isinstance(report.get("tool_version"), str)
        or not isinstance(report.get("verified_at"), str)
        or not provenance_valid
        or not isinstance(report.get("review_notes"), str)
        or len(report["review_notes"].strip()) < 20
        or not isinstance(report.get("concept_registration"), dict)
        or not isinstance(report.get("warning"), str)
        or len(report["warning"].strip()) < 20
    ):
        return False
    inspection = report.get("inspection")
    if not isinstance(inspection, dict) or set(inspection) != {"required", "result", "notes"}:
        return False
    if inspection.get("required") is True:
        if (
            inspection.get("result") != "passed"
            or not isinstance(inspection.get("notes"), str)
            or len(inspection["notes"].strip()) < 20
        ):
            return False
    elif inspection != {"required": False, "result": "not-required", "notes": None}:
        return False
    check = report.get("check")
    if check is not None and (
        not isinstance(check, dict)
        or set(check) != {"command", "exit_code", "output_sha256", "output_tail"}
        or not isinstance(check.get("command"), str)
        or not isinstance(check.get("exit_code"), int)
        or not isinstance(check.get("output_sha256"), str)
        or len(check["output_sha256"]) != 64
        or not isinstance(check.get("output_tail"), str)
    ):
        return False
    snapshot = report.get("tool_snapshot")
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("algorithm") != SNAPSHOT_ALGORITHM
        or snapshot.get("sha256") != digest
    ):
        return False
    files = snapshot.get("files")
    if not isinstance(files, list):
        return False
    manifest_records = [item for item in files if isinstance(item, dict) and item.get("path") == "tool.json"]
    return len(manifest_records) == 1 and report.get("manifest_sha256") == manifest_records[0].get("sha256")


def _try_platform_lock(handle: Any) -> bool:
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (BlockingIOError, OSError):
        return False


def _release_platform_lock(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def catalog_lock(mastery_root: Path) -> Iterator[None]:
    """Serialize catalog updates with a crash-released OS lock."""
    mastery_root.mkdir(parents=True, exist_ok=True)
    lock = mastery_root / ".tool-catalog.lock"
    handle = lock.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
        os.fsync(handle.fileno())
    deadline = time.monotonic() + 15
    acquired = False
    try:
        while not acquired:
            acquired = _try_platform_lock(handle)
            if acquired:
                break
            if time.monotonic() >= deadline:
                raise SystemExit(f"Timed out waiting for tool catalog lock: {lock}")
            time.sleep(0.025)
        yield
    finally:
        if acquired:
            try:
                _release_platform_lock(handle)
            except OSError:
                pass
        handle.close()


def load_catalog(path: Path, schema_version: int) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": schema_version, "updated_at": timestamp(), "tools": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Invalid existing tool catalog: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("tools"), list):
        raise SystemExit("Invalid tool catalog root or tools array")
    return value


def update_catalog_entry(
    catalog_path: Path,
    tool_id: str,
    root: Path,
    updates: dict[str, Any],
    schema_version: int,
    remove_keys: tuple[str, ...] = (),
) -> None:
    with catalog_lock(catalog_path.parent):
        catalog = load_catalog(catalog_path, schema_version)
        matches = [item for item in catalog["tools"] if isinstance(item, dict) and item.get("id") == tool_id]
        if len(matches) != 1:
            raise SystemExit("tool catalog must contain exactly one matching tool ID")
        try:
            if Path(matches[0].get("path", "")).resolve() != root.resolve():
                raise SystemExit("tool catalog path does not match the tool directory")
        except OSError as error:
            raise SystemExit(f"tool catalog path is invalid: {error}") from error
        matches[0].update(updates)
        for key in remove_keys:
            matches[0].pop(key, None)
        catalog["schema_version"] = schema_version
        catalog["updated_at"] = timestamp()
        atomic_json(catalog_path, catalog)


def update_catalog_validation(
    catalog_path: Path,
    tool_id: str,
    root: Path,
    current_sha256: str,
    schema_version: int,
) -> str:
    """Derive trust status from the current bytes and the last verified digest."""
    with catalog_lock(catalog_path.parent):
        catalog = load_catalog(catalog_path, schema_version)
        matches = [item for item in catalog["tools"] if isinstance(item, dict) and item.get("id") == tool_id]
        if len(matches) != 1:
            raise SystemExit("tool catalog must contain exactly one matching tool ID")
        entry = matches[0]
        try:
            if Path(entry.get("path", "")).resolve() != root.resolve():
                raise SystemExit("tool catalog path does not match the tool directory")
        except OSError as error:
            raise SystemExit(f"tool catalog path is invalid: {error}") from error

        verified_sha256 = entry.get("verified_tool_sha256")
        report_matches = isinstance(verified_sha256, str) and _verification_report_matches(
            catalog_path, entry, tool_id, verified_sha256
        )
        if report_matches and verified_sha256 == current_sha256:
            status = "verified"
            entry.pop("stale_at", None)
            entry.pop("stale_reason", None)
        elif isinstance(verified_sha256, str) and verified_sha256:
            status = "stale"
            entry["stale_at"] = timestamp()
            entry["stale_reason"] = (
                "tool content differs from the content covered by the verification report"
                if verified_sha256 != current_sha256
                else "verification report is missing or inconsistent with the catalog digest"
            )
        else:
            status = "structurally-valid"
            entry.pop("stale_at", None)
            entry.pop("stale_reason", None)
        entry.update({
            "status": status,
            "validated_at": timestamp(),
            "current_tool_sha256": current_sha256,
        })
        entry.pop("rejected_at", None)
        entry.pop("validation_errors", None)
        catalog["schema_version"] = schema_version
        catalog["updated_at"] = timestamp()
        atomic_json(catalog_path, catalog)
        return status


def update_catalog_rejection(
    catalog_path: Path,
    root: Path,
    current_sha256: str | None,
    errors: list[str],
    schema_version: int,
) -> None:
    """Make a failed validation visible to catalog-only consumers."""
    if not catalog_path.exists():
        return
    with catalog_lock(catalog_path.parent):
        catalog = load_catalog(catalog_path, schema_version)
        matches = []
        for item in catalog["tools"]:
            if not isinstance(item, dict):
                continue
            try:
                if Path(item.get("path", "")).resolve() == root.resolve():
                    matches.append(item)
            except OSError:
                continue
        if len(matches) != 1:
            return
        entry = matches[0]
        entry.update({
            "status": "rejected",
            "validated_at": timestamp(),
            "rejected_at": timestamp(),
            "validation_errors": errors[:20],
        })
        if current_sha256:
            entry["current_tool_sha256"] = current_sha256
        catalog["schema_version"] = schema_version
        catalog["updated_at"] = timestamp()
        atomic_json(catalog_path, catalog)


def require_current_validation(
    catalog_path: Path,
    tool_id: str,
    root: Path,
    current_sha256: str,
    schema_version: int,
) -> None:
    """Refuse to finalize bytes that were not the subject of the latest valid static check."""
    with catalog_lock(catalog_path.parent):
        catalog = load_catalog(catalog_path, schema_version)
        matches = [item for item in catalog["tools"] if isinstance(item, dict) and item.get("id") == tool_id]
        if len(matches) != 1:
            raise SystemExit("tool catalog must contain exactly one matching tool ID")
        entry = matches[0]
        try:
            if Path(entry.get("path", "")).resolve() != root.resolve():
                raise SystemExit("tool catalog path does not match the tool directory")
        except OSError as error:
            raise SystemExit(f"tool catalog path is invalid: {error}") from error
        if entry.get("status") == "rejected":
            raise SystemExit("Cannot finalize a tool whose latest static validation was rejected")
        if entry.get("current_tool_sha256") != current_sha256:
            raise SystemExit("Tool content changed after static validation; validate and run the external check again")


def register_catalog_entry(catalog_path: Path, entry: dict[str, Any], schema_version: int) -> None:
    with catalog_lock(catalog_path.parent):
        catalog = load_catalog(catalog_path, schema_version)
        if any(isinstance(item, dict) and item.get("id") == entry.get("id") for item in catalog["tools"]):
            raise SystemExit(f"Tool ID already exists in catalog: {entry.get('id')}")
        catalog["tools"].append(entry)
        catalog["schema_version"] = schema_version
        catalog["updated_at"] = timestamp()
        atomic_json(catalog_path, catalog)
