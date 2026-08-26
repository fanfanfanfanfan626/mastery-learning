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
        readme_head = "\n".join((ROOT / "README.md").read_text(encoding="utf-8").splitlines()[:45])
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        ai_install = (ROOT / "AI_INSTALL.md").read_text(encoding="utf-8")
        for content in (readme_head, install, agents, ai_install):
            self.assertIn("plugin", content.lower())
            self.assertIn("skill-installer", content)

    def test_ai_install_contract_defines_observable_success_and_safe_stops(self) -> None:
        contract = (ROOT / "AI_INSTALL.md").read_text(encoding="utf-8")
        normalized = " ".join(contract.split()).lower()
        self.assertIn("codex plugin add mastery-learning@mastery-learning", contract)
        self.assertIn("codex plugin list", contract)
        self.assertIn("mastery-coach", contract)
        self.assertIn("mastery-tool-creator", contract)
        self.assertIn("ask the learner", normalized)
        self.assertIn("do not download", normalized)
        self.assertIn("Do not claim success", contract)

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
            environment["CODEX_HOME"] = str(temporary_path / "codex-home")

            if os.name == "nt":
                powershell = shutil.which("pwsh") or shutil.which("powershell")
                self.assertIsNotNone(powershell, "PowerShell is required on Windows")
                fake = temporary_path / "codex.cmd"
                fake.write_text(
                    '@echo off\r\n'
                    '>>"%MASTERY_INSTALL_CAPTURE%" echo %*\r\n'
                    'if "%~1"=="--version" echo codex 0.test\r\n'
                    'if "%~1"=="plugin" if "%~2"=="list" echo mastery-learning installed enabled\r\n'
                    'exit /b 0\r\n',
                    encoding="utf-8",
                )
                command = [
                    str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "install.ps1"),
                    "-CodexCommand", str(fake),
                ]
            else:
                fake = temporary_path / "codex"
                fake.write_text(
                    '#!/bin/sh\n'
                    'printf \'%s\\n\' "$*" >> "$MASTERY_INSTALL_CAPTURE"\n'
                    '[ "$1" = "--version" ] && echo "codex 0.test"\n'
                    '[ "$1" = "plugin" ] && [ "$2" = "list" ] && echo "mastery-learning installed enabled"\n'
                    'exit 0\n',
                    encoding="utf-8",
                )
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
                "--version",
                f"plugin marketplace add {ROOT}",
                "plugin add mastery-learning@mastery-learning",
                "plugin list",
            ])
            self.assertNotIn("skill-installer", "\n".join(calls))

    def test_installer_stops_before_mutation_when_standalone_skills_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            legacy = temporary_path / "codex-home" / "skills" / "mastery-coach"
            legacy.mkdir(parents=True)
            capture = temporary_path / "calls.txt"
            environment = os.environ.copy()
            environment["CODEX_HOME"] = str(temporary_path / "codex-home")
            environment["MASTERY_INSTALL_CAPTURE"] = str(capture)
            command = self._installer_command(temporary_path, capture, succeeds=True)
            completed = subprocess.run(
                command, cwd=ROOT, env=environment, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            output = completed.stdout + completed.stderr
            normalized = " ".join(output.split())
            self.assertNotEqual(completed.returncode, 0, output)
            # Windows runners can expand an 8.3 temp path (RUNNER~1) to its long form
            # (runneradmin) inside PowerShell. The stable, user-actionable suffix must
            # still be printed even when the two processes spell the temp root differently.
            expected_path = (
                str(Path("codex-home") / "skills" / "mastery-coach")
                if os.name == "nt"
                else str(legacy)
            )
            self.assertIn(expected_path, output)
            self.assertIn("No Codex configuration was", normalized)
            self.assertIn("changed.", normalized)
            self.assertFalse(capture.exists(), "Codex must not run before legacy copies are resolved")

    def test_installer_does_not_mutate_after_cli_probe_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            capture = temporary_path / "calls.txt"
            environment = os.environ.copy()
            environment["CODEX_HOME"] = str(temporary_path / "codex-home")
            environment["MASTERY_INSTALL_CAPTURE"] = str(capture)
            command = self._installer_command(temporary_path, capture, succeeds=False)
            completed = subprocess.run(
                command, cwd=ROOT, env=environment, text=True, encoding="utf-8",
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            output = completed.stdout + completed.stderr
            self.assertNotEqual(completed.returncode, 0, output)
            self.assertEqual(capture.read_text(encoding="utf-8").splitlines(), ["--version"])
            self.assertIn("plugin is not installed", output)
            self.assertIn("Do not download another Codex CLI", output)

    def _installer_command(self, temporary_path: Path, capture: Path, *, succeeds: bool) -> list[str]:
        del capture
        if os.name == "nt":
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            self.assertIsNotNone(powershell, "PowerShell is required on Windows")
            fake = temporary_path / "codex.cmd"
            exit_code = 0 if succeeds else 9
            fake.write_text(
                '@echo off\r\n'
                '>>"%MASTERY_INSTALL_CAPTURE%" echo %*\r\n'
                f'if "%~1"=="--version" exit /b {exit_code}\r\n'
                'if "%~1"=="plugin" if "%~2"=="list" echo mastery-learning installed enabled\r\n'
                'exit /b 0\r\n',
                encoding="utf-8",
            )
            return [
                str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(ROOT / "install.ps1"), "-CodexCommand", str(fake),
            ]
        fake = temporary_path / "codex"
        probe = "exit 9" if not succeeds else "echo 'codex 0.test'; exit 0"
        fake.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$*\" >> \"$MASTERY_INSTALL_CAPTURE\"\n"
            f'[ "$1" = "--version" ] && {{ {probe}; }}\n'
            '[ "$1" = "plugin" ] && [ "$2" = "list" ] && echo "mastery-learning installed enabled"\n'
            "exit 0\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        return ["sh", str(ROOT / "install.sh"), "--codex", str(fake)]

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
