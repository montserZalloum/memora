"""Structure loader for progress engine.

This module handles loading and caching of subject structure JSON files
used by progress engine for computing node states.
"""

import json
import logging
import os
from functools import lru_cache
from typing import Dict, Any

logger = logging.getLogger(__name__)


DEFAULT_CACHE_SIZE = 32


def get_subject_json_path(subject_id: str) -> str:
	"""Get the file path for a subject's JSON structure.

	Args:
		subject_id: The subject document name (e.g., 'SUBJ-001')

	Returns:
		Absolute path to the subject JSON file

	Raises:
		FileNotFoundError: If the JSON file doesn't exist
	"""
	from frappe import local

	site_path = local.site_path
	json_path = os.path.join(
		site_path,
		"public",
		"memora_content",
		f"{subject_id}.json"
	)

	if not os.path.exists(json_path):
		raise FileNotFoundError(f"Subject JSON not found: {json_path}")

	return json_path


@lru_cache(maxsize=DEFAULT_CACHE_SIZE)
def load_subject_structure(subject_id: str) -> Dict[str, Any]:
	"""Load subject structure JSON from file with LRU caching.

	Args:
		subject_id: The subject document name

	Returns:
		Dictionary containing subject structure

	Raises:
		FileNotFoundError: If JSON file doesn't exist
		json.JSONDecodeError: If JSON file is malformed
	"""
	logger.debug(f"Loading structure for subject={subject_id}")
	json_path = get_subject_json_path(subject_id)

	with open(json_path, 'r', encoding='utf-8') as f:
		structure = json.load(f)

	logger.debug(f"Loaded structure for subject={subject_id} with {len(structure.get('tracks', []))} tracks")
	return structure


def clear_cache():
	"""Clear the LRU cache for subject structures.

	Useful when subject structure files are updated and need to be reloaded.
	"""
	load_subject_structure.cache_clear()


def validate_structure(structure: Dict[str, Any]) -> bool:
	"""Validate that subject structure has required fields.

	Args:
		structure: The subject structure dictionary

	Returns:
		True if valid, raises ValueError otherwise

	Raises:
		ValueError: If structure is missing required fields
	"""
	required_fields = ["id", "title", "is_linear", "tracks"]

	for field in required_fields:
		if field not in structure:
			logger.error(f"Subject structure missing required field: {field}")
			raise ValueError(f"Subject structure missing required field: {field}")

	if not isinstance(structure["tracks"], list):
		logger.error("Subject tracks must be a list")
		raise ValueError("Subject tracks must be a list")

	logger.debug("Structure validation passed")
	return True


def get_lesson_bit_index(structure: Dict[str, Any], lesson_id: str) -> int:
	"""Get the bit_index for a lesson from the structure.

	Args:
		structure: The subject structure dictionary
		lesson_id: The lesson ID to find

	Returns:
		The bit_index for the lesson

	Raises:
		ValueError: If lesson not found in structure
	"""

	def find_lesson_in_lessons(lessons: list) -> int:
		for lesson in lessons:
			if lesson.get("id") == lesson_id:
				bit_index = lesson.get("bit_index")
				if bit_index is None:
					raise ValueError(f"Lesson {lesson_id} missing bit_index")
				return bit_index
		raise ValueError(f"Lesson {lesson_id} not found")

	for track in structure.get("tracks", []):
		for unit in track.get("units", []):
			for topic in unit.get("topics", []):
				try:
					return find_lesson_in_lessons(topic.get("lessons", []))
				except ValueError:
					continue

	raise ValueError(f"Lesson {lesson_id} not found in structure")


def count_total_lessons(structure: Dict[str, Any]) -> int:
	"""Count total number of lessons in the subject structure.

	Args:
		structure: The subject structure dictionary

	Returns:
		Total number of lessons
	"""
	total = 0

	for track in structure.get("tracks", []):
		for unit in track.get("units", []):
			for topic in unit.get("topics", []):
				total += len(topic.get("lessons", []))

	return total


def get_lesson_ids(structure: Dict[str, Any]) -> list:
	"""Get all lesson IDs from the structure.

	Args:
		structure: The subject structure dictionary

	Returns:
		List of lesson IDs
	"""
	lesson_ids = []

	for track in structure.get("tracks", []):
		for unit in track.get("units", []):
			for topic in unit.get("topics", []):
				for lesson in topic.get("lessons", []):
					lesson_ids.append(lesson.get("id"))

	return lesson_ids
