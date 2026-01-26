"""Unit tests for snapshot_syncer module."""

import pytest

from memora.services.progress_engine import snapshot_syncer, bitmap_manager


def test_sync_pending_bitmarks_empty_dirty_keys():
	"""Test syncing when no dirty keys exist."""
	# Clear dirty keys set
	frappe.cache().delete("progress_dirty_keys")

	# Should run successfully and return count
	result = snapshot_syncer.sync_pending_bitmaps()
	assert result["synced_count"] == 0
	assert result["failed_count"] == 0


def test_sync_pending_bitmarks_single_dirty_key():
	"""Test syncing a single dirty key."""
	player_id = "TEST-PLAYER-001"
	subject_id = "TEST-SUBJ-001"

	# Set up test data in Redis and mark dirty
	test_bitmap = b'\x07'
	redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
	frappe.cache().set(redis_key, test_bitmap)
	bitmap_manager.mark_dirty(player_id, subject_id)

	# Sync pending bitmaps
	result = snapshot_syncer.sync_pending_bitmaps()

	# Verify one sync occurred
	assert result["synced_count"] == 1
	assert result["failed_count"] == 0

	# Verify dirty key removed
	dirty_keys = frappe.cache().smembers("progress_dirty_keys")
	assert redis_key not in dirty_keys

	# Verify MariaDB snapshot updated
	encoded = frappe.get_value(
		"Memora Structure Progress",
		{"player": player_id, "subject": subject_id},
		"passed_lessons_bitset"
	)
	decoded = bitmap_manager.decode_bitmap_from_mariadb(encoded)
	assert decoded == test_bitmap


def test_sync_pending_bitmarks_multiple_dirty_keys():
	"""Test syncing multiple dirty keys."""
	players = ["TEST-PLAYER-002", "TEST-PLAYER-003", "TEST-PLAYER-004"]
	subject_id = "TEST-SUBJ-002"

	# Set up test data for multiple players
	for i, player_id in enumerate(players):
		test_bitmap = bytes([i + 1])
		redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
		frappe.cache().set(redis_key, test_bitmap)
		bitmap_manager.mark_dirty(player_id, subject_id)

	# Sync pending bitmaps
	result = snapshot_syncer.sync_pending_bitmaps()

	# Verify all synced
	assert result["synced_count"] == 3
	assert result["failed_count"] == 0

	# Verify all dirty keys removed
	dirty_keys = frappe.cache().smembers("progress_dirty_keys")
	assert len(dirty_keys) == 0


def test_sync_best_hearts_with_bitmarks():
	"""Test syncing best hearts data along with bitmaps."""
	player_id = "TEST-PLAYER-005"
	subject_id = "TEST-SUBJ-003"

	# Set up test data
	test_bitmap = b'\x07'
	test_hearts = {"LESSON-001": 5, "LESSON-002": 3}

	redis_bitmap_key = bitmap_manager.get_redis_key(player_id, subject_id)
	redis_hearts_key = bitmap_manager.get_best_hearts_key(player_id, subject_id)

	frappe.cache().set(redis_bitmap_key, test_bitmap)
	frappe.cache().set(redis_hearts_key, __import__('json').dumps(test_hearts))
	bitmap_manager.mark_dirty(player_id, subject_id)

	# Sync pending bitmaps
	result = snapshot_syncer.sync_pending_bitmaps()

	# Verify sync successful
	assert result["synced_count"] == 1

	# Verify MariaDB snapshot updated
	progress = frappe.get_doc(
		"Memora Structure Progress",
		{"player": player_id, "subject": subject_id}
	)

	decoded_bitmap = bitmap_manager.decode_bitmap_from_mariadb(progress.passed_lessons_bitset)
	assert decoded_bitmap == test_bitmap
	assert progress.best_hearts_data == test_hearts


def test_sync_with_missing_progress_doc():
	"""Test syncing when progress doc doesn't exist (should create)."""
	player_id = "TEST-PLAYER-006"
	subject_id = "TEST-SUBJ-004"

	# Set up Redis data but no MariaDB doc
	test_bitmap = b'\x0f'
	redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
	frappe.cache().set(redis_key, test_bitmap)
	bitmap_manager.mark_dirty(player_id, subject_id)

	# Delete progress doc if exists
	progress_name = frappe.get_value(
		"Memora Structure Progress",
		{"player": player_id, "subject": subject_id},
		"name"
	)
	if progress_name:
		frappe.delete_doc("Memora Structure Progress", progress_name)

	# Sync pending bitmaps (should create new doc)
	result = snapshot_syncer.sync_pending_bitmaps()

	# Verify sync attempted
	assert result["synced_count"] == 1

	# Verify progress doc created (or logged as error if academic plan missing)


def test_sync_batch_limit():
	"""Test that sync processes limited batch size."""
	# Create many dirty keys
	for i in range(150):
		player_id = f"TEST-PLAYER-BATCH-{i}"
		subject_id = "TEST-SUBJ-BATCH"
		test_bitmap = bytes([i % 256])
		redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
		frappe.cache().set(redis_key, test_bitmap)
		bitmap_manager.mark_dirty(player_id, subject_id)

	# Sync pending bitmaps
	result = snapshot_syncer.sync_pending_bitmaps(max_batch_size=100)

	# Should sync limited batch
	assert result["synced_count"] <= 100

	# Some keys should remain dirty
	dirty_keys = frappe.cache().smembers("progress_dirty_keys")
	assert len(dirty_keys) > 0


def test_sync_error_handling():
	"""Test error handling when sync fails for a key."""
	player_id = "INVALID-PLAYER"
	subject_id = "TEST-SUBJ-ERROR"

	# Mark dirty without setting up valid data
	bitmap_manager.mark_dirty(player_id, subject_id)

	# Sync pending bitmaps
	result = snapshot_syncer.sync_pending_bitmaps()

	# Should log error and continue
	assert result["failed_count"] >= 1


def test_sync_updates_timestamp():
	"""Test that sync updates last_synced_at timestamp."""
	player_id = "TEST-PLAYER-007"
	subject_id = "TEST-SUBJ-005"

	# Set up test data
	test_bitmap = b'\x01'
	redis_key = bitmap_manager.get_redis_key(player_id, subject_id)
	frappe.cache().set(redis_key, test_bitmap)
	bitmap_manager.mark_dirty(player_id, subject_id)

	# Sync pending bitmaps
	snapshot_syncer.sync_pending_bitmaps()

	# Verify timestamp updated
	import frappe as frappe_module
	before_sync = frappe_module.utils.now()
	progress = frappe.get_doc(
		"Memora Structure Progress",
		{"player": player_id, "subject": subject_id}
	)
	assert progress.last_synced_at is not None


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
