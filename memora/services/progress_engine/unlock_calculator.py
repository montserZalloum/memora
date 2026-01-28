"""Unlock calculator for progress engine.

This module computes unlock states (locked/unlocked/passed) for all nodes
in a subject structure based on lesson completion bitmap and unlock rules.
"""

import logging
from typing import Dict, Any, Optional, List

from memora.services.progress_engine.bitmap_manager import check_bit

logger = logging.getLogger(__name__)


def compute_node_states(structure: Dict[str, Any], bitmap: bytes, player_id: str = None, subject_id: str = None) -> Dict[str, Any]:
	"""Compute unlock states for all nodes in subject structure.

	This function performs two passes:
	1. Bottom-up: Compute child lesson states and container states
	2. Top-down: Apply unlock rules based on parent is_linear flags

	Args:
		structure: The subject structure dictionary
		bitmap: Lesson completion bitmap from Redis
		player_id: Player ID for fetching best_hearts (optional)
		subject_id: Subject ID for fetching best_hearts (optional)

	Returns:
		Structure with status and unlock_state populated for all nodes
	"""
	logger.debug(f"Computing node states for structure={structure.get('id')}")
	structure_copy = _deep_copy_structure(structure)

	_phase1_compute_lesson_and_container_states(structure_copy, bitmap, player_id, subject_id)

	_phase2_apply_unlock_rules(structure_copy, structure_copy["is_linear"])

	logger.debug("Node states computed successfully")
	return structure_copy


def _deep_copy_structure(structure: Dict[str, Any]) -> Dict[str, Any]:
	"""Deep copy structure to avoid mutating input.

	Args:
		structure: The subject structure dictionary

	Returns:
		Deep copy of the structure
	"""
	import copy
	return copy.deepcopy(structure)


def _phase1_compute_lesson_and_container_states(
	structure: Dict[str, Any],
	bitmap: bytes,
	player_id: Optional[str],
	subject_id: Optional[str]
) -> None:
	"""Phase 1: Compute lesson states (passed/not_passed) and container states.

	Args:
		structure: The subject structure dictionary (will be mutated)
		bitmap: Lesson completion bitmap
		player_id: Player ID for fetching best_hearts
		subject_id: Subject ID for fetching best_hearts
	"""
	def process_node(node: Dict[str, Any], parent_is_linear: bool) -> None:
		node_type = node.get("type")  # آمن بدل node["type"]

		if node_type == "lesson":
			bit_index = node.get("bit_index")
			if bit_index is None:
				raise ValueError(f"Lesson {node.get('id')} missing bit_index")

			is_passed = check_bit(bitmap, bit_index)
			node["status"] = "passed" if is_passed else "not_passed"

			if is_passed and player_id and subject_id:
				node["best_hearts"] = _get_best_hearts_for_lesson(
					player_id, subject_id, node.get("id")
				)

		elif node_type in ["topic", "unit", "track", "subject"]:
			children = node.get("children", [])

			if not children:
				node["status"] = "unlocked"
			else:
				for child in children:
					child_is_linear = child.get("is_linear", True)
					process_node(child, child_is_linear)

				node["status"] = compute_container_status(node, children, structure)
		else:
			# أي node بدون type يعتبر unlocked بشكل افتراضي
			node["status"] = node.get("status", "unlocked")


	# استدعاء آمن
	process_node(structure, structure.get("is_linear", True))



def _phase2_apply_unlock_rules(structure: Dict[str, Any], parent_is_linear: bool) -> None:
	"""Phase 2: Apply unlock rules top-down through the tree.

	Args:
		structure: The subject structure dictionary (will be mutated)
		parent_is_linear: Whether the parent is linear
	"""
	def process_node(node: Dict[str, Any], parent_unlock_status: str, parent_is_linear: bool) -> str:
		if node["status"] == "passed":
			node["unlock_status"] = "passed"
		else:
			children = node.get("children", [])

			if children:
				prev_sibling_passed = None
				for child in children:
					child_is_first = (child == children[0])
					child_unlock_status = _compute_unlock_state(
						node_status=child["status"],
						parent_is_linear=node.get("is_linear", True),
						is_first_child=child_is_first,
						prev_sibling_passed=prev_sibling_passed,
						parent_unlock_status=node.get("unlock_status", "unlocked")
					)

					child["unlock_status"] = child_unlock_status

					if child["status"] == "passed":
						prev_sibling_passed = True

					process_node(child, child_unlock_status, node.get("is_linear", True))

		node["status"] = node.get("unlock_status", node["status"])
		return node["status"]

	process_node(structure, "unlocked", parent_is_linear)


