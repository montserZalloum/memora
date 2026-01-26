"""Unit tests for XP calculator."""

import pytest


def test_calculate_xp_first_completion_no_hearts():
	"""Test XP calculation for first completion with 0 hearts."""
	from memora.services.progress_engine.xp_calculator import calculate_xp

	result = calculate_xp(
		lesson_id="LESSON-001",
		hearts=0,
		is_first_completion=True,
		best_hearts_data={},
		base_xp=10
	)

	assert result["xp_earned"] == 10
	assert result["is_new_record"] is True
	assert result["best_hearts_data"]["LESSON-001"] == 0


def test_calculate_xp_first_completion_with_hearts():
	"""Test XP calculation for first completion with hearts."""
	from memora.services.progress_engine.xp_calculator import calculate_xp

	result = calculate_xp(
		lesson_id="LESSON-001",
		hearts=5,
		is_first_completion=True,
		best_hearts_data={},
		base_xp=10
	)

	assert result["xp_earned"] == 60  # base 10 + (5 * 10)
	assert result["is_new_record"] is True
	assert result["best_hearts_data"]["LESSON-001"] == 5


def test_calculate_xp_replay_lower_hearts():
	"""Test XP calculation for replay with lower hearts (no bonus)."""
	from memora.services.progress_engine.xp_calculator import calculate_xp

	result = calculate_xp(
		lesson_id="LESSON-001",
		hearts=3,
		is_first_completion=False,
		best_hearts_data={"LESSON-001": 5},
		base_xp=10
	)

	assert result["xp_earned"] == 0
	assert result["is_new_record"] is False
	assert result["best_hearts_data"]["LESSON-001"] == 5


def test_calculate_xp_replay_same_hearts():
	"""Test XP calculation for replay with same hearts (no bonus)."""
	from memora.services.progress_engine.xp_calculator import calculate_xp

	result = calculate_xp(
		lesson_id="LESSON-001",
		hearts=5,
		is_first_completion=False,
		best_hearts_data={"LESSON-001": 5},
		base_xp=10
	)

	assert result["xp_earned"] == 0
	assert result["is_new_record"] is False
	assert result["best_hearts_data"]["LESSON-001"] == 5


def test_calculate_xp_replay_new_record():
	"""Test XP calculation for replay with new record."""
	from memora.services.progress_engine.xp_calculator import calculate_xp

	result = calculate_xp(
		lesson_id="LESSON-001",
		hearts=5,
		is_first_completion=False,
		best_hearts_data={"LESSON-001": 3},
		base_xp=10
	)

	assert result["xp_earned"] == 20  # (5 - 3) * 10
	assert result["is_new_record"] is True
	assert result["best_hearts_data"]["LESSON-001"] == 5


def test_calculate_xp_multiple_lessons_in_data():
	"""Test XP calculation maintains data for multiple lessons."""
	from memora.services.progress_engine.xp_calculator import calculate_xp

	initial_data = {"LESSON-001": 3, "LESSON-002": 4}
	result = calculate_xp(
		lesson_id="LESSON-001",
		hearts=5,
		is_first_completion=False,
		best_hearts_data=initial_data,
		base_xp=10
	)

	assert result["xp_earned"] == 20
	assert result["is_new_record"] is True
	assert result["best_hearts_data"]["LESSON-001"] == 5
	assert result["best_hearts_data"]["LESSON-002"] == 4


def test_calculate_xp_invalid_hearts():
	"""Test XP calculation with invalid hearts (should clamp to 0-5)."""
	from memora.services.progress_engine.xp_calculator import calculate_xp

	result = calculate_xp(
		lesson_id="LESSON-001",
		hearts=6,
		is_first_completion=True,
		best_hearts_data={},
		base_xp=10
	)

	assert result["xp_earned"] == 60  # base 10 + (5 * 10) - hearts clamped to 5
	assert result["best_hearts_data"]["LESSON-001"] == 5


def test_calculate_xp_negative_hearts():
	"""Test XP calculation with negative hearts (should clamp to 0)."""
	from memora.services.progress_engine.xp_calculator import calculate_xp

	result = calculate_xp(
		lesson_id="LESSON-001",
		hearts=-1,
		is_first_completion=True,
		best_hearts_data={},
		base_xp=10
	)

	assert result["xp_earned"] == 10  # base 10 + (0 * 10)
	assert result["best_hearts_data"]["LESSON-001"] == 0


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
