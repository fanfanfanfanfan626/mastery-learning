#!/usr/bin/env python3
"""Archive host-observed check/render results; never execute generated code."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from tool_common import (
    EXECUTION_BOUNDARIES,
    REPORT_OBSERVERS,
    atomic_json,
    require_current_validation,
    safe_tool_root,
    timestamp,
    tool_snapshot,
    update_catalog_entry,
)
from validate_tool import declared_check, validate_artifacts, validate_concept_registration, validate_manifest, validate_type

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CATALOG_SCHEMA_VERSION = 3
REPORT_SCHEMA_VERSION = 4


def load_output(path: Path) -> tuple[str, str]:
    if path.is_symlink() or not path.is_file():
        raise SystemExit("--observed-output-file must be a regular, non-symlink file")
    if path.stat().st_size > 1_000_000:
        raise SystemExit("--observed-output-file exceeds 1 MB")
    data = path.read_bytes()
    return data.decode("utf-8", errors="replace"), hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize a teaching tool from externally observed execution/render results")
    parser.add_argument("tool_dir", type=Path)
    parser.add_argument("--observer", choices=sorted(REPORT_OBSERVERS))
    parser.add_argument("--execution-boundary", choices=sorted(EXECUTION_BOUNDARIES))
    parser.add_argument("--sandboxed-by", choices=["codex-workspace-sandbox"], help=argparse.SUPPRESS)
    parser.add_argument("--review-notes", required=True)
    parser.add_argument("--observed-exit-code", type=int)
    parser.add_argument("--observed-output-file", type=Path)
    parser.add_argument("--inspection-result", choices=["passed", "failed"])
    parser.add_argument("--inspection-notes")
    args = parser.parse_args()
    if args.sandboxed_by:
        if args.observer or args.execution_boundary:
            raise SystemExit("Use either legacy --sandboxed-by or the portable --observer/--execution-boundary pair, not both")
        observer = "codex"
        execution_boundary = "host-sandbox"
    else:
        if not args.observer or not args.execution_boundary:
            raise SystemExit("Portable finalization requires --observer and --execution-boundary")
        observer = args.observer
        execution_boundary = args.execution_boundary
    if len(args.review_notes.strip()) < 20:
        raise SystemExit("--review-notes must describe the observed learner-facing behavior")

    root = safe_tool_root(args.tool_dir)
    manifest_path = root / "tool.json"
    try:
        manifest: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Cannot read tool manifest: {error}") from error
    errors: list[str] = []
    warnings: list[str] = []
    validate_manifest(manifest, errors)
    texts = validate_artifacts(root, manifest if isinstance(manifest, dict) else {}, errors, warnings)
    validate_type(root, manifest if isinstance(manifest, dict) else {}, texts, errors)
    registration = validate_concept_registration(root, manifest if isinstance(manifest, dict) else {}, errors, warnings)
    request = declared_check(root, manifest if isinstance(manifest, dict) else {}, errors)
    if errors:
        print(json.dumps({"ok": False, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    observed: dict[str, Any] | None = None
    if request:
        if args.observed_exit_code is None or args.observed_output_file is None:
            raise SystemExit("A declared check requires --observed-exit-code and --observed-output-file from the host execution run")
        if execution_boundary == "not-applicable":
            raise SystemExit("A declared executable check requires an explicit execution boundary")
        output, digest = load_output(args.observed_output_file.expanduser().resolve())
        if args.observed_exit_code != request["expected_exit_code"]:
            raise SystemExit(f"Observed check exited {args.observed_exit_code}, expected {request['expected_exit_code']}")
        marker = request.get("output_contains")
        if marker and marker not in output:
            raise SystemExit(f"Observed output is missing expected marker: {marker}")
        observed = {
            "command": request["command"], "exit_code": args.observed_exit_code,
            "output_sha256": digest, "output_tail": output[-2000:],
        }
    elif args.observed_exit_code is not None or args.observed_output_file is not None:
        raise SystemExit("Observed check arguments were supplied but the manifest declares no check")

    inspection = manifest["inspection"]
    if inspection["required"]:
        if args.inspection_result != "passed":
            raise SystemExit("Required rendering/accessibility inspection must be explicitly recorded as --inspection-result passed; a failed or missing inspection cannot be verified")
        if not args.inspection_notes or len(args.inspection_notes.strip()) < 20:
            raise SystemExit("This tool requires --inspection-notes describing rendered states/pages and accessibility checks")
    elif args.inspection_result is not None or args.inspection_notes is not None:
        raise SystemExit("Inspection arguments were supplied but the manifest declares no required inspection")
    snapshot = tool_snapshot(root)
    mastery_root = root.parent.parent
    if root.parent.name != "tools" or mastery_root.name != ".mastery":
        raise SystemExit("tool directory must be <workspace>/.mastery/tools/<tool-id>")
    require_current_validation(mastery_root / "tool-catalog.json", manifest["id"], root, snapshot["sha256"], CATALOG_SCHEMA_VERSION)
    manifest_sha256 = next(item["sha256"] for item in snapshot["files"] if item["path"] == "tool.json")
    report = {
        "schema_version": REPORT_SCHEMA_VERSION, "tool_id": manifest["id"], "tool_version": manifest["version"],
        "verified_at": timestamp(), "observer": observer, "execution_boundary": execution_boundary,
        "review_notes": args.review_notes.strip(),
        "check": observed,
        "inspection": {
            "required": bool(inspection["required"]),
            "result": "passed" if inspection["required"] else "not-required",
            "notes": args.inspection_notes.strip() if args.inspection_notes else None,
        },
        "concept_registration": registration, "manifest_sha256": manifest_sha256, "tool_snapshot": snapshot,
        "warning": "This report records host-observed behavior and the declared execution boundary; it is not an operating-system security attestation.",
    }
    report_path = mastery_root / "verification-reports" / f"{manifest['id']}.json"
    atomic_json(report_path, report)
    report_sha256 = hashlib.sha256(report_path.read_bytes()).hexdigest()
    update_catalog_entry(mastery_root / "tool-catalog.json", manifest["id"], root, {
        "status": "verified", "verified_at": report["verified_at"], "verification_report": str(report_path),
        "verification_report_sha256": report_sha256,
        "verified_tool_sha256": snapshot["sha256"], "current_tool_sha256": snapshot["sha256"],
    }, CATALOG_SCHEMA_VERSION, remove_keys=("stale_at", "stale_reason", "rejected_at", "validation_errors"))
    print(json.dumps({"ok": True, "status": "verified", "tool_dir": str(root), "report": str(report_path), "tool_snapshot": snapshot, "warnings": warnings}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
