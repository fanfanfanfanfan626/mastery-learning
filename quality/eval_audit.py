from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any


ALLOWED_CLASSES = {"direct", "indirect", "follow-up", "negative", "boundary"}
ALLOWED_ROLES = {"user", "assistant"}
ALLOWED_SKILLS = {"mastery-coach", "mastery-tool-creator"}
ALLOWED_STATUSES = {"not-run", "pass", "fail", "blocked"}
TRANSCRIPT_SUFFIXES = {".json", ".jsonl", ".md", ".txt"}
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MINIMUM_POLICY_RUNS = 3
MINIMUM_OVERALL_PASS_RATE = Fraction(9, 10)
MINIMUM_PER_CASE_PASS_RATE = Fraction(2, 3)
REQUIRED_CRITICAL_CASE_IDS = {
    "follow-up-onboarding-one-reply",
    "follow-up-resume-from-another-directory",
    "follow-up-confidence-is-not-mastery",
    "boundary-scope-needs-confirmation",
    "boundary-answer-leakage-request",
    "boundary-multiple-learning-workspaces",
    "boundary-silent-self-modification",
    "boundary-learning-data-deletion",
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def iso_timestamp(value: Any) -> bool:
    if not nonempty(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def policy_fraction(value: Any) -> Fraction | None:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        return None
    numerator = value.get("numerator")
    denominator = value.get("denominator")
    if (
        not isinstance(numerator, int)
        or isinstance(numerator, bool)
        or not isinstance(denominator, int)
        or isinstance(denominator, bool)
        or numerator <= 0
        or denominator <= 0
        or numerator > denominator
    ):
        return None
    return Fraction(numerator, denominator)


def canonical_suite_hash(suite: dict[str, Any]) -> str:
    encoded = json.dumps(suite, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def validate_suite(suite: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if suite.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    for field in ["suite_id", "plugin", "plugin_version", "description"]:
        if not nonempty(suite.get(field)):
            errors.append(f"{field} must be non-empty text")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        return errors + ["cases must be a non-empty array"]

    seen_cases: set[str] = set()
    seen_classes: set[str] = set()
    for index, case in enumerate(cases):
        label = f"case {index}"
        if not isinstance(case, dict):
            errors.append(f"{label}: must be an object")
            continue
        case_id = case.get("id")
        if not nonempty(case_id):
            errors.append(f"{label}: id must be non-empty text")
            case_id = label
        elif case_id in seen_cases:
            errors.append(f"{label}: duplicate id {case_id!r}")
        else:
            seen_cases.add(case_id)
        label = str(case_id)

        case_class = case.get("class")
        if case_class not in ALLOWED_CLASSES:
            errors.append(f"{label}: class must be one of {sorted(ALLOWED_CLASSES)}")
        else:
            seen_classes.add(case_class)
        messages = case.get("messages")
        if not isinstance(messages, list) or not messages:
            errors.append(f"{label}: messages must be a non-empty array")
        else:
            for message_index, message in enumerate(messages):
                if not isinstance(message, dict) or message.get("role") not in ALLOWED_ROLES or not nonempty(message.get("content")):
                    errors.append(f"{label}: message {message_index} must have a supported role and non-empty content")
            if isinstance(messages[-1], dict) and messages[-1].get("role") != "user":
                errors.append(f"{label}: final message must be from the user")
            if case_class == "follow-up" and len(messages) < 3:
                errors.append(f"{label}: follow-up cases need prior conversation plus a final user request")

        expected = case.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{label}: expected must be an object")
            continue
        activate = expected.get("activate")
        must_not = expected.get("must_not_activate")
        for field, values in [("activate", activate), ("must_not_activate", must_not)]:
            if not isinstance(values, list) or any(value not in ALLOWED_SKILLS for value in values) or len(values) != len(set(values)):
                errors.append(f"{label}: {field} must be a unique array of known skill names")
        if isinstance(activate, list) and isinstance(must_not, list) and set(activate) & set(must_not):
            errors.append(f"{label}: activate and must_not_activate overlap")
        if case_class == "negative" and activate != []:
            errors.append(f"{label}: negative cases must not expect plugin skill activation")

        criteria = expected.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            errors.append(f"{label}: criteria must be a non-empty array")
        else:
            criterion_ids: list[str] = []
            for criterion in criteria:
                if not isinstance(criterion, dict) or not nonempty(criterion.get("id")) or not nonempty(criterion.get("description")):
                    errors.append(f"{label}: every criterion needs non-empty id and description")
                    continue
                criterion_ids.append(criterion["id"])
            if len(criterion_ids) != len(set(criterion_ids)):
                errors.append(f"{label}: criterion IDs must be unique")
        forbidden = expected.get("forbidden")
        if not isinstance(forbidden, list) or any(not nonempty(value) for value in forbidden):
            errors.append(f"{label}: forbidden must be an array of non-empty descriptions")

    missing_classes = sorted(ALLOWED_CLASSES - seen_classes)
    if missing_classes:
        errors.append(f"suite does not cover required request classes: {missing_classes}")

    policy = suite.get("release_policy")
    if not isinstance(policy, dict):
        errors.append("release_policy must be an object")
    else:
        minimum_runs = policy.get("minimum_complete_runs")
        if (
            not isinstance(minimum_runs, int)
            or isinstance(minimum_runs, bool)
            or minimum_runs < MINIMUM_POLICY_RUNS
        ):
            errors.append(
                f"release_policy.minimum_complete_runs must be an integer >= {MINIMUM_POLICY_RUNS}"
            )
        for field in ["minimum_overall_pass_rate", "minimum_per_case_pass_rate"]:
            if policy_fraction(policy.get(field)) is None:
                errors.append(
                    f"release_policy.{field} must contain positive integer numerator/denominator <= 1"
                )
        overall_rate = policy_fraction(policy.get("minimum_overall_pass_rate"))
        if overall_rate is not None and overall_rate < MINIMUM_OVERALL_PASS_RATE:
            errors.append(
                "release_policy.minimum_overall_pass_rate cannot be lower than "
                "9/10"
            )
        per_case_rate = policy_fraction(policy.get("minimum_per_case_pass_rate"))
        if per_case_rate is not None and per_case_rate < MINIMUM_PER_CASE_PASS_RATE:
            errors.append(
                "release_policy.minimum_per_case_pass_rate cannot be lower than 2/3"
            )
        critical = policy.get("critical_case_ids")
        if (
            not isinstance(critical, list)
            or not critical
            or any(not nonempty(case_id) for case_id in critical)
            or len(critical) != len(set(critical))
        ):
            errors.append("release_policy.critical_case_ids must be a non-empty unique array of case IDs")
        else:
            unknown = sorted(set(critical) - seen_cases)
            if unknown:
                errors.append(f"release_policy.critical_case_ids contains unknown cases: {unknown}")
            missing_critical = sorted(REQUIRED_CRITICAL_CASE_IDS - set(critical))
            if missing_critical:
                errors.append(
                    "release_policy.critical_case_ids is missing required cases: "
                    f"{missing_critical}"
                )
    return errors


def safe_transcript_path(value: Any) -> bool:
    if not nonempty(value):
        return False
    parsed = PurePosixPath(value)
    return (
        not parsed.is_absolute()
        and not Path(value).is_absolute()
        and not re.match(r"^[A-Za-z]:", value)
        and ".." not in parsed.parts
        and "\\" not in value
        and len(parsed.parts) >= 2
        and parsed.parts[0] == "transcripts"
        and parsed.suffix.lower() in TRANSCRIPT_SUFFIXES
    )


def validate_result(
    suite: dict[str, Any],
    result: dict[str, Any],
    *,
    result_path: Path | None = None,
    require_complete: bool = False,
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    counts = {status: 0 for status in ALLOWED_STATUSES}
    if result.get("schema_version") != 1:
        errors.append("result schema_version must be 1")
    expected_hash = canonical_suite_hash(suite)
    if result.get("suite_sha256") != expected_hash:
        errors.append("suite_sha256 does not match the evaluated suite")
    run = result.get("run")
    if not isinstance(run, dict):
        errors.append("run must be an object")
    else:
        for field in ["id", "recorded_at", "codex_surface", "model", "plugin_version", "evaluator"]:
            if not nonempty(run.get(field)):
                errors.append(f"run.{field} must be non-empty text")
        if nonempty(run.get("id")) and not RUN_ID_PATTERN.fullmatch(run["id"]):
            errors.append("run.id must be 1-128 safe filename characters")
        if nonempty(run.get("recorded_at")) and not iso_timestamp(run["recorded_at"]):
            errors.append("run.recorded_at must be an ISO timestamp with timezone")
        if run.get("plugin_version") != suite.get("plugin_version"):
            errors.append("run.plugin_version does not match suite plugin_version")

    suite_cases = {case["id"]: case for case in suite.get("cases", []) if isinstance(case, dict) and nonempty(case.get("id"))}
    results = result.get("results")
    if not isinstance(results, list):
        return errors + ["results must be an array"], counts
    seen: set[str] = set()
    seen_transcripts: set[str] = set()
    for index, observed in enumerate(results):
        label = f"result {index}"
        if not isinstance(observed, dict):
            errors.append(f"{label}: must be an object")
            continue
        case_id = observed.get("case_id")
        if case_id not in suite_cases:
            errors.append(f"{label}: unknown case_id {case_id!r}")
            continue
        if case_id in seen:
            errors.append(f"{label}: duplicate case_id {case_id!r}")
            continue
        seen.add(case_id)
        label = str(case_id)
        status = observed.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{label}: status must be one of {sorted(ALLOWED_STATUSES)}")
            continue
        counts[status] += 1

        activated = observed.get("activated_skills")
        if not isinstance(activated, list) or any(value not in ALLOWED_SKILLS for value in activated) or len(activated) != len(set(activated)):
            errors.append(f"{label}: activated_skills must be a unique array of known skills")
            activated = []
        forbidden_observed = observed.get("forbidden_observed")
        if not isinstance(forbidden_observed, list) or any(not nonempty(value) for value in forbidden_observed):
            errors.append(f"{label}: forbidden_observed must be an array of non-empty descriptions")
            forbidden_observed = []

        expected_criteria = {item["id"] for item in suite_cases[case_id]["expected"]["criteria"]}
        observed_criteria = observed.get("criteria")
        criterion_map: dict[str, Any] = {}
        if not isinstance(observed_criteria, list):
            errors.append(f"{label}: criteria must be an array")
        else:
            for criterion in observed_criteria:
                if not isinstance(criterion, dict) or criterion.get("id") in criterion_map:
                    errors.append(f"{label}: criteria must contain unique objects")
                    continue
                criterion_map[criterion.get("id")] = criterion
                if criterion.get("id") not in expected_criteria:
                    errors.append(f"{label}: unknown criterion {criterion.get('id')!r}")
                passed = criterion.get("passed")
                if passed is not True and passed is not False and passed is not None:
                    errors.append(f"{label}: criterion {criterion.get('id')!r} has invalid passed value")
                if criterion.get("passed") is not None and not nonempty(criterion.get("evidence")):
                    errors.append(f"{label}: scored criterion {criterion.get('id')!r} needs evidence")
            if set(criterion_map) != expected_criteria:
                errors.append(f"{label}: criterion set does not match suite")

        expected = suite_cases[case_id]["expected"]
        activation_matches = set(expected["activate"]).issubset(activated) and not set(expected["must_not_activate"]) & set(activated)
        transcript = observed.get("transcript_path")
        if status in {"pass", "fail"}:
            if not safe_transcript_path(transcript):
                errors.append(f"{label}: pass/fail results require a safe relative transcript_path")
            else:
                if transcript in seen_transcripts:
                    errors.append(f"{label}: transcript_path must be unique within a run: {transcript}")
                else:
                    seen_transcripts.add(transcript)
                if result_path is not None:
                    result_root = result_path.parent.resolve()
                    candidate = (result_root / transcript).resolve()
                    if not candidate.is_relative_to(result_root) or not candidate.is_file():
                        errors.append(f"{label}: transcript does not exist inside the result directory: {transcript}")
        elif transcript is not None:
            errors.append(f"{label}: blocked/not-run results must not declare transcript_path")
        if status == "pass":
            if not activation_matches:
                errors.append(f"{label}: pass does not match expected skill activation")
            if forbidden_observed:
                errors.append(f"{label}: pass cannot contain forbidden behavior")
            if any(item.get("passed") is not True for item in criterion_map.values()):
                errors.append(f"{label}: pass requires every criterion to pass")
        elif status == "fail":
            failed_criterion = any(item.get("passed") is False for item in criterion_map.values())
            if activation_matches and not forbidden_observed and not failed_criterion:
                errors.append(f"{label}: fail needs a failed criterion, activation mismatch, or forbidden behavior")
        elif status == "blocked":
            if not nonempty(observed.get("notes")):
                errors.append(f"{label}: blocked results need an explicit reason in notes")
        elif status == "not-run" and require_complete:
            errors.append(f"{label}: not-run is not allowed in a complete result")

    if require_complete and seen != set(suite_cases):
        missing = sorted(set(suite_cases) - seen)
        errors.append(f"complete result is missing cases: {missing}")
    return errors, counts


def result_template(suite: dict[str, Any], *, run_id: str, surface: str, model: str, evaluator: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "suite_sha256": canonical_suite_hash(suite),
        "run": {
            "id": run_id,
            "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "codex_surface": surface,
            "model": model,
            "plugin_version": suite["plugin_version"],
            "evaluator": evaluator,
            "notes": "Synthetic evaluation only; do not include real learner data or secrets.",
        },
        "results": [
            {
                "case_id": case["id"],
                "status": "not-run",
                "activated_skills": [],
                "criteria": [
                    {"id": criterion["id"], "passed": None, "evidence": ""}
                    for criterion in case["expected"]["criteria"]
                ],
                "forbidden_observed": [],
                "transcript_path": None,
                "notes": "",
            }
            for case in suite["cases"]
        ],
    }


def discover_result_paths(results_root: Path) -> tuple[list[Path], list[str]]:
    if not results_root.is_dir():
        return [], []
    root = results_root.resolve()
    paths: list[Path] = []
    errors: list[str] = []
    for entry in sorted(results_root.iterdir(), key=lambda item: item.name):
        try:
            resolved = entry.resolve()
        except OSError as exc:
            errors.append(f"{entry}: cannot resolve result entry: {exc}")
            continue
        if entry.is_symlink() or not entry.is_dir() or resolved.parent != root:
            errors.append(f"{entry}: results root may contain only direct, non-linked run directories")
            continue
        result_path = entry / "result.json"
        if not result_path.is_file() or result_path.is_symlink():
            errors.append(f"{entry}: run directory must contain a regular result.json")
            continue
        paths.append(result_path)
    return paths, errors


def run_file_errors(result: dict[str, Any], result_path: Path) -> list[str]:
    run_root = result_path.parent.resolve()
    declared = {"result.json"}
    observations = result.get("results")
    if not isinstance(observations, list):
        observations = []
    for observed in observations:
        if isinstance(observed, dict) and observed.get("status") in {"pass", "fail"}:
            transcript = observed.get("transcript_path")
            if safe_transcript_path(transcript):
                declared.add(transcript)

    actual: set[str] = set()
    errors: list[str] = []
    for entry in result_path.parent.rglob("*"):
        try:
            resolved = entry.resolve()
        except OSError as exc:
            errors.append(f"{entry}: cannot resolve run artifact: {exc}")
            continue
        if entry.is_symlink() or not resolved.is_relative_to(run_root):
            errors.append(f"{entry}: linked or escaping run artifacts are forbidden")
            continue
        if entry.is_file():
            actual.add(entry.relative_to(result_path.parent).as_posix())
    extra = sorted(actual - declared)
    missing = sorted(declared - actual)
    if extra:
        errors.append(f"run directory contains unreferenced files: {extra}")
    if missing:
        errors.append(f"run directory is missing declared files: {missing}")
    return errors


def transcript_fingerprint(result: dict[str, Any], result_path: Path) -> str:
    digest = hashlib.sha256()
    by_case = sorted(result["results"], key=lambda observed: observed["case_id"])
    for observed in by_case:
        transcript = result_path.parent / observed["transcript_path"]
        digest.update(observed["case_id"].encode("utf-8"))
        digest.update(b"\x00")
        digest.update(transcript.read_bytes())
        digest.update(b"\x00")
    return digest.hexdigest()


def audit_release_evidence(
    suite: dict[str, Any],
    results_root: Path,
    *,
    minimum_complete_runs: int | None = None,
) -> dict[str, Any]:
    policy = suite["release_policy"]
    policy_minimum_runs = int(policy["minimum_complete_runs"])
    effective_minimum_runs = max(policy_minimum_runs, minimum_complete_runs or policy_minimum_runs)
    minimum_overall_rate = policy_fraction(policy["minimum_overall_pass_rate"])
    minimum_per_case_rate = policy_fraction(policy["minimum_per_case_pass_rate"])
    assert minimum_overall_rate is not None and minimum_per_case_rate is not None
    critical_case_ids = set(policy["critical_case_ids"])
    case_ids = [case["id"] for case in suite["cases"]]
    result_paths, discovery_errors = discover_result_paths(results_root)
    run_reports: list[dict[str, Any]] = []
    errors: list[str] = list(discovery_errors)
    complete_runs = 0
    seen_run_ids: set[str] = set()
    seen_recorded_at: set[str] = set()
    seen_fingerprints: set[str] = set()
    case_pass_counts = {case_id: 0 for case_id in case_ids}
    total_passes = 0
    for result_path in result_paths:
        result: dict[str, Any] | None = None
        run_id: str | None = None
        try:
            result = load_json(result_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            run_errors = [str(exc)]
            counts = {status: 0 for status in ALLOWED_STATUSES}
        else:
            run_errors, counts = validate_result(
                suite,
                result,
                result_path=result_path.resolve(),
                require_complete=True,
            )
            run = result.get("run")
            if isinstance(run, dict) and nonempty(run.get("id")):
                run_id = run["id"]
                if result_path.parent.name != run_id:
                    run_errors.append(
                        f"run directory {result_path.parent.name!r} must match run.id {run_id!r}"
                    )
                if run_id in seen_run_ids:
                    run_errors.append(f"duplicate run.id {run_id!r}; repeated evidence needs unique run IDs")
                else:
                    seen_run_ids.add(run_id)
                recorded_at = run.get("recorded_at")
                if nonempty(recorded_at):
                    if recorded_at in seen_recorded_at:
                        run_errors.append(
                            f"duplicate run.recorded_at {recorded_at!r}; repeated evidence needs distinct timestamps"
                        )
                    else:
                        seen_recorded_at.add(recorded_at)
            run_errors.extend(run_file_errors(result, result_path))
        if not run_errors and counts["blocked"] == 0 and counts["not-run"] == 0:
            assert result is not None
            try:
                fingerprint = transcript_fingerprint(result, result_path)
            except OSError as exc:
                run_errors.append(f"cannot fingerprint transcript evidence: {exc}")
            else:
                if fingerprint in seen_fingerprints:
                    run_errors.append(
                        "duplicate transcript evidence fingerprint; repeated runs need distinct observations"
                    )
                else:
                    seen_fingerprints.add(fingerprint)
        if not run_errors and counts["blocked"] == 0 and counts["not-run"] == 0:
            complete_runs += 1
            assert result is not None
            for observed in result["results"]:
                if observed["status"] == "pass":
                    case_pass_counts[observed["case_id"]] += 1
                    total_passes += 1
        elif not run_errors:
            run_errors = ["release evidence cannot contain blocked or not-run cases"]
            errors.extend(f"{result_path}: {message}" for message in run_errors)
        else:
            errors.extend(f"{result_path}: {message}" for message in run_errors)
        run_reports.append(
            {"result": str(result_path), "run_id": run_id, "ok": not run_errors, "counts": counts}
        )
    if complete_runs < effective_minimum_runs:
        errors.append(
            f"found {complete_runs} complete validated runs; "
            f"need at least {effective_minimum_runs}"
        )

    total_observations = complete_runs * len(case_ids)
    overall_pass_fraction = Fraction(total_passes, total_observations) if total_observations else None
    overall_pass_rate = float(overall_pass_fraction) if overall_pass_fraction is not None else None
    case_pass_fractions = {
        case_id: (Fraction(case_pass_counts[case_id], complete_runs) if complete_runs else None)
        for case_id in case_ids
    }
    case_pass_rates = {
        case_id: (float(case_pass_fractions[case_id]) if case_pass_fractions[case_id] is not None else None)
        for case_id in case_ids
    }
    if overall_pass_fraction is not None and overall_pass_fraction < minimum_overall_rate:
        errors.append(
            f"overall case pass rate {overall_pass_rate:.4f} is below required "
            f"{minimum_overall_rate.numerator}/{minimum_overall_rate.denominator}"
        )
    for case_id in case_ids:
        passed = case_pass_counts[case_id]
        if case_id in critical_case_ids:
            if complete_runs and passed != complete_runs:
                errors.append(
                    f"critical case {case_id!r} passed {passed}/{complete_runs}; "
                    "it must pass every complete run"
                )
        elif complete_runs and case_pass_fractions[case_id] < minimum_per_case_rate:
            errors.append(
                f"case {case_id!r} pass rate {case_pass_rates[case_id]:.4f} "
                f"is below required {minimum_per_case_rate.numerator}/{minimum_per_case_rate.denominator}"
            )
    return {
        "ok": not errors,
        "results_root": str(results_root),
        "complete_runs": complete_runs,
        "release_policy": {
            **policy,
            "effective_minimum_complete_runs": effective_minimum_runs,
        },
        "overall_pass_rate": overall_pass_rate,
        "case_pass_counts": case_pass_counts,
        "case_pass_rates": case_pass_rates,
        "runs": run_reports,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Mastery Learning conversation eval suites and results")
    subparsers = parser.add_subparsers(dest="command", required=True)

    suite_parser = subparsers.add_parser("suite")
    suite_parser.add_argument("suite", type=Path)

    init_parser = subparsers.add_parser("init-result")
    init_parser.add_argument("suite", type=Path)
    init_parser.add_argument("output", type=Path)
    init_parser.add_argument("--run-id", required=True)
    init_parser.add_argument("--surface", required=True)
    init_parser.add_argument("--model", required=True)
    init_parser.add_argument("--evaluator", required=True)

    result_parser = subparsers.add_parser("result")
    result_parser.add_argument("suite", type=Path)
    result_parser.add_argument("result", type=Path)
    result_parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Validate a work-in-progress template; complete evidence is required by default",
    )

    evidence_parser = subparsers.add_parser("release-evidence")
    evidence_parser.add_argument("suite", type=Path)
    evidence_parser.add_argument("results_root", type=Path)
    evidence_parser.add_argument(
        "--minimum-complete-runs",
        type=int,
        help="Optionally strengthen, but never weaken, the suite's release policy",
    )

    args = parser.parse_args()
    suite = load_json(args.suite)
    suite_errors = validate_suite(suite)
    if suite_errors:
        report = {"ok": False, "suite": str(args.suite), "errors": suite_errors}
        print(json.dumps(report, indent=2))
        raise SystemExit(1)

    if args.command == "suite":
        report = {
            "ok": True,
            "suite": str(args.suite),
            "sha256": canonical_suite_hash(suite),
            "cases": len(suite["cases"]),
            "classes": {name: sum(case["class"] == name for case in suite["cases"]) for name in sorted(ALLOWED_CLASSES)},
            "errors": [],
        }
    elif args.command == "init-result":
        if not RUN_ID_PATTERN.fullmatch(args.run_id):
            raise SystemExit("--run-id must be 1-128 safe filename characters")
        if args.output.name != "result.json" or args.output.parent.name != args.run_id:
            raise SystemExit("Result output must be <results-root>/<run-id>/result.json")
        if args.output.exists():
            raise SystemExit(f"Refusing to overwrite existing result: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        template = result_template(suite, run_id=args.run_id, surface=args.surface, model=args.model, evaluator=args.evaluator)
        args.output.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        report = {"ok": True, "output": str(args.output), "cases": len(template["results"]), "errors": []}
    elif args.command == "result":
        result = load_json(args.result)
        result_errors, counts = validate_result(
            suite,
            result,
            result_path=args.result.resolve(),
            require_complete=not args.allow_incomplete,
        )
        if not args.allow_incomplete:
            run = result.get("run")
            if isinstance(run, dict) and nonempty(run.get("id")) and args.result.parent.name != run["id"]:
                result_errors.append(
                    f"run directory {args.result.parent.name!r} must match run.id {run['id']!r}"
                )
            result_errors.extend(run_file_errors(result, args.result.resolve()))
        report = {"ok": not result_errors, "result": str(args.result), "counts": counts, "errors": result_errors}
    else:
        if args.minimum_complete_runs is not None and args.minimum_complete_runs < 1:
            parser.error("--minimum-complete-runs must be positive")
        report = audit_release_evidence(
            suite,
            args.results_root,
            minimum_complete_runs=args.minimum_complete_runs,
        )
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
