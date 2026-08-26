#!/usr/bin/env python3
"""Privacy-minimal workspace discovery for Mastery Coach.

The registry is an index, not learner state.  It stores only a stable workspace
identifier, the workspace path, and an update timestamp.  Searchable learner
metadata is loaded from the selected workspace when discovery runs.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REGISTRY_SCHEMA_VERSION = 3
LEGACY_ENTRY_SCHEMA_VERSION = 2
REGISTRY_FIELDS = {"schema_version", "workspace_id", "path", "updated_at"}


def _iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_time(raw: str, label: str) -> datetime:
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"invalid {label}: {raw}") from error
    if value.tzinfo is None:
        raise ValueError(f"{label} must include a timezone offset")
    return value.astimezone(timezone.utc)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
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


def registry_base() -> Path:
    override = os.environ.get("MASTERY_HOME")
    if override:
        return Path(override).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser().resolve() / "mastery-learning"
    portable = (Path.home() / ".mastery-learning").resolve()
    legacy_codex = (Path.home() / ".codex" / "mastery-learning").resolve()
    if not portable.exists() and legacy_codex.exists():
        return legacy_codex
    return portable


def registry_dir() -> Path:
    return registry_base() / "workspaces.d"


def legacy_registry_path() -> Path:
    return registry_base() / "workspaces.json"


def workspace_key(workspace: Path) -> str:
    canonical = os.path.normcase(str(workspace.resolve()))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def preflight_registry() -> None:
    directory = registry_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / f".write-probe-{os.getpid()}-{uuid.uuid4().hex}"
        descriptor = os.open(str(probe), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(descriptor)
        probe.unlink()
    except OSError as error:
        raise SystemExit(
            f"The durable workspace registry is not writable at {directory}: {error}. "
            "Set MASTERY_HOME to a persistent writable directory or authorize that location before initializing."
        ) from error


def registry_value(workspace: Path, workspace_id: str, *, updated_at: str | None = None) -> dict[str, str | int]:
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "workspace_id": workspace_id,
        "path": str(workspace.resolve()),
        "updated_at": updated_at or _iso(),
    }


def register_workspace(workspace: Path, workspace_id: str) -> None:
    try:
        _atomic_json(
            registry_dir() / f"{workspace_key(workspace)}.json",
            registry_value(workspace, workspace_id),
        )
    except OSError as error:
        raise SystemExit(
            f"Learner state exists, but durable registry update failed at {registry_dir()}: {error}"
        ) from error


def unregister_workspace(workspace: Path) -> str | None:
    entry = registry_dir() / f"{workspace_key(workspace)}.json"
    try:
        entry.unlink(missing_ok=True)
        return None
    except OSError as error:
        return f"Could not remove stale registry entry {entry}: {error}"


def registry_entry_problem(value: Any) -> str | None:
    if not isinstance(value, dict):
        return "registry entry must be an object"
    schema = value.get("schema_version")
    required = ["workspace_id", "path", "updated_at"]
    if schema == LEGACY_ENTRY_SCHEMA_VERSION:
        required.append("goal")
    missing = [
        field
        for field in required
        if not isinstance(value.get(field), str) or not value[field].strip()
    ]
    if schema not in {LEGACY_ENTRY_SCHEMA_VERSION, REGISTRY_SCHEMA_VERSION} or missing:
        return f"invalid registry schema or fields: {missing}"
    try:
        _parse_time(value["updated_at"], "registry updated_at")
    except ValueError as error:
        return str(error)
    return None


def _sanitize_entry(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    """Reduce every valid entry to the complete privacy allowlist on observation."""
    sanitized = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "workspace_id": value["workspace_id"],
        "path": value["path"],
        "updated_at": value["updated_at"],
    }
    if value != sanitized:
        _atomic_json(path, sanitized)
    return sanitized


def _privacy_project_entry(path: Path, value: Any) -> Any:
    """Remove learner metadata before validity checks, including from corrupt entries."""
    if not isinstance(value, dict):
        return value
    projected = {key: item for key, item in value.items() if key in REGISTRY_FIELDS}
    if value.get("schema_version") == LEGACY_ENTRY_SCHEMA_VERSION:
        projected["schema_version"] = REGISTRY_SCHEMA_VERSION
    if projected != value:
        _atomic_json(path, projected)
    return projected


def inspect_registry_entry(path: Path) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """Read, privacy-minimize, and validate one registry entry in that order."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, {
            "code": "invalid-registry-entry",
            "entry": str(path),
            "message": f"unreadable registry entry: {error}",
        }
    try:
        value = _privacy_project_entry(path, value)
    except OSError as error:
        return None, {
            "code": "registry-privacy-migration-failed",
            "entry": str(path),
            "message": f"could not remove learner metadata before validation: {error}",
        }
    problem = registry_entry_problem(value)
    if problem:
        return None, {"code": "invalid-registry-entry", "entry": str(path), "message": problem}
    assert isinstance(value, dict)
    try:
        return _sanitize_entry(path, value), None
    except OSError as error:
        return None, {
            "code": "registry-privacy-migration-failed",
            "entry": str(path),
            "message": f"could not enforce the registry privacy allowlist: {error}",
        }


