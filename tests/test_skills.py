"""Unit tests for Skill search, retrieval, versioning, and provenance."""
import unittest
from backend.services.skill_service import skill_service
from backend.models.skill import SkillVersion

class TestSkillManagement(unittest.TestCase):

    def test_preseeded_skills(self):
        skill = skill_service.get_skill("correlation_001")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.current_version, 1)
        self.assertIn(1, skill.versions)

    def test_semantic_search(self):
        matches = skill_service.search_skills("correlation between sales and profit")
        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0].skill_id, "correlation_001")

    def test_skill_versioning(self):
        initial_ver = skill_service.get_skill("coefficient_variation_001").current_version
        v_next = skill_service.update_skill_version(
            skill_id="coefficient_variation_001",
            modifications={
                "logic": "Use population standard deviation ddof=0",
                "formula": "CV = (std_pop / mean) * 100"
            },
            feedback="Use population standard deviation"
        )
        self.assertEqual(v_next.version, initial_ver + 1)

        # Ensure v1 is preserved (Section 26: never blindly overwrite a skill)
        v1 = skill_service.get_skill_version("coefficient_variation_001", 1)
        self.assertIsNotNone(v1)
        self.assertIn("ddof=1", v1.logic)

        # Current version is updated
        updated_skill = skill_service.get_skill("coefficient_variation_001")
        self.assertEqual(updated_skill.current_version, initial_ver + 1)

if __name__ == "__main__":
    unittest.main()
