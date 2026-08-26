from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CiCompatibilityContractTests(unittest.TestCase):
    def test_supported_python_boundaries_and_three_operating_systems_are_exercised(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
        self.assertIn("python-compatibility:", workflow)
        self.assertIn('python: ["3.10", "3.13"]', workflow)
        for runner in ["ubuntu-latest", "windows-latest", "macos-latest"]:
            self.assertIn(runner, workflow)
        self.assertIn("Compare macOS and Linux candidate bytes", workflow)

    def test_release_cannot_publish_before_its_cross_platform_gate(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("reproducibility:", workflow)
        self.assertIn("needs: reproducibility", workflow)
        for runner in ["ubuntu-latest", "windows-latest", "macos-latest"]:
            self.assertIn(runner, workflow)
        self.assertIn("Compare Linux, Windows, and macOS release bytes", workflow)
        self.assertIn("quality/release_audit.py compare", workflow)


if __name__ == "__main__":
    unittest.main()
