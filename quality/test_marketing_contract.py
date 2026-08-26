from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def image_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    if data.startswith((b"GIF87a", b"GIF89a")):
        return struct.unpack("<HH", data[6:10])
    raise AssertionError(f"unsupported image format: {path}")


class MarketingContractTests(unittest.TestCase):
    def test_readme_opens_with_value_demo_and_supported_install(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        head = "\n".join(readme.splitlines()[:50]).lower()
        normalized_head = " ".join(head.split())
        self.assertIn("# mastery tutor", head)
        self.assertIn("a local-first mastery tutor for ai agents", normalized_head)
        self.assertIn("guided html lessons", normalized_head)
        self.assertIn("verified adapter", normalized_head)
        self.assertIn("experimental", normalized_head)
        self.assertIn("core-compatible", normalized_head)
        self.assertIn("docs/assets/demo.gif", head)
        self.assertIn("ai_install.md", head)
        self.assertIn("mastery-tutor", head)
        self.assertIn("readme.zh-cn.md", head)

    def test_public_copy_prefers_concrete_actions_to_hype(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        manifest = json.loads(
            (ROOT / "plugins" / "mastery-tutor" / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        public_copy = "\n".join([
            readme,
            str(manifest["description"]),
            str(manifest["interface"]),
        ]).lower()
        for phrase in ["beautiful interactive html lessons", "honest mastery", "durable progress"]:
            self.assertNotIn(phrase, public_copy)
        for phrase in ["guided html lessons", "hands-on practice", "local progress"]:
            self.assertIn(phrase, public_copy)
        self.assertIn("transfer checks", public_copy)
        self.assertIn("learner-owned local progress", public_copy)

    def test_discovery_metadata_points_to_real_brand_assets(self) -> None:
        manifest = json.loads(
            (ROOT / "plugins" / "mastery-tutor" / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["homepage"], "https://github.com/fanfanfanfanfan626/mastery-tutor")
        self.assertEqual(manifest["repository"], manifest["homepage"])
        self.assertEqual(manifest["interface"]["displayName"], "Mastery Tutor")
        self.assertEqual(
            manifest["interface"]["shortDescription"],
            "Guided lessons, hands-on practice, and local progress.",
        )
        self.assertTrue(
            {"ai-teaching", "teaching-skill", "ai-tutor", "agent-skill", "codex", "machine-learning", "llm", "spaced-repetition"}.issubset(
                set(manifest["keywords"])
            )
        )
        plugin_root = ROOT / "plugins" / "mastery-tutor"
        interface = manifest["interface"]
        for field in ["composerIcon", "logo", "logoDark"]:
            path = plugin_root / interface[field].removeprefix("./")
            self.assertTrue(path.is_file(), f"missing {field}: {path}")
            self.assertEqual(image_dimensions(path), (512, 512))
        screenshot = plugin_root / interface["screenshots"][0].removeprefix("./")
        self.assertEqual(image_dimensions(screenshot), (1280, 720))
        self.assertEqual(image_dimensions(ROOT / "docs" / "assets" / "social-preview.png"), (1280, 640))
        self.assertEqual(image_dimensions(ROOT / "docs" / "assets" / "demo.gif"), (960, 540))

    def test_repository_has_a_clear_maintainer_onramp(self) -> None:
        for relative in [
            "CONTRIBUTING.md",
            "ROADMAP.md",
            ".github/ISSUE_TEMPLATE/bug-report.yml",
            ".github/ISSUE_TEMPLATE/feature-request.yml",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/ISSUE_TEMPLATE/adapter-bug.yml",
            ".github/pull_request_template.md",
            "SECURITY.md",
            "SUPPORT.md",
            "CODE_OF_CONDUCT.md",
        ]:
            self.assertTrue((ROOT / relative).is_file(), f"missing maintainer entrypoint: {relative}")


if __name__ == "__main__":
    unittest.main()
