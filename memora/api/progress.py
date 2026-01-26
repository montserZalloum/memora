"""
Progress API - Lesson completion and progress tracking endpoints.

This module provides Frappe whitelisted API endpoints for:
- Marking lessons as completed and awarding XP
- Retrieving full progress trees with unlock states
- Computing completion percentages and next lesson suggestions

All endpoints require authenticated player sessions and validate enrollment.
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional

from memora.services.progress_engine import bitmap_manager, xp_calculator


@frappe.whitelist()
def complete_lesson(lesson_id: str, hearts: int) -> Dict[str, Any]:
	"""Mark a lesson as completed and award XP.

	This endpoint validates the request, updates the progress bitmap in Redis,
	calculates XP based on hearts and record-breaking bonuses, awards XP
	to the player's wallet, and logs the completion event.

	Args:
		lesson_id: The unique identifier of the lesson being completed
		hearts: Number of hearts remaining at lesson completion (0-5)

	Returns:
		Dictionary with keys:
			- success: bool - Whether the completion was recorded successfully
			- xp_earned: int - XP earned from this completion
			- new_total_xp: int - Player's new total XP after this completion
			- is_first_completion: bool - True if first time completing this lesson
			- is_new_record: bool - True if this beat previous best hearts

	Raises:
		frappe.ValidationError: If hearts is invalid or player has no hearts remaining
	"""
	# Validate input parameters
	if not lesson_id:
		frappe.throw(_("Lesson ID is required"), exc=frappe.ValidationError)

	if not isinstance(hearts, int) or hearts < 0 or hearts > 5:
		frappe.throw(_("Hearts must be an integer between 0 and 5"), exc=frappe.ValidationError)

	# Get player ID from current session first (before any database queries)
	player_id = frappe.session.user
	if not player_id or player_id == "Guest":
		frappe.throw(_("User must be logged in"), exc=frappe.ValidationError)

	# Sanitize and validate lesson_id
	if not lesson_id or not isinstance(lesson_id, str):
		frappe.throw(_("Invalid lesson ID"), exc=frappe.ValidationError)

	# Validate hearts parameter
	if not isinstance(hearts, int):
		frappe.throw(_("Hearts must be an integer"), exc=frappe.ValidationError)

	if hearts < 0 or hearts > 5:
		frappe.throw(_("Hearts must be between 0 and 5"), exc=frappe.ValidationError)

	# Get lesson information
	try:
		lesson = frappe.get_doc("Memora Lesson", lesson_id)
	except frappe.DoesNotExistError:
		frappe.throw(_("Lesson not found"), exc=frappe.ValidationError)

	# T018: Hearts validation - check player has hearts > 0
	if hearts <= 0:
		frappe.throw(
			_("No hearts remaining. Wait for hearts to regenerate."),
			exc=frappe.ValidationError,
			title=_("No Hearts")
		)

	# Get subject ID from lesson hierarchy
	topic = frappe.get_doc("Memora Topic", lesson.parent_topic)
	unit = frappe.get_doc("Memora Unit", topic.parent_unit)
	track = frappe.get_doc("Memora Track", unit.parent_track)
	subject_id = track.parent_subject

	# T063: Security - verify player is enrolled in subject
	_verify_player_enrollment(player_id, subject_id)

	# Get existing structure progress record
	progress_doc = frappe.db.get_value(
		"Memora Structure Progress",
		{
			"player": player_id,
			"subject": subject_id
		},
		"name"
	)

	if not progress_doc:
		frappe.throw(
			_("Not enrolled in this subject"),
			exc=frappe.ValidationError,
			title=_("Not Enrolled")
		)

	progress_doc = frappe.get_doc("Memora Structure Progress", progress_doc)

	# Determine if this is first completion
	bitmap = bitmap_manager.get_bitmap(player_id, subject_id)
	is_first_completion = not bitmap_manager.check_bit(bitmap, lesson.bit_index)

	# Get best hearts data from Redis
	best_hearts_data = bitmap_manager.get_best_hearts(player_id, subject_id)

	# Calculate XP
	xp_result = xp_calculator.calculate_xp(
		lesson_id=lesson_id,
		hearts=hearts,
		is_first_completion=is_first_completion,
		best_hearts_data=best_hearts_data,
		base_xp=lesson.base_xp if hasattr(lesson, 'base_xp') else 10
	)

	# Update bitmap
	bitmap_manager.update_bitmap(player_id, subject_id, lesson.bit_index)

	# Update best hearts data in Redis and mark for sync
	from memora.services.progress_engine import snapshot_syncer
	snapshot_syncer.sync_best_hearts_with_bitmap(
		player_id, subject_id, xp_result["best_hearts_data"]
	)

	# Calculate completion percentage
	passed_lessons = bin(int.from_bytes(bitmap_manager.get_bitmap(player_id, subject_id) or b'\x00', 'big')).count('1')
	total_lessons = frappe.db.count("Memora Lesson", {"parent_subject": subject_id})
	completion_percentage = (passed_lessons / total_lessons * 100) if total_lessons > 0 else 0

	progress_doc.completion_percentage = completion_percentage
	progress_doc.total_xp_earned = progress_doc.total_xp_earned + xp_result["xp_earned"] if progress_doc.total_xp_earned else xp_result["xp_earned"]
	progress_doc.last_synced_at = frappe.utils.now()
	progress_doc.save(ignore_permissions=True)

	# T019: Integrate XP award with Memora Player Wallet
	player_wallet = frappe.db.get_value(
		"Memora Player Wallet",
		{"player": player_id},
		"name"
	)

	if not player_wallet:
		frappe.throw(_("Player wallet not found"), exc=frappe.ValidationError)

	player_wallet_doc = frappe.get_doc("Memora Player Wallet", player_wallet)
	player_wallet_doc.total_xp = player_wallet_doc.total_xp + xp_result["xp_earned"]
	player_wallet_doc.save(ignore_permissions=True)

	# T020: Add interaction logging for lesson completion events
	_log_lesson_completion(player_id, lesson_id, hearts, xp_result["xp_earned"])

	return {
		"success": True,
		"xp_earned": xp_result["xp_earned"],
		"new_total_xp": player_wallet_doc.total_xp,
		"is_first_completion": is_first_completion,
		"is_new_record": xp_result["is_new_record"]
	}


@frappe.whitelist()
def get_progress(subject_id: str) -> Dict[str, Any]:
	"""Get full progress tree for a subject.

	This endpoint retrieves the complete progress tree with unlock states,
	completion percentage, total XP, and next lesson suggestion.

	Args:
		subject_id: The unique identifier of subject

	Returns:
		Dictionary with progress information including:
			- subject_id: str - The subject identifier
			- root: Dict - The root progress node (subject) with all children
			- completion_percentage: float - Percentage of lessons completed (0-100)
			- total_xp_earned: int - Total XP earned in this subject
			- suggested_next_lesson_id: Optional[str] - Next unlocked lesson ID or None
			- total_lessons: int - Total number of lessons
			- passed_lessons: int - Number of passed lessons

	Raises:
		frappe.ValidationError: If subject_id is invalid or user not enrolled
	"""
	# T032: Implement get_progress API endpoint
	# Sanitize and validate input
	if not subject_id or not isinstance(subject_id, str):
		frappe.throw(_("Invalid subject ID"), exc=frappe.ValidationError)

	# Get player ID from current session
	player_id = frappe.session.user
	if not player_id or player_id == "Guest":
		frappe.throw(_("User must be logged in"), exc=frappe.ValidationError)

	# T063: Security - verify player enrollment
	_verify_player_enrollment(player_id, subject_id)

	# Get progress doc
	progress_doc = frappe.db.get_value(
		"Memora Structure Progress",
		{
			"player": player_id,
			"subject": subject_id
		},
		["name", "total_xp_earned"]
	)

	# Use progress_computer to compute full progress tree
	from memora.services.progress_engine.progress_computer import compute_progress

	progress = compute_progress(subject_id)

	return progress


def _log_lesson_completion(player_id: str, lesson_id: str, hearts: int, xp_earned: int) -> None:
	"""Log lesson completion event to Memora Interaction Log.

	This is a non-blocking operation - failures are logged but don't
	prevent the lesson completion flow.

	Args:
		player_id: Player's unique identifier
		lesson_id: Lesson's unique identifier
		hearts: Hearts earned
		xp_earned: XP earned
	"""
	try:
		frappe.get_doc({
			"doctype": "Memora Interaction Log",
			"player": player_id,
			"interaction_type": "lesson_completion",
			"reference_id": lesson_id,
			"interaction_data": {
				"hearts": hearts,
				"xp_earned": xp_earned
			}
		}).insert(ignore_permissions=True)
	except Exception as e:
		# Log failure but don't block the completion flow
		frappe.log_error(
			message=f"Failed to log lesson completion: {str(e)}",
			title="Interaction Log Error"
		)


def _verify_player_enrollment(player_id: str, subject_id: str) -> None:
	"""Verify that player is enrolled in the subject.

	This security check ensures players can only access progress data
	for subjects they are explicitly enrolled in through academic plans.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Raises:
		frappe.ValidationError: If player is not enrolled
	"""
	progress_doc = frappe.db.get_value(
		"Memora Structure Progress",
		{
			"player": player_id,
			"subject": subject_id
		},
		"name"
	)

	if not progress_doc:
		frappe.throw(
			_("Not enrolled in this subject"),
			exc=frappe.ValidationError,
			title=_("Not Enrolled")
		)
