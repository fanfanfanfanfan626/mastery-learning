from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
PLUGIN_MANIFEST = ROOT / "plugins" / "mastery-tutor" / ".codex-plugin" / "plugin.json"
KINDS = ("bundle", "core", "codex")
COMMON_FILES = [
    Path(".gitattributes"),
    Path(".gitignore"),
    Path("VERSION"),
    Path("LICENSE"),
    Path("README.md"),
    Path("README.zh-CN.md"),
    Path("CHANGELOG.md"),
    Path("COMPATIBILITY.md"),
    Path("MIGRATION.md"),
    Path("SECURITY.md"),
    Path("SUPPORT.md"),
    Path("CODE_OF_CONDUCT.md"),
]
CORE_FILES = [
    Path("AGENTS.md"),
    Path("AGENT_INSTALL.md"),
    Path("AI_INSTALL.md"),
    Path("INSTALL.md"),
    Path("agent-skill-set.json"),
    Path("install-agent-skills.py"),
]
CODEX_FILES = [
    Path("AGENTS.md"),
    Path("AGENT_INSTALL.md"),
    Path("AI_INSTALL.md"),
    Path("INSTALL.md"),
    Path("agent-skill-set.json"),
    Path("install-agent-skills.py"),
    Path("install.ps1"),
    Path("install.sh"),
    Path(".agents/plugins/marketplace.json"),
]
BUNDLE_FILES = [
    Path("CONTRIBUTING.md"),
    Path("ROADMAP.md"),
]
CORE_TREES = [Path("skills"), Path("docs")]
CODEX_TREES = [Path("skills"), Path("plugins/mastery-tutor"), Path("docs")]
BUNDLE_TREES = [
    Path(".github"),
    Path("adapters"),
    Path("quality"),
]
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".zip"}
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
TEXT_SUFFIXES = {
    ".css", ".csv", ".html", ".js", ".json", ".jsonl", ".md", ".mjs",
    ".ps1", ".py", ".sh", ".svg", ".toml", ".ts", ".txt", ".yaml", ".yml",
}
TEXT_FILENAMES = {".gitattributes", ".gitignore", "LICENSE", "VERSION"}


def version() -> str:
    value = VERSION_FILE.read_text(encoding="utf-8").strip()
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise SystemExit("VERSION must contain one numeric semantic version")
    return value


def release_files(kind: str = "bundle") -> list[Path]:
    if kind not in KINDS:
        raise SystemExit(f"Unknown release kind: {kind!r}")
    files: set[Path] = set(COMMON_FILES)
    trees: list[Path] = []
    if kind in {"core", "bundle"}:
        files.update(CORE_FILES)
        trees.extend(CORE_TREES)
    if kind in {"codex", "bundle"}:
        files.update(CODEX_FILES)
        trees.extend(CODEX_TREES)
    if kind == "bundle":
        files.update(BUNDLE_FILES)
        trees.extend(BUNDLE_TREES)
    for relative in files:
        if not (ROOT / relative).is_file():
            raise SystemExit(f"Required {kind} release file is missing: {relative.as_posix()}")
    for tree in trees:
        path = ROOT / tree
        if not path.is_dir():
            raise SystemExit(f"Required {kind} release tree is missing: {tree.as_posix()}")
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


def build(output: Path, kind: str = "bundle") -> dict[str, object]:
    current_version = version()
    files = release_files(kind)
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as archive:
            for relative in files:
                info = zipfile.ZipInfo(safe_archive_name(relative), FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_STORED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                source = canonical_release_bytes(relative, (ROOT / relative).read_bytes())
                archive.writestr(info, source)
        verify_archive(temporary, current_version, kind)
        os.replace(temporary, output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "ok": True,
        "kind": kind,
        "version": current_version,
        "output": str(output),
        "files": len(files),
        "sha256": digest,
    }


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


def verify_archive(path: Path, expected_version: str, kind: str = "bundle") -> None:
    expected_names = {safe_archive_name(item) for item in release_files(kind)}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise SystemExit("Release archive contains duplicate paths")
        if names != sorted(names):
            raise SystemExit("Release archive paths are not deterministic")
        if set(names) != expected_names:
            missing = sorted(expected_names - set(names))
            extra = sorted(set(names) - expected_names)
            raise SystemExit(f"Release archive file set differs; missing={missing}, extra={extra}")
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
        archived_version = archive.read("VERSION").decode("utf-8").strip()
        if archived_version != expected_version:
            raise SystemExit("Archived VERSION does not match the requested version")
        if kind in {"core", "bundle"}:
            skill_set = json.loads(archive.read("agent-skill-set.json"))
            if skill_set.get("version_source") != "VERSION":
                raise SystemExit("Archived core manifest does not use VERSION")
            for name in ("mastery-coach", "mastery-tool-creator"):
                if f"skills/{name}/SKILL.md" not in names:
                    raise SystemExit(f"Archived core is missing canonical Skill: {name}")
        if kind in {"codex", "bundle"}:
            plugin = json.loads(
                archive.read("plugins/mastery-tutor/.codex-plugin/plugin.json")
            )
            if plugin.get("name") != "mastery-tutor" or plugin.get("version") != expected_version:
                raise SystemExit("Archived Codex adapter identity/version does not match VERSION")
            for name in ("mastery-coach", "mastery-tool-creator"):
                if f"plugins/mastery-tutor/skills/{name}/SKILL.md" not in names:
                    raise SystemExit(f"Archived Codex adapter is missing Skill: {name}")


def main() -> None:
    current_version = version()
    parser = argparse.ArgumentParser(description="Build a deterministic Mastery Tutor release archive")
    parser.add_argument("--kind", choices=KINDS, default="bundle")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--checksum-output", type=Path)
    args = parser.parse_args()
    output = args.output
    if output is None:
        suffix = "" if args.kind == "bundle" else f"-{args.kind}"
        output = ROOT / "outputs" / f"mastery-tutor-{current_version}{suffix}.zip"
    report = build(output, args.kind)
    if args.checksum_output:
        write_checksum(args.checksum_output, output.resolve(), str(report["sha256"]))
        report["checksum_output"] = str(args.checksum_output.resolve())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
