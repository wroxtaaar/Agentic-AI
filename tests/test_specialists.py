import unittest

from agents.specialists import SPECIALISTS


class SpecialistRegistryTests(unittest.TestCase):
    def test_team_includes_research_and_qa_roles(self):
        by_name = {specialist.name: specialist for specialist in SPECIALISTS}
        self.assertIn("research", by_name)
        self.assertIn("verifier", by_name)
        self.assertIn("QA", by_name["verifier"].mission)

    def test_research_triggers_on_comparison_tasks(self):
        research = next(s for s in SPECIALISTS if s.name == "research")
        self.assertTrue(any(word in research.triggers for word in ("research", "compare", "evaluate")))

    def test_coding_and_devops_roles_remain_available(self):
        names = {specialist.name for specialist in SPECIALISTS}
        self.assertIn("coding", names)
        self.assertIn("devops", names)
        self.assertIn("security", names)


if __name__ == "__main__":
    unittest.main()
