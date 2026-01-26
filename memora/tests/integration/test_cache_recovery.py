"""Integration tests for cache miss recovery."""

import pytest
import frappe
from frappe.tests.utils import FrappeTestCase


class TestCacheRecoveryIntegration(FrappeTestCase):
	"""Integration tests for cache miss and recovery flow."""

	def setUp(self):
		"""Set up test data before each test."""
		frappe.set_user("Administrator")

	def test_cache_miss_warms_from_mariadb(self):
		"""Test that cache miss triggers MariaDB warm."""
		player_id = "TEST-PLAYER-REC-001"
		subject_id = "TEST-SUBJ-REC-001"

		# Create progress record with bitmap in MariaDB
		test_bitmap = b'\x07'
		encoded = __import__('memora.services.progress_engine.bitmap_manager', fromlist=['bitmap_manager']).bitmap_manager.encode_bitmap_for_mariadb(test_bitmap)

		academic_plan = frappe.get_value("Memora Subject", subject_id, "academic_plan") or "TEST-PLAN-001"

		progress_doc = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": player_id,
			"subject": subject_id,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": encoded,
			"best_hearts_data": {}
		})
		progress_doc.insert(ignore_permissions=True)

		# Clear Redis cache to force cache miss
		from memora.services.progress_engine.bitmap_manager import get_redis_key
		redis_key = get_redis_key(player_id, subject_id)
		frappe.cache().delete(redis_key)

		# Request progress (should warm cache)
		from memora.services.progress_engine import progress_computer
		progress = progress_computer.compute_progress(subject_id)

		# Verify cache was warmed
		cached_bitmap = frappe.cache().get(redis_key)
		assert cached_bitmap is not None
		assert cached_bitmap == test_bitmap

	def test_redis_failure_falls_back_to_mariadb(self):
		"""Test that Redis failure falls back to MariaDB."""
		player_id = "TEST-PLAYER-REC-002"
		subject_id = "TEST-SUBJ-REC-002"

		# Create progress record with bitmap in MariaDB
		test_bitmap = b'\x0f'
		encoded = __import__('memora.services.progress_engine.bitmap_manager', fromlist=['bitmap_manager']).bitmap_manager.encode_bitmap_for_mariadb(test_bitmap)

		academic_plan = frappe.get_value("Memora Subject", subject_id, "academic_plan") or "TEST-PLAN-002"

		progress_doc = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": player_id,
			"subject": subject_id,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": encoded,
			"best_hearts_data": {}
		})
		progress_doc.insert(ignore_permissions=True)

		# Simulate Redis failure by deleting cache
		from memora.services.progress_engine.bitmap_manager import get_redis_key
		redis_key = get_redis_key(player_id, subject_id)
		frappe.cache().delete(redis_key)

		# Request progress (should fall back to MariaDB)
		from memora.services.progress_engine import progress_computer
		progress = progress_computer.compute_progress(subject_id)

		# Verify progress computed correctly from MariaDB
		assert progress is not None
		assert progress["subject_id"] == subject_id

	def test_cache_warm_updates_dirty_key_tracking(self):
		"""Test that cache warming doesn't affect dirty key tracking."""
		player_id = "TEST-PLAYER-REC-003"
		subject_id = "TEST-SUBJ-REC-003"

		# Create progress record in MariaDB
		test_bitmap = b'\x03'
		encoded = __import__('memora.services.progress_engine.bitmap_manager', fromlist=['bitmap_manager']).bitmap_manager.encode_bitmap_for_mariadb(test_bitmap)

		academic_plan = frappe.get_value("Memora Subject", subject_id, "academic_plan") or "TEST-PLAN-003"

		progress_doc = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": player_id,
			"subject": subject_id,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": encoded,
			"best_hearts_data": {}
		})
		progress_doc.insert(ignore_permissions=True)

		# Warm cache
		from memora.services.progress_engine import cache_warmer
		cache_warmer.warm_from_mariadb(player_id, subject_id)

		# Verify key not marked as dirty
		dirty_keys = frappe.cache().smembers("progress_dirty_keys")
		from memora.services.progress_engine.bitmap_manager import get_redis_key
		assert get_redis_key(player_id, subject_id) not in dirty_keys

	def test_warm_both_bitmap_and_best_hearts(self):
		"""Test warming both bitmap and best hearts data."""
		player_id = "TEST-PLAYER-REC-004"
		subject_id = "TEST-SUBJ-REC-004"

		# Create progress record with both bitmap and best hearts
		test_bitmap = b'\x07'
		test_hearts = {"LESSON-001": 5, "LESSON-002": 3}
		encoded = __import__('memora.services.progress_engine.bitmap_manager', fromlist=['bitmap_manager']).bitmap_manager.encode_bitmap_for_mariadb(test_bitmap)

		academic_plan = frappe.get_value("Memora Subject", subject_id, "academic_plan") or "TEST-PLAN-004"

		progress_doc = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": player_id,
			"subject": subject_id,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": encoded,
			"best_hearts_data": test_hearts
		})
		progress_doc.insert(ignore_permissions=True)

		# Warm all data
		from memora.services.progress_engine import cache_warmer
		bitmap, hearts_data = cache_warmer.warm_all_from_mariadb(player_id, subject_id)

		# Verify both warmed correctly
		assert bitmap == test_bitmap
		assert hearts_data == test_hearts

	def test_snapshot_sync_after_recovery(self):
		"""Test that snapshot sync works after cache recovery."""
		player_id = "TEST-PLAYER-REC-005"
		subject_id = "TEST-SUBJ-REC-005"

		# Create progress record in MariaDB
		test_bitmap = b'\x01'
		encoded = __import__('memora.services.progress_engine.bitmap_manager', fromlist=['bitmap_manager']).bitmap_manager.encode_bitmap_for_mariadb(test_bitmap)

		academic_plan = frappe.get_value("Memora Subject", subject_id, "academic_plan") or "TEST-PLAN-005"

		progress_doc = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": player_id,
			"subject": subject_id,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": encoded,
			"best_hearts_data": {}
		})
		progress_doc.insert(ignore_permissions=True)

		# Warm cache
		from memora.services.progress_engine import cache_warmer
		cache_warmer.warm_from_mariadb(player_id, subject_id)

		# Update bitmap in Redis
		from memora.services.progress_engine.bitmap_manager import update_bitmap
		update_bitmap(player_id, subject_id, 1)

		# Mark dirty
		from memora.services.progress_engine.bitmap_manager import mark_dirty
		mark_dirty(player_id, subject_id)

		# Run snapshot sync
		from memora.services.progress_engine import snapshot_syncer
		result = snapshot_syncer.sync_pending_bitmaps()

		# Verify sync successful
		assert result["synced_count"] == 1

		# Verify MariaDB updated
		updated_progress = frappe.get_doc(
			"Memora Structure Progress",
			{"player": player_id, "subject": subject_id}
		)
		updated_bitmap = __import__('memora.services.progress_engine.bitmap_manager', fromlist=['bitmap_manager']).bitmap_manager.decode_bitmap_from_mariadb(updated_progress.passed_lessons_bitset)
		updated_int = int.from_bytes(updated_bitmap or b'\x00', 'big')
		assert (updated_int & (1 << 1)) != 0

	def test_recovery_with_no_progress_record(self):
		"""Test recovery when no progress record exists."""
		player_id = "TEST-PLAYER-REC-006"
		subject_id = "TEST-SUBJ-REC-006"

		# Ensure no progress record exists
		progress_name = frappe.get_value(
			"Memora Structure Progress",
			{"player": player_id, "subject": subject_id},
			"name"
		)
		if progress_name:
			frappe.delete_doc("Memora Structure Progress", progress_name)

		# Try to warm cache (should return empty)
		from memora.services.progress_engine import cache_warmer
		bitmap = cache_warmer.warm_from_mariadb(player_id, subject_id)

		# Should return empty bitmap
		assert bitmap == b''

	def test_concurrent_cache_warms(self):
		"""Test that concurrent cache warm requests are handled correctly."""
		player_id = "TEST-PLAYER-REC-007"
		subject_id = "TEST-SUBJ-REC-007"

		# Create progress record
		test_bitmap = b'\x0f'
		encoded = __import__('memora.services.progress_engine.bitmap_manager', fromlist=['bitmap_manager']).bitmap_manager.encode_bitmap_for_mariadb(test_bitmap)

		academic_plan = frappe.get_value("Memora Subject", subject_id, "academic_plan") or "TEST-PLAN-007"

		progress_doc = frappe.get_doc({
			"doctype": "Memora Structure Progress",
			"player": player_id,
			"subject": subject_id,
			"academic_plan": academic_plan,
			"passed_lessons_bitset": encoded,
			"best_hearts_data": {}
		})
		progress_doc.insert(ignore_permissions=True)

		# Clear Redis cache
		from memora.services.progress_engine.bitmap_manager import get_redis_key
		redis_key = get_redis_key(player_id, subject_id)
		frappe.cache().delete(redis_key)

		# Simulate concurrent warm requests
		from memora.services.progress_engine import cache_warmer
		import threading

		results = []
		def warm_cache():
			result = cache_warmer.warm_from_mariadb(player_id, subject_id)
			results.append(result)

		threads = [threading.Thread(target=warm_cache) for _ in range(5)]
		for t in threads:
			t.start()
		for t in threads:
			t.join()

		# All should succeed with same bitmap
		assert len(results) == 5
		assert all(r == test_bitmap for r in results)


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
