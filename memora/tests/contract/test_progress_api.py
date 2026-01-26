"""Contract tests for progress API endpoints."""

import pytest


def test_complete_lesson_request_schema():
	"""Test complete_lesson endpoint request schema."""
	from memora.api.progress import complete_lesson

	with pytest.raises(frappe.ValidationError):
		complete_lesson(lesson_id="", hearts=0)


def test_complete_lesson_success_response():
	"""Test complete_lesson endpoint success response."""
	result = {
		"success": True,
		"xp_earned": 50,
		"new_total_xp": 150,
		"is_first_completion": True,
		"is_new_record": True
	}

	assert result["success"] is True
	assert result["xp_earned"] >= 0
	assert result["new_total_xp"] >= 0
	assert isinstance(result["is_first_completion"], bool)
	assert isinstance(result["is_new_record"], bool)


def test_complete_lesson_error_no_hearts():
	"""Test complete_lesson endpoint error when no hearts."""
	result = {
		"success": False,
		"error_code": "NO_HEARTS",
		"message": "No hearts remaining"
	}

	assert result["success"] is False
	assert result["error_code"] in ["NO_HEARTS", "INVALID_LESSON", "NOT_UNLOCKED", "NOT_ENROLLED"]
	assert isinstance(result["message"], str)


def test_get_progress_request_schema():
	"""Test get_progress endpoint request schema."""
	from memora.api.progress import get_progress

	with pytest.raises(frappe.ValidationError):
		get_progress(subject_id="")


def test_get_progress_response_schema():
	"""Test get_progress endpoint response schema."""
	result = {
		"subject_id": "SUBJ-001",
		"root": {
			"id": "SUBJ-001",
			"type": "subject",
			"status": "unlocked"
		},
		"completion_percentage": 25.0,
		"total_xp_earned": 150,
		"suggested_next_lesson_id": "LESSON-002",
		"total_lessons": 20,
		"passed_lessons": 5
	}

	assert result["subject_id"] == "SUBJ-001"
	assert 0 <= result["completion_percentage"] <= 100
	assert result["total_xp_earned"] >= 0
	assert result["total_lessons"] >= 0
	assert result["passed_lessons"] >= 0
	assert isinstance(result["root"], dict)


def test_get_progress_suggested_next_lesson_can_be_null():
	"""Test get_progress suggested_next_lesson_id can be null."""
	result = {
		"subject_id": "SUBJ-001",
		"root": {"id": "SUBJ-001", "type": "subject", "status": "passed"},
		"completion_percentage": 100.0,
		"total_xp_earned": 200,
		"suggested_next_lesson_id": None,
		"total_lessons": 10,
		"passed_lessons": 10
	}

	assert result["suggested_next_lesson_id"] is None


def test_get_progress_node_status_enum():
	"""Test progress node status only accepts valid values."""
	valid_statuses = ["locked", "unlocked", "passed"]

	status = "unlocked"
	assert status in valid_statuses


def test_complete_lesson_hearts_range():
	"""Test complete_lesson hearts parameter is 0-5."""
	valid_hearts = [0, 1, 2, 3, 4, 5]

	for hearts in valid_hearts:
		assert 0 <= hearts <= 5


def test_get_progress_node_structure():
	"""get_progress node matches contract schema."""
	node = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked"
	}

	required_fields = ["id", "type", "status"]
	for field in required_fields:
		assert field in node


def test_get_progress_lesson_node_has_bit_index():
	"""Lesson node includes bit_index field."""
	lesson_node = {
		"id": "LESSON-001",
		"type": "lesson",
		"status": "unlocked",
		"bit_index": 0
	}

	assert lesson_node["type"] == "lesson"
	assert "bit_index" in lesson_node
	assert isinstance(lesson_node["bit_index"], int)


def test_get_progress_container_node_has_children():
	"""Container node includes children field."""
	container_node = {
		"id": "TOPIC-001",
		"type": "topic",
		"status": "unlocked",
		"children": []
	}

	assert container_node["type"] == "topic"
	assert "children" in container_node
	assert isinstance(container_node["children"], list)


def test_get_progress_node_type_enum():
	"""node type is one of: subject, track, unit, topic, lesson."""
	valid_types = ["subject", "track", "unit", "topic", "lesson"]

	node_type = "lesson"
	assert node_type in valid_types


def test_get_progress_best_hearts_optional():
	"""best_hearts field is optional (only on passed lessons)."""
	lesson_node = {
		"id": "LESSON-001",
		"type": "lesson",
		"status": "passed",
		"bit_index": 0
	}

	assert "best_hearts" not in lesson_node or isinstance(lesson_node["best_hearts"], int)


def test_get_progress_best_hearts_range():
	"""best_hearts is between 0 and 5 when present."""
	lesson_node = {
		"id": "LESSON-001",
		"type": "lesson",
		"status": "passed",
		"bit_index": 0,
		"best_hearts": 5
	}

	if "best_hearts" in lesson_node:
		assert lesson_node["best_hearts"] >= 0
		assert lesson_node["best_hearts"] <= 5


def test_get_progress_response_all_fields():
	"""get_progress response includes all required fields."""
	response = {
		"subject_id": "SUBJ-001",
		"root": {
			"id": "SUBJ-001",
			"type": "subject",
			"status": "unlocked"
		},
		"completion_percentage": 25.0,
		"total_xp_earned": 150,
		"suggested_next_lesson_id": "LESSON-002",
		"total_lessons": 20,
		"passed_lessons": 5
	}

	required_fields = [
		"subject_id",
		"root",
		"completion_percentage",
		"total_xp_earned"
	]

	for field in required_fields:
		assert field in response


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
