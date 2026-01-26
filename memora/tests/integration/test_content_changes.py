"""Integration tests for content management resilience.

Tests that lesson reordering, deletion, and addition don't break
existing student progress tracking.
"""

import pytest
import frappe
from frappe.tests.utils import FrappeTestCase
from memora.api.progress import get_progress
from memora.services.progress_engine import bitmap_manager
from memora.services.progress_engine.structure_loader import load_subject_structure
from memora.services.cdn_export.json_generator import generate_subject_json


class TestContentChanges(FrappeTestCase):
	"""Integration tests for content management resilience."""

	def setUp(self):
		"""Set up test fixtures."""
		frappe.set_user("Administrator")
		self.setup_test_data()

	def tearDown(self):
		"""Clean up test data."""
		frappe.db.rollback()

	def setup_test_data(self):
		"""Create test subject structure and player."""
		player = frappe.get_doc({
			"doctype": "Memora Player Profile",
			"player_name": "Test Player",
			"email": "test@example.com"
		}).insert()

		self.player_id = player.name

		subject = frappe.get_doc({
			"doctype": "Memora Subject",
			"title": "Test Subject",
			"is_linear": True,
			"next_bit_index": 3
		}).insert()

		self.subject_id = subject.name

		track = frappe.get_doc({
			"doctype": "Memora Track",
			"title": "Test Track",
			"parent_subject": self.subject_id,
			"is_linear": True
		}).insert()

		unit = frappe.get_doc({
			"doctype": "Memora Unit",
			"title": "Test Unit",
			"parent_track": track.name,
			"is_linear": True
		}).insert()

		topic = frappe.get_doc({
			"doctype": "Memora Topic",
			"title": "Test Topic",
			"parent_unit": unit.name,
			"is_linear": True
		}).insert()

		self.lesson_001 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "Test Lesson 1",
			"parent_topic": topic.name,
			"bit_index": 0
		}).insert()

		self.lesson_002 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "Test Lesson 2",
			"parent_topic": topic.name,
			"bit_index": 1
		}).insert()

		self.lesson_003 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "Test Lesson 3",
			"parent_topic": topic.name,
			"bit_index": 2
		}).insert()

		frappe.cache().delete_key(f"user_prog:{self.player_id}:{self.subject_id}")

	def test_progress_unchanged_after_lesson_reorder(self):
		"""Progress remains valid after lesson sort_order changes.

		When lessons are reordered (sort_order changes), the progress
		should still be tracked correctly using bit_index, not sort_order.
		"""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 2)

		result_before = get_progress(subject_id=self.subject_id)
		assert result_before["passed_lessons"] == 2

		lesson_002 = frappe.get_doc("Memora Lesson", self.lesson_002.name)
		original_sort_order = lesson_002.sort_order
		lesson_002.sort_order = 999
		lesson_002.save()

		result_after = get_progress(subject_id=self.subject_id)

		assert result_after["passed_lessons"] == 2
		assert result_after["total_lessons"] == 3

		topic = result_after["root"]["children"][0]["children"][0]["children"][0]
		lessons = {l["id"]: l["status"] for l in topic["children"]}

		assert lessons[self.lesson_001.name] == "passed"
		assert lessons[self.lesson_002.name] == "not_passed"
		assert lessons[self.lesson_003.name] == "passed"

	def test_progress_after_reorder_with_json_regenerate(self):
		"""Progress correct after reorder and JSON regeneration."""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 1)

		result_before = get_progress(subject_id=self.subject_id)
		assert result_before["passed_lessons"] == 1

		self.lesson_002.sort_order = 0
		self.lesson_002.save()
		self.lesson_001.sort_order = 1
		self.lesson_001.save()

		generate_subject_json(self.subject_id)

		result_after = get_progress(subject_id=self.subject_id)

		assert result_after["passed_lessons"] == 1
		assert result_after["total_lessons"] == 3

		topic = result_after["root"]["children"][0]["children"][0]["children"][0]
		lessons = {l["id"]: l["status"] for l in topic["children"]}

		assert lessons[self.lesson_001.name] == "not_passed"
		assert lessons[self.lesson_002.name] == "passed"
		assert lessons[self.lesson_003.name] == "not_passed"

	def test_progress_handles_deleted_lesson_gracefully(self):
		"""Progress computation skips deleted lessons (not in JSON).

		When a lesson is deleted from the subject (not in JSON file),
		it should be gracefully skipped during progress computation.
		"""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 1)

		result_before = get_progress(subject_id=self.subject_id)
		assert result_before["passed_lessons"] == 2

		self.lesson_002.delete()

		generate_subject_json(self.subject_id)

		result_after = get_progress(subject_id=self.subject_id)

		assert result_after["passed_lessons"] == 1
		assert result_after["total_lessons"] == 2

		topic = result_after["root"]["children"][0]["children"][0]["children"][0]
		lesson_ids = [l["id"] for l in topic["children"]]

		assert self.lesson_001.name in lesson_ids
		assert self.lesson_002.name not in lesson_ids
		assert self.lesson_003.name in lesson_ids

	def test_progress_after_multiple_deletions(self):
		"""Progress correct after multiple lesson deletions."""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 1)
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 2)

		result_before = get_progress(subject_id=self.subject_id)
		assert result_before["passed_lessons"] == 3
		assert result_before["completion_percentage"] == 100.0

		self.lesson_001.delete()
		self.lesson_003.delete()

		generate_subject_json(self.subject_id)

		result_after = get_progress(subject_id=self.subject_id)

		assert result_after["passed_lessons"] == 0
		assert result_after["total_lessons"] == 1

	def test_new_lesson_gets_unique_bit_index(self):
		"""New lessons receive unique bit_index from subject counter.

		When a new lesson is added, it should get a unique bit_index
		from the subject's next_bit_index counter.
		"""
		subject = frappe.get_doc("Memora Subject", self.subject_id)
		initial_next_bit_index = subject.next_bit_index

		new_lesson = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "New Lesson",
			"parent_topic": self.lesson_001.parent_topic
		}).insert()

		assert new_lesson.bit_index == initial_next_bit_index

		subject = frappe.get_doc("Memora Subject", self.subject_id)
		assert subject.next_bit_index == initial_next_bit_index + 1

	def test_multiple_new_lessons_get_unique_bit_indices(self):
		"""Multiple new lessons receive consecutive unique bit_indices."""
		subject = frappe.get_doc("Memora Subject", self.subject_id)
		initial_next_bit_index = subject.next_bit_index

		new_lesson_1 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "New Lesson 1",
			"parent_topic": self.lesson_001.parent_topic
		}).insert()

		new_lesson_2 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "New Lesson 2",
			"parent_topic": self.lesson_001.parent_topic
		}).insert()

		new_lesson_3 = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "New Lesson 3",
			"parent_topic": self.lesson_001.parent_topic
		}).insert()

		assert new_lesson_1.bit_index == initial_next_bit_index
		assert new_lesson_2.bit_index == initial_next_bit_index + 1
		assert new_lesson_3.bit_index == initial_next_bit_index + 2

		subject = frappe.get_doc("Memora Subject", self.subject_id)
		assert subject.next_bit_index == initial_next_bit_index + 3

	def test_progress_includes_newly_added_lesson(self):
		"""Progress includes newly added lessons after JSON regeneration."""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)

		result_before = get_progress(subject_id=self.subject_id)
		assert result_before["total_lessons"] == 3

		subject = frappe.get_doc("Memora Subject", self.subject_id)
		initial_next_bit_index = subject.next_bit_index

		new_lesson = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "New Lesson",
			"parent_topic": self.lesson_001.parent_topic
		}).insert()

		generate_subject_json(self.subject_id)

		result_after = get_progress(subject_id=self.subject_id)

		assert result_after["total_lessons"] == 4
		assert result_after["passed_lessons"] == 1

	def test_new_lesson_not_affecting_existing_progress(self):
		"""Adding new lessons doesn't affect existing student progress."""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 1)

		result_before = get_progress(subject_id=self.subject_id)
		assert result_before["passed_lessons"] == 2
		assert result_before["total_lessons"] == 3
		expected_percentage = (2 / 3) * 100

		new_lesson = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "New Lesson",
			"parent_topic": self.lesson_001.parent_topic
		}).insert()

		generate_subject_json(self.subject_id)

		result_after = get_progress(subject_id=self.subject_id)

		assert result_after["passed_lessons"] == 2
		assert result_after["total_lessons"] == 4

		new_percentage = (2 / 4) * 100

		assert abs(result_after["percentage_difference"] - (new_percentage - expected_percentage)) < 0.01

	def test_unlock_states_correct_after_content_changes(self):
		"""Unlock states remain correct after content modifications."""
		bitmap_manager.update_bitmap(self.player_id, self.subject_id, 0)

		result_before = get_progress(subject_id=self.subject_id)

		topic_before = result_before["root"]["children"][0]["children"][0]["children"][0]
		lessons_before = topic_before["children"]

		assert lessons_before[0]["status"] == "passed"
		assert lessons_before[1]["status"] == "unlocked"
		assert lessons_before[2]["status"] == "locked"

		self.lesson_002.delete()

		generate_subject_json(self.subject_id)

		result_after = get_progress(subject_id=self.subject_id)

		topic_after = result_after["root"]["children"][0]["children"][0]["children"][0]
		lessons_after = topic_after["children"]

		assert lessons_after[0]["status"] == "passed"
		assert lessons_after[1]["status"] == "unlocked"

	def test_bit_index_unchanged_after_content_changes(self):
		"""Bit indices remain immutable after content changes."""
		original_bit_indices = {
			self.lesson_001.name: self.lesson_001.bit_index,
			self.lesson_002.name: self.lesson_002.bit_index,
			self.lesson_003.name: self.lesson_003.bit_index
		}

		self.lesson_002.sort_order = 999
		self.lesson_002.save()

		new_lesson = frappe.get_doc({
			"doctype": "Memora Lesson",
			"title": "New Lesson",
			"parent_topic": self.lesson_001.parent_topic
		}).insert()

		lesson_001_after = frappe.get_doc("Memora Lesson", self.lesson_001.name)
		lesson_002_after = frappe.get_doc("Memora Lesson", self.lesson_002.name)
		lesson_003_after = frappe.get_doc("Memora Lesson", self.lesson_003.name)

		assert lesson_001_after.bit_index == original_bit_indices[self.lesson_001.name]
		assert lesson_002_after.bit_index == original_bit_indices[self.lesson_002.name]
		assert lesson_003_after.bit_index == original_bit_indices[self.lesson_003.name]

		assert new_lesson.bit_index == 3


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
