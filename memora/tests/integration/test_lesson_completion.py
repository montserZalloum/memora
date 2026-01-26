"""Integration tests for lesson completion flow."""

import pytest
import frappe
from frappe.tests.utils import FrappeTestCase


class TestLessonCompletionIntegration(FrappeTestCase):
	"""Integration tests for the complete lesson workflow."""

	def setUp(self):
		"""Set up test data before each test."""
		frappe.set_user("Administrator")

	def test_complete_lesson_full_flow(self):
		"""Test complete lesson from start to finish."""
		player_id = "TEST-PLAYER-001"
		lesson_id = "TEST-LESSON-001"
		subject_id = "TEST-SUBJ-001"

		complete_lesson(lesson_id=lesson_id, hearts=5)

		bitmap = frappe.cache().get(f"user_prog:{player_id}:{subject_id}")
		assert bitmap is not None

		progress = frappe.get_value(
			"Memora Player Wallet",
			{"player": player_id},
			"total_xp"
		)
		assert progress > 0

	def test_complete_lesson_with_replay(self):
		"""Test lesson completion and replay with bonus."""
		player_id = "TEST-PLAYER-002"
		lesson_id = "TEST-LESSON-002"
		subject_id = "TEST-SUBJ-001"

		result1 = complete_lesson(lesson_id=lesson_id, hearts=3)
		assert result1["xp_earned"] > 0
		assert result1["is_first_completion"] is True

		result2 = complete_lesson(lesson_id=lesson_id, hearts=5)
		assert result2["xp_earned"] > 0
		assert result2["is_new_record"] is True

	def test_complete_lesson_no_hearts_error(self):
		"""Test error when player has no hearts."""
		lesson_id = "TEST-LESSON-003"

		with self.assertRaises(frappe.ValidationError) as context:
			complete_lesson(lesson_id=lesson_id, hearts=0)

		assert "NO_HEARTS" in str(context.exception)

	def test_complete_lesson_progress_persists(self):
		"""Test that lesson completion persists in Redis."""
		player_id = "TEST-PLAYER-003"
		lesson_id = "TEST-LESSON-004"
		subject_id = "TEST-SUBJ-001"

		complete_lesson(lesson_id=lesson_id, hearts=4)

		bitmap_key = f"user_prog:{player_id}:{subject_id}"
		bitmap = frappe.cache().get(bitmap_key)
		assert bitmap is not None

		dirty_keys = frappe.cache().smembers("progress_dirty_keys")
		assert bitmap_key in dirty_keys

	def test_complete_lesson_updates_wallet(self):
		"""Test that XP is added to player wallet."""
		player_id = "TEST-PLAYER-004"
		lesson_id = "TEST-LESSON-005"

		initial_xp = frappe.get_value(
			"Memora Player Wallet",
			{"player": player_id},
			"total_xp"
		) or 0

		result = complete_lesson(lesson_id=lesson_id, hearts=5)

		new_xp = frappe.get_value(
			"Memora Player Wallet",
			{"player": player_id},
			"total_xp"
		)

		assert new_xp == initial_xp + result["xp_earned"]

	def test_complete_lesson_logs_interaction(self):
		"""Test that lesson completion is logged."""
		lesson_id = "TEST-LESSON-006"

		result = complete_lesson(lesson_id=lesson_id, hearts=4)

		logs = frappe.get_all(
			"Memora Interaction Log",
			filters={
				"interaction_type": "lesson_completion",
				"reference_id": lesson_id
			}
		)

		assert len(logs) > 0


def complete_lesson(lesson_id: str, hearts: int) -> dict:
	"""Helper function to call complete_lesson API."""
	from memora.api.progress import complete_lesson
	return complete_lesson(lesson_id=lesson_id, hearts=hearts)


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
