"""
Bitmap Manager - Redis bitmap operations for lesson completion tracking.

This module provides functions to manage bitmaps stored in Redis for tracking
which lessons a student has completed.
"""

import base64
import json
import logging

import frappe

logger = logging.getLogger(__name__)


REDIS_BITMAP_KEY_PATTERN = "user_prog:{player_id}:{subject_id}"
REDIS_BEST_HEARTS_KEY_PATTERN = "best_hearts:{player_id}:{subject_id}"
DIRTY_KEYS_SET = "progress_dirty_keys"


def get_redis_key(player_id: str, subject_id: str) -> str:
	"""Generate Redis key for player-subject progress bitmap."""
	return REDIS_BITMAP_KEY_PATTERN.format(player_id=player_id, subject_id=subject_id)


def set_bit(bitmap_bytes: bytes, bit_index: int) -> bytes:
	"""Set a specific bit in the bitmap.

	Args:
		bitmap_bytes: Current bitmap as bytes
		bit_index: Index of the bit to set

	Returns:
		Updated bitmap as bytes
	"""
	bitmap_int = int.from_bytes(bitmap_bytes, 'big') if bitmap_bytes else 0
	bitmap_int |= (1 << bit_index)
	byte_length = (bit_index // 8) + 1
	return bitmap_int.to_bytes(max(byte_length, len(bitmap_bytes or b'')), 'big')


def check_bit(bitmap_bytes: bytes, bit_index: int) -> bool:
	"""Check if a specific bit is set in the bitmap.

	Args:
		bitmap_bytes: Current bitmap as bytes
		bit_index: Index of the bit to check

	Returns:
		True if bit is set, False otherwise
	"""
	if not bitmap_bytes:
		return False
	bitmap_int = int.from_bytes(bitmap_bytes, 'big')
	return bool(bitmap_int & (1 << bit_index))


def get_bitmap(player_id: str, subject_id: str) -> bytes:
	"""Get the progress bitmap for a player-subject pair from Redis.

	This function includes automatic cache warming from MariaDB on cache miss.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Returns:
		Bitmap as bytes (empty bytes if not found)
	"""
	key = get_redis_key(player_id, subject_id)
	bitmap = frappe.cache().get(key)

	if bitmap is None:
		logger.debug(f"Cache miss for bitmap key={key}, warming from MariaDB")
		from memora.services.progress_engine import cache_warmer
		bitmap = cache_warmer.warm_on_cache_miss(player_id, subject_id)
		logger.info(f"Warmed bitmap for player={player_id}, subject={subject_id}")
	else:
		logger.debug(f"Cache hit for bitmap key={key}")

	return bitmap if bitmap else b''


def update_bitmap(player_id: str, subject_id: str, bit_index: int) -> bytes:
	"""Update a lesson's completion status in the bitmap.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier
		bit_index: Bit index of the lesson to mark as complete

	Returns:
		Updated bitmap as bytes
	"""
	key = get_redis_key(player_id, subject_id)
	bitmap = get_bitmap(player_id, subject_id)
	bitmap = set_bit(bitmap, bit_index)
	frappe.cache().set(key, bitmap)
	mark_dirty(player_id, subject_id)
	logger.info(f"Updated bitmap for player={player_id}, subject={subject_id}, bit_index={bit_index}")
	return bitmap


def mark_dirty(player_id: str, subject_id: str):
	"""Mark a player-subject progress key as dirty (pending sync to MariaDB).

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier
	"""
	key = get_redis_key(player_id, subject_id)
	frappe.cache().sadd(DIRTY_KEYS_SET, key)
	logger.debug(f"Marked key={key} as dirty for sync")


def encode_bitmap_for_mariadb(bitmap_bytes: bytes) -> str:
	"""Encode bitmap bytes for storage in MariaDB (Base64).

	Args:
		bitmap_bytes: Bitmap as bytes

	Returns:
		Base64-encoded string
	"""
	if not bitmap_bytes:
		return ''
	return base64.b64encode(bitmap_bytes).decode('utf-8')


def decode_bitmap_from_mariadb(encoded: str) -> bytes:
	"""Decode bitmap from MariaDB Base64 string to bytes.

	Args:
		encoded: Base64-encoded string from MariaDB

	Returns:
		Bitmap as bytes (empty bytes if empty string)
	"""
	if not encoded:
		return b''
	return base64.b64decode(encoded.encode('utf-8'))


def get_best_hearts_key(player_id: str, subject_id: str) -> str:
	"""Generate Redis key for best hearts data.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Returns:
		Redis key for best hearts data
	"""
	return REDIS_BEST_HEARTS_KEY_PATTERN.format(player_id=player_id, subject_id=subject_id)


def get_best_hearts(player_id: str, subject_id: str) -> dict:
	"""Get best hearts data from Redis.

	This function includes automatic cache warming from MariaDB on cache miss.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier

	Returns:
		Dictionary mapping lesson_id → best hearts (empty dict if not found)
	"""
	key = get_best_hearts_key(player_id, subject_id)
	data = frappe.cache().get(key)

	if data is None:
		from memora.services.progress_engine import cache_warmer
		data = cache_warmer.warm_best_hearts_on_cache_miss(player_id, subject_id)
		return data

	return json.loads(data) if data else {}


def set_best_hearts(player_id: str, subject_id: str, best_hearts_data: dict):
	"""Set best hearts data in Redis.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier
		best_hearts_data: Dictionary mapping lesson_id → best hearts
	"""
	key = get_best_hearts_key(player_id, subject_id)
	frappe.cache().set(key, json.dumps(best_hearts_data))
	mark_dirty(player_id, subject_id)


def update_best_hearts(player_id: str, subject_id: str, lesson_id: str, hearts: int):
	"""Update best hearts for a specific lesson in Redis.

	Args:
		player_id: Player's unique identifier
		subject_id: Subject's unique identifier
		lesson_id: Lesson's unique identifier
		hearts: Hearts achieved (0-5)

	Returns:
		Updated best_hearts_data dictionary
	"""
	best_hearts_data = get_best_hearts(player_id, subject_id)
	best_hearts_data[lesson_id] = hearts
	set_best_hearts(player_id, subject_id, best_hearts_data)
	logger.info(f"Updated best hearts for player={player_id}, lesson={lesson_id}, hearts={hearts}")
	return best_hearts_data
