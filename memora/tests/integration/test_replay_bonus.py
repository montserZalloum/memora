"""Integration tests for replay bonus XP feature."""

import pytest
import frappe
from frappe.tests.utils import FrappeTestCase


class TestReplayBonusIntegration(FrappeTestCase):
	"""Integration tests for lesson replay and record-breaking XP bonuses."""

	def setUp(self):
		"""Set up test data before each test."""
		frappe.set_user("Administrator")

	def test_replay_beat_record_earns_bonus_xp(self):
		"""Test that beating previous record earns differential bonus XP."""
		player_id = "TEST-PLAYER-REPLAY-001"
		lesson_id = "TEST-LESSON-REPLAY-001"
		subject_id = "TEST-SUBJ-REPLAY-001"

		result1 = complete_lesson(lesson_id=lesson_id, hearts=3)
		
		assert result1["xp_earned"] == 40
		assert result1["is_first_completion"] is True
		assert result1["is_new_record"] is True

		result2 = complete_lesson(lesson_id=lesson_id, hearts=5)
		
		assert result2["xp_earned"] == 20
		assert result2["is_first_completion"] is False
		assert result2["is_new_record"] is True

		new_total_xp = result1["new_total_xp"] + result2["xp_earned"]
		assert result2["new_total_xp"] == new_total_xp

	def test_replay_lower_hearts_no_bonus(self):
		"""Test that replay with lower hearts earns no bonus."""
		player_id = "TEST-PLAYER-REPLAY-002"
		lesson_id = "TEST-LESSON-REPLAY-002"
		subject_id = "TEST-SUBJ-REPLAY-001"

		result1 = complete_lesson(lesson_id=lesson_id, hearts=5)
		
		assert result1["xp_earned"] == 60
		assert result1["is_first_completion"] is True

		result2 = complete_lesson(lesson_id=lesson_id, hearts=3)
		
		assert result2["xp_earned"] == 0
		assert result2["is_first_completion"] is False
		assert result2["is_new_record"] is False

		assert result2["new_total_xp"] == result1["new_total_xp"]

	def test_replay_same_hearts_no_bonus(self):
		"""Test that replay with same hearts earns no bonus."""
		player_id = "TEST-PLAYER-REPLAY-003"
		lesson_id = "TEST-LESSON-REPLAY-003"
		subject_id = "TEST-SUBJ-REPLAY-001"

		result1 = complete_lesson(lesson_id=lesson_id, hearts=4)
		
		assert result1["xp_earned"] == 50
		assert result1["is_first_completion"] is True

		result2 = complete_lesson(lesson_id=lesson_id, hearts=4)
		
		assert result2["xp_earned"] == 0
		assert result2["is_first_completion"] is False
		assert result2["is_new_record"] is False

		assert result2["new_total_xp"] == result1["new_total_xp"]

	def test_multiple_replays_progressive_improvements(self):
		"""Test multiple replays with progressive improvements."""
		player_id = "TEST-PLAYER-REPLAY-004"
		lesson_id = "TEST-LESSON-REPLAY-004"
		subject_id = "TEST-SUBJ-REPLAY-001"

		result1 = complete_lesson(lesson_id=lesson_id, hearts=1)
		assert result1["xp_earned"] == 20
		assert result1["is_new_record"] is True

		result2 = complete_lesson(lesson_id=lesson_id, hearts=3)
		assert result2["xp_earned"] == 20
		assert result2["is_new_record"] is True

		result3 = complete_lesson(lesson_id=lesson_id, hearts=4)
		assert result3["xp_earned"] == 10
		assert result3["is_new_record"] is True

		result4 = complete_lesson(lesson_id=lesson_id, hearts=5)
		assert result4["xp_earned"] == 10
		assert result4["is_new_record"] is True

	def test_replay_best_hearts_persists_in_redis(self):
		"""Test that best hearts data is stored in Redis."""
		player_id = "TEST-PLAYER-REPLAY-005"
		lesson_id = "TEST-LESSON-REPLAY-005"
		subject_id = "TEST-SUBJ-REPLAY-001"

		complete_lesson(lesson_id=lesson_id, hearts=4)

		from memora.services.progress_engine import bitmap_manager
		best_hearts_key = f"best_hearts:{player_id}:{subject_id}"
		best_hearts_data = frappe.cache().get(best_hearts_key)
		
		assert best_hearts_data is not None

	def test_replay_best_hearts_updates_on_record_break(self):
		"""Test that best hearts in Redis updates when record is broken."""
		player_id = "TEST-PLAYER-REPLAY-006"
		lesson_id = "TEST-LESSON-REPLAY-006"
		subject_id = "TEST-SUBJ-REPLAY-001"
		best_hearts_key = f"best_hearts:{player_id}:{subject_id}"

		complete_lesson(lesson_id=lesson_id, hearts=3)

		import json
		initial_best_hearts = json.loads(frappe.cache().get(best_hearts_key))
		assert initial_best_hearts[lesson_id] == 3

		complete_lesson(lesson_id=lesson_id, hearts=5)

		updated_best_hearts = json.loads(frappe.cache().get(best_hearts_key))
		assert updated_best_hearts[lesson_id] == 5

	def test_replay_mixed_across_lessons(self):
		"""Test replays across multiple different lessons."""
		player_id = "TEST-PLAYER-REPLAY-007"
		lesson1_id = "TEST-LESSON-REPLAY-007-1"
		lesson2_id = "TEST-LESSON-REPLAY-007-2"
		subject_id = "TEST-SUBJ-REPLAY-001"

		result1 = complete_lesson(lesson_id=lesson1_id, hearts=2)
		assert result1["xp_earned"] == 30

		result2 = complete_lesson(lesson_id=lesson2_id, hearts=4)
		assert result2["xp_earned"] == 50

		result3 = complete_lesson(lesson_id=lesson1_id, hearts=5)
		assert result3["xp_earned"] == 30

		result4 = complete_lesson(lesson_id=lesson2_id, hearts=5)
		assert result4["xp_earned"] == 10

	def test_replay_no_bonus_when_worse_than_best(self):
		"""Test that replay earns no XP when performing worse than best."""
		player_id = "TEST-PLAYER-REPLAY-008"
		lesson_id = "TEST-LESSON-REPLAY-008"
		subject_id = "TEST-SUBJ-REPLAY-001"

		result1 = complete_lesson(lesson_id=lesson_id, hearts=5)
		assert result1["xp_earned"] == 60

		result2 = complete_lesson(lesson_id=lesson_id, hearts=1)
		assert result2["xp_earned"] == 0
		assert result2["is_new_record"] is False


def complete_lesson(lesson_id: str, hearts: int) -> dict:
	"""Helper function to call complete_lesson API."""
	from memora.api.progress import complete_lesson
	return complete_lesson(lesson_id=lesson_id, hearts=hearts)


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
