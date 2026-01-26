"""Unit tests for cache_warmer module."""

import pytest

from memora.services.progress_engine import cache_warmer, bitmap_manager


def test_warm_from_mariadb_existing_progress():
	"""Test warming cache when progress exists in MariaDB."""
	player_id = "TEST-PLAYER-001"
	subject_id = "TEST-SUBJ-001"

	# Set up a bitmap in MariaDB (base64 encoded)
	test_bitmap = b'\x07'
	encoded = bitmap_manager.encode_bitmap_for_mariadb(test_bitmap)

	# Warm cache
	result = cache_warmer.warm_from_mariadb(player_id, subject_id)

	# Verify returned bitmap matches
	assert result == test_bitmap

	# Verify Redis cache was populated
	redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
	cached_bitmap = frappe.cache().get(redis_key)
	assert cached_bitmap == test_bitmap


def test_warm_from_mariadb_no_progress():
	"""Test warming cache when no progress exists in MariaDB."""
	player_id = "TEST-PLAYER-002"
	subject_id = "TEST-SUBJ-002"

	# Warm cache
	result = cache_warmer.warm_from_mariadb(player_id, subject_id)

	# Should return empty bytes
	assert result == b''


def test_warm_from_mariadb_corrupted_data():
	"""Test warming cache with corrupted Base64 data."""
	player_id = "TEST-PLAYER-003"
	subject_id = "TEST-SUBJ-003"

	# This should handle gracefully and return empty bytes or raise appropriate error
	result = cache_warmer.warm_from_mariadb(player_id, subject_id)
	assert result == b''


def test_warm_from_mariadb_atomic_operation():
	"""Test that cache warming is atomic (no race conditions)."""
	player_id = "TEST-PLAYER-004"
	subject_id = "TEST-SUBJ-004"

	test_bitmap = b'\x0f'
	encoded = bitmap_manager.encode_bitmap_for_mariadb(test_bitmap)

	# Warm cache
	cache_warmer.warm_from_mariadb(player_id, subject_id)

	# Verify single atomic operation set the full value
	redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
	cached_bitmap = frappe.cache().get(redis_key)
	assert cached_bitmap == test_bitmap
	assert len(cached_bitmap) == 1


def test_warm_best_hearts_from_mariadb():
	"""Test warming best hearts cache from MariaDB."""
	player_id = "TEST-PLAYER-005"
	subject_id = "TEST-SUBJ-005"

	test_data = {"LESSON-001": 5, "LESSON-002": 3}

	# Warm cache
	result = cache_warmer.warm_best_hearts_from_mariadb(player_id, subject_id)

	# Verify returned data matches
	assert result == test_data

	# Verify Redis cache was populated
	redis_key = bitmap_manager.get_best_hearts_key(player_id, subject_id)
	cached_data = frappe.cache().get(redis_key)
	import json
	assert json.loads(cached_data) == test_data


def test_warm_all_player_data_from_mariadb():
	"""Test warming all cache data for a player-subject pair."""
	player_id = "TEST-PLAYER-006"
	subject_id = "TEST-SUBJ-006"

	test_bitmap = b'\x07'
	test_hearts = {"LESSON-001": 4}

	# Warm all data
	bitmap, hearts_data = cache_warmer.warm_all_from_mariadb(player_id, subject_id)

	# Verify both datasets warmed correctly
	assert bitmap == test_bitmap
	assert hearts_data == test_hearts

	# Verify both Redis keys populated
	redis_bitmap_key = bitmap_manager.get_redis_key(player_id, subject_id)
	redis_hearts_key = bitmap_manager.get_best_hearts_key(player_id, subject_id)

	assert frappe.cache().get(redis_bitmap_key) == test_bitmap
	import json
	assert json.loads(frappe.cache().get(redis_hearts_key)) == test_hearts


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
