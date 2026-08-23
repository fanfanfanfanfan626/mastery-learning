from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallContractTests(unittest.TestCase):
    def test_repository_is_explicitly_a_plugin_not_a_root_skill(self) -> None:
        self.assertFalse((ROOT / "SKILL.md").exists())
        readme_head = "\n".join((ROOT / "README.md").read_text(encoding="utf-8").splitlines()[:30])
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for content in (readme_head, install, agents):
            self.assertIn("plugin", content.lower())
            self.assertIn("skill-installer", content)

    def test_marketplace_and_plugin_identities_match(self) -> None:
        marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        manifest = json.loads(
            (ROOT / "plugins" / "mastery-learning" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["name"], "mastery-learning")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], manifest["name"])
        self.assertEqual(entry["source"], {"source": "local", "path": "./plugins/mastery-learning"})
        self.assertEqual(manifest["skills"], "./skills/")

    def test_platform_installer_invokes_only_the_plugin_flow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            capture = temporary_path / "calls.txt"
            environment = os.environ.copy()
            environment["MASTERY_INSTALL_CAPTURE"] = str(capture)

            if os.name == "nt":
                powershell = shutil.which("pwsh") or shutil.which("powershell")
                self.assertIsNotNone(powershell, "PowerShell is required on Windows")
                fake = temporary_path / "codex.cmd"
                fake.write_text('@echo off\r\n>>"%MASTERY_INSTALL_CAPTURE%" echo %*\r\nexit /b 0\r\n', encoding="utf-8")
                command = [
                    str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install.ps1"),
                    "-CodexCommand", str(fake),
                ]
            else:
                fake = temporary_path / "codex"
                fake.write_text('#!/bin/sh\nprintf \'%s\\n\' "$*" >> "$MASTERY_INSTALL_CAPTURE"\n', encoding="utf-8")
                fake.chmod(0o755)
                command = ["sh", str(ROOT / "install.sh"), "--codex", str(fake)]

            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            calls = capture.read_text(encoding="utf-8").splitlines()
            self.assertEqual(calls, [
                f"plugin marketplace add {ROOT}",
                "plugin add mastery-learning@mastery-learning",
            ])
            self.assertNotIn("skill-installer", "\n".join(calls))

    def test_check_only_does_not_require_or_invoke_codex(self) -> None:
        if os.name == "nt":
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            self.assertIsNotNone(powershell, "PowerShell is required on Windows")
            command = [
                str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install.ps1"),
                "-CheckOnly", "-CodexCommand", "definitely-not-a-command",
            ]
        else:
            command = ["sh", str(ROOT / "install.sh"), "--check-only", "--codex", "definitely-not-a-command"]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("Check-only mode", completed.stdout)


if __name__ == "__main__":
    unittest.main()
