from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_ENGINE = ROOT / "plugins" / "mastery-learning" / "skills" / "mastery-coach" / "scripts" / "mastery.py"


class MaintainabilityBudgetTests(unittest.TestCase):
    def test_state_entrypoint_cannot_keep_growing(self) -> None:
        source = STATE_ENGINE.read_text(encoding="utf-8")
        self.assertLessEqual(
            len(source.splitlines()),
            2350,
            "Extract a cohesive state-engine module before adding more entrypoint code.",
        )

    def test_top_level_functions_remain_reviewable(self) -> None:
        module = ast.parse(STATE_ENGINE.read_text(encoding="utf-8"))
        oversized = {
            node.name: node.end_lineno - node.lineno + 1
            for node in module.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.end_lineno is not None
            and node.end_lineno - node.lineno + 1 > 150
        }
        self.assertEqual(
            oversized,
            {},
            "Split oversized behavior by invariant before extending it.",
        )


if __name__ == "__main__":
    unittest.main()
