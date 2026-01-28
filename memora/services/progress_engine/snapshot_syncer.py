"""
Snapshot Syncer - Batch sync Redis cache to MariaDB snapshots.

This module provides background job functionality to periodically flush
pending bitmap changes from Redis to durable MariaDB storage.
"""

import json

import frappe

from memora.services.progress_engine import bitmap_manager

DIRTY_KEYS_SET = "progress_dirty_keys"


def sync_pending_bitmaps(max_batch_size: int = 100) -> dict:
	"""Sync all pending bitmaps from Redis to MariaDB.

	This function is called by the scheduler every 30 seconds to flush
	dirty keys from Redis to MariaDB snapshots. It processes keys
	in batches to avoid overwhelming the database.

	Args:
		max_batch_size: Maximum number of dirty keys to process in one run

	Returns:
		Dictionary with sync statistics:
			- synced_count: Number of keys successfully synced
			- failed_count: Number of keys that failed to sync
	"""
	synced_count = 0
	failed_count = 0

	try:
		dirty_keys = frappe.cache().smembers(DIRTY_KEYS_SET)

		if not dirty_keys:
			return {"synced_count": 0, "failed_count": 0}

		limit = min(len(dirty_keys), max_batch_size)

		for i, redis_key in enumerate(dirty_keys):
			if i >= limit:
				break

			try:
				player_id, subject_id = _parse_redis_key(redis_key)
				_sync_single_key(player_id, subject_id, redis_key)
				synced_count += 1
			except Exception as e:
				failed_count += 1
				frappe.log_error(
					message=f"Failed to sync key {redis_key}: {str(e)}",
					title="Snapshot Sync Error"
				)

	except Exception as e:
		frappe.log_error(
			message=f"Snapshot sync failed: {str(e)}",
			title="Snapshot Sync Error"
		)

	return {
		"synced_count": synced_count,
		"failed_count": failed_count
	}


def _parse_redis_key(redis_key: str) -> tuple[str, str]:
	"""Parse player_id and subject_id from Redis key.

	Args:
		redis_key: Redis key in format "user_prog:{player_id}:{subject_id}"

	Returns:
		Tuple of (player_id, subject_id)

	Raises:
		ValueError: If key format is invalid
	"""
	parts = redis_key.split(":")
	if len(parts) != 3 or parts[0] != "user_prog":
		raise ValueError(f"Invalid Redis key format: {redis_key}")

	return parts[1], parts[2]


def _sync_single_key(player_id: str, subject_id: str, redis_key: str):
	"""Sync a single player-subject progress record.

	This function fetches both bitmap and best hearts data from Redis
	and updates the corresponding MariaDB record.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier
		redis_key: Redis key for this player-subject pair
	"""
	bitmap_key = bitmap_manager.get_redis_key(player_id, subject_id)
	hearts_key = bitmap_manager.get_best_hearts_key(player_id, subject_id)

	bitmap = frappe.cache().get(bitmap_key)
	hearts_data = frappe.cache().get(hearts_key)

	encoded_bitmap = bitmap_manager.encode_bitmap_for_mariadb(bitmap) if bitmap else ''

	_progress_doc = frappe.db.get_value(
		"Memora Structure Progress",
		{"player": player_id, "subject": subject_id},
		["name", "academic_plan"]
	)

	if _progress_doc:
		progress_name = _progress_doc[0]
		progress = frappe.get_doc("Memora Structure Progress", progress_name)
		progress.passed_lessons_bitset = encoded_bitmap
		progress.best_hearts_data = json.loads(hearts_data) if hearts_data else {}
		progress.last_synced_at = frappe.utils.now()
		progress.save(ignore_permissions=True)
	else:
		academic_plan = frappe.get_value("Memora Subject", subject_id, "academic_plan")
		if not academic_plan:
			frappe.throw(f"Subject {subject_id} not linked to academic plan")

		progress = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": player_id,
			"subject": subject_id,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": encoded_bitmap,
			"best_hearts_data": json.loads(hearts_data) if hearts_data else {},
			"completion_percentage": 0,
			"total_xp_earned": 0,
			"last_synced_at": frappe.utils.now()
		})
		progress.insert(ignore_permissions=True)

	frappe.cache().srem(DIRTY_KEYS_SET, redis_key)


def sync_best_hearts_with_bitmap(player_id: str, subject_id: str, hearts_data: dict):
	"""Sync best hearts data along with bitmap.

	This is a helper function used by the complete_lesson API
	to ensure best hearts are synced when the bitmap is updated.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier
		hearts_data: Dictionary mapping lesson_id → best hearts
	"""
	bitmap_key = bitmap_manager.get_redis_key(player_id, subject_id)
	hearts_key = bitmap_manager.get_best_hearts_key(player_id, subject_id)

	bitmap = frappe.cache().get(bitmap_key)
	frappe.cache().set(hearts_key, json.dumps(hearts_data))
	bitmap_manager.mark_dirty(player_id, subject_id)
