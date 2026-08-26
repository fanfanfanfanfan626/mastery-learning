from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_ENGINE = ROOT / "skills" / "mastery-coach" / "scripts" / "mastery.py"
REGISTRY_ENGINE = ROOT / "skills" / "mastery-coach" / "scripts" / "mastery_registry.py"


class MaintainabilityBudgetTests(unittest.TestCase):
    def test_state_entrypoint_cannot_keep_growing(self) -> None:
        source = STATE_ENGINE.read_text(encoding="utf-8")
        self.assertLessEqual(
            len(source.splitlines()),
            2200,
            "Extract a cohesive state-engine module before adding more entrypoint code.",
        )

    def test_registry_has_a_separate_privacy_owned_module(self) -> None:
        entrypoint = STATE_ENGINE.read_text(encoding="utf-8")
        registry = REGISTRY_ENGINE.read_text(encoding="utf-8")
        self.assertIn("from mastery_registry import", entrypoint)
        self.assertIn("The registry is an index, not learner state", registry)
        self.assertIn('"schema_version": REGISTRY_SCHEMA_VERSION', registry)
        self.assertIn("def registry_value", registry)

    def test_registry_changes_stay_inside_the_state_transaction(self) -> None:
        module = ast.parse(STATE_ENGINE.read_text(encoding="utf-8"))
        for function_name, registry_call in [
            ("cmd_init", "register_workspace"),
            ("cmd_migrate", "register_workspace"),
            ("cmd_delete", "unregister_workspace"),
        ]:
            function = next(
                node for node in module.body
                if isinstance(node, ast.FunctionDef) and node.name == function_name
            )
            lock = next(
                node for node in function.body
                if isinstance(node, ast.With)
                and any(
                    isinstance(item.context_expr, ast.Call)
                    and isinstance(item.context_expr.func, ast.Name)
                    and item.context_expr.func.id == "state_lock"
                    for item in node.items
                )
            )
            calls_inside_lock = {
                node.func.id
                for node in ast.walk(lock)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            calls_after_lock = {
                node.func.id
                for statement in function.body[function.body.index(lock) + 1 :]
                for node in ast.walk(statement)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            }
            self.assertIn(registry_call, calls_inside_lock)
            self.assertNotIn(registry_call, calls_after_lock)

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