def _get_best_hearts_for_lesson(player_id: str, subject_id: str, lesson_id: str) -> Optional[int]:
	"""Get best hearts for a lesson from Redis.

	Args:
		player_id: Player ID
		subject_id: Subject ID
		lesson_id: Lesson ID

	Returns:
		Best hearts value (0-5) or None if not set
	"""
	import frappe

	key = f"best_hearts:{player_id}:{subject_id}"
	best_hearts_data = frappe.cache().get_value(key)

	if not best_hearts_data:
		return None

	import json
	try:
		best_hearts = json.loads(best_hearts_data)
		return best_hearts.get(lesson_id)
	except (json.JSONDecodeError, AttributeError):
		return None


def compute_container_status(node: Dict[str, Any], children: List[Dict[str, Any]], structure: Dict[str, Any]) -> str:
	"""Compute container status based on children.

	Container is 'passed' only if ALL children are 'passed'.
	Otherwise, container is 'unlocked'.

	Args:
		node: The container node
		children: List of child nodes
		structure: The full subject structure (for context)

	Returns:
		Container status: 'passed' or 'unlocked'
	"""
	if not children:
		return "unlocked"

	all_children_passed = all(
		child["status"] == "passed"
		for child in children
	)

	return "passed" if all_children_passed else "unlocked"


def _compute_unlock_state(
	node_status: str,
	parent_is_linear: bool,
	is_first_child: bool,
	prev_sibling_passed: Optional[bool],
	parent_unlock_status: str
) -> str:
	"""Compute unlock state for a node based on rules.

	Args:
		node_status: The node's status ('passed' or 'not_passed')
		parent_is_linear: Whether the parent is linear
		is_first_child: Whether this is the first child
		prev_sibling_passed: Whether previous sibling is passed (linear only)
		parent_unlock_status: The parent's unlock status

	Returns:
		Unlock state: 'locked', 'unlocked', or 'passed'
	"""
	if node_status == "passed":
		return "passed"

	if parent_unlock_status == "locked":
		return "locked"

	if parent_is_linear:
		if _is_linear_unlock_locked(is_first_child, prev_sibling_passed):
			return "locked"
		else:
			return "unlocked"
	else:
		return "unlocked"


def _is_linear_unlock_locked(is_first_child: bool, prev_sibling_passed: Optional[bool]) -> bool:
	"""Determine if a node is locked under linear unlock rules.

	Args:
		is_first_child: Whether this is the first child
		prev_sibling_passed: Whether previous sibling is passed

	Returns:
		True if node should be locked
	"""
	if is_first_child:
		return False

	if prev_sibling_passed is None or not prev_sibling_passed:
		return True

	return False


def flatten_nodes(structure: Dict[str, Any], node_type: Optional[str] = None) -> List[Dict[str, Any]]:
	"""Flatten structure to list of nodes.

	Args:
		structure: The subject structure dictionary
		node_type: Optional filter by node type

	Returns:
		Flattened list of nodes
	"""
	nodes = []

	def collect_nodes(node: Dict[str, Any]) -> None:
		if node_type is None or node.get("type") == node_type:
			nodes.append(node)

		for child in node.get("children", []):
			collect_nodes(child)

	collect_nodes(structure)
	return nodes


def find_node_by_id(structure: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
	"""Find a node by ID in the structure.

	Args:
		structure: The subject structure dictionary
		node_id: The node ID to find

	Returns:
		The node dictionary or None if not found
	"""
	def search_node(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
		if node.get("id") == node_id:
			return node

		for child in node.get("children", []):
			result = search_node(child)
			if result:
				return result

		return None

	return search_node(structure)
