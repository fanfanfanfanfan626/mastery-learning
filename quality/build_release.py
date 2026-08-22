from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_MANIFEST = ROOT / "plugins" / "mastery-learning" / ".codex-plugin" / "plugin.json"
ROOT_FILES = [
    Path(".agents/plugins/marketplace.json"),
    Path(".github/workflows/verify.yml"),
    Path(".gitignore"),
    Path("CHANGELOG.md"),
    Path("LICENSE"),
    Path("README.md"),
]
TREES = [Path("docs"), Path("plugins/mastery-learning"), Path("quality")]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip"}
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def release_files() -> list[Path]:
    files: set[Path] = set()
    for relative in ROOT_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"Required release file is missing: {relative.as_posix()}")
        files.add(relative)
    for tree in TREES:
        path = ROOT / tree
        if not path.is_dir():
            raise SystemExit(f"Required release tree is missing: {tree.as_posix()}")
        for candidate in path.rglob("*"):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(ROOT)
            if EXCLUDED_PARTS.intersection(relative.parts) or candidate.suffix.lower() in EXCLUDED_SUFFIXES:
                continue
            files.add(relative)
    return sorted(files, key=lambda item: item.as_posix())


def safe_archive_name(relative: Path) -> str:
    name = relative.as_posix()
    parsed = PurePosixPath(name)
    if parsed.is_absolute() or ".." in parsed.parts or not name or "\\" in name:
        raise SystemExit(f"Unsafe release path: {name!r}")
    return name


def build(output: Path) -> dict[str, object]:
    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    version = manifest.get("version")
    if not isinstance(version, str) or not version.strip():
        raise SystemExit("Plugin manifest version must be non-empty text")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative in release_files():
                info = zipfile.ZipInfo(safe_archive_name(relative), FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, (ROOT / relative).read_bytes())
        verify_archive(temporary, version)
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {"ok": True, "version": version, "output": str(output), "files": len(release_files()), "sha256": digest}


def verify_archive(path: Path, version: str) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise SystemExit("Release archive contains duplicate paths")
        if names != sorted(names):
            raise SystemExit("Release archive paths are not deterministic")
        for name in names:
            parsed = PurePosixPath(name)
            if parsed.is_absolute() or ".." in parsed.parts or "\\" in name:
                raise SystemExit(f"Release archive contains unsafe path: {name!r}")
        archived_manifest = json.loads(archive.read("plugins/mastery-learning/.codex-plugin/plugin.json"))
        if archived_manifest.get("version") != version:
            raise SystemExit("Archived plugin version does not match source manifest")
        required = {safe_archive_name(path) for path in ROOT_FILES}
        required.update({
            "plugins/mastery-learning/skills/mastery-coach/SKILL.md",
            "plugins/mastery-learning/skills/mastery-tool-creator/SKILL.md",
            "quality/test_state_regressions_v4.py",
            "quality/test_tool_contract_v4.py",
        })
        missing = sorted(required - set(names))
        if missing:
            raise SystemExit(f"Release archive is missing required paths: {missing}")


def main() -> None:
    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    default = ROOT / "outputs" / f"mastery-learning-{manifest.get('version', 'unknown')}.zip"
    parser = argparse.ArgumentParser(description="Build a deterministic Mastery Learning release archive")
    parser.add_argument("--output", type=Path, default=default)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))


if __name__ == "__main__":
    main()
