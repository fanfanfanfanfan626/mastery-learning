#!/usr/bin/env python3
"""Audit curriculum identity, coverage, sources, and prerequisite integrity."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_DIMENSIONS = {"recall", "conceptual", "application", "debugging", "transfer", "creation"}
SOURCE_FIELDS = {
    "id", "title", "organization", "url", "type", "authority", "version_or_date",
    "license_reuse", "concepts", "known_gaps", "checked_at",
}
FAST_MOVING_SOURCE_TYPES = {"official-docs", "official-examples"}
FAST_MOVING_MAX_AGE_DAYS = 365
GENERAL_SOURCE_WARNING_AGE_DAYS = 730


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def audit(path: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"ok": False, "file": str(path), "errors": [f"invalid curriculum JSON: {error}"], "warnings": []}
    if not isinstance(data, dict):
        return {"ok": False, "file": str(path), "errors": ["curriculum root must be an object"], "warnings": []}
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not nonempty(data.get("id")) or not ID_PATTERN.fullmatch(data.get("id", "")):
        errors.append("curriculum id must be lowercase hyphen-case")
    for field in ["version", "title", "description"]:
        if not nonempty(data.get(field)):
            errors.append(f"curriculum {field} must be non-empty")
    scope = data.get("scope")
    if not isinstance(scope, dict) or not all(isinstance(scope.get(field), list) and scope[field] for field in ["included", "excluded"]):
        errors.append("scope must declare non-empty included and excluded arrays")

    concepts = data.get("concepts")
    if not isinstance(concepts, list) or not concepts:
        concepts = []
        errors.append("concepts must be a non-empty array")
    sources_list = data.get("sources")
    if not isinstance(sources_list, list) or not sources_list:
        sources_list = []
        errors.append("sources must be a non-empty array")

    source_ids = [item.get("id") for item in sources_list if isinstance(item, dict)]
    duplicate_sources = sorted(key for key, count in Counter(source_ids).items() if key and count > 1)
    if duplicate_sources:
        errors.append(f"duplicate source IDs: {', '.join(duplicate_sources)}")
    source_map = {item.get("id"): item for item in sources_list if isinstance(item, dict) and item.get("id")}
    for index, source in enumerate(sources_list):
        if not isinstance(source, dict):
            errors.append(f"source {index}: must be an object")
            continue
        label = source.get("id") or f"index {index}"
        missing = sorted(field for field in SOURCE_FIELDS if field not in source)
        if missing:
            errors.append(f"source {label}: missing fields {missing}")
        if not nonempty(source.get("id")) or not ID_PATTERN.fullmatch(source.get("id", "")):
            errors.append(f"source {label}: invalid id")
        for field in ["title", "organization", "type", "authority", "version_or_date", "license_reuse", "known_gaps"]:
            if not nonempty(source.get(field)):
                errors.append(f"source {label}: {field} must be non-empty")
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"source {label}: canonical URL must be valid HTTPS")
        checked = None
        try:
            checked = date.fromisoformat(source.get("checked_at", ""))
            if checked > date.today():
                errors.append(f"source {label}: checked_at cannot be in the future")
        except (TypeError, ValueError):
            errors.append(f"source {label}: checked_at must be YYYY-MM-DD")
        if checked is not None:
            age_days = (date.today() - checked).days
            if source.get("type") in FAST_MOVING_SOURCE_TYPES and age_days > FAST_MOVING_MAX_AGE_DAYS:
                errors.append(f"source {label}: fast-moving source check is stale ({age_days} days)")
            elif age_days > GENERAL_SOURCE_WARNING_AGE_DAYS:
                warnings.append(f"source {label}: source check is old ({age_days} days); re-verify before release")
        declared_concepts = source.get("concepts")
        if not isinstance(declared_concepts, list) or not declared_concepts or any(not nonempty(item) for item in declared_concepts):
            errors.append(f"source {label}: concepts must be a non-empty string array")

    ids = [item.get("id") for item in concepts if isinstance(item, dict)]
    known = {item for item in ids if isinstance(item, str)}
    duplicates = sorted(key for key, count in Counter(ids).items() if key and count > 1)
    if duplicates:
        errors.append(f"duplicate concept IDs: {', '.join(duplicates)}")
    graph: dict[str, list[str]] = defaultdict(list)
    referenced_by_source: dict[str, set[str]] = defaultdict(set)
    modules: set[str] = set()
    concept_modules: dict[str, str] = {}
    for index, item in enumerate(concepts):
        if not isinstance(item, dict):
            errors.append(f"concept {index}: must be an object")
            continue
        concept_id = item.get("id")
        if not nonempty(concept_id) or not ID_PATTERN.fullmatch(concept_id):
            errors.append(f"concept {index}: invalid id")
            continue
        module = item.get("module")
        outcome = item.get("outcome")
        if not nonempty(module) or not ID_PATTERN.fullmatch(module):
            errors.append(f"{concept_id}: invalid module")
        else:
            modules.add(module)
            concept_modules[concept_id] = module
        if not nonempty(outcome) or len(outcome.strip()) < 12:
            errors.append(f"{concept_id}: outcome must be observable and at least 12 characters")
        prerequisites = item.get("prerequisites")
        if not isinstance(prerequisites, list) or len(prerequisites) != len(set(prerequisites)):
            errors.append(f"{concept_id}: prerequisites must be a unique array")
            prerequisites = []
        for prerequisite in prerequisites:
            if prerequisite == concept_id:
                errors.append(f"{concept_id}: cannot depend on itself")
            elif prerequisite not in known:
                errors.append(f"{concept_id}: missing prerequisite {prerequisite}")
            graph[concept_id].append(prerequisite)
        required = item.get("required_dimensions")
        if not isinstance(required, list) or not required or len(required) != len(set(required)):
            errors.append(f"{concept_id}: required_dimensions must be a non-empty unique array")
            required = []
        invalid_dimensions = set(required) - ALLOWED_DIMENSIONS
        if invalid_dimensions:
            errors.append(f"{concept_id}: invalid dimensions {sorted(invalid_dimensions)}")
        item_sources = item.get("sources")
        if not isinstance(item_sources, list) or not item_sources or len(item_sources) != len(set(item_sources)):
            errors.append(f"{concept_id}: sources must be a non-empty unique array")
            item_sources = []
        unknown_sources = set(item_sources) - set(source_map)
        if unknown_sources:
            errors.append(f"{concept_id}: unknown sources {sorted(unknown_sources)}")
        for source_id in item_sources:
            referenced_by_source[source_id].add(concept_id)
        if "optional" in item and not isinstance(item["optional"], bool):
            errors.append(f"{concept_id}: optional must be boolean")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            errors.append("cycle: " + " -> ".join(trail + [node]))
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            if dependency in known:
                visit(dependency, trail + [node])
        visiting.remove(node)
        visited.add(node)

    for concept_id in sorted(known):
        visit(concept_id, [])

    profiles = data.get("target_profiles")
    outcomes = data.get("target_outcomes")
    if not isinstance(profiles, dict) or not profiles:
        profiles = {}
        errors.append("target_profiles must be a non-empty object")
    if not isinstance(outcomes, dict) or set(outcomes) != set(profiles):
        outcomes = outcomes if isinstance(outcomes, dict) else {}
        errors.append("target_outcomes must have exactly the same profile IDs as target_profiles")
    covered_concepts: set[str] = set()
    for profile, profile_endpoints in profiles.items():
        if not ID_PATTERN.fullmatch(profile):
            errors.append(f"invalid target profile ID: {profile}")
        if not isinstance(profile_endpoints, list) or not profile_endpoints or len(profile_endpoints) != len(set(profile_endpoints)):
            errors.append(f"profile {profile}: endpoints must be a non-empty unique array")
            continue
        missing = set(profile_endpoints) - known
        if missing:
            errors.append(f"profile {profile}: unknown endpoint concepts {sorted(missing)}")
        closure: set[str] = set()
        pending = [item for item in profile_endpoints if item in known]
        while pending:
            concept_id = pending.pop()
            if concept_id in closure:
                continue
            closure.add(concept_id)
            pending.extend(item for item in graph[concept_id] if item in known)
        optional_in_required_closure = sorted(
            concept_id for concept_id in closure
            if next((entry.get("optional", False) for entry in concepts if isinstance(entry, dict) and entry.get("id") == concept_id), False)
        )
        if optional_in_required_closure:
            errors.append(f"profile {profile}: optional concepts occur in its required prerequisite closure {optional_in_required_closure}")
        covered_concepts.update(closure)
        profile_outcomes = outcomes.get(profile)
        if not isinstance(profile_outcomes, list) or not profile_outcomes or any(not nonempty(item) or len(item.strip()) < 12 for item in profile_outcomes):
            errors.append(f"profile {profile}: target outcomes must be a non-empty array of observable statements")
    required_concepts = {item.get("id") for item in concepts if isinstance(item, dict) and item.get("id") and not item.get("optional", False)}
    orphan_concepts = required_concepts - covered_concepts
    if orphan_concepts:
        errors.append(f"required concepts not covered by any target profile closure: {sorted(orphan_concepts)}")
    covered_modules = {concept_modules[item] for item in covered_concepts if item in concept_modules}
    orphan_modules = modules - covered_modules
    if orphan_modules:
        errors.append(f"modules not used by any target profile: {sorted(orphan_modules)}")

    for source_id, source in source_map.items():
        declared = set(source.get("concepts", [])) if isinstance(source.get("concepts"), list) else set()
        actual = referenced_by_source.get(source_id, set())
        missing_declarations = actual - declared
        unknown_declarations = declared - known
        if missing_declarations:
            errors.append(f"source {source_id}: concepts metadata omits {sorted(missing_declarations)}")
        if unknown_declarations:
            errors.append(f"source {source_id}: concepts metadata names unknown concepts {sorted(unknown_declarations)}")
        if not actual:
            warnings.append(f"source {source_id} is not referenced by any concept")

    if not any(item.get("optional") for item in concepts if isinstance(item, dict)):
        warnings.append("no optional enrichment is identified")
    return {
        "ok": not errors,
        "file": str(path),
        "concept_count": len(concepts),
        "module_count": len(modules),
        "source_count": len(source_map),
        "profile_count": len(profiles),
        "modules": sorted(modules),
        "errors": errors,
        "warnings": warnings,
        "limitations": [
            "This offline audit validates structure and recorded check dates; it does not prove URL availability, license terms, or factual accuracy.",
        ],
    }


def main() -> None:
    default = Path(__file__).resolve().parent.parent / "assets" / "curricula" / "ml-ai-llm.json"
    parser = argparse.ArgumentParser(description="Audit a mastery curriculum JSON file")
    parser.add_argument("path", nargs="?", type=Path, default=default)
    args = parser.parse_args()
    result = audit(args.path.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
