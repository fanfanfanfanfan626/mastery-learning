#!/usr/bin/env python3
"""Build or verify generated host adapters from the canonical root Skills."""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"
SKILLS_ROOT = ROOT / "skills"
CODEX_SOURCE = ROOT / "adapters" / "codex"
GENERATED_MARKETPLACE = Path(".agents/plugins/marketplace.json")
GENERATED_PLUGIN = Path("plugins/mastery-tutor")
IGNORED = {"__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"}


def version() -> str:
    value = VERSION_FILE.read_text(encoding="utf-8").strip()
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise SystemExit("VERSION must contain one numeric semantic version")
    return value


def is_link(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def validate_sources() -> tuple[dict[str, object], dict[str, object]]:
    manifest_path = CODEX_SOURCE / "plugin" / ".codex-plugin" / "plugin.json"
    marketplace_path = CODEX_SOURCE / "marketplace.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    current_version = version()
    if manifest.get("name") != "mastery-tutor" or manifest.get("version") != "$VERSION":
        raise SystemExit("Codex adapter manifest must use mastery-tutor and the $VERSION token")
    plugins = marketplace.get("plugins")
    if (
        marketplace.get("name") != "mastery-tutor"
        or not isinstance(plugins, list)
        or len(plugins) != 1
        or plugins[0].get("name") != "mastery-tutor"
        or plugins[0].get("source") != {"source": "local", "path": "./plugins/mastery-tutor"}
    ):
        raise SystemExit("Codex marketplace template does not point to mastery-tutor")
    for name in ("mastery-coach", "mastery-tool-creator"):
        skill = SKILLS_ROOT / name
        if not skill.is_dir() or is_link(skill) or not (skill / "SKILL.md").is_file():
            raise SystemExit(f"Canonical Skill is missing or linked: {skill}")
    return manifest, marketplace


def copy_tree(source: Path, destination: Path) -> None:
    def ignore(_: str, names: list[str]) -> set[str]:
        return {name for name in names if name in IGNORED or Path(name).suffix.lower() in {".pyc", ".pyo"}}

    for path in source.rglob("*"):
        if is_link(path):
            raise SystemExit(f"Adapter source contains a link or reparse point: {path}")
    shutil.copytree(source, destination, ignore=ignore)


def build(output_root: Path) -> None:
    manifest, _ = validate_sources()
    output_root = output_root.resolve()
    marketplace_target = output_root / GENERATED_MARKETPLACE
    plugin_target = output_root / GENERATED_PLUGIN
    marketplace_target.parent.mkdir(parents=True, exist_ok=True)
    plugin_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CODEX_SOURCE / "marketplace.json", marketplace_target)
    copy_tree(CODEX_SOURCE / "plugin", plugin_target)
    manifest["version"] = version()
    (plugin_target / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    skills_target = plugin_target / "skills"
    skills_target.mkdir()
    for name in ("mastery-coach", "mastery-tool-creator"):
        copy_tree(SKILLS_ROOT / name, skills_target / name)


def compare_tree(expected: Path, actual: Path) -> list[str]:
    problems: list[str] = []
    if not actual.exists():
        return [f"missing generated path: {actual}"]
    comparison = filecmp.dircmp(expected, actual)
    for name in comparison.left_only:
        problems.append(f"missing from generated adapter: {(actual / name)}")
    for name in comparison.right_only:
        problems.append(f"unexpected generated adapter path: {(actual / name)}")
    for name in comparison.diff_files:
        problems.append(f"generated adapter drift: {(actual / name)}")
    for name, child in comparison.subdirs.items():
        problems.extend(compare_tree(expected / name, actual / name))
    return problems


def replace_generated(staged: Path) -> None:
    targets = [ROOT / ".agents", ROOT / "plugins"]
    for target in targets:
        resolved_parent = target.parent.resolve()
        if resolved_parent != ROOT.resolve():
            raise SystemExit(f"Refusing to replace generated path outside repository root: {target}")
    backups: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    backup_root = Path(tempfile.mkdtemp(prefix=".adapter-backup-", dir=ROOT))
    try:
        for target in targets:
            if target.exists():
                backup = backup_root / target.name
                os.replace(target, backup)
                backups.append((backup, target))
        for name in (".agents", "plugins"):
            source = staged / name
            target = ROOT / name
            os.replace(source, target)
            installed.append(target)
    except BaseException:
        for target in reversed(installed):
            if target.exists():
                os.replace(target, staged / target.name)
        for backup, target in reversed(backups):
            if backup.exists():
                os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build generated Mastery Tutor host adapters")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="replace checked-in generated adapters")
    mode.add_argument("--check", action="store_true", help="fail when checked-in adapters drift")
    mode.add_argument("--output", type=Path, help="build a complete adapter marketplace elsewhere")
    args = parser.parse_args()

    if args.output:
        output = args.output.expanduser().resolve()
        if output.exists() and any(output.iterdir()):
            raise SystemExit(f"Adapter output must be empty: {output}")
        output.mkdir(parents=True, exist_ok=True)
        build(output)
        print(json.dumps({"ok": True, "status": "built", "output": str(output), "version": version()}, indent=2))
        return

    with tempfile.TemporaryDirectory(prefix="mastery-tutor-adapter-") as temporary:
        staged = Path(temporary)
        build(staged)
        if args.check:
            problems = compare_tree(staged / ".agents", ROOT / ".agents")
            problems.extend(compare_tree(staged / "plugins", ROOT / "plugins"))
            print(json.dumps({"ok": not problems, "status": "verified" if not problems else "drift", "version": version(), "errors": problems}, indent=2))
            raise SystemExit(0 if not problems else 1)
        replace_generated(staged)
    print(json.dumps({"ok": True, "status": "written", "version": version()}, indent=2))


if __name__ == "__main__":
    main()
