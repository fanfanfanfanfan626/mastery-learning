from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install-agent-skills.py"
SET_MANIFEST = ROOT / "agent-skill-set.json"
if str(ROOT / "quality") not in sys.path:
    sys.path.insert(0, str(ROOT / "quality"))


def run_installer(*args: str | Path, expect: int = 0) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(INSTALLER), *map(str, args)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != expect:
        raise AssertionError(
            f"installer exit {completed.returncode}, expected {expect}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return json.loads(completed.stdout)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AgentSkillDistributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(SET_MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_points_to_one_canonical_required_pair(self) -> None:
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["specification"], "https://agentskills.io/specification")
        plugin = json.loads(
            (ROOT / "plugins" / "mastery-tutor" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.manifest["version_source"], "VERSION")
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8").strip(), plugin["version"])
        skills = self.manifest["skills"]
        self.assertEqual([item["name"] for item in skills], ["mastery-coach", "mastery-tool-creator"])
        self.assertTrue(all(item["required"] is True for item in skills))
        for item in skills:
            source = ROOT / item["source"]
            self.assertTrue((source / "SKILL.md").is_file())
            self.assertEqual(source.name, item["name"])
        self.assertFalse((ROOT / "SKILL.md").exists(), "The bundle must not masquerade as one root Skill")

    def test_custom_install_and_post_install_check_verify_both_trees(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            installed = run_installer("--host", "custom", "--target", target)
            self.assertTrue(installed["ok"])
            self.assertEqual(installed["status"], "installed")
            checked = run_installer("--host", "custom", "--target", target, "--check")
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["status"], "verified")
            self.assertEqual({item["status"] for item in checked["skills"]}, {"verified"})
            for item in self.manifest["skills"]:
                source = ROOT / item["source"] / "SKILL.md"
                copied = target / item["name"] / "SKILL.md"
                self.assertEqual(file_sha(source), file_sha(copied))

    def test_existing_identical_skill_does_not_block_missing_companion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            run_installer("--host", "custom", "--target", target)
            creator = target / "mastery-tool-creator"
            import shutil

            shutil.rmtree(creator)
            report = run_installer("--host", "custom", "--target", target)
            self.assertTrue(report["ok"])
            self.assertTrue(creator.is_dir())
            checked = run_installer("--host", "custom", "--target", target, "--check")
            self.assertTrue(checked["ok"])

    def test_conflict_stops_without_overwriting_and_replace_keeps_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "skills"
            run_installer("--host", "custom", "--target", target)
            changed = target / "mastery-coach" / "SKILL.md"
            changed.write_text(changed.read_text(encoding="utf-8") + "\nlocal change\n", encoding="utf-8")
            local_digest = file_sha(changed)

            conflict = run_installer("--host", "custom", "--target", target, expect=1)
            self.assertFalse(conflict["ok"])
            self.assertEqual(conflict["status"], "conflict")
            self.assertEqual(file_sha(changed), local_digest)

            replaced = run_installer("--host", "custom", "--target", target, "--replace")
            self.assertTrue(replaced["ok"])
            backup = Path(str(replaced["backup"]))
            self.assertTrue((backup / "mastery-coach" / "SKILL.md").is_file())
            self.assertEqual(file_sha(backup / "mastery-coach" / "SKILL.md"), local_digest)
            self.assertTrue(run_installer("--host", "custom", "--target", target, "--check")["ok"])

    def test_host_mappings_and_claims_are_explicit(self) -> None:
        adapters = self.manifest["adapters"]
        self.assertEqual(adapters["claude-code"]["user_directory"], "~/.claude/skills")
        self.assertEqual(adapters["github-copilot"]["project_directory"], ".agents/skills")
        self.assertEqual(adapters["codex"]["status"], "verified-adapter")
        self.assertEqual(adapters["claude-code"]["status"], "experimental")
        self.assertEqual(adapters["github-copilot"]["status"], "experimental")
        self.assertEqual(adapters["opencode"]["status"], "planned")
        support = (ROOT / "docs" / "host-adapters.md").read_text(encoding="utf-8").lower()
        self.assertIn("file installation from agent behavior", support)
        self.assertIn("behavior verification pending", support)

    def test_named_project_hosts_install_into_their_documented_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            cases = {
                "agent-skills": Path(".agents/skills"),
                "claude-code": Path(".claude/skills"),
                "github-copilot": Path(".agents/skills"),
            }
            for host, relative in cases.items():
                project = base / host
                project.mkdir()
                installed = run_installer(
                    "--host", host, "--scope", "project", "--project-root", project
                )
                self.assertTrue(installed["ok"], installed)
                target = project / relative
                self.assertTrue((target / "mastery-coach" / "SKILL.md").is_file())
                self.assertTrue((target / "mastery-tool-creator" / "SKILL.md").is_file())
                checked = run_installer(
                    "--host", host, "--scope", "project", "--project-root", project, "--check"
                )
                self.assertEqual(checked["status"], "verified")

    def test_release_contract_includes_portable_installation_surface(self) -> None:
        from build_release import release_files

        names = {path.as_posix() for path in release_files()}
        self.assertTrue({
            "AGENT_INSTALL.md",
            "agent-skill-set.json",
            "install-agent-skills.py",
            "docs/host-adapters.md",
        }.issubset(names))

    def test_extracted_release_installs_without_repository_context(self) -> None:
        from build_release import build

        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            archive = temporary_path / "release.zip"
            extracted = temporary_path / "release"
            target = temporary_path / "installed-skills"
            build(archive)
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extracted)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(extracted / "install-agent-skills.py"),
                    "--host", "custom",
                    "--target", str(target),
                ],
                cwd=extracted,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["status"], "installed")
            self.assertTrue((target / "mastery-coach" / "SKILL.md").is_file())
            self.assertTrue((target / "mastery-tool-creator" / "SKILL.md").is_file())

    def test_registry_uses_portable_default_without_hiding_existing_codex_data(self) -> None:
        state_script = ROOT / "skills" / "mastery-coach" / "scripts" / "mastery.py"
        spec = importlib.util.spec_from_file_location("mastery_registry_contract", state_script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            environment = {key: value for key, value in os.environ.items() if key not in {"MASTERY_HOME", "CODEX_HOME"}}
            with mock.patch.dict("os.environ", environment, clear=True), mock.patch.object(Path, "home", return_value=home):
                self.assertEqual(module.registry_base(), (home / ".mastery-learning").resolve())
                legacy = home / ".codex" / "mastery-learning"
                legacy.mkdir(parents=True)
                self.assertEqual(module.registry_base(), legacy.resolve())
                portable = home / ".mastery-learning"
                portable.mkdir()
                self.assertEqual(module.registry_base(), portable.resolve())


if __name__ == "__main__":
    unittest.main()
