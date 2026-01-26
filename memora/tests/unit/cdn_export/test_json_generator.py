import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime


class TestGenerateManifestAtomic(unittest.TestCase):
    """Tests for generate_manifest_atomic() function - Phase 3: User Story 1"""

    def _setup_manifest_mocks(self):
        """Helper to setup common mocks for manifest tests"""
        patcher_frappe = patch('memora.services.cdn_export.json_generator.frappe')
        patcher_now = patch('memora.services.cdn_export.json_generator.now_datetime')
        patcher_overrides = patch('memora.services.cdn_export.json_generator.apply_plan_overrides')
        patcher_calc = patch('memora.services.cdn_export.json_generator.calculate_access_level')
        patcher_url = patch('memora.services.cdn_export.json_generator.get_content_url')

        mock_frappe = patcher_frappe.start()
        mock_now = patcher_now.start()
        mock_overrides = patcher_overrides.start()
        mock_calc = patcher_calc.start()
        mock_url = patcher_url.start()

        # Setup datetime
        mock_now.return_value = datetime(2026, 1, 26, 10, 0, 0)
        mock_now.return_value.timestamp = Mock(return_value=1706270400)
        mock_now.return_value.isoformat = Mock(return_value="2026-01-26T10:00:00")

        # Setup URL resolver
        mock_url.side_effect = lambda x: x

        # Setup overrides
        mock_overrides.return_value = {}

        return {
            'frappe': (patcher_frappe, mock_frappe),
            'now': (patcher_now, mock_now),
            'overrides': (patcher_overrides, mock_overrides),
            'calc': (patcher_calc, mock_calc),
            'url': (patcher_url, mock_url)
        }

    def test_generate_manifest_atomic_subjects_array_structure(self):
        """T014: Validate subjects array structure in manifest"""
        from memora.services.cdn_export.json_generator import generate_manifest_atomic

        mocks = self._setup_manifest_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]

            # Setup mock plan
            plan_doc = Mock()
            plan_doc.name = "PLAN-001"
            plan_doc.title = "Test Plan"
            plan_doc.season = None
            plan_doc.grade = None
            plan_doc.stream = None

            # Setup mock subjects
            subject1 = Mock()
            subject1.name = "SUBJ-001"
            subject1.title = "Mathematics"
            subject1.description = "Math subject"
            subject1.image = None
            subject1.color_code = None
            subject1.is_published = True
            subject1.is_linear = False

            subject2 = Mock()
            subject2.name = "SUBJ-002"
            subject2.title = "Science"
            subject2.description = None
            subject2.image = "/files/science.png"
            subject2.color_code = "#3B82F6"
            subject2.is_published = True
            subject2.is_linear = True

            # Setup plan subjects
            plan_subject1 = Mock()
            plan_subject1.subject = "SUBJ-001"

            plan_subject2 = Mock()
            plan_subject2.subject = "SUBJ-002"

            mock_frappe.get_all.side_effect = [
                [plan_subject1, plan_subject2],  # Plan subjects
                [subject1, subject2]  # Subjects
            ]

            # Mock calculate_access_level
            mock_calc.side_effect = ["public", "paid"]

            manifest = generate_manifest_atomic(plan_doc)

            # Assertions
            self.assertIsNotNone(manifest)
            self.assertEqual(manifest["plan_id"], "PLAN-001")
            self.assertEqual(manifest["title"], "Test Plan")
            self.assertIn("subjects", manifest)
            self.assertEqual(len(manifest["subjects"]), 2)

            # Validate subjects array structure
            for subject in manifest["subjects"]:
                self.assertIn("id", subject)
                self.assertIn("title", subject)
                self.assertIn("is_linear", subject)
                self.assertIn("hierarchy_url", subject)
                self.assertIn("bitmap_url", subject)
                self.assertIn("access", subject)
                self.assertIn("access_level", subject["access"])
                self.assertIn("is_published", subject["access"])
        finally:
            for patcher, _ in mocks.values():
                patcher.stop()

    def test_generate_manifest_atomic_includes_hierarchy_and_bitmap_urls(self):
        """T015: Manifest includes hierarchy_url and bitmap_url per subject"""
        from memora.services.cdn_export.json_generator import generate_manifest_atomic

        mocks = self._setup_manifest_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]

            # Setup mocks
            plan_doc = Mock()
            plan_doc.name = "PLAN-GRADE12-2024"
            plan_doc.title = "Grade 12"
            plan_doc.season = "2024"
            plan_doc.grade = "Grade 12"
            plan_doc.stream = "Scientific"

            # Setup subjects
            subject1 = Mock()
            subject1.name = "SUBJ-MATH"
            subject1.title = "Mathematics"
            subject1.description = None
            subject1.image = None
            subject1.color_code = None
            subject1.is_published = True
            subject1.is_linear = False

            plan_subject1 = Mock()
            plan_subject1.subject = "SUBJ-MATH"

            mock_frappe.get_all.side_effect = [
                [plan_subject1],
                [subject1]
            ]

            mock_calc.return_value = "paid"

            manifest = generate_manifest_atomic(plan_doc)

            # Verify hierarchy and bitmap URLs are present
            self.assertEqual(len(manifest["subjects"]), 1)
            subject = manifest["subjects"][0]

            # Should include hierarchy URL
            self.assertIn("hierarchy_url", subject)
            self.assertIn("PLAN-GRADE12-2024", subject["hierarchy_url"])
            self.assertIn("SUBJ-MATH_h.json", subject["hierarchy_url"])

            # Should include bitmap URL
            self.assertIn("bitmap_url", subject)
            self.assertIn("PLAN-GRADE12-2024", subject["bitmap_url"])
            self.assertIn("SUBJ-MATH_b.json", subject["bitmap_url"])
        finally:
            for patcher, _ in mocks.values():
                patcher.stop()

    def test_generate_manifest_atomic_empty_subjects_array(self):
        """T016: Empty subjects array when plan has no subjects"""
        from memora.services.cdn_export.json_generator import generate_manifest_atomic

        mocks = self._setup_manifest_mocks()
        try:
            mock_frappe = mocks['frappe'][1]

            # Setup mocks
            plan_doc = Mock()
            plan_doc.name = "PLAN-EMPTY"
            plan_doc.title = "Empty Plan"
            plan_doc.season = None
            plan_doc.grade = None
            plan_doc.stream = None

            # No plan subjects
            mock_frappe.get_all.side_effect = [
                [],  # Plan subjects empty
                []   # Subjects empty
            ]

            manifest = generate_manifest_atomic(plan_doc)

            # Verify empty subjects array
            self.assertIsNotNone(manifest)
            self.assertIn("subjects", manifest)
            self.assertEqual(len(manifest["subjects"]), 0)
            self.assertIsInstance(manifest["subjects"], list)
        finally:
            for patcher, _ in mocks.values():
                patcher.stop()


    def test_manifest_has_required_fields(self):
        """T020: Manifest has all required fields per schema"""
        mocks = self._setup_manifest_mocks()
        try:
            from memora.services.cdn_export.json_generator import generate_manifest_atomic

            mock_frappe = mocks['frappe'][1]

            # Setup plan
            plan_doc = Mock()
            plan_doc.name = "PLAN-001"
            plan_doc.title = "Test Plan"
            plan_doc.season = "2026"
            plan_doc.grade = "12"
            plan_doc.stream = "Science"

            # No subjects for simplicity
            mock_frappe.get_all.side_effect = [
                [],  # Plan subjects
                []   # Subjects
            ]

            manifest = generate_manifest_atomic(plan_doc)

            # Verify all required fields present
            required_fields = ["plan_id", "title", "version", "generated_at", "subjects"]
            for field in required_fields:
                self.assertIn(field, manifest, f"Missing required field: {field}")

            # Verify version is integer
            self.assertIsInstance(manifest["version"], int)

            # Verify generated_at is string
            self.assertIsInstance(manifest["generated_at"], str)

            # Verify subjects is array
            self.assertIsInstance(manifest["subjects"], list)

            # Verify optional season, grade, stream if provided
            self.assertIn("season", manifest)
            self.assertIn("grade", manifest)
            self.assertIn("stream", manifest)

        finally:
            for patcher, _ in mocks.values():
                patcher.stop()


if __name__ == '__main__':
    unittest.main()