def registry_entries() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    if registry_dir().exists():
        for path in sorted(registry_dir().glob("*.json")):
            value, error = inspect_registry_entry(path)
            if error:
                errors.append(error)
            elif value is not None:
                entries.append(value)

    legacy = legacy_registry_path()
    if legacy.exists():
        try:
            value = json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append({
                "code": "invalid-legacy-registry",
                "entry": str(legacy),
                "message": f"unreadable legacy registry: {error}",
            })
        else:
            workspaces = value.get("workspaces") if isinstance(value, dict) else None
            if not isinstance(workspaces, list):
                errors.append({
                    "code": "invalid-legacy-registry",
                    "entry": str(legacy),
                    "message": "legacy registry must contain a workspaces array",
                })
            else:
                remaining: list[dict[str, str]] = []
                for index, item in enumerate(workspaces):
                    raw = item.get("path") if isinstance(item, dict) else None
                    if not isinstance(raw, str) or not raw.strip():
                        errors.append({
                            "code": "invalid-legacy-registry",
                            "entry": f"{legacy}#workspaces[{index}]",
                            "message": "legacy workspace entry is invalid",
                        })
                        remaining.append({"migration_error": "workspace path is missing"})
                        continue
                    workspace = Path(raw).expanduser().resolve()
                    profile_path = workspace / ".mastery" / "profile.json"
                    try:
                        profile = json.loads(profile_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as error:
                        errors.append({
                            "code": "invalid-legacy-registry",
                            "entry": f"{legacy}#workspaces[{index}]",
                            "message": f"cannot migrate workspace profile: {error}",
                        })
                        remaining.append({"path": raw})
                        continue
                    workspace_id = profile.get("workspace_id") if isinstance(profile, dict) else None
                    if not isinstance(workspace_id, str) or not workspace_id.strip():
                        errors.append({
                            "code": "invalid-legacy-registry",
                            "entry": f"{legacy}#workspaces[{index}]",
                            "message": "workspace profile has no stable workspace_id",
                        })
                        remaining.append({"path": raw})
                        continue
                    entry = registry_value(workspace, workspace_id)
                    try:
                        _atomic_json(registry_dir() / f"{workspace_key(workspace)}.json", entry)
                    except OSError as error:
                        errors.append({
                            "code": "legacy-registry-migration-failed",
                            "entry": f"{legacy}#workspaces[{index}]",
                            "message": f"could not write privacy-minimal registry entry: {error}",
                        })
                        remaining.append({"path": raw})
                        continue
                    entries.append(entry)
                try:
                    _atomic_json(
                        legacy,
                        {
                            "schema_version": 2,
                            "workspaces": remaining,
                            "migrated_to": "workspaces.d",
                        },
                    )
                except OSError as error:
                    errors.append({
                        "code": "registry-privacy-migration-failed",
                        "entry": str(legacy),
                        "message": f"could not remove legacy learner metadata: {error}",
                    })
    return entries, errors


def discover_workspaces() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    entries: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    seen: set[str] = set()
    current = Path.cwd().resolve()
    for candidate in [current, *current.parents]:
        profile_path = candidate / ".mastery" / "profile.json"
        if profile_path.exists():
            try:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                errors.append({"code": "invalid-current-workspace", "entry": str(profile_path), "message": str(error)})
            else:
                goal = profile.get("goal") if isinstance(profile, dict) else None
                if not isinstance(goal, str) or not goal.strip():
                    errors.append({
                        "code": "invalid-current-workspace",
                        "entry": str(profile_path),
                        "message": "profile root/goal is invalid",
                    })
                else:
                    entries.append({"path": str(candidate), "goal": goal, "source": "current-tree"})
                    seen.add(os.path.normcase(str(candidate)))
            break

    registered, registry_errors = registry_entries()
    errors.extend(registry_errors)
    for item in registered:
        raw = item.get("path")
        assert isinstance(raw, str)
        candidate = Path(raw).expanduser().resolve()
        key = os.path.normcase(str(candidate))
        if key in seen:
            continue
        profile_path = candidate / ".mastery" / "profile.json"
        if not profile_path.exists():
            warnings.append({"code": "stale-registry-entry", "entry": str(candidate), "message": "workspace profile is missing"})
            continue
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append({"code": "invalid-registered-workspace", "entry": str(profile_path), "message": str(error)})
            continue
        goal = profile.get("goal") if isinstance(profile, dict) else None
        workspace_id = profile.get("workspace_id") if isinstance(profile, dict) else None
        if not isinstance(goal, str) or not goal.strip() or workspace_id != item.get("workspace_id"):
            errors.append({
                "code": "invalid-registered-workspace",
                "entry": str(profile_path),
                "message": "profile goal/workspace_id is invalid or does not match the registry",
            })
            continue
        entries.append({"path": str(candidate), "goal": goal, "source": "registry"})
        seen.add(key)
    return entries, errors, warnings


def resolve_workspace(raw: str | None) -> Path:
    if raw:
        workspace = Path(raw).expanduser().resolve()
        if not (workspace / ".mastery" / "profile.json").exists():
            raise SystemExit(
                f"No initialized learner state at {workspace}. Run `mastery.py init`, `migrate`, or `locate`."
            )
        return workspace
    entries, errors, _ = discover_workspaces()
    if errors:
        details = "\n".join(f"- {item['entry']}: {item['message']}" for item in errors)
        raise SystemExit(f"Learner workspace discovery is unsafe because registry/profile data is invalid:\n{details}")
    if len(entries) == 1:
        return Path(entries[0]["path"])
    if not entries:
        raise SystemExit("No learner workspace found. Pass --workspace or initialize one with `mastery.py init`.")
    choices = "\n".join(f"- {item['path']} — {item['goal']}" for item in entries)
    raise SystemExit(f"Multiple learner workspaces found. Pass --workspace explicitly:\n{choices}")
