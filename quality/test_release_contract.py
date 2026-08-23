from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "quality") not in sys.path:
    sys.path.insert(0, str(ROOT / "quality"))

from build_release import build, canonical_release_bytes, write_checksum
from release_audit import audit_archive, compare_archives


class ReleaseContractTests(unittest.TestCase):
    def test_text_bytes_are_checkout_independent(self) -> None:
        path = Path("metadata.json")
        self.assertEqual(
            canonical_release_bytes(path, b'{\r\n  "ok": true\r\n}\r\n'),
            b'{\n  "ok": true\n}\n',
        )
        binary = b"PNG\r\n\x00payload\r"
        self.assertEqual(canonical_release_bytes(Path("image.png"), binary), binary)

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
