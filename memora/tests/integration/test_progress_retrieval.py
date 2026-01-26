"""Integration tests for progress retrieval API"""

import pytest
import frappe
from frappe.tests.utils import FrappeTestCase
from memora.api.progress import get_progress
from memora.services.progress_engine import bitmap_manager


class TestProgressRetrieval(FrappeTestCase):
	"""Integration tests for get_progress endpoint."""

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

	def test_get_progress_no_completion(self):
		"""get_progress returns correct state with no lessons completed."""
		result = get_progress(subject_id=self.subject_id)

		assert result["subject_id"] == self.subject_id
		assert result["completion_percentage"] == 0.0
		assert result["total_lessons"] == 3
		assert result["passed_lessons"] == 0
		assert result["total_xp_earned"] == 0
		assert result["suggested_next_lesson_id"] == self.lesson_001.name

		assert result["root"]["status"] == "unlocked"

	def test_get_progress_first_lesson_completed(self):
		"""get_progress returns correct state after first lesson completed."""
		bitmap_manager.set_bit(self.player_id, self.subject_id, 0)

		result = get_progress(subject_id=self.subject_id)

		assert result["completion_percentage"] > 0.0
		assert result["passed_lessons"] == 1
		assert result["suggested_next_lesson_id"] == self.lesson_002.name

		assert result["root"]["status"] == "unlocked"

	def test_get_progress_all_lessons_completed(self):
		"""get_progress returns correct state after all lessons completed."""
		for i in range(3):
			bitmap_manager.set_bit(self.player_id, self.subject_id, i)

		result = get_progress(subject_id=self.subject_id)

		assert result["completion_percentage"] == 100.0
		assert result["passed_lessons"] == 3
		assert result["suggested_next_lesson_id"] is None

		assert result["root"]["status"] == "passed"

	def test_get_progress_linear_unlock_logic(self):
		"""get_progress respects linear unlock logic."""
		bitmap_manager.set_bit(self.player_id, self.subject_id, 0)

		result = get_progress(subject_id=self.subject_id)

		topic = result["root"]["children"][0]["children"][0]["children"][0]
		lessons = topic["children"]

		assert lessons[0]["status"] == "passed"
		assert lessons[1]["status"] == "unlocked"
		assert lessons[2]["status"] == "locked"

	def test_get_progress_nonlinear_unlock_logic(self):
		"""get_progress respects non-linear unlock logic."""
		subject = frappe.get_doc("Memora Subject", self.subject_id)
		subject.is_linear = False
		subject.save()

		topic = frappe.get_doc("Memora Topic", self.lesson_001.parent_topic)
		topic.is_linear = False
		topic.save()

		bitmap_manager.set_bit(self.player_id, self.subject_id, 1)

		result = get_progress(subject_id=self.subject_id)

		topic_node = result["root"]["children"][0]["children"][0]["children"][0]
		lessons = topic_node["children"]

		assert lessons[0]["status"] == "unlocked"
		assert lessons[1]["status"] == "passed"
		assert lessons[2]["status"] == "unlocked"

	def test_get_progress_container_state_passed(self):
		"""Container state is passed when all children passed."""
		for i in range(3):
			bitmap_manager.set_bit(self.player_id, self.subject_id, i)

		result = get_progress(subject_id=self.subject_id)

		topic = result["root"]["children"][0]["children"][0]["children"][0]
		unit = result["root"]["children"][0]["children"][0]
		track = result["root"]["children"][0]

		assert topic["status"] == "passed"
		assert unit["status"] == "passed"
		assert track["status"] == "passed"

	def test_get_progress_container_state_unpassed(self):
		"""Container state is unlocked when some children unpassed."""
		bitmap_manager.set_bit(self.player_id, self.subject_id, 0)

		result = get_progress(subject_id=self.subject_id)

		topic = result["root"]["children"][0]["children"][0]["children"][0]
		unit = result["root"]["children"][0]["children"][0]
		track = result["root"]["children"][0]

		assert topic["status"] == "unlocked"
		assert unit["status"] == "unlocked"
		assert track["status"] == "unlocked"

	def test_get_progress_completion_percentage_accuracy(self):
		"""completion_percentage is calculated accurately."""
		bitmap_manager.set_bit(self.player_id, self.subject_id, 0)

		result = get_progress(subject_id=self.subject_id)

		expected_percentage = (1 / 3) * 100
		assert abs(result["completion_percentage"] - expected_percentage) < 0.01

	def test_get_progress_node_structure_integrity(self):
		"""Progress tree structure matches subject structure."""
		result = get_progress(subject_id=self.subject_id)

		assert result["root"]["type"] == "subject"
		assert len(result["root"]["children"]) == 1

		track = result["root"]["children"][0]
		assert track["type"] == "track"
		assert len(track["children"]) == 1

		unit = track["children"][0]
		assert unit["type"] == "unit"
		assert len(unit["children"]) == 1

		topic = unit["children"][0]
		assert topic["type"] == "topic"
		assert len(topic["children"]) == 3

		for lesson in topic["children"]:
			assert lesson["type"] == "lesson"
			assert "bit_index" in lesson

	def test_get_progress_cached_bitmap_used(self):
		"""get_progress uses cached bitmap when available."""
		bitmap_manager.set_bit(self.player_id, self.subject_id, 0)

		result1 = get_progress(subject_id=self.subject_id)
		result2 = get_progress(subject_id=self.subject_id)

		assert result1["passed_lessons"] == result2["passed_lessons"] == 1

	def test_get_progress_with_best_hearts(self):
		"""get_progress includes best_hearts for passed lessons."""
		bitmap_manager.set_bit(self.player_id, self.subject_id, 0)
		bitmap_manager.set_bit(self.player_id, self.subject_id, 1)

		frappe.cache().set_value(
			f"best_hearts:{self.player_id}:{self.subject_id}",
			'{"LESSON-001": 5, "LESSON-002": 3}'
		)

		result = get_progress(subject_id=self.subject_id)

		topic = result["root"]["children"][0]["children"][0]["children"][0]
		lessons = topic["children"]

		assert lessons[0]["best_hearts"] == 5
		assert lessons[1]["best_hearts"] == 3
		assert "best_hearts" not in lessons[2]

	def test_get_progress_subject_not_found(self):
		"""get_progress raises error when subject not found."""
		with pytest.raises(frappe.ValidationError):
			get_progress(subject_id="INVALID-SUBJECT")

	def test_get_progress_empty_subject(self):
		"""get_progress handles subject with no lessons gracefully."""
		empty_subject = frappe.get_doc({
			"doctype": "Memora Subject",
			"title": "Empty Subject",
			"is_linear": True,
			"next_bit_index": 0
		}).insert()

		result = get_progress(subject_id=empty_subject.name)

		assert result["completion_percentage"] == 0.0
		assert result["total_lessons"] == 0
		assert result["passed_lessons"] == 0
		assert result["suggested_next_lesson_id"] is None

	def test_get_progress_player_not_enrolled(self):
		"""get_progress handles player not enrolled."""
		pass


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
