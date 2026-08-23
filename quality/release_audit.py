from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "quality") not in sys.path:
    sys.path.insert(0, str(ROOT / "quality"))

from build_release import (  # noqa: E402
    PLUGIN_MANIFEST,
    canonical_release_bytes,
    release_files,
    safe_archive_name,
    verify_archive,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_executable() -> str | None:
    configured = os.environ.get("GIT_EXECUTABLE")
    if configured and Path(configured).is_file():
        return configured
    return shutil.which("git")


def git_blob(reference: str, relative: Path) -> tuple[bytes | None, str | None]:
    executable = git_executable()
    if not executable:
        return None, "git executable is unavailable; set GIT_EXECUTABLE"
    completed = subprocess.run(
        [executable, "show", f"{reference}:{relative.as_posix()}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        return None, message or f"git show failed with exit {completed.returncode}"
    return completed.stdout, None


def audit_archive(path: Path, *, git_ref: str | None = None, expected_version: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    errors: list[str] = []
    if not path.is_file():
        return {"ok": False, "archive": str(path), "errors": ["archive does not exist"]}

    try:
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        version = manifest.get("version")
        verify_archive(path, version)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, SystemExit) as exc:
        errors.append(str(exc))
        version = None

    expected_paths = release_files()
    expected_names = [safe_archive_name(relative) for relative in expected_paths]
    archive_names: list[str] = []
    if not errors:
        with zipfile.ZipFile(path) as archive:
            archive_names = archive.namelist()
            if archive_names != expected_names:
                missing = sorted(set(expected_names) - set(archive_names))
                extra = sorted(set(archive_names) - set(expected_names))
                errors.append(f"archive file set differs from release contract; missing={missing}, extra={extra}")

            for relative in expected_paths:
                name = safe_archive_name(relative)
                if name not in archive_names:
                    continue
                archived = archive.read(name)
                if git_ref:
                    source, problem = git_blob(git_ref, relative)
                    if problem:
                        errors.append(f"{name}: cannot read {git_ref!r}: {problem}")
                        continue
                    assert source is not None
                else:
                    source = (ROOT / relative).read_bytes()
                canonical = canonical_release_bytes(relative, source)
                if archived != canonical:
                    errors.append(
                        f"{name}: archive bytes do not match canonical bytes from "
                        f"{'Git ref ' + git_ref if git_ref else 'working tree'}"
                    )

            if expected_version is not None:
                try:
                    archived_manifest = json.loads(
                        archive.read("plugins/mastery-learning/.codex-plugin/plugin.json")
                    )
                except (KeyError, json.JSONDecodeError) as exc:
                    errors.append(f"cannot read archived plugin version: {exc}")
                else:
                    if archived_manifest.get("version") != expected_version:
                        errors.append(
                            f"archived version {archived_manifest.get('version')!r} "
                            f"does not match expected {expected_version!r}"
                        )

    return {
        "ok": not errors,
        "archive": str(path),
        "sha256": sha256_bytes(path.read_bytes()),
        "files": len(archive_names),
        "source": f"git:{git_ref}" if git_ref else "working-tree",
        "version": version,
        "errors": errors,
    }


def compare_archives(paths: list[Path]) -> dict[str, Any]:
    resolved = [path.resolve() for path in paths]
    missing = [str(path) for path in resolved if not path.is_file()]
    if missing:
        return {"ok": False, "errors": [f"archives do not exist: {missing}"]}
    digests = {str(path): sha256_bytes(path.read_bytes()) for path in resolved}
    unique = sorted(set(digests.values()))
    return {
        "ok": len(unique) == 1,
        "archives": digests,
        "sha256": unique[0] if len(unique) == 1 else None,
        "errors": [] if len(unique) == 1 else ["archives are not byte-for-byte identical"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit reproducible Mastery Learning release archives")
    subparsers = parser.add_subparsers(dest="command", required=True)

    archive_parser = subparsers.add_parser("archive", help="Audit one archive against source bytes")
    archive_parser.add_argument("archive", type=Path)
    archive_parser.add_argument("--git-ref")
    archive_parser.add_argument("--expected-version")

    compare_parser = subparsers.add_parser("compare", help="Compare two or more release archives")
    compare_parser.add_argument("archives", nargs="+", type=Path)

    args = parser.parse_args()
    if args.command == "archive":
        report = audit_archive(args.archive, git_ref=args.git_ref, expected_version=args.expected_version)
    else:
        if len(args.archives) < 2:
            parser.error("compare requires at least two archives")
        report = compare_archives(args.archives)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
