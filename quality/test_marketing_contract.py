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
        head = "\n".join(readme.splitlines()[:40]).lower()
        self.assertIn("turn codex into a local-first ai tutor", head)
        self.assertIn("docs/assets/demo.gif", head)
        self.assertIn("codex plugin marketplace", head)
        self.assertIn("skill-installer", head)
        self.assertIn("60 秒开始使用", head)

    def test_discovery_metadata_points_to_real_brand_assets(self) -> None:
        manifest = json.loads(
            (ROOT / "plugins" / "mastery-learning" / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["homepage"], "https://github.com/fanfanfanfanfan626/mastery-learning")
        self.assertEqual(manifest["repository"], manifest["homepage"])
        self.assertTrue(
            {"ai-tutor", "codex", "machine-learning", "llm", "spaced-repetition"}.issubset(
                set(manifest["keywords"])
            )
        )
        plugin_root = ROOT / "plugins" / "mastery-learning"
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
        ]:
            self.assertTrue((ROOT / relative).is_file(), f"missing maintainer entrypoint: {relative}")


if __name__ == "__main__":
    unittest.main()
