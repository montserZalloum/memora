"""
XP Calculator - Calculate XP for lesson completion.

This module provides functions to calculate XP earned from lesson completion,
including base XP, hearts bonus, and record-breaking bonuses for replays.
"""

import logging

logger = logging.getLogger(__name__)


def calculate_xp(
	lesson_id: str,
	hearts: int,
	is_first_completion: bool,
	best_hearts_data: dict,
	base_xp: int = 10
) -> dict:
	"""Calculate XP earned from lesson completion.

	Args:
		lesson_id: Unique identifier of lesson
		hearts: Hearts remaining at completion (0-5)
		is_first_completion: Whether this is first time completing the lesson
		best_hearts_data: Dictionary mapping lesson_id → best hearts achieved
		base_xp: Base XP awarded on first completion (default: 10)

	Returns:
		Dictionary with keys:
			- xp_earned: XP earned from this completion
			- is_new_record: True if this beat the previous best
			- best_hearts_data: Updated best_hearts_data dictionary
	"""
	# Clamp hearts to valid range
	hearts = max(0, min(5, hearts))

	xp = 0
	is_new_record = False

	# Make a copy to avoid mutating
	updated_best_hearts_data = dict(best_hearts_data)

	if is_first_completion:
		# First completion: base XP + hearts bonus
		xp = base_xp + (hearts * 10)
		is_new_record = True
		updated_best_hearts_data[lesson_id] = hearts
		logger.info(f"First completion for lesson={lesson_id}, hearts={hearts}, xp={xp}")
	else:
		# Replay: award record-breaking bonus if applicable
		prev_best = updated_best_hearts_data.get(lesson_id, 0)
		if hearts > prev_best:
			xp = (hearts - prev_best) * 10
			is_new_record = True
			updated_best_hearts_data[lesson_id] = hearts
			logger.info(f"Record break for lesson={lesson_id}, prev={prev_best}, new={hearts}, bonus_xp={xp}")
		else:
			logger.debug(f"No record break for lesson={lesson_id}, prev={prev_best}, current={hearts}")

	return {
		"xp_earned": xp,
		"is_new_record": is_new_record,
		"best_hearts_data": updated_best_hearts_data
	}
