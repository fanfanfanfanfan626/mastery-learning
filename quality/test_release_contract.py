from __future__ import annotations

import tempfile
import unittest
import sys
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "quality") not in sys.path:
    sys.path.insert(0, str(ROOT / "quality"))

from build_release import build, canonical_release_bytes, write_checksum
from release_audit import audit_archive, compare_archives


class ReleaseContractTests(unittest.TestCase):
    def test_version_is_single_source_for_manifests_and_workflows(self) -> None:
        current = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        source_plugin = json.loads(
            (ROOT / "adapters" / "codex" / "plugin" / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        generated_plugin = json.loads(
            (ROOT / "plugins" / "mastery-tutor" / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        skill_set = json.loads((ROOT / "agent-skill-set.json").read_text(encoding="utf-8"))
        self.assertEqual(source_plugin["version"], "$VERSION")
        self.assertEqual(generated_plugin["version"], current)
        self.assertEqual(skill_set["version_source"], "VERSION")
        for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
            self.assertNotIn(current, workflow.read_text(encoding="utf-8"))
        completed = subprocess.run(
            [sys.executable, str(ROOT / "quality" / "build_adapters.py"), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_core_and_codex_archives_have_distinct_installable_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            core = Path(temporary) / "core.zip"
            codex = Path(temporary) / "codex.zip"
            build(core, "core")
            build(codex, "codex")
            self.assertTrue(audit_archive(core, kind="core")["ok"])
            self.assertTrue(audit_archive(codex, kind="codex")["ok"])
            with zipfile.ZipFile(core) as archive:
                names = set(archive.namelist())
                self.assertIn("skills/mastery-coach/SKILL.md", names)
                self.assertIn("skills/mastery-tool-creator/SKILL.md", names)
                self.assertIn("install-agent-skills.py", names)
                self.assertNotIn("plugins/mastery-tutor/.codex-plugin/plugin.json", names)
            with zipfile.ZipFile(codex) as archive:
                names = set(archive.namelist())
                self.assertIn("plugins/mastery-tutor/.codex-plugin/plugin.json", names)
                self.assertIn("skills/mastery-coach/SKILL.md", names)
                self.assertIn("skills/mastery-tool-creator/SKILL.md", names)
                self.assertIn("agent-skill-set.json", names)
                self.assertIn("install.ps1", names)
                self.assertIn("install.sh", names)

    def test_text_bytes_are_checkout_independent(self) -> None:
        path = Path("metadata.json")
        self.assertEqual(
            canonical_release_bytes(path, b'{\r\n  "ok": true\r\n}\r\n'),
            b'{\n  "ok": true\n}\n',
        )
        binary = b"PNG\r\n\x00payload\r"
        self.assertEqual(canonical_release_bytes(Path("image.png"), binary), binary)

    def test_extensionless_license_is_checkout_independent(self) -> None:
        self.assertEqual(
            canonical_release_bytes(Path("LICENSE"), b"MIT License\r\n\r\nCopyright\r\n"),
            b"MIT License\n\nCopyright\n",
        )

    def test_platform_installers_are_checkout_independent(self) -> None:
        self.assertEqual(
            canonical_release_bytes(Path("install.ps1"), b"Write-Output ok\r\n"),
            b"Write-Output ok\n",
        )
        self.assertEqual(
            canonical_release_bytes(Path("install.sh"), b"#!/bin/sh\r\necho ok\r\n"),
            b"#!/bin/sh\necho ok\n",
        )

    def test_two_builds_are_identical_and_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.zip"
            second = Path(temporary) / "second.zip"
            build(first)
            build(second)
            comparison = compare_archives([first, second])
            self.assertTrue(comparison["ok"], comparison)
            report = audit_archive(first)
            self.assertTrue(report["ok"], report)

    def test_comparison_rejects_modified_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.zip"
            second = Path(temporary) / "second.zip"
            build(first)
            second.write_bytes(first.read_bytes() + b"tampered")
            comparison = compare_archives([first, second])
            self.assertFalse(comparison["ok"])
            self.assertIn("not byte-for-byte identical", "\n".join(comparison["errors"]))

    def test_checksum_file_names_the_exact_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "release.zip"
            checksum = Path(temporary) / "release.zip.sha256"
            report = build(archive)
            write_checksum(checksum, archive, str(report["sha256"]))
            self.assertEqual(checksum.read_text(encoding="utf-8"), f"{report['sha256']}  release.zip\n")
            with self.assertRaises(SystemExit):
                write_checksum(archive, archive, str(report["sha256"]))


if __name__ == "__main__":
    unittest.main()
