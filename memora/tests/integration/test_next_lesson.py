"""Integration tests for next lesson suggestion."""

import pytest
import frappe
from frappe.tests.utils import FrappeTestCase
from memora.api.progress import get_progress
from memora.services.progress_engine import bitmap_manager


class TestNextLessonSuggestion(FrappeTestCase):
	"""Integration tests for suggested_next_lesson_id."""

	def setUp(self):
		"""Set up test fixtures."""
		self.setup_test_data()

	def tearDown(self):
		"""Clean up test data."""
		frappe.db.rollback()

	def setup_test_data(self):
		"""Create test subject structure and player."""
		player = frappe.get_doc({
			"doctype": "Memora Player Profile",
			"player_name": "Test Player Next Lesson",
			"email": "testnext@example.com"
		}).insert()

		self.player_id = player.name

		subject = frappe.get_doc({
			"doctype": "Memora Subject",
			"title": "Test Subject Next Lesson",
			"is_linear": True,
			"next_bit_index": 3
		}).insert()

		self.subject_id = subject.name

		track = frappe.get_doc({
			"doctype": "Memora Track",
			"title": "Test Track Next Lesson",
			"parent_subject": self.subject_id,
			"is_linear": True
		}).insert()

		unit = frappe.get_doc({
			"doctype": "Memora Unit",
			"title": "Test Unit Next Lesson",
			"parent_track": track.name,
			"is_linear": True
		}).insert()

		topic = frappe.get_doc({
			"doctype": "Memora Topic",
			"title": "Test Topic Next Lesson",
			"parent_unit": unit.name,
			"is_linear": True
		}).insert()

		self.lesson_001 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "Test Lesson 1 Next",
			"parent_topic": topic.name,
			"bit_index": 0
		}).insert()

		self.lesson_002 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "Test Lesson 2 Next",
			"parent_topic": topic.name,
			"bit_index": 1
		}).insert()

		self.lesson_003 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "Test Lesson 3 Next",
			"parent_topic": topic.name,
			"bit_index": 2
		}).insert()

		academic_plan = frappe.get_value("Memora Subject", self.subject_id, "academic_plan")

		progress = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": self.player_id,
			"subject": self.subject_id,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": "",
			"best_hearts_data": {},
			"total_xp_earned": 0
		}).insert()

		frappe.cache().delete_key(f"user_prog:{self.player_id}:{self.subject_id}")

	def test_get_progress_suggests_first_lesson_no_completion(self):
		"""suggested_next_lesson_id points to first lesson when no completion."""
		result = get_progress(subject_id=self.subject_id)

		assert result["suggested_next_lesson_id"] == self.lesson_001.name
		assert result["passed_lessons"] == 0

	def test_get_progress_suggests_second_lesson_after_first(self):
		"""suggested_next_lesson_id points to second lesson after first completed."""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)

		result = get_progress(subject_id=self.subject_id)

		assert result["suggested_next_lesson_id"] == self.lesson_002.name
		assert result["passed_lessons"] == 1

	def test_get_progress_suggests_third_lesson_after_two(self):
		"""suggested_next_lesson_id points to third lesson after two completed."""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 1)

		result = get_progress(subject_id=self.subject_id)

		assert result["suggested_next_lesson_id"] == self.lesson_003.name
		assert result["passed_lessons"] == 2

	def test_get_progress_no_suggestion_when_all_passed(self):
		"""suggested_next_lesson_id is None when all lessons passed."""
		for i in range(3):
			bitmap_manager.update_bitmap(self.player_id, self.subject_id, i)

		result = get_progress(subject_id=self.subject_id)

		assert result["suggested_next_lesson_id"] is None
		assert result["passed_lessons"] == 3
		assert result["completion_percentage"] == 100.0

	def test_get_progress_no_suggestion_when_empty_subject(self):
		"""suggested_next_lesson_id is None for subject with no lessons."""
		empty_subject = frappe.get_doc({
			"doctype": "Memora Subject",
			"title": "Empty Subject Next",
			"is_linear": True,
			"next_bit_index": 0
		}).insert()

		academic_plan = frappe.get_value("Memora Subject", empty_subject.name, "academic_plan")

		progress = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": self.player_id,
			"subject": empty_subject.name,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": "",
			"best_hearts_data": {},
			"total_xp_earned": 0
		}).insert()

		result = get_progress(subject_id=empty_subject.name)

		assert result["suggested_next_lesson_id"] is None
		assert result["total_lessons"] == 0
		assert result["passed_lessons"] == 0

	def test_get_progress_no_suggestion_when_all_locked(self):
		"""suggested_next_lesson_id is None when all lessons locked."""
		subject = frappe.get_doc({
			"doctype": "Memora Subject",
			"title": "Locked Subject Next",
			"is_linear": True,
			"next_bit_index": 1
		}).insert()

		track = frappe.get_doc({
			"doctype": "Memora Track",
			"title": "Locked Track",
			"parent_subject": subject.name,
			"is_linear": True
		}).insert()

		unit = frappe.get_doc({
			"doctype": "Memora Unit",
			"title": "Locked Unit",
			"parent_track": track.name,
			"is_linear": True
		}).insert()

		topic = frappe.get_doc({
			"doctype": "Memora Topic",
			"title": "Locked Topic",
			"parent_unit": unit.name,
			"is_linear": True
		}).insert()

		lesson = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "Locked Lesson",
			"parent_topic": topic.name,
			"bit_index": 10
		}).insert()

		academic_plan = frappe.get_value("Memora Subject", subject.name, "academic_plan")

		progress = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": self.player_id,
			"subject": subject.name,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": "",
			"best_hearts_data": {},
			"total_xp_earned": 0
		}).insert()

		result = get_progress(subject_id=subject.name)

		assert result["suggested_next_lesson_id"] is None

	def test_get_progress_suggestion_with_linear_unlock(self):
		"""suggested_next_lesson_id respects linear unlock rules."""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)

		result = get_progress(subject_id=self.subject_id)

		assert result["suggested_next_lesson_id"] == self.lesson_002.name

		topic = result["root"]["children"][0]["children"][0]["children"][0]
		assert topic["children"][0]["status"] == "passed"
		assert topic["children"][1]["status"] == "unlocked"
		assert topic["children"][2]["status"] == "locked"

	def test_get_progress_suggestion_with_nonlinear_unlock(self):
		"""suggested_next_lesson_id respects non-linear unlock rules."""
		subject = frappe.get_doc("Memora Subject", self.subject_id)
		subject.is_linear = False
		subject.save()

		topic = frappe.get_doc("Memora Topic", self.lesson_001.parent_topic)
		topic.is_linear = False
		topic.save()

		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 1)

		result = get_progress(subject_id=self.subject_id)

		assert result["suggested_next_lesson_id"] == self.lesson_001.name

		topic_node = result["root"]["children"][0]["children"][0]["children"][0]
		assert topic_node["children"][0]["status"] == "unlocked"
		assert topic_node["children"][1]["status"] == "passed"
		assert topic_node["children"][2]["status"] == "unlocked"

	def test_get_progress_suggestion_multiple_tracks(self):
		"""suggested_next_lesson_id works correctly with multiple tracks."""
		track2 = frappe.get_doc({
			"doctype": "Memora Track",
			"title": "Test Track 2 Next",
			"parent_subject": self.subject_id,
			"is_linear": True
		}).insert()

		unit2 = frappe.get_doc({
			"doctype": "Memora Unit",
			"title": "Test Unit 2 Next",
			"parent_track": track2.name,
			"is_linear": True
		}).insert()

		topic2 = frappe.get_doc({
			"doctype": "Memora Topic",
			"title": "Test Topic 2 Next",
			"parent_unit": unit2.name,
			"is_linear": True
		}).insert()

		lesson_004 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "Test Lesson 4 Next",
			"parent_topic": topic2.name,
			"bit_index": 3
		}).insert()

		for i in range(3):
			bitmap_manager.update_bitmap(self.player_id, self.subject_id, i)

		result = get_progress(subject_id=self.subject_id)

		assert result["suggested_next_lesson_id"] == lesson_004.name

	def test_get_progress_suggestion_completes_cycle(self):
		"""suggested_next_lesson_id completes full cycle correctly."""
		for i in range(3):
			bitmap_manager.update_bitmap(self.player_id, self.subject_id, i)

		result1 = get_progress(subject_id=self.subject_id)
		assert result1["suggested_next_lesson_id"] is None
		assert result1["completion_percentage"] == 100.0

		bitmap_manager.cache.delete_key(f"user_prog:{self.player_id}:{self.subject_id}")
		frappe.cache().delete_key(f"user_prog:{self.player_id}:{self.subject_id}")

		result2 = get_progress(subject_id=self.subject_id)
		assert result2["suggested_next_lesson_id"] is None

	def test_get_progress_suggestion_consistency(self):
		"""suggested_next_lesson_id returns consistent results."""
		result1 = get_progress(subject_id=self.subject_id)
		result2 = get_progress(subject_id=self.subject_id)

		assert result1["suggested_next_lesson_id"] == result2["suggested_next_lesson_id"]


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
