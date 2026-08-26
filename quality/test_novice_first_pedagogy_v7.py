from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COACH = ROOT / "skills" / "mastery-coach"
REFERENCES = COACH / "references"


class NoviceFirstPedagogyV7ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = (COACH / "SKILL.md").read_text(encoding="utf-8")
        cls.contract = (REFERENCES / "novice-first-teaching.md").read_text(encoding="utf-8")
        cls.learning = (REFERENCES / "learning-contract.md").read_text(encoding="utf-8")
        cls.diagnostic = (REFERENCES / "diagnostic-and-planning.md").read_text(encoding="utf-8")
        cls.session = (REFERENCES / "teaching-session.md").read_text(encoding="utf-8")
        cls.delivery = (REFERENCES / "lesson-delivery.md").read_text(encoding="utf-8")
        cls.assessment = (REFERENCES / "assessment-and-mastery.md").read_text(encoding="utf-8")
        cls.curriculum = (REFERENCES / "curriculum-ml-ai-llm.md").read_text(encoding="utf-8")

    def test_skill_routes_novices_to_one_directly_linked_contract_and_stays_concise(self) -> None:
        self.assertIn("[novice-first-teaching.md](references/novice-first-teaching.md)", self.skill)
        self.assertLessEqual(
            len(self.skill.splitlines()),
            175,
            "Keep detailed beginner pedagogy in the directly linked reference, not SKILL.md.",
        )
        for routed_reference in [self.diagnostic, self.session, self.delivery, self.assessment]:
            self.assertIn("novice-first-teaching.md", routed_reference)

    def test_beginner_turn_has_one_experience_one_move_and_a_hard_term_budget(self) -> None:
        lowered = self.contract.lower()
        for invariant in [
            "concrete experience before terminology",
            "exactly one mental move",
            "at most 2–3 new terms",
            "example + counterexample + visual",
            "one highlighted action",
        ]:
            self.assertIn(invariant, lowered)
        experience = lowered.index("concrete experience before terminology")
        naming = lowered.index("name the terminology")
        self.assertLess(experience, naming)

    def test_first_course_turn_starts_from_a_learner_problem_not_a_taxonomy(self) -> None:
        for source in [self.diagnostic, self.delivery, self.curriculum]:
            lowered = source.lower()
            self.assertIn("learner problem", lowered)
            self.assertIn("not a taxonomy", lowered)
        self.assertIn("百科全书", self.contract)

    def test_chinese_delivery_is_plain_conversational_and_jargon_is_delayed(self) -> None:
        lowered = self.contract.lower()
        self.assertIn("plain conversational chinese", lowered)
        self.assertIn("先说人话，再补术语", self.contract)
        self.assertIn("do not translate the internal curriculum map", lowered)
        self.assertRegex(self.contract, r"2[–-]3")

    def test_capability_evidence_names_the_atomic_behavior_and_support(self) -> None:
        evidence = self.contract.lower()
        for required in [
            "capability evidence precision",
            "observable behavior",
            "assistance used",
            "not observed",
            "do not infer neighboring capabilities",
        ]:
            self.assertIn(required, evidence)
        assessment = self.assessment.lower()
        self.assertIn("atomic behavior", assessment)
        self.assertIn("assistance used", assessment)

    def test_teaching_turn_spec_is_the_single_coordination_boundary(self) -> None:
        heading = re.search(
            r"## TeachingTurnSpec(?P<body>.*?)(?=\n## |\Z)",
            self.contract,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(heading)
        body = heading.group("body")
        for field in [
            "learner_problem",
            "current_target",
            "mental_move",
            "new_terms",
            "answer_options",
            "concrete_experience",
            "example",
            "counterexample",
            "visual",
            "action",
            "evidence_boundary",
            "feedback_plan",
        ]:
            self.assertIn(f"`{field}`", body)
        self.assertIn("exactly one `TeachingTurnSpec`", body)
        self.assertIn("below hint level 5", body)

    def test_optional_multi_agent_protocol_is_bounded_host_neutral_and_serialized(self) -> None:
        protocol = re.search(
            r"## Optional host-neutral multi-agent protocol(?P<body>.*?)(?=\n## |\Z)",
            self.contract,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(protocol)
        body = protocol.group("body").lower()
        for invariant in [
            "one learner-facing lead",
            "exactly one state writer",
            "roles are capped at four",
            "single teachingturnspec",
            "single-agent fallback",
        ]:
            self.assertIn(invariant, body)
        for host_specific in ["spawn_agent", "create_thread", "codex"]:
            self.assertNotIn(host_specific, body)

    def test_failure_mode_table_names_encyclopedia_opening(self) -> None:
        lowered = self.learning.lower()
        self.assertIn("encyclopedia opening", lowered)
        self.assertIn("problem → experience → language", lowered)


if __name__ == "__main__":
    unittest.main()
