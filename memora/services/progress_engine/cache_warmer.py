"""
Cache Warmer - Restore progress data from MariaDB on cache miss.

This module provides functions to warm the Redis cache from MariaDB snapshots,
enabling recovery from Redis failures and cold starts.
"""

import frappe

from memora.services.progress_engine import bitmap_manager


def warm_from_mariadb(player_id: str, subject_id: str) -> bytes:
	"""Warm bitmap cache from MariaDB snapshot.

	This function retrieves the passed_lessons_bitset from MariaDB and
	populates the Redis cache. Used when Redis cache is empty or after
	a Redis failure.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Returns:
		Bitmap as bytes (empty bytes if not found)
	"""
	try:
		# Fetch encoded bitmap from MariaDB
		encoded = frappe.get_value(
			"Memora Structure Progress",
			{"player": player_id, "subject": subject_id},
			"passed_lessons_bitset"
		)

		# Decode if exists, otherwise empty bitmap
		if encoded:
			bitmap = bitmap_manager.decode_bitmap_from_mariadb(encoded)
		else:
			bitmap = b''

		# Store in Redis cache atomically
		redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
		frappe.cache().set(redis_key, bitmap)

		return bitmap

	except Exception as e:
		frappe.log_error(
			message=f"Cache warming failed for player={player_id}, subject={subject_id}: {str(e)}",
			title="Cache Warmer Error"
		)
		return b''


def warm_best_hearts_from_mariadb(player_id: str, subject_id: str) -> dict:
	"""Warm best hearts cache from MariaDB snapshot.

	This function retrieves the best_hearts_data from MariaDB and
	populates the Redis cache.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Returns:
		Dictionary mapping lesson_id → best hearts (empty dict if not found)
	"""
	try:
		# Fetch best hearts data from MariaDB
		best_hearts_data = frappe.get_value(
			"Memora Structure Progress",
			{"player": player_id, "subject": subject_id},
			"best_hearts_data"
		)

		# Default to empty dict if not found
		if not best_hearts_data:
			best_hearts_data = {}

		# Store in Redis cache atomically
		redis_key = bitmap_manager.get_best_hearts_key(player_id, subject_id)
		frappe.cache().set(redis_key, best_hearts_data)

		return best_hearts_data

	except Exception as e:
		frappe.log_error(
			message=f"Best hearts warming failed for player={player_id}, subject={subject_id}: {str(e)}",
			title="Cache Warmer Error"
		)
		return {}


def warm_all_from_mariadb(player_id: str, subject_id: str) -> tuple[bytes, dict]:
	"""Warm both bitmap and best hearts cache from MariaDB snapshot.

	This is a convenience function that warms both datasets in a single
	call, useful for cold starts.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Returns:
		Tuple of (bitmap bytes, best_hearts_data dict)
	"""
	bitmap = warm_from_mariadb(player_id, subject_id)
	best_hearts_data = warm_best_hearts_from_mariadb(player_id, subject_id)
	return bitmap, best_hearts_data


def warm_on_cache_miss(player_id: str, subject_id: str) -> bytes:
	"""Check cache and warm from MariaDB on miss.

	This function first checks if the bitmap exists in Redis. If not,
	it automatically warms the cache from MariaDB. This is the primary
	fallback mechanism for the progress engine.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Returns:
		Bitmap as bytes
	"""
	redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
	bitmap = frappe.cache().get(redis_key)

	if bitmap is None:
		bitmap = warm_from_mariadb(player_id, subject_id)

	return bitmap if bitmap else b''


def warm_best_hearts_on_cache_miss(player_id: str, subject_id: str) -> dict:
	"""Check cache and warm best hearts from MariaDB on miss.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Returns:
		Dictionary mapping lesson_id → best hearts
	"""
	redis_key = bitmap_manager.get_best_hearts_key(player_id, subject_id)
	data = frappe.cache().get(redis_key)

	if data is None:
		data = warm_best_hearts_from_mariadb(player_id, subject_id)

	return data if data else {}
