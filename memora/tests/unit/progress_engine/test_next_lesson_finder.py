"""Unit tests for next_lesson_finder functionality."""

import pytest
from memora.services.progress_engine.progress_computer import find_next_lesson


@pytest.fixture
def sample_progress_structure():
	"""Sample progress structure for testing."""
	return {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked",
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "unlocked",
				"is_linear": True,
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "unlocked",
						"is_linear": True,
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "unlocked",
								"is_linear": True,
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "unlocked"
									},
									{
										"id": "LESSON-002",
										"type": "lesson",
										"status": "locked"
									},
									{
										"id": "LESSON-003",
										"type": "lesson",
										"status": "locked"
									}
								]
							}
						]
					}
				]
			}
		]
	}


def test_find_next_lesson_first_unlocked_lesson(sample_progress_structure):
	"""find_next_lesson returns first unlocked not passed lesson."""
	next_lesson_id = find_next_lesson(sample_progress_structure)

	assert next_lesson_id == "LESSON-001"


def test_find_next_lesson_after_first_completed(sample_progress_structure):
	"""find_next_lesson returns second lesson after first is passed."""
	sample_progress_structure["children"][0]["children"][0]["children"][0]["children"][0]["status"] = "passed"
	sample_progress_structure["children"][0]["children"][0]["children"][0]["children"][1]["status"] = "unlocked"

	next_lesson_id = find_next_lesson(sample_progress_structure)

	assert next_lesson_id == "LESSON-002"


def test_find_next_lesson_all_passed():
	"""find_next_lesson returns None when all lessons are passed."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "passed",
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "passed",
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "passed",
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "passed",
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "passed"
									},
									{
										"id": "LESSON-002",
										"type": "lesson",
										"status": "passed"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id is None


def test_find_next_lesson_empty_subject():
	"""find_next_lesson returns None for subject with no lessons."""
	structure = {
		"id": "SUBJ-EMPTY",
		"type": "subject",
		"status": "unlocked",
		"children": []
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id is None


def test_find_next_lesson_no_unlocked_lessons():
	"""find_next_lesson returns None when all lessons are locked."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "locked",
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "locked",
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "locked",
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "locked",
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "locked"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id is None


def test_find_next_lesson_multiple_tracks():
	"""find_next_lesson works correctly with multiple tracks."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked",
		"is_linear": True,
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "passed",
				"is_linear": True,
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "passed",
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "passed",
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "passed"
									}
								]
							}
						]
					}
				]
			},
			{
				"id": "TRACK-002",
				"type": "track",
				"status": "unlocked",
				"is_linear": True,
				"children": [
					{
						"id": "UNIT-002",
						"type": "unit",
						"status": "unlocked",
						"children": [
							{
								"id": "TOPIC-002",
								"type": "topic",
								"status": "unlocked",
								"children": [
									{
										"id": "LESSON-002",
										"type": "lesson",
										"status": "unlocked"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id == "LESSON-002"


def test_find_next_lesson_nonlinear_progress():
	"""find_next_lesson works correctly with non-linear structure."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked",
		"is_linear": False,
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "unlocked",
				"is_linear": False,
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "unlocked",
						"is_linear": False,
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "unlocked",
								"is_linear": False,
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "passed"
									},
									{
										"id": "LESSON-002",
										"type": "lesson",
										"status": "passed"
									},
									{
										"id": "LESSON-003",
										"type": "lesson",
										"status": "unlocked"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id == "LESSON-003"


def test_find_next_lesson_skips_locked_container():
	"""find_next_lesson skips locked containers."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked",
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "passed",
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "passed",
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "passed",
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "passed"
									}
								]
							}
						]
					}
				]
			},
			{
				"id": "TRACK-002",
				"type": "track",
				"status": "locked",
				"children": [
					{
						"id": "UNIT-002",
						"type": "unit",
						"status": "locked",
						"children": [
							{
								"id": "TOPIC-002",
								"type": "topic",
								"status": "locked",
								"children": [
									{
										"id": "LESSON-002",
										"type": "lesson",
										"status": "locked"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id is None


def test_find_next_lesson_first_unlocked_in_second_track():
	"""find_next_lesson finds lesson in second track after first is fully passed."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked",
		"is_linear": True,
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "passed",
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "passed",
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "passed",
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "passed"
									}
								]
							}
						]
					}
				]
			},
			{
				"id": "TRACK-002",
				"type": "track",
				"status": "unlocked",
				"children": [
					{
						"id": "UNIT-002",
						"type": "unit",
						"status": "unlocked",
						"children": [
							{
								"id": "TOPIC-002",
								"type": "topic",
								"status": "unlocked",
								"children": [
									{
										"id": "LESSON-002",
										"type": "lesson",
										"status": "unlocked"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id == "LESSON-002"


def test_find_next_lesson_deeply_nested():
	"""find_next_lesson handles deeply nested structures."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked",
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "unlocked",
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "unlocked",
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "unlocked",
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "passed"
									},
									{
										"id": "LESSON-002",
										"type": "lesson",
										"status": "passed"
									},
									{
										"id": "LESSON-003",
										"type": "lesson",
										"status": "unlocked"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id == "LESSON-003"


def test_find_next_lesson_lesson_without_id():
	"""find_next_lesson handles lessons without id field gracefully."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked",
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "unlocked",
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "unlocked",
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "unlocked",
								"children": [
									{
										"type": "lesson",
										"status": "unlocked"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id is None


def test_find_next_lesson_mixed_passed_unpassed():
	"""find_next_lesson handles mixed passed/unpassed lessons correctly."""
	structure = {
		"id": "SUBJ-001",
		"type": "subject",
		"status": "unlocked",
		"children": [
			{
				"id": "TRACK-001",
				"type": "track",
				"status": "unlocked",
				"children": [
					{
						"id": "UNIT-001",
						"type": "unit",
						"status": "unlocked",
						"children": [
							{
								"id": "TOPIC-001",
								"type": "topic",
								"status": "unlocked",
								"children": [
									{
										"id": "LESSON-001",
										"type": "lesson",
										"status": "passed"
									},
									{
										"id": "LESSON-002",
										"type": "lesson",
										"status": "locked"
									},
									{
										"id": "LESSON-003",
										"type": "lesson",
										"status": "passed"
									},
									{
										"id": "LESSON-004",
										"type": "lesson",
										"status": "locked"
									}
								]
							}
						]
					}
				]
			}
		]
	}

	next_lesson_id = find_next_lesson(structure)

	assert next_lesson_id is None


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
