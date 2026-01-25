import unittest
from unittest.mock import patch, call
from memora.services.cdn_export.dependency_resolver import get_affected_plan_ids

class TestDependencyResolver(unittest.TestCase):

    @patch('frappe.db.get_value')
    @patch('frappe.db.get_all')
    def test_lesson_change_resolves_to_plan(self, mock_get_all, mock_get_value):
        # Arrange
        mock_get_value.side_effect = [
            "TOPIC-001", # parent_topic of LESSON-001
            "UNIT-001",  # parent_unit of TOPIC-001
            "TRACK-001", # parent_track of UNIT-001
            "SUBJECT-001" # parent_subject of TRACK-001
        ]
        mock_get_all.return_value = ["PLAN-001", "PLAN-002"]

        # Act
        plan_ids = get_affected_plan_ids("Memora Lesson", "LESSON-001")

        # Assert
        self.assertEqual(sorted(plan_ids), ["PLAN-001", "PLAN-002"])
        
        mock_get_value.assert_has_calls([
            call("Memora Lesson", "LESSON-001", "parent_topic"),
            call("Memora Topic", "TOPIC-001", "parent_unit"),
            call("Memora Unit", "UNIT-001", "parent_track"),
            call("Memora Track", "TRACK-001", "parent_subject"),
        ])
        
        mock_get_all.assert_called_once_with(
            "Memora Plan Subject",
            filters={"subject": "SUBJECT-001"},
            pluck="parent"
        )

    @patch('frappe.db.get_value')
    @patch('frappe.db.get_all')
    def test_subject_change_resolves_to_plan(self, mock_get_all, mock_get_value):
        # Arrange
        mock_get_all.return_value = ["PLAN-003"]

        # Act
        plan_ids = get_affected_plan_ids("Memora Subject", "SUBJECT-002")

        # Assert
        self.assertEqual(plan_ids, ["PLAN-003"])
        mock_get_value.assert_not_called()
        mock_get_all.assert_called_once_with(
            "Memora Plan Subject",
            filters={"subject": "SUBJECT-002"},
            pluck="parent"
        )
        
    @patch('frappe.db.get_all')
    def test_unrelated_doctype(self, mock_get_all):
        # Act
        plan_ids = get_affected_plan_ids("User", "test@example.com")

        # Assert
        self.assertEqual(plan_ids, [])
        mock_get_all.assert_not_called()

if __name__ == '__main__':
    unittest.main()
