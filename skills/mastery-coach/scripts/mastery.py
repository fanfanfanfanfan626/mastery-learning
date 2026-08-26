#!/usr/bin/env python3
"""Transparent, local, event-sourced learner state for Mastery Coach."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import time
import uuid
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from mastery_registry import (  # noqa: E402
    discover_workspaces,
    inspect_registry_entry,
    preflight_registry,
    register_workspace,
    registry_base,
    registry_dir,
    registry_entries,
    resolve_workspace,
    unregister_workspace,
    workspace_key,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = 4
DIMENSIONS = {"recall", "conceptual", "application", "debugging", "transfer", "creation"}
KINDS = {"diagnostic", "recall", "explain", "exercise", "debug", "transfer", "project", "review"}
KIND_DIMENSIONS = {
    "diagnostic": ["conceptual"], "recall": ["recall"], "explain": ["conceptual"],
    "exercise": ["application"], "debug": ["debugging", "application"],
    "transfer": ["transfer", "conceptual"], "project": ["creation", "application", "transfer"],
    "review": ["recall"],
}
DEFAULT_REQUIRED = ["recall", "conceptual", "application"]
PASS_THRESHOLD = 0.75
MEANINGFUL_THRESHOLD = 0.5
INTERVALS = [1, 3, 7, 14, 30, 60]
MIN_DELAY = timedelta(hours=12)
LOCK_TIMEOUT_SECONDS = 15
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EVENT_ID_PATTERN = re.compile(r"^ev-[A-Za-z0-9._-]{8,}$")
SESSION_ID_PATTERN = re.compile(r"^session-[A-Za-z0-9._-]{8,}$")
PLAN_STATUSES = {"diagnostic", "active", "paused", "complete"}
CORE_FILES = {
    "profile.json", "plan.json", "concepts.json", "mastery.json", "reviews.json",
    "sources.json", "evidence.jsonl", "sessions.jsonl", "state-revision.json",
}
EVENT_FIELDS = {
    "schema_version", "id", "timestamp", "concept", "kind", "score", "difficulty",
    "hints", "assisted", "independent", "delayed", "delay_hours", "dimensions",
    "notes", "legacy", "support", "request_fingerprint",
}
SESSION_FIELDS = {
    "schema_version", "id", "closed_at", "demonstrated", "unresolved",
    "next_action", "next_review", "notes",
}
PRIVACY_CONTENT = "*\n!.gitignore\n"


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or now()).astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_time(raw: str, label: str = "timestamp") -> datetime:
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"invalid {label}: {raw}") from error
    if value.tzinfo is None:
        raise ValueError(f"{label} must include a timezone offset")
    return value.astimezone(timezone.utc)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def explicit_workspace(raw: str | None) -> Path:
    return Path(raw or ".").expanduser().resolve()


def state_dir(workspace: Path | str) -> Path:
    return Path(workspace).expanduser().resolve() / ".mastery"


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


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def revision_value(root: Path) -> int:
    path = root / "state-revision.json"
    if not path.exists():
        return 0
    value = load_json(path)
    if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("revision"), int) or value["revision"] < 0:
        raise SystemExit("state-revision.json is invalid")
    return value["revision"]


def recover_transaction(root: Path) -> None:
    journal_path = root / "transaction.json"
    if not journal_path.exists():
        return
    journal = load_json(journal_path)
    if not isinstance(journal, dict) or journal.get("journal_schema_version") != 1:
        raise SystemExit("transaction.json is invalid; restore from backup before continuing")
    base, target, files = journal.get("base_revision"), journal.get("target_revision"), journal.get("files")
    if not isinstance(base, int) or not isinstance(target, int) or target != base + 1 or not isinstance(files, dict):
        raise SystemExit("transaction.json has an invalid revision boundary")
    current = revision_value(root)
    if current not in {base, target}:
        raise SystemExit(f"transaction revision conflict: current={current}, base={base}, target={target}")
    for name, item in files.items():
        if not isinstance(name, str) or Path(name).name != name or name in {"transaction.json", "state-revision.json"}:
            raise SystemExit("transaction.json contains an unsafe file target")
        if not isinstance(item, dict) or not isinstance(item.get("content"), str) or not isinstance(item.get("sha256"), str):
            raise SystemExit(f"transaction.json has an invalid payload for {name}")
        digest = hashlib.sha256(item["content"].encode("utf-8")).hexdigest()
        if digest != item["sha256"]:
            raise SystemExit(f"transaction.json payload hash mismatch for {name}")
        atomic_text(root / name, item["content"])
    atomic_json(root / "state-revision.json", {
        "schema_version": 1,
        "revision": target,
        "updated_at": journal["created_at"],
        "transaction_id": journal["transaction_id"],
    })
    try:
        journal_path.unlink()
    except OSError:
        # The revision file is the commit point. A leftover journal is safely
        # replayed and cleaned on the next locked command.
        pass


def commit_files(root: Path, files: dict[str, str | dict[str, Any]]) -> int:
    """Commit a validated candidate with a replayable write-ahead journal."""
    root.mkdir(parents=True, exist_ok=True)
    base = revision_value(root)
    target = base + 1
    transaction_id = f"tx-{uuid.uuid4().hex}"
    payloads: dict[str, dict[str, str]] = {}
    for name, value in files.items():
        if Path(name).name != name or name in {"transaction.json", "state-revision.json"}:
            raise ValueError(f"unsafe transaction target: {name}")
        content = value if isinstance(value, str) else json_text(value)
        payloads[name] = {"content": content, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}
    created_at = iso()
    journal = {
        "journal_schema_version": 1,
        "transaction_id": transaction_id,
        "created_at": created_at,
        "base_revision": base,
        "target_revision": target,
        "files": payloads,
    }
    atomic_json(root / "transaction.json", journal)
    recover_transaction(root)
    return target


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise SystemExit(f"Missing state file: {path}. Run `mastery.py init` first.")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error


def split_values(raw: str | None, allowed: set[str], label: str) -> list[str]:
    if not raw:
        return []
    values = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = sorted(set(values) - allowed)
    if invalid:
        raise SystemExit(f"Invalid {label}: {', '.join(invalid)}")
    return list(dict.fromkeys(values))


def split_ids(raw: str | None, label: str) -> list[str]:
    if not raw:
        return []
    values = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = [item for item in values if not ID_PATTERN.fullmatch(item)]
    if invalid:
        raise SystemExit(f"Invalid {label}: {', '.join(invalid)}")
    return list(dict.fromkeys(values))


def path_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False


def pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def read_lock(lock: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(lock.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def try_platform_lock(handle: Any) -> bool:
    """Acquire one OS-managed byte lock; the operating system releases it on process death."""
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


def release_platform_lock(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def state_lock(workspace: Path) -> Iterator[None]:
    """Serialize state changes with a crash-released OS lock, without lock-file deletion races."""
    workspace.mkdir(parents=True, exist_ok=True)
    lock_directory = registry_base() / "locks"
    lock_directory.mkdir(parents=True, exist_ok=True)
    lock = lock_directory / f"{workspace_key(workspace)}.lock"
    handle = lock.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
        os.fsync(handle.fileno())
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    acquired = False
    try:
        while not acquired:
            acquired = try_platform_lock(handle)
            if acquired:
                break
            if time.monotonic() >= deadline:
                raise SystemExit(f"Timed out waiting for learner-state lock: {lock}")
            time.sleep(0.025)
        recover_transaction(state_dir(workspace))
        yield
    finally:
        if acquired:
            try:
                release_platform_lock(handle)
            except OSError:
                # The protected operation already committed. Never turn successful work into
                # an ambiguous failure because a platform unlock reports a cleanup race.
                pass
        handle.close()


def ensure_privacy_file(root: Path) -> str | None:
    target = root / ".gitignore"
    if target.exists():
        current = target.read_text(encoding="utf-8")
        if current == PRIVACY_CONTENT:
            return None
        backup = root / ".gitignore.user-backup"
        if not backup.exists():
            atomic_text(backup, current)
        atomic_text(target, PRIVACY_CONTENT)
        return str(backup)
    atomic_text(target, PRIVACY_CONTENT)
    return None


def profile_errors(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["profile.json: root must be an object"]
    errors: list[str] = []
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append("profile.json: unsupported schema_version; run migrate for v1/v2/v3 state")
    for field in ["workspace_id", "goal", "proof_of_completion", "created_at", "updated_at"]:
        if not isinstance(value.get(field), str) or not value[field].strip():
            errors.append(f"profile.json: {field} must be non-empty text")
    for field in ["created_at", "updated_at"]:
        try:
            parse_time(value.get(field, ""), f"profile {field}")
        except ValueError as error:
            errors.append(f"profile.json: {error}")
    if not is_number(value.get("hours_per_week")) or not 0 < value["hours_per_week"] <= 168:
        errors.append("profile.json: hours_per_week must be greater than 0 and at most 168")
    minutes = value.get("session_minutes")
    if not isinstance(minutes, int) or isinstance(minutes, bool) or not 5 <= minutes <= 480:
        errors.append("profile.json: session_minutes must be an integer from 5 to 480")
    deadline = value.get("deadline")
    if deadline is not None and (not isinstance(deadline, str) or not deadline.strip()):
        errors.append("profile.json: deadline must be non-empty text or null")
    elif isinstance(deadline, str):
        try:
            datetime.fromisoformat(deadline)
        except ValueError:
            errors.append("profile.json: deadline must be an ISO date or datetime")
    for field in ["constraints", "interests"]:
        items = value.get(field)
        if not isinstance(items, list) or any(not isinstance(item, str) or not item.strip() for item in items):
            errors.append(f"profile.json: {field} must be an array of non-empty strings")
    hypotheses = value.get("hypotheses")
    if not isinstance(hypotheses, list):
        errors.append("profile.json: hypotheses must be an array")
    else:
        for index, item in enumerate(hypotheses):
            if not isinstance(item, dict):
                errors.append(f"profile.json: hypotheses[{index}] must be an object")
                continue
            if not all(isinstance(item.get(field), str) and item[field].strip() for field in ["observation", "inference", "observed_at"]):
                errors.append(f"profile.json: hypotheses[{index}] needs observation, inference, and observed_at")
            else:
                try:
                    observed_at = parse_time(item["observed_at"], f"hypotheses[{index}].observed_at")
                    if observed_at > now() + timedelta(minutes=5):
                        errors.append(f"profile.json: hypotheses[{index}].observed_at is in the future")
                except ValueError as error:
                    errors.append(f"profile.json: {error}")
            if not is_number(item.get("confidence")) or not 0 <= item["confidence"] <= 1:
                errors.append(f"profile.json: hypotheses[{index}].confidence must be between 0 and 1")
    return errors


def plan_errors(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["plan.json: root must be an object"]
    errors: list[str] = []
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append("plan.json: unsupported schema_version")
    if value.get("status") not in PLAN_STATUSES:
        errors.append(f"plan.json: status must be one of {sorted(PLAN_STATUSES)}")
    for field in ["coverage_pack", "target_artifact"]:
        if value.get(field) is not None and (not isinstance(value.get(field), str) or not value[field].strip()):
            errors.append(f"plan.json: {field} must be non-empty text or null")
    scope = value.get("scope_selection")
    if not isinstance(scope, dict):
        errors.append("plan.json: scope_selection must be an object")
    else:
        if scope.get("status") not in {"unselected", "confirmed"}:
            errors.append("plan.json: scope_selection.status must be unselected or confirmed")
        for field in ["profiles", "additional_targets", "enrichment_targets"]:
            items = scope.get(field)
            if not isinstance(items, list) or any(not isinstance(item, str) or not ID_PATTERN.fullmatch(item) for item in items):
                errors.append(f"plan.json: scope_selection.{field} must contain lowercase hyphen-case IDs")
            elif len(items) != len(set(items)):
                errors.append(f"plan.json: scope_selection.{field} must not contain duplicates")
        if not isinstance(scope.get("reason"), str):
            errors.append("plan.json: scope_selection.reason must be text")
        if scope.get("confirmed_at") is not None:
            try:
                parse_time(scope["confirmed_at"], "scope confirmed_at")
            except (TypeError, ValueError) as error:
                errors.append(f"plan.json: {error}")
        if scope.get("status") == "confirmed":
            if not scope.get("profiles") and not scope.get("additional_targets"):
                errors.append("plan.json: confirmed scope needs at least one profile or additional target")
            if not isinstance(scope.get("reason"), str) or not scope["reason"].strip():
                errors.append("plan.json: confirmed scope needs a non-empty learner-confirmation reason")
            if scope.get("confirmed_at") is None:
                errors.append("plan.json: confirmed scope needs confirmed_at")
        elif scope.get("status") == "unselected":
            if scope.get("profiles") or scope.get("additional_targets"):
                errors.append("plan.json: unselected scope cannot contain required profiles or targets")
            if scope.get("confirmed_at") is not None:
                errors.append("plan.json: unselected scope cannot have confirmed_at")
    for field in ["active_path", "excluded_scope", "open_questions"]:
        items = value.get(field)
        if not isinstance(items, list):
            errors.append(f"plan.json: {field} must be an array")
        elif any(not isinstance(item, str) or not item.strip() for item in items):
            errors.append(f"plan.json: {field} must contain non-empty strings")
        elif len(items) != len(set(items)):
            errors.append(f"plan.json: {field} must not contain duplicates")
    try:
        parse_time(value.get("updated_at", ""), "plan updated_at")
    except ValueError as error:
        errors.append(f"plan.json: {error}")
    return errors


def concepts_errors(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["concepts.json: root must be an object"]
    errors: list[str] = []
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append("concepts.json: unsupported schema_version")
    concepts = value.get("concepts")
    if not isinstance(concepts, dict):
        return errors + ["concepts.json: concepts must be an object"]
    curriculum = value.get("curriculum")
    if curriculum is not None:
        if not isinstance(curriculum, dict):
            errors.append("concepts.json: curriculum must be an object or null")
        else:
            for field in ["id", "version", "title"]:
                if not isinstance(curriculum.get(field), str) or not curriculum[field].strip():
                    errors.append(f"concepts.json: curriculum.{field} must be non-empty text")
            if not isinstance(curriculum.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", curriculum["sha256"]):
                errors.append("concepts.json: curriculum.sha256 must be SHA-256")
            profiles = curriculum.get("target_profiles")
            outcomes = curriculum.get("target_outcomes")
            if not isinstance(profiles, dict) or not profiles:
                errors.append("concepts.json: curriculum.target_profiles must be a non-empty object")
            elif not isinstance(outcomes, dict) or set(outcomes) != set(profiles):
                errors.append("concepts.json: curriculum target profile/outcome IDs must match")
            else:
                for profile_id, endpoints in profiles.items():
                    if not ID_PATTERN.fullmatch(str(profile_id)) or not isinstance(endpoints, list) or not endpoints or len(endpoints) != len(set(endpoints)) or any(not isinstance(item, str) for item in endpoints):
                        errors.append(f"concepts.json: curriculum target profile {profile_id!r} is invalid")
                    elif any(item not in concepts for item in endpoints):
                        errors.append(f"concepts.json: curriculum target profile {profile_id!r} references unknown concepts")
    for concept_id, item in concepts.items():
        if not isinstance(concept_id, str) or not ID_PATTERN.fullmatch(concept_id):
            errors.append(f"concepts.json: invalid concept ID {concept_id!r}")
            continue
        if not isinstance(item, dict):
            errors.append(f"concepts.json: {concept_id} must be an object")
            continue
        if item.get("id") != concept_id:
            errors.append(f"concepts.json: {concept_id}.id must match its key")
        for field in ["title", "outcome"]:
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"concepts.json: {concept_id}.{field} must be non-empty text")
        required = item.get("required_dimensions")
        if not isinstance(required, list) or not required or len(required) != len(set(required)) or set(required) - DIMENSIONS:
            errors.append(f"concepts.json: {concept_id}.required_dimensions is invalid")
        prerequisites = item.get("prerequisites")
        if not isinstance(prerequisites, list) or len(prerequisites) != len(set(prerequisites)) or any(not isinstance(entry, str) for entry in prerequisites):
            errors.append(f"concepts.json: {concept_id}.prerequisites must be a unique string array")
        elif any(entry not in concepts for entry in prerequisites):
            errors.append(f"concepts.json: {concept_id} has unknown prerequisites")
        if not isinstance(item.get("optional"), bool):
            errors.append(f"concepts.json: {concept_id}.optional must be boolean")
        if "module" in item and (not isinstance(item.get("module"), str) or not item["module"].strip()):
            errors.append(f"concepts.json: {concept_id}.module must be non-empty text")
        if "sources" in item and (not isinstance(item.get("sources"), list) or any(not isinstance(source, str) or not source for source in item["sources"])):
            errors.append(f"concepts.json: {concept_id}.sources must contain source IDs")
    if not errors:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(concept_id: str, path: list[str]) -> None:
            if concept_id in visiting:
                start = path.index(concept_id)
                errors.append("concepts.json: prerequisite cycle: " + " -> ".join(path[start:] + [concept_id]))
                return
            if concept_id in visited:
                return
            visiting.add(concept_id)
            for prerequisite in concepts[concept_id]["prerequisites"]:
                visit(prerequisite, [*path, concept_id])
            visiting.remove(concept_id)
            visited.add(concept_id)

        for concept_id in concepts:
            visit(concept_id, [])
    return errors


def cross_document_errors(plan: Any, concepts: Any) -> list[str]:
    if not isinstance(plan, dict) or not isinstance(concepts, dict) or not isinstance(concepts.get("concepts"), dict):
        return []
    errors: list[str] = []
    active = plan.get("active_path")
    if isinstance(active, list) and all(isinstance(item, str) for item in active):
        unknown = sorted(set(active) - set(concepts["concepts"]))
        if unknown:
            errors.append(f"plan.json: active_path references undefined concepts: {unknown}")
    scope = plan.get("scope_selection")
    curriculum = concepts.get("curriculum")
    profiles = curriculum.get("target_profiles", {}) if isinstance(curriculum, dict) else {}
    if isinstance(scope, dict):
        selected_profiles = scope.get("profiles", [])
        unknown_profiles = sorted(set(selected_profiles) - set(profiles)) if isinstance(selected_profiles, list) else []
        if unknown_profiles:
            errors.append(f"plan.json: scope_selection references unknown profiles: {unknown_profiles}")
        target_ids = set(scope.get("additional_targets", [])) | set(scope.get("enrichment_targets", []))
        unknown_targets = sorted(target_ids - set(concepts["concepts"]))
        if unknown_targets:
            errors.append(f"plan.json: scope_selection references undefined concepts: {unknown_targets}")
        if not unknown_profiles and not unknown_targets and scope.get("status") == "confirmed":
            try:
                required, enrichment = scope_sets(plan, concepts)
            except ValueError as error:
                errors.append(f"plan.json: {error}")
            else:
                outside = sorted(set(active or []) - required - enrichment)
                if outside:
                    errors.append(f"plan.json: active_path is outside confirmed scope: {outside}")
    return errors


def sources_errors(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["sources.json: root must be an object"]
    errors: list[str] = []
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append("sources.json: unsupported schema_version")
    sources = value.get("sources")
    if not isinstance(sources, list):
        return errors + ["sources.json: sources must be an array"]
    seen: set[str] = set()
    for index, item in enumerate(sources):
        if not isinstance(item, dict):
            errors.append(f"sources.json: sources[{index}] must be an object")
            continue
        source_id = item.get("id")
        if not isinstance(source_id, str) or not ID_PATTERN.fullmatch(source_id):
            errors.append(f"sources.json: sources[{index}].id is invalid")
        elif source_id in seen:
            errors.append(f"sources.json: duplicate source ID {source_id}")
        seen.add(source_id)
        for field in ["title", "organization", "type", "authority", "version_or_date", "license_reuse", "known_gaps"]:
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"sources.json: {source_id or index}.{field} must be non-empty text")
        parsed = urlparse(item.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"sources.json: {source_id or index}.url must be canonical HTTPS")
        concepts = item.get("concepts")
        if not isinstance(concepts, list) or not concepts or any(not isinstance(entry, str) or not entry for entry in concepts):
            errors.append(f"sources.json: {source_id or index}.concepts must be a non-empty string array")
        try:
            checked = date.fromisoformat(item.get("checked_at", ""))
            if checked > date.today():
                errors.append(f"sources.json: {source_id or index}.checked_at cannot be in the future")
        except (TypeError, ValueError):
            errors.append(f"sources.json: {source_id or index}.checked_at must be YYYY-MM-DD")
    return errors


def source_cross_document_errors(concepts: Any, sources: Any) -> list[str]:
    if (
        not isinstance(concepts, dict)
        or not isinstance(concepts.get("concepts"), dict)
        or not isinstance(sources, dict)
        or not isinstance(sources.get("sources"), list)
    ):
        return []
    errors: list[str] = []
    known_concepts = set(concepts["concepts"])
    known_sources = {source.get("id") for source in sources["sources"] if isinstance(source, dict)}
    for source in sources["sources"]:
        if isinstance(source, dict) and isinstance(source.get("concepts"), list):
            unknown = sorted(set(source["concepts"]) - known_concepts)
            if unknown:
                errors.append(f"sources.json: {source.get('id', '?')} references undefined concepts: {unknown}")
    for concept_id, concept in concepts["concepts"].items():
        if isinstance(concept, dict) and isinstance(concept.get("sources"), list):
            unknown = sorted(set(concept["sources"]) - known_sources)
            if unknown:
                errors.append(f"concepts.json: {concept_id} references undefined sources: {unknown}")
    return errors


def document_errors(name: str, value: Any) -> list[str]:
    return {"profile.json": profile_errors, "plan.json": plan_errors, "concepts.json": concepts_errors, "sources.json": sources_errors}[name](value)


def event_errors(event: Any, line_number: int | None = None) -> list[str]:
    prefix = f"evidence line {line_number}: " if line_number else "event: "
    if not isinstance(event, dict):
        return [prefix + "must be an object"]
    errors: list[str] = []
    missing, unknown = EVENT_FIELDS - set(event), set(event) - EVENT_FIELDS
    if missing:
        errors.append(prefix + f"missing fields {sorted(missing)}")
    if unknown:
        errors.append(prefix + f"unknown fields {sorted(unknown)}")
    if event.get("schema_version") != SCHEMA_VERSION:
        errors.append(prefix + "unsupported schema_version; run migrate for legacy evidence")
    if not isinstance(event.get("id"), str) or not EVENT_ID_PATTERN.fullmatch(event.get("id", "")):
        errors.append(prefix + "invalid id")
    try:
        parse_time(event.get("timestamp", ""))
    except (TypeError, ValueError) as error:
        errors.append(prefix + str(error))
    if not isinstance(event.get("concept"), str) or not ID_PATTERN.fullmatch(event.get("concept", "")):
        errors.append(prefix + "concept must be lowercase hyphen-case")
    kind = event.get("kind")
    if kind not in KINDS:
        errors.append(prefix + "invalid kind")
    if not is_number(event.get("score")) or not 0 <= event["score"] <= 1:
        errors.append(prefix + "invalid score")
    difficulty = event.get("difficulty")
    if not isinstance(difficulty, int) or isinstance(difficulty, bool) or not 1 <= difficulty <= 5:
        errors.append(prefix + "difficulty must be an integer from 1 to 5")
    hints = event.get("hints")
    if not isinstance(hints, int) or isinstance(hints, bool) or hints < 0:
        errors.append(prefix + "hints must be a non-negative integer")
    for field in ["assisted", "independent", "delayed", "legacy"]:
        if not isinstance(event.get(field), bool):
            errors.append(prefix + f"{field} must be boolean")
    if isinstance(hints, int) and isinstance(event.get("assisted"), bool) and isinstance(event.get("independent"), bool):
        if event["independent"] is not (hints == 0 and not event["assisted"]):
            errors.append(prefix + "independent conflicts with hints/assisted")
    support = event.get("support")
    if support not in {"independent", "assisted", "unknown"}:
        errors.append(prefix + "support must be independent, assisted, or unknown")
    elif support == "independent" and event.get("independent") is not True:
        errors.append(prefix + "support independent conflicts with independent flag")
    elif support == "assisted" and event.get("independent") is not False:
        errors.append(prefix + "support assisted conflicts with independent flag")
    elif support == "unknown" and event.get("legacy") is not True:
        errors.append(prefix + "support unknown is reserved for legacy evidence")
    fingerprint = event.get("request_fingerprint")
    if event.get("legacy"):
        if fingerprint is not None and (not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
            errors.append(prefix + "legacy request_fingerprint must be null or SHA-256")
    elif not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        errors.append(prefix + "request_fingerprint must be SHA-256 for current evidence")
    dimensions = event.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions or len(dimensions) != len(set(dimensions)) or set(dimensions) - DIMENSIONS:
        errors.append(prefix + "invalid dimensions")
    elif kind in KINDS and not event.get("legacy") and not set(KIND_DIMENSIONS[kind]).issubset(dimensions):
        errors.append(prefix + f"dimensions must include semantic minimum {KIND_DIMENSIONS[kind]} for kind {kind}")
    if event.get("delayed") is True:
        if kind not in {"recall", "review"} or not isinstance(dimensions, list) or "recall" not in dimensions:
            errors.append(prefix + "delayed evidence must be recall/review evidence with the recall dimension")
        if not is_number(event.get("delay_hours")) or event["delay_hours"] < 12:
            errors.append(prefix + "delay_hours is missing or below the minimum")
    elif event.get("delay_hours") is not None:
        errors.append(prefix + "delay_hours must be null when delayed is false")
    if not isinstance(event.get("notes"), str):
        errors.append(prefix + "notes must be text")
    return errors


def validate_event_sequence(indexed_events: list[tuple[int, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    identifiers: set[str] = set()
    last_time: datetime | None = None
    previous_by_concept: dict[str, datetime] = {}
    for line_number, event in indexed_events:
        current_errors = event_errors(event, line_number)
        errors.extend(current_errors)
        if current_errors:
            continue
        if event["id"] in identifiers:
            errors.append(f"evidence line {line_number}: duplicate event id {event['id']}")
        identifiers.add(event["id"])
        timestamp = parse_time(event["timestamp"])
        if timestamp > now() + timedelta(minutes=5):
            errors.append(f"evidence line {line_number}: timestamp is in the future")
        if last_time and timestamp < last_time:
            errors.append(f"evidence line {line_number}: events are not chronological")
        last_time = timestamp
        previous = previous_by_concept.get(event["concept"])
        if event["delayed"] and (previous is None or timestamp - previous < MIN_DELAY):
            errors.append(f"evidence line {line_number}: delayed evidence is less than 12 hours after prior evidence")
        if event["delayed"] and previous is not None:
            actual = round((timestamp - previous).total_seconds() / 3600, 2)
            if abs(float(event["delay_hours"]) - actual) > 0.02:
                errors.append(f"evidence line {line_number}: delay_hours does not match timestamps")
        previous_by_concept[event["concept"]] = timestamp
        events.append(event)
    return events, errors


def read_events(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = root / "evidence.jsonl"
    if not path.exists():
        return [], ["missing evidence.jsonl"]
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return [], [f"cannot read evidence.jsonl: {error}"]
    parsed: list[tuple[int, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            parsed.append((line_number, json.loads(line)))
        except json.JSONDecodeError as error:
            errors.append(f"evidence line {line_number}: {error}")
    events, sequence_errors = validate_event_sequence(parsed)
    return events, [*errors, *sequence_errors]


def session_errors(session: Any, line_number: int) -> list[str]:
    prefix = f"sessions line {line_number}: "
    if not isinstance(session, dict):
        return [prefix + "must be an object"]
    errors: list[str] = []
    missing, unknown = SESSION_FIELDS - set(session), set(session) - SESSION_FIELDS
    if missing:
        errors.append(prefix + f"missing fields {sorted(missing)}")
    if unknown:
        errors.append(prefix + f"unknown fields {sorted(unknown)}")
    if session.get("schema_version") != 1:
        errors.append(prefix + "unsupported schema_version")
    if not isinstance(session.get("id"), str) or not SESSION_ID_PATTERN.fullmatch(session.get("id", "")):
        errors.append(prefix + "invalid id")
    try:
        parse_time(session.get("closed_at", ""), "closed_at")
    except (TypeError, ValueError) as error:
        errors.append(prefix + str(error))
    for field in ["demonstrated", "unresolved", "next_action"]:
        if not isinstance(session.get(field), str) or not session[field].strip():
            errors.append(prefix + f"{field} must be non-empty text")
    if session.get("next_review") is not None:
        try:
            parse_time(session["next_review"], "next_review")
        except (TypeError, ValueError) as error:
            errors.append(prefix + str(error))
    if not isinstance(session.get("notes"), str):
        errors.append(prefix + "notes must be text")
    return errors


def validate_session_sequence(indexed_sessions: list[tuple[int, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    sessions: list[dict[str, Any]] = []
    errors: list[str] = []
    identifiers: set[str] = set()
    last_closed: datetime | None = None
    for line_number, session in indexed_sessions:
        current = session_errors(session, line_number)
        errors.extend(current)
        if current:
            continue
        if session["id"] in identifiers:
            errors.append(f"sessions line {line_number}: duplicate session id {session['id']}")
        identifiers.add(session["id"])
        closed = parse_time(session["closed_at"], "closed_at")
        if closed > now() + timedelta(minutes=5):
            errors.append(f"sessions line {line_number}: closed_at is in the future")
        if last_closed and closed < last_closed:
            errors.append(f"sessions line {line_number}: sessions are not chronological")
        last_closed = closed
        sessions.append(session)
    return sessions, errors


def read_sessions(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = root / "sessions.jsonl"
    if not path.exists():
        return [], ["missing sessions.jsonl"]
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return [], [f"cannot read sessions.jsonl: {error}"]
    parsed: list[tuple[int, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            parsed.append((line_number, json.loads(line)))
        except json.JSONDecodeError as error:
            errors.append(f"sessions line {line_number}: {error}")
    sessions, validation_errors = validate_session_sequence(parsed)
    return sessions, errors + validation_errors


def classify(concept: dict[str, Any]) -> str:
    if concept.get("fragile_since"):
        return "fragile"
    if concept["evidence_count"] == 0:
        return "unassessed"
    required, scores = concept["required_dimensions"], concept["dimensions"]
    tested = [scores.get(item) for item in required]
    if any(value is None for value in tested) or min(tested) < 0.5:
        return "emerging"
    independent = concept["independent_passing_by_dimension"]
    if min(tested) >= PASS_THRESHOLD and all(independent.get(item, 0) >= 1 for item in required):
        durable = concept["delayed_count"] >= 1 and concept["transfer_count"] >= 1
        return "mastered" if concept["meaningful_evidence_count"] >= 3 and durable else "provisional"
    return "developing"


def apply_review(reviews: dict[str, Any], event: dict[str, Any], timestamp: datetime) -> None:
    concept_id, score = event["concept"], float(event["score"])
    meaningful = score >= MEANINGFUL_THRESHOLD and event["kind"] != "diagnostic"
    current = reviews["concepts"].get(concept_id)
    if current is None:
        if not meaningful:
            return
        current = {
            "interval_step": 0, "interval_days": 1, "last_score": None,
            "last_reviewed_at": None, "last_learning_at": event["timestamp"],
            "due_at": iso(timestamp + timedelta(days=1)),
        }
        reviews["concepts"][concept_id] = current
    due_at = parse_time(current["due_at"], "review due_at")
    if event["kind"] not in {"recall", "review"}:
        if meaningful:
            current["last_learning_at"] = event["timestamp"]
        return
    independent = event.get("support") == "independent" and bool(event["independent"]) and not bool(event.get("legacy"))
    current.update({"last_score": round(score, 4), "last_reviewed_at": event["timestamp"]})
    if not independent or score < PASS_THRESHOLD:
        retry_due = min(due_at, timestamp + timedelta(days=1))
        current.update({"interval_step": 0, "interval_days": 1, "due_at": iso(retry_due)})
        return
    if timestamp < due_at:
        return
    step = int(current.get("interval_step", 0))
    step = min(step + 1, len(INTERVALS) - 1) if score >= 0.8 else max(0, step - 1)
    days = INTERVALS[step]
    current.update({"interval_step": step, "interval_days": days, "due_at": iso(timestamp + timedelta(days=days))})


def derive(events: list[dict[str, Any]], concepts_doc: dict[str, Any], base_time: str) -> tuple[dict[str, Any], dict[str, Any]]:
    updated_at = events[-1]["timestamp"] if events else base_time
    mastery: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "updated_at": updated_at, "concepts": {}}
    reviews: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "updated_at": updated_at, "concepts": {}}
    definitions = concepts_doc["concepts"]
    for event in events:
        timestamp = parse_time(event["timestamp"])
        definition = definitions[event["concept"]]
        concept = mastery["concepts"].setdefault(event["concept"], {
            "title": definition["title"], "required_dimensions": definition["required_dimensions"],
            "dimensions": {}, "evidence_count": 0, "meaningful_evidence_count": 0,
            "independent_count": 0, "independent_passing_by_dimension": {},
            "delayed_count": 0, "transfer_count": 0, "ever_mastered": False,
            "mastered_at": None, "fragile_since": None, "recovered_at": None, "status": "unassessed",
        })
        score = float(event["score"])
        independent = bool(event["independent"])
        credible_independent = event.get("support") == "independent" and independent and not bool(event.get("legacy"))
        alpha = (0.35 if credible_independent else 0.2) * (0.85 + int(event["difficulty"]) * 0.05)
        for dimension in event["dimensions"]:
            previous = concept["dimensions"].get(dimension)
            updated = score if previous is None else previous + alpha * (score - previous)
            concept["dimensions"][dimension] = round(max(0.0, min(1.0, updated)), 4)
            if credible_independent and score >= PASS_THRESHOLD:
                counts = concept["independent_passing_by_dimension"]
                counts[dimension] = counts.get(dimension, 0) + 1
        qualifying_delayed = event["delayed"] and event["kind"] in {"recall", "review"} and "recall" in event["dimensions"] and credible_independent and score >= PASS_THRESHOLD
        qualifying_transfer = event["kind"] in {"transfer", "project"} and "transfer" in event["dimensions"] and credible_independent and score >= PASS_THRESHOLD
        concept["evidence_count"] += 1
        concept["meaningful_evidence_count"] += int(score >= MEANINGFUL_THRESHOLD)
        concept["independent_count"] += int(credible_independent)
        concept["delayed_count"] += int(qualifying_delayed)
        concept["transfer_count"] += int(qualifying_transfer)
        concept["last_score"], concept["last_evidence_at"] = round(score, 4), event["timestamp"]
        if concept["ever_mastered"] and event["kind"] in {"recall", "review"} and (
            score < PASS_THRESHOLD or not credible_independent
        ):
            concept["fragile_since"] = event["timestamp"]
        if concept.get("fragile_since") and qualifying_delayed and timestamp > parse_time(concept["fragile_since"]):
            concept["recovered_at"], concept["fragile_since"] = event["timestamp"], None
        status = classify(concept)
        if status == "mastered":
            concept["ever_mastered"] = True
            concept["mastered_at"] = concept["mastered_at"] or event["timestamp"]
        concept["status"] = status
        apply_review(reviews, event, timestamp)
    return mastery, reviews


def load_core_documents(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    documents = {name: load_json(root / name) for name in ["profile.json", "plan.json", "concepts.json", "sources.json"]}
    errors = [issue for name, value in documents.items() for issue in document_errors(name, value)]
    errors += cross_document_errors(documents["plan.json"], documents["concepts.json"])
    errors += source_cross_document_errors(documents["concepts.json"], documents["sources.json"])
    if errors:
        raise SystemExit("State metadata is invalid; run validate before continuing:\n" + "\n".join(errors))
    return documents["profile.json"], documents["plan.json"], documents["concepts.json"], documents["sources.json"]


def write_derived(root: Path, events: list[dict[str, Any]], profile: dict[str, Any], concepts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    mastery, reviews = derive(events, concepts, profile["created_at"])
    commit_files(root, {"mastery.json": mastery, "reviews.json": reviews})
    return mastery, reviews


def audit_curriculum_file(path: Path) -> dict[str, Any]:
    audit_path = Path(__file__).resolve().with_name("curriculum_audit.py")
    spec = importlib.util.spec_from_file_location("mastery_learning_curriculum_audit", audit_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load curriculum auditor: {audit_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.audit(path)


def concepts_from_curriculum(raw: str | None) -> tuple[dict[str, Any], str | None, dict[str, Any]]:
    if not raw:
        return (
            {"schema_version": SCHEMA_VERSION, "updated_at": iso(), "curriculum": None, "concepts": {}},
            None,
            {"schema_version": SCHEMA_VERSION, "updated_at": iso(), "sources": []},
        )
    path = Path(__file__).resolve().parent.parent / "assets" / "curricula" / "ml-ai-llm.json" if raw == "ml-ai-llm" else Path(raw).expanduser().resolve()
    audit = audit_curriculum_file(path)
    if not audit["ok"]:
        raise SystemExit("Curriculum audit failed before initialization:\n" + "\n".join(audit["errors"]))
    data = load_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("concepts"), list) or not data.get("id"):
        raise SystemExit(f"Invalid curriculum pack: {path}")
    concepts: dict[str, Any] = {}
    for item in data["concepts"]:
        if not isinstance(item, dict) or not ID_PATTERN.fullmatch(str(item.get("id", ""))):
            raise SystemExit(f"Invalid concept in curriculum pack: {item}")
        concept_id = item["id"]
        concepts[concept_id] = {
            "id": concept_id, "title": str(item.get("title") or concept_id.replace("-", " ").title()),
            "outcome": str(item.get("outcome") or "Demonstrate the declared curriculum capability."),
            "prerequisites": item.get("prerequisites", []), "required_dimensions": item.get("required_dimensions", DEFAULT_REQUIRED),
            "optional": bool(item.get("optional", False)), "source_pack": str(data["id"]),
            "module": str(item.get("module", "unassigned")), "sources": list(item.get("sources", [])),
        }
    raw_bytes = path.read_bytes()
    document = {
        "schema_version": SCHEMA_VERSION, "updated_at": iso(),
        "curriculum": {
            "id": data["id"], "version": str(data.get("version", "unknown")),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(), "title": str(data.get("title", data["id"])),
            "target_profiles": data.get("target_profiles", {}), "target_outcomes": data.get("target_outcomes", {}),
            "declared_scope": data.get("scope", {}),
        },
        "concepts": concepts,
    }
    issues = concepts_errors(document)
    if issues:
        raise SystemExit("Curriculum cannot initialize concept definitions:\n" + "\n".join(issues))
    sources = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": document["updated_at"],
        "sources": data.get("sources", []),
    }
    source_issues = sources_errors(sources)
    if source_issues:
        raise SystemExit("Curriculum cannot initialize source ledger:\n" + "\n".join(source_issues))
    return document, str(data["id"]), sources


def prerequisite_closure(concepts: dict[str, Any], seeds: set[str]) -> set[str]:
    closure: set[str] = set()

    def visit(concept_id: str) -> None:
        if concept_id in closure:
            return
        if concept_id not in concepts:
            raise ValueError(f"unknown scope concept: {concept_id}")
        closure.add(concept_id)
        for prerequisite in concepts[concept_id]["prerequisites"]:
            visit(prerequisite)

    for seed in sorted(seeds):
        visit(seed)
    return closure


def topological_scope(concepts: dict[str, Any], selected: set[str]) -> list[str]:
    ordered: list[str] = []
    visited: set[str] = set()

    def visit(concept_id: str) -> None:
        if concept_id in visited:
            return
        visited.add(concept_id)
        for prerequisite in concepts[concept_id]["prerequisites"]:
            if prerequisite in selected:
                visit(prerequisite)
        ordered.append(concept_id)

    for concept_id in sorted(selected):
        visit(concept_id)
    return ordered


def scope_sets(plan: dict[str, Any], concepts_doc: dict[str, Any]) -> tuple[set[str], set[str]]:
    selection = plan.get("scope_selection", {})
    if not isinstance(selection, dict) or selection.get("status") != "confirmed":
        return set(), set()
    curriculum = concepts_doc.get("curriculum")
    profile_map = curriculum.get("target_profiles", {}) if isinstance(curriculum, dict) else {}
    seeds: set[str] = set(selection.get("additional_targets", []))
    for profile_id in selection.get("profiles", []):
        seeds.update(profile_map.get(profile_id, []))
    required = prerequisite_closure(concepts_doc["concepts"], seeds)
    enrichment_all = prerequisite_closure(concepts_doc["concepts"], set(selection.get("enrichment_targets", [])))
    return required, enrichment_all - required


def scope_selection(profiles: list[str], additional: list[str], enrichment: list[str], reason: str) -> dict[str, Any]:
    confirmed = bool(profiles or additional)
    if confirmed and not reason.strip():
        raise SystemExit("Confirmed scope requires a non-empty reason describing the learner's explicit choice")
    return {
        "status": "confirmed" if confirmed else "unselected",
        "profiles": profiles,
        "additional_targets": additional,
        "enrichment_targets": enrichment,
        "reason": reason.strip(),
        "confirmed_at": iso() if confirmed else None,
    }


def concept_definition(concept_id: str, title: str | None, outcome: str | None, required: list[str], prerequisites: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": concept_id, "title": title.strip() if title and title.strip() else concept_id.replace("-", " ").title(),
        "outcome": outcome.strip() if outcome and outcome.strip() else f"Demonstrate independent use of {concept_id.replace('-', ' ')}.",
        "prerequisites": prerequisites or [], "required_dimensions": required,
        "optional": False, "source_pack": "custom",
    }


def cmd_init(args: argparse.Namespace) -> None:
    workspace, root = explicit_workspace(args.workspace), state_dir(args.workspace)
    if not args.goal.strip():
        raise SystemExit("--goal must be non-empty")
    if args.hours_per_week is not None and not 0 < args.hours_per_week <= 168:
        raise SystemExit("--hours-per-week must be greater than 0 and at most 168")
    if args.session_minutes is not None and not 5 <= args.session_minutes <= 480:
        raise SystemExit("--session-minutes must be between 5 and 480")
    if args.deadline:
        try:
            datetime.fromisoformat(args.deadline)
        except ValueError as error:
            raise SystemExit("--deadline must be an ISO date or datetime") from error
    preflight_registry()
    workspace.mkdir(parents=True, exist_ok=True)
    with state_lock(workspace):
        root.mkdir(parents=True, exist_ok=True)
        existing_core = any((root / name).exists() for name in CORE_FILES)
        if existing_core:
            existing_profile = load_json(root / "profile.json", {}) if (root / "profile.json").exists() else {}
            if not isinstance(existing_profile, dict) or existing_profile.get("schema_version") != SCHEMA_VERSION:
                raise SystemExit(f"Legacy learner state detected at {root}; run `mastery.py migrate --workspace {workspace}` before init/repair.")
            if not args.force:
                raise SystemExit(f"State already exists at {root}. Use status, rebuild, or --force for a non-destructive repair.")
            profile, plan, concepts, sources = load_core_documents(root)
            events, issues = read_events(root)
            if issues:
                raise SystemExit("Existing evidence is invalid; repair it before initialization:\n" + "\n".join(issues))
            sessions, session_issues = read_sessions(root)
            if session_issues:
                raise SystemExit("Existing sessions are invalid; repair them before initialization:\n" + "\n".join(session_issues))
            if events and profile["goal"] != args.goal.strip():
                raise SystemExit("Refusing to attach preserved evidence to a different goal.")
            profile.update({"updated_at": iso(), "goal": args.goal.strip()})
            if args.hours_per_week is not None:
                profile["hours_per_week"] = args.hours_per_week
            if args.session_minutes is not None:
                profile["session_minutes"] = args.session_minutes
            if args.deadline is not None:
                profile["deadline"] = args.deadline
            if args.proof:
                profile["proof_of_completion"] = args.proof
            if args.curriculum:
                new_concepts, pack, new_sources = concepts_from_curriculum(args.curriculum)
                if events and new_concepts["concepts"] != concepts["concepts"]:
                    raise SystemExit("Cannot replace concept definitions after evidence exists; create a new workspace or version concepts explicitly.")
                concepts, sources, plan["coverage_pack"] = new_concepts, new_sources, pack
            if args.target_profile or args.additional_targets or args.enrichment_targets:
                plan["scope_selection"] = scope_selection(
                    list(dict.fromkeys(args.target_profile or [])),
                    split_ids(args.additional_targets, "additional targets"),
                    split_ids(args.enrichment_targets, "enrichment targets"),
                    args.scope_reason or "",
                )
            plan["updated_at"], sources["updated_at"] = iso(), iso()
        else:
            concepts, pack, sources = concepts_from_curriculum(args.curriculum)
            created = iso()
            profile = {
                "schema_version": SCHEMA_VERSION, "workspace_id": f"ws-{uuid.uuid4().hex}", "created_at": created,
                "updated_at": created, "goal": args.goal.strip(), "proof_of_completion": args.proof or "To be agreed after guided learning observations",
                "hours_per_week": args.hours_per_week if args.hours_per_week is not None else 5,
                "session_minutes": args.session_minutes if args.session_minutes is not None else 45,
                "deadline": args.deadline,
                "constraints": [], "interests": [], "hypotheses": [],
            }
            selection = scope_selection(
                list(dict.fromkeys(args.target_profile or [])),
                split_ids(args.additional_targets, "additional targets"),
                split_ids(args.enrichment_targets, "enrichment targets"),
                args.scope_reason or "",
            )
            plan = {
                "schema_version": SCHEMA_VERSION, "updated_at": created, "status": "diagnostic", "coverage_pack": pack,
                "target_artifact": args.proof, "active_path": [], "excluded_scope": [],
                "open_questions": ["Starting level will be refined through guided learning."], "scope_selection": selection,
            }
            events, sessions = [], []
        issues = (
            profile_errors(profile) + plan_errors(plan) + concepts_errors(concepts) + sources_errors(sources)
            + cross_document_errors(plan, concepts) + source_cross_document_errors(concepts, sources)
        )
        if issues:
            raise SystemExit("Initialization metadata is invalid:\n" + "\n".join(issues))
        mastery, reviews = derive(events, concepts, profile["created_at"])
        commit_files(root, {
            "profile.json": profile,
            "plan.json": plan,
            "concepts.json": concepts,
            "sources.json": sources,
            "evidence.jsonl": "".join(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in events),
            "sessions.jsonl": "".join(json.dumps(session, ensure_ascii=False, sort_keys=True) + "\n" for session in sessions),
            "mastery.json": mastery,
            "reviews.json": reviews,
        })
        privacy_backup = ensure_privacy_file(root)
        if not (root / "improvement-proposals.md").exists():
            atomic_text(root / "improvement-proposals.md", "# Improvement proposals\n\nNo proposals yet.\n")
        register_workspace(workspace, profile["workspace_id"])
    print(json.dumps({"ok": True, "state_dir": str(root), "status": plan["status"], "preserved_evidence": len(events), "privacy_backup": privacy_backup}, ensure_ascii=False, indent=2))


def cmd_concept_add(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    if not ID_PATTERN.fullmatch(args.id):
        raise SystemExit("--id must be lowercase hyphen-case")
    required = split_values(args.required, DIMENSIONS, "required dimensions")
    if not required:
        raise SystemExit("--required must declare at least one mastery dimension")
    with state_lock(workspace):
        profile, plan, concepts, _ = load_core_documents(root)
        events, issues = read_events(root)
        if issues:
            raise SystemExit("State evidence is invalid:\n" + "\n".join(issues))
        existing = concepts["concepts"].get(args.id)
        if existing and not args.replace:
            raise SystemExit(f"Concept already exists: {args.id}; use --replace for metadata-only correction")
        prerequisites = (
            list(existing["prerequisites"])
            if existing and args.prerequisites is None
            else [item.strip() for item in (args.prerequisites or "").split(",") if item.strip()]
        )
        unknown = sorted(set(prerequisites) - set(concepts["concepts"]))
        if unknown:
            raise SystemExit(f"Unknown prerequisites: {unknown}")
        if existing:
            replacement = dict(existing)
            replacement.update({
                "title": args.title.strip() if args.title and args.title.strip() else existing["title"],
                "outcome": args.outcome.strip() if args.outcome and args.outcome.strip() else existing["outcome"],
                "required_dimensions": required,
                "prerequisites": prerequisites,
            })
            semantic_fields = ("outcome", "required_dimensions", "prerequisites")
            if events and any(existing.get(field) != replacement.get(field) for field in semantic_fields):
                raise SystemExit(
                    "Concept outcome, required dimensions, and prerequisites are immutable after any evidence exists; "
                    "create a versioned concept instead."
                )
        else:
            replacement = concept_definition(args.id, args.title, args.outcome, required, prerequisites)
        concepts["concepts"][args.id] = replacement
        concepts["updated_at"] = iso()
        issues = concepts_errors(concepts) + cross_document_errors(plan, concepts)
        if issues:
            raise SystemExit("Invalid concept definition:\n" + "\n".join(issues))
        mastery, reviews = derive(events, concepts, profile["created_at"])
        commit_files(root, {"concepts.json": concepts, "mastery.json": mastery, "reviews.json": reviews})
    print(json.dumps({"ok": True, "workspace": str(workspace), "concept": concepts["concepts"][args.id]}, ensure_ascii=False, indent=2))


def event_request_fingerprint(args: argparse.Namespace, dimensions: list[str], required: list[str]) -> str:
    occurred_at = iso(parse_time(args.occurred_at, "--occurred-at")) if args.occurred_at else None
    request = {
        "concept": args.concept,
        "kind": args.kind,
        "score": round(args.score, 4),
        "difficulty": args.difficulty,
        "hints": args.hints,
        "support": "assisted" if args.assisted or args.hints > 0 else "independent",
        "requested_delayed": bool(args.delayed),
        "occurred_at": occurred_at,
        "dimensions": sorted(dimensions),
        "notes": args.notes or "",
        "title": args.title.strip() if args.title and args.title.strip() else None,
        "outcome": args.outcome.strip() if args.outcome and args.outcome.strip() else None,
        "required": sorted(required),
    }
    encoded = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def event_matches_retry(existing: dict[str, Any], request_fingerprint: str) -> bool:
    return existing.get("request_fingerprint") == request_fingerprint and not existing.get("legacy")


def cmd_record(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    if not ID_PATTERN.fullmatch(args.concept):
        raise SystemExit("--concept must be lowercase hyphen-case")
    if not 0 <= args.score <= 1 or not 1 <= args.difficulty <= 5 or args.hints < 0:
        raise SystemExit("score must be 0..1, difficulty 1..5, and hints non-negative")
    dimensions = split_values(args.dimensions, DIMENSIONS, "dimensions") or KIND_DIMENSIONS[args.kind]
    if not set(KIND_DIMENSIONS[args.kind]).issubset(dimensions):
        raise SystemExit(f"Evidence kind {args.kind} requires dimensions {KIND_DIMENSIONS[args.kind]}; dimensions may add but not remove semantics.")
    requested_required = split_values(args.required, DIMENSIONS, "required dimensions")
    request_fingerprint = event_request_fingerprint(args, dimensions, requested_required)
    timestamp = parse_time(args.occurred_at, "--occurred-at") if args.occurred_at else None
    if timestamp is not None and timestamp > now() + timedelta(minutes=5):
        raise SystemExit("--occurred-at cannot be in the future")
    event_id = args.event_id or f"ev-{uuid.uuid4().hex}"
    if not EVENT_ID_PATTERN.fullmatch(event_id):
        raise SystemExit("--event-id must start with ev- and contain at least eight safe identifier characters")
    with state_lock(workspace):
        if not (root / "profile.json").exists():
            raise SystemExit("Learner state was deleted while waiting for the lock; do not record.")
        profile, _, concepts, _ = load_core_documents(root)
        events, errors = read_events(root)
        if errors:
            raise SystemExit("State evidence is invalid; run validate before recording:\n" + "\n".join(errors))
        if timestamp is None:
            timestamp = now()
            if events:
                timestamp = max(timestamp, parse_time(events[-1]["timestamp"]))
        existing_event = next((item for item in events if item["id"] == event_id), None)
        if existing_event:
            if not event_matches_retry(existing_event, request_fingerprint):
                raise SystemExit(f"Event ID {event_id} already exists with different evidence")
            mastery, reviews = derive(events, concepts, profile["created_at"])
            if load_json(root / "mastery.json") != mastery or load_json(root / "reviews.json") != reviews:
                commit_files(root, {"mastery.json": mastery, "reviews.json": reviews})
            concept = mastery["concepts"][args.concept]
            due_at = reviews["concepts"].get(args.concept, {}).get("due_at")
            print(json.dumps({"ok": True, "duplicate": True, "event": existing_event, "status": concept["status"], "due_at": due_at}, ensure_ascii=False, indent=2))
            return
        definition = concepts["concepts"].get(args.concept)
        if definition is None:
            if not requested_required:
                raise SystemExit("Unknown concept. Bind a curriculum, run concept-add, or provide --required on its first record.")
            definition = concept_definition(args.concept, args.title, args.outcome, requested_required)
            concepts["concepts"][args.concept] = definition
            concepts["updated_at"] = iso()
        elif requested_required and requested_required != definition["required_dimensions"]:
            raise SystemExit(f"Required dimensions for {args.concept} are fixed at {definition['required_dimensions']}; evidence cannot shrink or replace them.")
        if events and timestamp < parse_time(events[-1]["timestamp"]):
            raise SystemExit("--occurred-at cannot be earlier than the latest event; evidence is append-only and chronological")
        previous = next((parse_time(item["timestamp"]) for item in reversed(events) if item["concept"] == args.concept), None)
        delayed, delay_hours = False, None
        if args.delayed:
            if args.kind not in {"recall", "review"} or "recall" not in dimensions:
                raise SystemExit("--delayed is reserved for recall/review evidence with the recall dimension")
            if previous is None or timestamp - previous < MIN_DELAY:
                raise SystemExit("--delayed requires prior evidence at least 12 hours earlier")
            delayed = True
            delay_hours = round((timestamp - previous).total_seconds() / 3600, 2)
        independent = args.hints == 0 and not args.assisted
        support = "independent" if independent else "assisted"
        event = {
            "schema_version": SCHEMA_VERSION, "id": event_id, "timestamp": iso(timestamp), "concept": args.concept,
            "kind": args.kind, "score": round(args.score, 4), "difficulty": args.difficulty, "hints": args.hints,
            "assisted": bool(args.assisted), "independent": independent, "delayed": delayed, "delay_hours": delay_hours,
            "dimensions": sorted(dimensions), "notes": args.notes or "", "legacy": False,
            "support": support, "request_fingerprint": request_fingerprint,
        }
        issues = event_errors(event)
        if issues:
            raise SystemExit("\n".join(issues))
        candidate_events = [*events, event]
        candidate_mastery, candidate_reviews = derive(candidate_events, concepts, profile["created_at"])
        commit_files(root, {
            "concepts.json": concepts,
            "evidence.jsonl": "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in candidate_events),
            "mastery.json": candidate_mastery,
            "reviews.json": candidate_reviews,
        })
    concept = candidate_mastery["concepts"][args.concept]
    due_at = candidate_reviews["concepts"].get(args.concept, {}).get("due_at")
    print(json.dumps({"ok": True, "duplicate": False, "event": event, "status": concept["status"], "due_at": due_at}, ensure_ascii=False, indent=2))


def cmd_rebuild(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    with state_lock(workspace):
        profile, _, concepts, _ = load_core_documents(root)
        events, errors = read_events(root)
        if errors:
            raise SystemExit("Cannot rebuild from invalid evidence:\n" + "\n".join(errors))
        unknown = sorted({event["concept"] for event in events} - set(concepts["concepts"]))
        if unknown:
            raise SystemExit(f"Cannot rebuild: evidence references undefined concepts {unknown}")
        mastery, reviews = derive(events, concepts, profile["created_at"])
        commit_files(root, {"mastery.json": mastery, "reviews.json": reviews})
    print(json.dumps({"ok": True, "state_dir": str(root), "events": len(events), "concepts": len(mastery["concepts"]), "reviews": len(reviews["concepts"])}, ensure_ascii=False, indent=2))


def latest_session(root: Path) -> dict[str, Any] | None:
    sessions, errors = read_sessions(root)
    if errors:
        raise SystemExit("State sessions are invalid; run validate before resuming:\n" + "\n".join(errors))
    return sessions[-1] if sessions else None


def verified_derived(root: Path, profile: dict[str, Any], concepts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    events, errors = read_events(root)
    if errors:
        raise SystemExit("State evidence is invalid; run validate before continuing:\n" + "\n".join(errors))
    expected_mastery, expected_reviews = derive(events, concepts, profile["created_at"])
    actual_mastery, actual_reviews = load_json(root / "mastery.json"), load_json(root / "reviews.json")
    if actual_mastery != expected_mastery or actual_reviews != expected_reviews:
        raise SystemExit("Derived state does not match evidence; run `mastery.py rebuild` before continuing")
    return actual_mastery, actual_reviews, events


def cmd_status(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    with state_lock(workspace):
        profile, plan, concepts, _ = load_core_documents(root)
        mastery, reviews, events = verified_derived(root, profile, concepts)
        if not isinstance(mastery, dict) or not isinstance(mastery.get("concepts"), dict):
            raise SystemExit("mastery.json is invalid; run validate/rebuild")
        if not isinstance(reviews, dict) or not isinstance(reviews.get("concepts"), dict):
            raise SystemExit("reviews.json is invalid; run validate/rebuild")
        selection = plan["scope_selection"]
        required, enrichment = scope_sets(plan, concepts)
        confirmed = selection["status"] == "confirmed"
        display_ids = topological_scope(concepts["concepts"], required) if confirmed else sorted(mastery["concepts"])
        rows = []
        for concept_id in display_ids:
            item = mastery["concepts"].get(concept_id, {})
            definition = concepts["concepts"][concept_id]
            values = list(item.get("dimensions", {}).values())
            rows.append({
                "id": concept_id, "title": item.get("title", definition["title"]), "status": item.get("status", "unassessed"),
                "average": round(sum(values) / len(values), 3) if values else None, "evidence": item.get("evidence_count", 0),
                "due_at": reviews["concepts"].get(concept_id, {}).get("due_at"),
            })
        status_counts = {name: sum(row["status"] == name for row in rows) for name in ["mastered", "provisional", "fragile", "unassessed"]}
        attempted = len(rows) - status_counts["unassessed"]
        total_dimensions = sum(len(concepts["concepts"][concept_id]["required_dimensions"]) for concept_id in required)
        passing_dimensions = 0
        for concept_id in required:
            item = mastery["concepts"].get(concept_id, {})
            for dimension in concepts["concepts"][concept_id]["required_dimensions"]:
                passing_dimensions += int(item.get("dimensions", {}).get(dimension, 0) >= PASS_THRESHOLD)
        coverage = {
            "scope_status": selection["status"],
            "defined": len(concepts["concepts"]),
            "required": len(required),
            "enrichment": len(enrichment),
            "not_selected": len(concepts["concepts"]) - len(required) - len(enrichment) if confirmed else len(concepts["concepts"]),
            "assessed": sum(item.get("evidence_count", 0) > 0 for item in mastery["concepts"].values()),
            "attempted_required": attempted if confirmed else 0,
            **status_counts,
            "completion_ratio": round(status_counts["mastered"] / len(required), 4) if required else None,
            "dimension_ratio": round(passing_dimensions / total_dimensions, 4) if total_dimensions else None,
            "out_of_scope_evidence": sum(event["concept"] not in required and event["concept"] not in enrichment for event in events) if confirmed else 0,
        }
        result = {
            "goal": profile["goal"], "workspace": str(workspace), "state_dir": str(root), "plan_status": plan["status"],
            "scope_selection": selection, "coverage": coverage, "latest_session": latest_session(root), "concepts": rows,
        }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if result["coverage"]["scope_status"] == "confirmed":
        coverage_line = f"Mastered: {result['coverage']['mastered']}/{result['coverage']['required']} required concepts"
    else:
        coverage_line = f"Scope unselected; {result['coverage']['assessed']}/{result['coverage']['defined']} concepts assessed"
    print(f"Goal: {result['goal']}\nWorkspace: {workspace}\nCoverage: {coverage_line}")
    if not rows:
        print("No evidence recorded yet. Start with a guided lesson and record only observed learner work.")
        return
    print(f"{'Concept':28} {'State':12} {'Score':7} {'Evidence':8} Due")
    for row in rows:
        score = "—" if row["average"] is None else f"{row['average']:.2f}"
        print(f"{row['id'][:28]:28} {row['status'][:12]:12} {score:7} {row['evidence']:<8} {row['due_at'] or '—'}")


def cmd_due(args: argparse.Namespace) -> None:
    if args.within_days < 0:
        raise SystemExit("--within-days must be non-negative")
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    with state_lock(workspace):
        profile, plan, concepts, _ = load_core_documents(root)
        mastery, reviews, _ = verified_derived(root, profile, concepts)
        if not isinstance(reviews, dict) or not isinstance(reviews.get("concepts"), dict):
            raise SystemExit("reviews.json is invalid; run validate/rebuild")
        all_due = []
        selection = plan.get("scope_selection", {})
        scope_status = selection.get("status") if isinstance(selection, dict) else "unselected"
        required, enrichment = scope_sets(plan, concepts) if scope_status == "confirmed" else (set(), set())
        for concept_id, item in reviews["concepts"].items():
            try:
                due_at = parse_time(item["due_at"], "due_at")
            except (KeyError, TypeError, ValueError):
                continue
            if due_at <= now() + timedelta(days=args.within_days):
                concept = mastery.get("concepts", {}).get(concept_id, {}) if isinstance(mastery, dict) else {}
                scope = (
                    "required" if concept_id in required else
                    "enrichment" if concept_id in enrichment else
                    "not-selected" if scope_status == "confirmed" else
                    "unselected"
                )
                all_due.append({"concept": concept_id, "title": concept.get("title", concept_id), "status": concept.get("status"), "scope_class": scope, **item})
        all_due.sort(key=lambda item: item["due_at"])
        enrichment_due = [item for item in all_due if item["scope_class"] == "enrichment"]
        out_of_scope_due = [item for item in all_due if item["scope_class"] == "not-selected"]
        required_due = [item for item in all_due if item["scope_class"] == "required"]
        due = all_due if scope_status != "confirmed" or args.include_nonrequired else required_due
    if args.json:
        print(json.dumps({
            "workspace": str(workspace), "scope_status": scope_status, "includes_nonrequired": bool(args.include_nonrequired),
            "due": due, "enrichment_due": enrichment_due, "out_of_scope_due": out_of_scope_due,
        }, ensure_ascii=False, indent=2))
    elif not due:
        print("No reviews due in the selected window.")
    else:
        for item in due:
            print(f"{item['due_at']}  {item['concept']}  {item.get('status', 'unassessed')}  {item['scope_class']}")
        if scope_status == "confirmed" and not args.include_nonrequired and (enrichment_due or out_of_scope_due):
            print(f"Additional due items: {len(enrichment_due)} enrichment, {len(out_of_scope_due)} not-selected; use --include-nonrequired or --json to inspect them.")


def cmd_validate(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    with state_lock(workspace):
        errors: list[str] = []
        warnings: list[str] = []
        for name in CORE_FILES:
            if not (root / name).exists():
                errors.append(f"missing {name}")
        values: dict[str, Any] = {}
        for name in ["profile.json", "plan.json", "concepts.json", "mastery.json", "reviews.json", "sources.json"]:
            path = root / name
            if not path.exists():
                continue
            try:
                values[name] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"{name}: invalid JSON: {error}")
        for name in ["profile.json", "plan.json", "concepts.json", "sources.json"]:
            if name in values:
                errors.extend(document_errors(name, values[name]))
        for name in ["mastery.json", "reviews.json"]:
            value = values.get(name)
            if name in values and (not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION or not isinstance(value.get("concepts"), dict)):
                errors.append(f"{name}: root/schema/concepts is invalid")
        events, event_issues = read_events(root)
        errors.extend(event_issues)
        sessions, session_issues = read_sessions(root)
        errors.extend(session_issues)
        concepts_value = values.get("concepts.json")
        if isinstance(concepts_value, dict) and isinstance(concepts_value.get("concepts"), dict):
            unknown = sorted({event["concept"] for event in events} - set(concepts_value["concepts"]))
            if unknown:
                errors.append(f"evidence references undefined concepts: {unknown}")
        plan_value = values.get("plan.json")
        if isinstance(plan_value, dict) and isinstance(concepts_value, dict):
            errors.extend(cross_document_errors(plan_value, concepts_value))
        sources_value = values.get("sources.json")
        errors.extend(source_cross_document_errors(concepts_value, sources_value))
        try:
            revision_value(root)
        except SystemExit as error:
            errors.append(str(error))
        try:
            if (root / ".gitignore").read_text(encoding="utf-8") != PRIVACY_CONTENT:
                errors.append(".gitignore is not the engine-managed privacy guard; run init --force after validation")
        except OSError:
            errors.append("missing .gitignore privacy guard")
        profile_value = values.get("profile.json")
        if not errors and isinstance(profile_value, dict) and isinstance(concepts_value, dict):
            expected_mastery, expected_reviews = derive(events, concepts_value, profile_value["created_at"])
            if values.get("mastery.json") != expected_mastery:
                errors.append("mastery.json does not match evidence/concept definitions; run `mastery.py rebuild`")
            if values.get("reviews.json") != expected_reviews:
                errors.append("reviews.json does not match evidence; run `mastery.py rebuild`")
        if (root / "session-log.md").exists():
            warnings.append("legacy session-log.md remains; new session summaries use sessions.jsonl")
        if isinstance(profile_value, dict):
            entry_path = registry_dir() / f"{workspace_key(workspace)}.json"
            entry_value, registry_error = inspect_registry_entry(entry_path)
            if registry_error:
                warnings.append(
                    f"workspace registry entry is invalid at {entry_path}: {registry_error['message']}"
                )
            elif entry_value is not None and entry_value.get("workspace_id") != profile_value.get("workspace_id"):
                warnings.append(f"workspace registry entry is invalid at {entry_path}: workspace_id mismatch")
        result = {"ok": not errors, "workspace": str(workspace), "state_dir": str(root), "events": len(events), "sessions": len(sessions), "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


def cmd_locate(args: argparse.Namespace) -> None:
    entries, errors, warnings = discover_workspaces()
    if args.goal:
        query = args.goal.casefold()
        entries = [item for item in entries if query in item.get("goal", "").casefold()]
    print(json.dumps({"ok": not errors, "registry": str(registry_dir()), "workspaces": entries, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


def validate_set_value(target: str, field: str, value: Any) -> None:
    if target == "profile":
        if field == "proof_of_completion" and (not isinstance(value, str) or not value.strip()):
            raise SystemExit("profile.proof_of_completion must be non-empty text")
        if field == "hours_per_week" and (not is_number(value) or not 0 < value <= 168):
            raise SystemExit("profile.hours_per_week must be greater than 0 and at most 168")
        if field == "session_minutes" and (not isinstance(value, int) or isinstance(value, bool) or not 5 <= value <= 480):
            raise SystemExit("profile.session_minutes must be an integer from 5 to 480")
        if field == "deadline" and value is not None and (not isinstance(value, str) or not value.strip()):
            raise SystemExit("profile.deadline must be non-empty text or null")
        if field in {"constraints", "interests"} and (not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value)):
            raise SystemExit(f"profile.{field} must be an array of non-empty strings")
        if field == "hypotheses":
            trial = {"schema_version": SCHEMA_VERSION, "workspace_id": "ws-test", "created_at": iso(), "updated_at": iso(), "goal": "test", "proof_of_completion": "test", "hours_per_week": 1, "session_minutes": 30, "deadline": None, "constraints": [], "interests": [], "hypotheses": value}
            issues = [item for item in profile_errors(trial) if "hypotheses" in item]
            if issues:
                raise SystemExit("\n".join(issues))
    else:
        if field == "status" and value not in PLAN_STATUSES:
            raise SystemExit(f"plan.status must be one of {sorted(PLAN_STATUSES)}")
        if field == "target_artifact" and value is not None and (not isinstance(value, str) or not value.strip()):
            raise SystemExit("plan.target_artifact must be non-empty text or null")
        if field in {"excluded_scope", "open_questions"} and (not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value)):
            raise SystemExit(f"plan.{field} must be an array of non-empty strings")
        if field == "active_path" and (not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value)):
            raise SystemExit("plan.active_path must be an array of concept IDs")


def cmd_set(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    allowed = {
        "profile": {"proof_of_completion", "hours_per_week", "session_minutes", "deadline", "constraints", "interests", "hypotheses"},
        "plan": {"status", "target_artifact", "active_path", "excluded_scope", "open_questions"},
    }
    if args.field not in allowed[args.target]:
        raise SystemExit(f"Cannot update {args.target}.{args.field}; allowed fields: {', '.join(sorted(allowed[args.target]))}")
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError as error:
        raise SystemExit("--value must be valid JSON; quote strings as JSON strings") from error
    validate_set_value(args.target, args.field, value)
    filename = f"{args.target}.json"
    with state_lock(workspace):
        profile, plan, concepts, sources = load_core_documents(root)
        document = {"profile": profile, "plan": plan}[args.target]
        issues = document_errors(filename, document)
        if issues:
            raise SystemExit("Cannot update invalid state:\n" + "\n".join(issues))
        document[args.field], document["updated_at"] = value, iso()
        issues = document_errors(filename, document)
        if args.target == "plan":
            issues += cross_document_errors(document, concepts)
        if issues:
            raise SystemExit("Update would violate state schema:\n" + "\n".join(issues))
        commit_files(root, {filename: document})
    print(json.dumps({"ok": True, "workspace": str(workspace), "updated": f"{args.target}.{args.field}", "value": value}, ensure_ascii=False, indent=2))


def cmd_scope_apply(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    profiles = list(dict.fromkeys(args.target_profile or []))
    additional = split_ids(args.additional_targets, "additional targets")
    enrichment = split_ids(args.enrichment_targets, "enrichment targets")
    candidate_selection = scope_selection(profiles, additional, enrichment, args.reason)
    if candidate_selection["status"] != "confirmed":
        raise SystemExit("Scope confirmation requires at least one --target-profile or --additional-targets value")
    with state_lock(workspace):
        _, plan, concepts, _ = load_core_documents(root)
        candidate = json.loads(json.dumps(plan))
        candidate["scope_selection"] = candidate_selection
        candidate["updated_at"] = iso()
        issues = plan_errors(candidate) + cross_document_errors(candidate, concepts)
        if issues:
            raise SystemExit("Scope selection is invalid:\n" + "\n".join(issues))
        required, optional = scope_sets(candidate, concepts)
        commit_files(root, {"plan.json": candidate})
    print(json.dumps({
        "ok": True, "workspace": str(workspace), "scope_selection": candidate_selection,
        "required_count": len(required), "enrichment_count": len(optional),
        "required_concepts": topological_scope(concepts["concepts"], required),
        "enrichment_concepts": topological_scope(concepts["concepts"], optional),
    }, ensure_ascii=False, indent=2))


def cmd_scope_status(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    with state_lock(workspace):
        _, plan, concepts, _ = load_core_documents(root)
        issues = cross_document_errors(plan, concepts)
        if issues:
            raise SystemExit("Scope state is invalid:\n" + "\n".join(issues))
        required, enrichment = scope_sets(plan, concepts)
        result = {
            "ok": True, "workspace": str(workspace), "scope_selection": plan["scope_selection"],
            "required_count": len(required), "enrichment_count": len(enrichment),
            "not_selected_count": len(concepts["concepts"]) - len(required) - len(enrichment),
            "required_concepts": topological_scope(concepts["concepts"], required),
            "enrichment_concepts": topological_scope(concepts["concepts"], enrichment),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_source_add(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    if not ID_PATTERN.fullmatch(args.id):
        raise SystemExit("--id must be lowercase hyphen-case")
    parsed = urlparse(args.url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("--url must be a canonical HTTPS URL")
    try:
        checked = date.fromisoformat(args.checked_at or date.today().isoformat())
    except ValueError as error:
        raise SystemExit("--checked-at must be YYYY-MM-DD") from error
    if checked > date.today():
        raise SystemExit("--checked-at cannot be in the future")
    concept_ids = [item.strip() for item in args.concepts.split(",") if item.strip()]
    source = {
        "id": args.id, "title": args.title, "organization": args.organization, "url": args.url,
        "type": args.type, "authority": args.authority, "version_or_date": args.version_or_date,
        "license_reuse": args.license_reuse, "concepts": concept_ids, "known_gaps": args.known_gaps,
        "checked_at": checked.isoformat(),
    }
    with state_lock(workspace):
        _, _, concepts, ledger = load_core_documents(root)
        unknown = sorted(set(concept_ids) - set(concepts["concepts"]))
        if unknown:
            raise SystemExit(f"Source references undefined concepts: {unknown}")
        if any(item.get("id") == args.id for item in ledger["sources"]) and not args.replace:
            raise SystemExit(f"source ID already exists: {args.id}; use --replace to update it")
        ledger["sources"] = [item for item in ledger["sources"] if item.get("id") != args.id] + [source]
        ledger["updated_at"] = iso()
        issues = sources_errors(ledger)
        if issues:
            raise SystemExit("Invalid source metadata:\n" + "\n".join(issues))
        commit_files(root, {"sources.json": ledger})
    print(json.dumps({"ok": True, "workspace": str(workspace), "source": source}, ensure_ascii=False, indent=2))


def cmd_session_close(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    if args.next_review:
        try:
            parse_time(args.next_review, "--next-review")
        except ValueError as error:
            raise SystemExit(str(error)) from error
    for field in ["demonstrated", "unresolved", "next_action"]:
        if not getattr(args, field).strip():
            raise SystemExit(f"--{field.replace('_', '-')} must be non-empty")
    if not SESSION_ID_PATTERN.fullmatch(args.session_id):
        raise SystemExit("--session-id must start with session- and contain at least eight safe identifier characters")
    request = {
        "demonstrated": args.demonstrated.strip(), "unresolved": args.unresolved.strip(),
        "next_action": args.next_action.strip(), "next_review": args.next_review, "notes": args.notes or "",
    }
    with state_lock(workspace):
        load_core_documents(root)
        sessions, errors = read_sessions(root)
        if errors:
            raise SystemExit("State sessions are invalid; repair them before closing another session:\n" + "\n".join(errors))
        existing = next((item for item in sessions if item["id"] == args.session_id), None)
        if existing:
            compared = ["demonstrated", "unresolved", "next_action", "next_review", "notes"]
            if any(existing[field] != request[field] for field in compared):
                raise SystemExit(f"Session ID {args.session_id} already exists with a different handoff")
            print(json.dumps({"ok": True, "duplicate": True, "workspace": str(workspace), "session": existing}, ensure_ascii=False, indent=2))
            return
        closed_at = now()
        if sessions:
            closed_at = max(closed_at, parse_time(sessions[-1]["closed_at"], "closed_at"))
        event = {"schema_version": 1, "id": args.session_id, "closed_at": iso(closed_at), **request}
        candidate = [*sessions, event]
        _, candidate_errors = validate_session_sequence(list(enumerate(candidate, 1)))
        if candidate_errors:
            raise SystemExit("Session would violate the state schema:\n" + "\n".join(candidate_errors))
        commit_files(root, {"sessions.jsonl": "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in candidate)})
    print(json.dumps({"ok": True, "workspace": str(workspace), "session": event}, ensure_ascii=False, indent=2))


def safe_export_target(root: Path, output: Path) -> None:
    if path_inside(output, root):
        raise SystemExit("Export/backup must be outside .mastery so it cannot include or delete itself")
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing export: {output}")


def write_export(root: Path, output: Path) -> None:
    safe_export_target(root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    raise SystemExit(f"Refusing to export symbolic link from learner state: {path}")
                if path.is_file():
                    archive.write(path, Path(".mastery") / path.relative_to(root))
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def cmd_export(args: argparse.Namespace) -> None:
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    output = Path(args.output).expanduser().resolve()
    with state_lock(workspace):
        if not root.exists():
            raise SystemExit("Learner state was deleted while waiting for the lock")
        write_export(root, output)
    print(json.dumps({"ok": True, "workspace": str(workspace), "export": str(output)}, ensure_ascii=False, indent=2))


def cmd_delete(args: argparse.Namespace) -> None:
    if args.confirm != "DELETE-MASTERY-DATA":
        raise SystemExit("Deletion requires --confirm DELETE-MASTERY-DATA")
    workspace = resolve_workspace(args.workspace)
    root = state_dir(workspace)
    if root.name != ".mastery" or root.parent != workspace:
        raise SystemExit("Refusing unsafe deletion target")
    backup = Path(args.backup).expanduser().resolve() if args.backup else None
    warning: str | None = None
    with state_lock(workspace):
        if not root.exists():
            raise SystemExit("Learner state was already deleted")
        if backup:
            write_export(root, backup)
        tombstone = workspace / f".mastery.deleting-{uuid.uuid4().hex}"
        os.replace(root, tombstone)
        try:
            shutil.rmtree(tombstone)
        except Exception:
            if tombstone.exists() and not root.exists():
                os.replace(tombstone, root)
            raise
        # Keep registry removal in the same workspace transaction. Otherwise
        # an older delete can unlink a concurrent init's fresh registration.
        warning = unregister_workspace(workspace)
    print(json.dumps({"ok": True, "deleted": str(root), "recoverable_from": str(backup) if backup else None, "warning": warning}, ensure_ascii=False, indent=2))


def migration_backup_path(workspace: Path, old_schema: Any) -> Path:
    stamp = now().strftime("%Y%m%dT%H%M%SZ")
    return workspace / f"mastery-migration-v{old_schema or 'unknown'}-{stamp}-{uuid.uuid4().hex[:8]}.zip"


def load_legacy_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise SystemExit(f"Cannot read legacy evidence: {error}") from error
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Legacy evidence line {number} is invalid JSON: {error}") from error
        if not isinstance(value, dict):
            raise SystemExit(f"Legacy evidence line {number} must be an object")
        events.append(value)
    return events


def migrate_event(old: dict[str, Any], used_ids: set[str], previous: datetime | None, old_schema: Any) -> dict[str, Any]:
    try:
        timestamp = parse_time(old.get("timestamp", ""))
    except ValueError as error:
        raise SystemExit(f"Cannot migrate event with invalid timestamp: {error}") from error
    kind = old.get("kind") if old.get("kind") in KINDS else "diagnostic"
    raw_dimensions = old.get("dimensions") if isinstance(old.get("dimensions"), list) else KIND_DIMENSIONS[kind]
    dimensions = list(dict.fromkeys(item for item in raw_dimensions if item in DIMENSIONS)) or KIND_DIMENSIONS[kind]
    explicit_hints = isinstance(old.get("hints"), int) and not isinstance(old.get("hints"), bool) and old["hints"] >= 0
    explicit_assisted = isinstance(old.get("assisted"), bool)
    explicit_independent = isinstance(old.get("independent"), bool)
    hints = old["hints"] if explicit_hints else 0
    fields_consistent = (
        explicit_hints and explicit_assisted and explicit_independent
        and old["independent"] is (hints == 0 and not old["assisted"])
    )
    if fields_consistent:
        assisted = bool(old["assisted"])
        independent = bool(old["independent"])
        support = "independent" if independent else "assisted"
    else:
        assisted, independent, support = True, False, "unknown"
    raw_id = old.get("id")
    event_id = raw_id if isinstance(raw_id, str) and EVENT_ID_PATTERN.fullmatch(raw_id) and raw_id not in used_ids else f"ev-{uuid.uuid4().hex}"
    used_ids.add(event_id)
    delayed = bool(old.get("delayed")) and kind in {"recall", "review"} and "recall" in dimensions and previous is not None and timestamp - previous >= MIN_DELAY
    delay_hours = round((timestamp - previous).total_seconds() / 3600, 2) if delayed and previous else None
    score = float(old["score"]) if is_number(old.get("score")) and 0 <= float(old["score"]) <= 1 else 0.0
    difficulty = old.get("difficulty", 3)
    difficulty = difficulty if isinstance(difficulty, int) and not isinstance(difficulty, bool) and 1 <= difficulty <= 5 else 3
    notes = str(old.get("notes", ""))
    legacy = bool(old.get("legacy", True)) if old_schema == 3 else True
    if legacy:
        support = "unknown"
        assisted, independent = True, False
    stored_request = {
        "concept": str(old.get("concept", "legacy-concept")), "kind": kind, "score": round(score, 4),
        "difficulty": difficulty, "hints": hints, "support": support, "requested_delayed": delayed,
        "occurred_at": iso(timestamp), "dimensions": sorted(dimensions), "notes": notes,
        "title": None, "outcome": None,
        "required": sorted(old.get("required_dimensions", [])) if isinstance(old.get("required_dimensions"), list) else [],
    }
    fingerprint = old.get("request_fingerprint") if old_schema == 3 else None
    if not legacy and (not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
        fingerprint = hashlib.sha256(json.dumps(stored_request, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION, "id": event_id, "timestamp": iso(timestamp), "concept": str(old.get("concept", "legacy-concept")),
        "kind": kind, "score": round(score, 4), "difficulty": difficulty, "hints": hints, "assisted": assisted,
        "independent": independent, "delayed": delayed, "delay_hours": delay_hours, "dimensions": sorted(dimensions),
        "notes": f"{notes} [migrated from schema v{old_schema}; uncertain support cannot certify mastery]".strip(),
        "legacy": legacy, "support": support, "request_fingerprint": fingerprint,
    }


def cmd_migrate(args: argparse.Namespace) -> None:
    workspace = explicit_workspace(args.workspace)
    root = state_dir(workspace)
    if not (root / "profile.json").exists():
        raise SystemExit(f"No learner state to migrate at {root}")
    preflight_registry()
    with state_lock(workspace):
        old_profile = load_json(root / "profile.json")
        if not isinstance(old_profile, dict):
            raise SystemExit("Cannot migrate: profile.json root must be an object")
        old_schema = old_profile.get("schema_version")
        if old_schema == SCHEMA_VERSION:
            raise SystemExit("State is already schema v4; run validate instead")
        if old_schema not in {1, 2, 3}:
            raise SystemExit(f"Unsupported migration source schema: {old_schema}")
        backup = Path(args.backup).expanduser().resolve() if args.backup else migration_backup_path(workspace, old_schema)
        write_export(root, backup)
        old_events = load_legacy_events(root / "evidence.jsonl")
        old_mastery = load_json(root / "mastery.json", {})
        old_concepts = old_mastery.get("concepts", {}) if isinstance(old_mastery, dict) and isinstance(old_mastery.get("concepts"), dict) else {}
        old_concepts_document = load_json(root / "concepts.json", {}) if old_schema == 3 else {}
        upgraded_concepts_document: dict[str, Any] | None = None
        upgraded_sources: dict[str, Any] | None = None
        old_curriculum = old_concepts_document.get("curriculum") if isinstance(old_concepts_document, dict) else None
        if old_schema == 3 and isinstance(old_curriculum, dict) and old_curriculum.get("id") == "ml-ai-llm":
            candidate_concepts, _, candidate_sources = concepts_from_curriculum("ml-ai-llm")
            old_map = old_concepts_document.get("concepts", {})
            comparable_fields = ["id", "outcome", "prerequisites", "required_dimensions", "optional", "source_pack"]
            if set(old_map) == set(candidate_concepts["concepts"]) and all(
                all(old_map[concept_id].get(field) == candidate_concepts["concepts"][concept_id].get(field) for field in comparable_fields)
                for concept_id in old_map
            ):
                upgraded_concepts_document, upgraded_sources = candidate_concepts, candidate_sources
        requirement_sets: dict[str, set[str]] = {}
        titles: dict[str, str] = {}
        for concept_id, item in old_concepts.items():
            if isinstance(item, dict):
                requirement_sets.setdefault(concept_id, set()).update(dim for dim in item.get("required_dimensions", []) if dim in DIMENSIONS)
                if isinstance(item.get("title"), str):
                    titles[concept_id] = item["title"]
        previous_by_concept: dict[str, datetime] = {}
        used_ids: set[str] = set()
        events: list[dict[str, Any]] = []
        last_timestamp: datetime | None = None
        for old in old_events:
            concept_id = str(old.get("concept", "legacy-concept"))
            if not ID_PATTERN.fullmatch(concept_id):
                raise SystemExit(f"Cannot migrate invalid legacy concept ID: {concept_id}")
            requirement_sets.setdefault(concept_id, set()).update(dim for dim in old.get("required_dimensions", []) if dim in DIMENSIONS)
            event = migrate_event(old, used_ids, previous_by_concept.get(concept_id), old_schema)
            timestamp = parse_time(event["timestamp"])
            if last_timestamp and timestamp < last_timestamp:
                raise SystemExit("Cannot migrate non-chronological legacy evidence without changing history")
            last_timestamp = timestamp
            previous_by_concept[concept_id] = timestamp
            events.append(event)
        concepts_map: dict[str, Any] = {}
        if upgraded_concepts_document is not None:
            concepts_map = json.loads(json.dumps(upgraded_concepts_document["concepts"]))
        elif isinstance(old_concepts_document, dict) and isinstance(old_concepts_document.get("concepts"), dict):
            concepts_map = json.loads(json.dumps(old_concepts_document["concepts"]))
        for concept_id in sorted({*requirement_sets, *(event["concept"] for event in events)}):
            if concept_id not in concepts_map:
                required = sorted(requirement_sets.get(concept_id) or set(DEFAULT_REQUIRED))
                concepts_map[concept_id] = concept_definition(concept_id, titles.get(concept_id), None, required)
                concepts_map[concept_id]["source_pack"] = f"migrated-v{old_schema}"
        created_at = old_profile.get("created_at") if isinstance(old_profile.get("created_at"), str) else iso()
        try:
            parse_time(created_at)
        except ValueError:
            created_at = iso()
        profile = {
            "schema_version": SCHEMA_VERSION,
            "workspace_id": old_profile.get("workspace_id") if isinstance(old_profile.get("workspace_id"), str) else f"ws-{uuid.uuid4().hex}",
            "created_at": created_at, "updated_at": iso(), "goal": str(old_profile.get("goal") or "Migrated learning goal"),
            "proof_of_completion": str(old_profile.get("proof_of_completion") or "To be agreed after migration review"),
            "hours_per_week": old_profile.get("hours_per_week") if is_number(old_profile.get("hours_per_week")) and 0 < old_profile["hours_per_week"] <= 168 else 5,
            "session_minutes": old_profile.get("session_minutes") if isinstance(old_profile.get("session_minutes"), int) and not isinstance(old_profile.get("session_minutes"), bool) and 5 <= old_profile["session_minutes"] <= 480 else 45,
            "deadline": old_profile.get("deadline") if old_profile.get("deadline") is None or isinstance(old_profile.get("deadline"), str) else None,
            "constraints": old_profile.get("constraints") if isinstance(old_profile.get("constraints"), list) and all(isinstance(x, str) for x in old_profile["constraints"]) else [],
            "interests": old_profile.get("interests") if isinstance(old_profile.get("interests"), list) and all(isinstance(x, str) for x in old_profile["interests"]) else [],
            "hypotheses": old_profile.get("hypotheses", []),
        }
        old_plan = load_json(root / "plan.json", {})
        old_plan = old_plan if isinstance(old_plan, dict) else {}
        plan = {
            "schema_version": SCHEMA_VERSION, "updated_at": iso(),
            "status": old_plan.get("status") if old_plan.get("status") in PLAN_STATUSES else "diagnostic",
            "coverage_pack": old_plan.get("coverage_pack") if isinstance(old_plan.get("coverage_pack"), str) else ("ml-ai-llm" if upgraded_concepts_document is not None else None),
            "target_artifact": old_plan.get("target_artifact") if isinstance(old_plan.get("target_artifact"), str) else None,
            "active_path": [item for item in old_plan.get("active_path", []) if isinstance(item, str) and item in concepts_map],
            "excluded_scope": old_plan.get("excluded_scope") if isinstance(old_plan.get("excluded_scope"), list) and all(isinstance(x, str) for x in old_plan["excluded_scope"]) else [],
            "open_questions": ["Review migrated evidence semantics and concept requirements before continuing."],
            "scope_selection": scope_selection([], [], [], "Legacy state requires explicit scope confirmation."),
        }
        quarantined_active_path = [item for item in old_plan.get("active_path", []) if item not in plan["active_path"]] if isinstance(old_plan.get("active_path"), list) else []
        old_sources = load_json(root / "sources.json", {})
        source_list = upgraded_sources["sources"] if upgraded_sources is not None else (old_sources.get("sources", []) if isinstance(old_sources, dict) and isinstance(old_sources.get("sources"), list) else [])
        sources = {"schema_version": SCHEMA_VERSION, "updated_at": iso(), "sources": source_list}
        previous_curriculum = upgraded_concepts_document["curriculum"] if upgraded_concepts_document is not None else (old_concepts_document.get("curriculum") if isinstance(old_concepts_document, dict) else None)
        if not (
            isinstance(previous_curriculum, dict)
            and isinstance(previous_curriculum.get("sha256"), str)
            and isinstance(previous_curriculum.get("target_profiles"), dict)
            and isinstance(previous_curriculum.get("target_outcomes"), dict)
        ):
            previous_curriculum = None
        concepts = {"schema_version": SCHEMA_VERSION, "updated_at": iso(), "curriculum": previous_curriculum, "concepts": concepts_map}
        issues = (
            profile_errors(profile) + plan_errors(plan) + concepts_errors(concepts) + sources_errors(sources)
            + cross_document_errors(plan, concepts) + source_cross_document_errors(concepts, sources)
        )
        if issues:
            raise SystemExit("Migration normalization failed before commit:\n" + "\n".join(issues))
        normalized_events, event_issues = validate_event_sequence(list(enumerate(events, 1)))
        if event_issues:
            raise SystemExit("Migration event normalization failed before commit:\n" + "\n".join(event_issues))
        events = normalized_events
        sessions, session_issues = read_sessions(root) if (root / "sessions.jsonl").exists() else ([], [])
        if session_issues:
            raise SystemExit("Migration session validation failed before commit:\n" + "\n".join(session_issues))
        ensure_privacy_file(root)
        report = {
            "report_schema_version": 1, "migrated_at": iso(), "from_schema": old_schema, "to_schema": SCHEMA_VERSION,
            "backup": str(backup), "events": len(events), "concepts": len(concepts_map),
            "unknown_support_events": sum(event["support"] == "unknown" for event in events),
            "quarantined_active_path": quarantined_active_path,
            "warning": "Uncertain legacy support cannot certify mastery; confirm scope and collect fresh evidence.",
        }
        mastery, reviews = derive(events, concepts, profile["created_at"])
        commit_files(root, {
            "profile.json": profile, "plan.json": plan, "concepts.json": concepts, "sources.json": sources,
            "evidence.jsonl": "".join(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in events),
            "sessions.jsonl": "".join(json.dumps(session, ensure_ascii=False, sort_keys=True) + "\n" for session in sessions),
            "mastery.json": mastery, "reviews.json": reviews, "migration-report.json": report,
        })
        register_workspace(workspace, profile["workspace_id"])
    print(json.dumps({"ok": True, "workspace": str(workspace), **report}, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transparent, event-sourced local state for Mastery Coach")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Initialize or repair schema-v4 learner state")
    init.add_argument("--workspace", default=".")
    init.add_argument("--goal", required=True)
    init.add_argument("--proof")
    init.add_argument("--hours-per-week", type=float)
    init.add_argument("--session-minutes", type=int)
    init.add_argument("--deadline")
    init.add_argument("--curriculum", help="Curriculum JSON path or built-in ID ml-ai-llm")
    init.add_argument("--target-profile", action="append", help="Confirmed curriculum target profile; repeat to combine profiles")
    init.add_argument("--additional-targets", help="Comma-separated explicit goal concepts")
    init.add_argument("--enrichment-targets", help="Comma-separated optional enrichment concepts")
    init.add_argument("--scope-reason", help="Why this learning boundary was selected")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)
    migrate = sub.add_parser("migrate", help="Back up and migrate schema-v1/v2/v3 state to v4")
    migrate.add_argument("--workspace", required=True)
    migrate.add_argument("--backup")
    migrate.set_defaults(func=cmd_migrate)
    concept = sub.add_parser("concept-add", help="Add or correct an explicit concept definition")
    concept.add_argument("--workspace")
    concept.add_argument("--id", required=True)
    concept.add_argument("--title")
    concept.add_argument("--outcome")
    concept.add_argument("--required", required=True)
    concept.add_argument("--prerequisites")
    concept.add_argument("--replace", action="store_true")
    concept.set_defaults(func=cmd_concept_add)
    record = sub.add_parser("record", help="Append idempotent evidence and rebuild derived mastery")
    record.add_argument("--workspace")
    record.add_argument("--event-id")
    record.add_argument("--concept", required=True)
    record.add_argument("--title")
    record.add_argument("--outcome")
    record.add_argument("--kind", required=True, choices=sorted(KINDS))
    record.add_argument("--score", required=True, type=float)
    record.add_argument("--difficulty", type=int, default=3)
    record.add_argument("--hints", type=int, default=0)
    record.add_argument("--assisted", action="store_true")
    record.add_argument("--delayed", action="store_true")
    record.add_argument("--occurred-at")
    record.add_argument("--dimensions")
    record.add_argument("--required", help="Only for the first record of a custom concept")
    record.add_argument("--notes")
    record.set_defaults(func=cmd_record)
    rebuild = sub.add_parser("rebuild")
    rebuild.add_argument("--workspace")
    rebuild.set_defaults(func=cmd_rebuild)
    status = sub.add_parser("status")
    status.add_argument("--workspace")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    due = sub.add_parser("due")
    due.add_argument("--workspace")
    due.add_argument("--within-days", type=int, default=0)
    due.add_argument("--include-nonrequired", action="store_true")
    due.add_argument("--json", action="store_true")
    due.set_defaults(func=cmd_due)
    validate = sub.add_parser("validate")
    validate.add_argument("--workspace")
    validate.set_defaults(func=cmd_validate)
    locate = sub.add_parser("locate")
    locate.add_argument("--goal")
    locate.set_defaults(func=cmd_locate)
    set_value = sub.add_parser("set")
    set_value.add_argument("--workspace")
    set_value.add_argument("--target", required=True, choices=["profile", "plan"])
    set_value.add_argument("--field", required=True)
    set_value.add_argument("--value", required=True)
    set_value.set_defaults(func=cmd_set)
    scope_apply = sub.add_parser("scope-apply", help="Confirm a target profile and compute its prerequisite-closed learning boundary")
    scope_apply.add_argument("--workspace")
    scope_apply.add_argument("--target-profile", action="append")
    scope_apply.add_argument("--additional-targets")
    scope_apply.add_argument("--enrichment-targets")
    scope_apply.add_argument("--reason", required=True)
    scope_apply.set_defaults(func=cmd_scope_apply)
    scope_status = sub.add_parser("scope-status", help="Show the derived required and enrichment scope")
    scope_status.add_argument("--workspace")
    scope_status.set_defaults(func=cmd_scope_status)
    source = sub.add_parser("source-add")
    source.add_argument("--workspace")
    for field in ["id", "title", "organization", "url", "type", "authority", "version-or-date", "license-reuse", "concepts", "known-gaps"]:
        source.add_argument(f"--{field}", required=True)
    source.add_argument("--checked-at")
    source.add_argument("--replace", action="store_true")
    source.set_defaults(func=cmd_source_add)
    session = sub.add_parser("session-close")
    session.add_argument("--workspace")
    session.add_argument("--session-id", required=True)
    session.add_argument("--demonstrated", required=True)
    session.add_argument("--unresolved", required=True)
    session.add_argument("--next-action", required=True)
    session.add_argument("--next-review")
    session.add_argument("--notes")
    session.set_defaults(func=cmd_session_close)
    export = sub.add_parser("export")
    export.add_argument("--workspace")
    export.add_argument("--output", required=True)
    export.set_defaults(func=cmd_export)
    delete = sub.add_parser("delete")
    delete.add_argument("--workspace")
    delete.add_argument("--backup")
    delete.add_argument("--confirm", required=True)
    delete.set_defaults(func=cmd_delete)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
