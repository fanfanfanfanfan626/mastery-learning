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
    Path(".gitattributes"),
    Path(".gitignore"),
    Path("AGENTS.md"),
    Path("CHANGELOG.md"),
    Path("INSTALL.md"),
    Path("LICENSE"),
    Path("README.md"),
    Path("install.ps1"),
    Path("install.sh"),
]
TREES = [Path("docs"), Path("plugins/mastery-learning"), Path("quality")]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip"}
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
TEXT_SUFFIXES = {
    ".css", ".csv", ".html", ".js", ".json", ".jsonl", ".md", ".mjs",
    ".ps1", ".py", ".sh", ".svg", ".toml", ".ts", ".txt", ".yaml", ".yml",
}
TEXT_FILENAMES = {".gitattributes", ".gitignore", "LICENSE"}


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


def canonical_release_bytes(relative: Path, data: bytes) -> bytes:
    """Return checkout-independent bytes for files treated as text by the release."""
    if relative.name not in TEXT_FILENAMES and relative.suffix.lower() not in TEXT_SUFFIXES:
        return data
    if b"\x00" in data:
        raise SystemExit(f"Release text file contains a NUL byte: {relative.as_posix()}")
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


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
        # Stored entries avoid zlib-version-dependent output. The archive is small, and exact
        # cross-platform reproducibility is more valuable here than marginal compression.
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
            for relative in release_files():
                info = zipfile.ZipInfo(safe_archive_name(relative), FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                source = canonical_release_bytes(relative, (ROOT / relative).read_bytes())
                archive.writestr(info, source)
        verify_archive(temporary, version)
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {"ok": True, "version": version, "output": str(output), "files": len(release_files()), "sha256": digest}


def write_checksum(output: Path, archive: Path, digest: str) -> None:
    output = output.resolve()
    archive = archive.resolve()
    if output == archive:
        raise SystemExit("Checksum output must not overwrite the release archive")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(f"{digest}  {archive.name}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


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
            info = archive.getinfo(name)
            if info.date_time != FIXED_TIMESTAMP or info.compress_type != zipfile.ZIP_STORED:
                raise SystemExit(f"Release archive contains non-deterministic metadata: {name!r}")
            archived = archive.read(name)
            if canonical_release_bytes(Path(name), archived) != archived:
                raise SystemExit(f"Release archive text is not LF-canonical: {name!r}")
        archived_manifest = json.loads(archive.read("plugins/mastery-learning/.codex-plugin/plugin.json"))
        if archived_manifest.get("version") != version:
            raise SystemExit("Archived plugin version does not match source manifest")
        required = {safe_archive_name(path) for path in ROOT_FILES}
        required.update({
            "AGENTS.md",
            "INSTALL.md",
            "install.ps1",
            "install.sh",
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
    parser.add_argument("--checksum-output", type=Path)
    args = parser.parse_args()
    report = build(args.output)
    if args.checksum_output:
        write_checksum(args.checksum_output, args.output.resolve(), str(report["sha256"]))
        report["checksum_output"] = str(args.checksum_output.resolve())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
