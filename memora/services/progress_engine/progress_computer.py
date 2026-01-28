"""Progress computer for progress engine.

This module orchestrates computation of progress by combining:
1. Bitmap retrieval (from Redis or fallback to MariaDB)
2. Subject structure loading
3. Unlock state calculation
4. Next lesson suggestion
5. Completion percentage calculation
"""

import logging
from typing import Dict, Any, Optional

import frappe

from memora.services.progress_engine.bitmap_manager import get_bitmap
from memora.services.progress_engine.structure_loader import (
	load_subject_structure,
	count_total_lessons,
	validate_structure,
)
from memora.services.progress_engine.unlock_calculator import compute_node_states, flatten_nodes

logger = logging.getLogger(__name__)
from memora.services.progress_engine.unlock_calculator import compute_node_states, flatten_nodes


def compute_progress(subject_id: str) -> Dict[str, Any]:
	"""Compute full progress for a subject.

	This orchestrates the complete progress computation flow:
	1. Load subject structure from JSON file
	2. Get player bitmap from Redis (with MariaDB fallback)
	3. Compute node states (passed/unlocked/locked)
	4. Calculate completion percentage
	5. Find next lesson suggestion
	6. Get total XP earned

	Args:
		subject_id: The subject document name

	Returns:
		Dictionary containing:
		- subject_id: The subject ID
		- root: The root progress node (subject)
		- completion_percentage: Percentage of lessons completed (0-100)
		- total_xp_earned: Total XP earned in this subject
		- suggested_next_lesson_id: Next unlocked lesson ID or None
		- total_lessons: Total number of lessons
		- passed_lessons: Number of passed lessons

	Raises:
		FileNotFoundError: If subject JSON file doesn't exist
		frappe.ValidationError: If subject is invalid or player not enrolled
	"""
	player_id = _get_current_player_id()

	if not player_id:
		raise frappe.ValidationError("No authenticated player")

	logger.debug(f"Loading structure for subject={subject_id}")
	structure = _load_and_validate_structure(subject_id)
	logger.debug(f"Getting bitmap for player={player_id}, subject={subject_id}")
	bitmap = get_bitmap(player_id, subject_id)

	logger.debug("Computing node states")
	progress_structure = compute_node_states(structure, bitmap, player_id, subject_id)

	_ensure_structure_has_children(progress_structure)

	total_lessons = count_total_lessons(progress_structure)
	passed_lessons = _count_passed_lessons(progress_structure)
	completion_percentage = _calculate_completion_percentage(passed_lessons, total_lessons)
	total_xp_earned = _get_total_xp_earned(player_id, subject_id)
	suggested_next_lesson_id = find_next_lesson(progress_structure)

	logger.info(
		f"Progress computed: player={player_id}, subject={subject_id}, "
		f"passed={passed_lessons}/{total_lessons} ({completion_percentage}%), "
		f"xp={total_xp_earned}, next={suggested_next_lesson_id}"
	)

	return {
		"subject_id": subject_id,
		"root": progress_structure,
		"completion_percentage": completion_percentage,
		"total_xp_earned": total_xp_earned,
		"suggested_next_lesson_id": suggested_next_lesson_id,
		"total_lessons": total_lessons,
		"passed_lessons": passed_lessons,
	}


def _get_current_player_id() -> Optional[str]:
	"""Get current authenticated player ID.

	Returns:
		Player ID or None if not authenticated
	"""
	return frappe.session.user


def _load_and_validate_structure(subject_id: str) -> Dict[str, Any]:
	"""Load and validate subject structure.

	Args:
		subject_id: The subject document name

	Returns:
		Validated subject structure

	Raises:
		FileNotFoundError: If subject JSON file doesn't exist
		frappe.ValidationError: If structure is invalid
	"""
	try:
		structure = load_subject_structure(subject_id)
		validate_structure(structure)
		return structure
	except FileNotFoundError as e:
		raise frappe.ValidationError(f"Subject structure not found: {e}")
	except ValueError as e:
		raise frappe.ValidationError(f"Invalid subject structure: {e}")


def _ensure_structure_has_children(structure: Dict[str, Any]) -> None:
	"""Ensure structure has 'children' key for traversal.

	This transforms the structure to use 'children' instead of 'tracks'
	at the root level for consistent traversal.

	Args:
		structure: The subject structure dictionary (will be mutated)
	"""
	if "tracks" in structure and "children" not in structure:
		structure["children"] = structure.pop("tracks")

	for track in structure.get("children", []):
		if "units" in track and "children" not in track:
			track["children"] = track.pop("units")

	for track in structure.get("children", []):
		for unit in track.get("children", []):
			if "topics" in unit and "children" not in unit:
				unit["children"] = unit.pop("topics")

	for track in structure.get("children", []):
		for unit in track.get("children", []):
			for topic in unit.get("children", []):
				if "lessons" in topic and "children" not in topic:
					topic["children"] = topic.pop("lessons")


def _count_passed_lessons(structure: Dict[str, Any]) -> int:
	"""Count number of passed lessons in structure.

	Args:
		structure: The subject structure dictionary

	Returns:
		Number of passed lessons
	"""
	all_lessons = flatten_nodes(structure, node_type="lesson")
	passed_count = sum(1 for lesson in all_lessons if lesson.get("status") == "passed")
	return passed_count


def _calculate_completion_percentage(passed_lessons: int, total_lessons: int) -> float:
	"""Calculate completion percentage.

	Args:
		passed_lessons: Number of passed lessons
		total_lessons: Total number of lessons

	Returns:
		Completion percentage (0-100)
	"""
	if total_lessons == 0:
		return 0.0

	percentage = (passed_lessons / total_lessons) * 100
	return round(percentage, 2)


def _get_total_xp_earned(player_id: str, subject_id: str) -> int:
	"""Get total XP earned in subject.

	This queries the Memora Structure Progress document.

	Args:
		player_id: Player ID
		subject_id: Subject ID

	Returns:
		Total XP earned
	"""
	total_xp = frappe.get_value(
		"Memora Structure Progress",
		filters={"player": player_id, "subject": subject_id},
		fieldname="total_xp_earned",
	)

	return total_xp or 0


def find_next_lesson(structure: Dict[str, Any]) -> Optional[str]:
	"""Find the next unlocked (not passed) lesson.

	This traverses the structure in tree order and returns the first
	lesson that is 'unlocked' (not 'passed' and not 'locked').

	Args:
		structure: The subject structure dictionary

	Returns:
		Lesson ID or None if all lessons are passed
	"""

	def search_next_lesson(node: Dict[str, Any]) -> Optional[str]:
		if node.get("type") == "lesson":
			if node.get("status") == "unlocked":
				return node.get("id")
			return None

		if node.get("status") == "locked":
			return None

		for child in node.get("children", []):
			res = search_next_lesson(child)
			if res:
				return res

		return None

	return search_next_lesson(structure)
