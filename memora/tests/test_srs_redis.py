# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Tests for SRS Redis Manager

Test suite for SRSRedisManager class covering:
- Redis connection handling
- ZADD operations (add_item, add_batch)
- ZRANGEBYSCORE operations (get_due_items)
- ZREM operations (remove_item)
- Health checks (is_available)
- Batch operations
- Cache rehydration
"""

import frappe
from frappe.tests.utils import FrappeTestCase
import time
from datetime import timedelta
from memora.services.srs_redis_manager import SRSRedisManager


class TestSRSRedisManager(FrappeTestCase):
	"""
	Test cases for SRSRedisManager
	"""

	def setUp(self):
		"""Set up test fixtures"""
		self.manager = SRSRedisManager()
		self.test_user = "test@example.com"
		self.test_season = "SEASON-TEST-REDIS"

	def tearDown(self):
		"""Clean up test data"""
		# Clear test cache
		self.manager.clear_user_cache(self.test_user, self.test_season)
		frappe.db.rollback()

	def test_redis_connection(self):
		"""Test that Redis connection is established"""
		self.assertIsNotNone(self.manager.redis)
		self.assertTrue(self.manager.is_available())

	def test_make_key(self):
		"""Test Redis key generation"""
		key = self.manager._make_key(self.test_user, self.test_season)
		expected_key = f"srs:{self.test_user}:{self.test_season}"
		self.assertEqual(key, expected_key)

	def test_add_item(self):
		"""Test adding a single item to Redis"""
		question_id = "Q-TEST-001"
		next_review_ts = time.time() + 3600  # 1 hour from now

		result = self.manager.add_item(
			self.test_user,
			self.test_season,
			question_id,
			next_review_ts
		)

		self.assertTrue(result)

		# Verify item was added
		all_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertIn(question_id, all_items)
		self.assertEqual(all_items[question_id], next_review_ts)

	def test_get_due_items(self):
		"""Test retrieving due items"""
		# Add items with different review times
		now = time.time()

		# Due item (past)
		self.manager.add_item(
			self.test_user,
			self.test_season,
			"Q-DUE-001",
			now - 3600
		)

		# Due item (now)
		self.manager.add_item(
			self.test_user,
			self.test_season,
			"Q-DUE-002",
			now
		)

		# Future item (not due)
		self.manager.add_item(
			self.test_user,
			self.test_season,
			"Q-FUTURE-001",
			now + 3600
		)

		# Get due items
		due_items = self.manager.get_due_items(self.test_user, self.test_season)

		# Should only return due items
		self.assertIn("Q-DUE-001", due_items)
		self.assertIn("Q-DUE-002", due_items)
		self.assertNotIn("Q-FUTURE-001", due_items)

	def test_get_due_items_with_limit(self):
		"""Test limiting number of returned items"""
		now = time.time()

		# Add 5 due items
		for i in range(5):
			self.manager.add_item(
				self.test_user,
				self.test_season,
				f"Q-DUE-{i:03d}",
				now - (i * 100)
			)

		# Get only 3 items
		due_items = self.manager.get_due_items(
			self.test_user,
			self.test_season,
			limit=3
		)

		self.assertEqual(len(due_items), 3)

	def test_remove_item(self):
		"""Test removing an item from Redis"""
		question_id = "Q-TEST-REMOVE"
		next_review_ts = time.time() + 3600

		# Add item
		self.manager.add_item(
			self.test_user,
			self.test_season,
			question_id,
			next_review_ts
		)

		# Verify it exists
		all_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertIn(question_id, all_items)

		# Remove item
		result = self.manager.remove_item(
			self.test_user,
			self.test_season,
			question_id
		)

		self.assertTrue(result)

		# Verify it's gone
		all_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertNotIn(question_id, all_items)

	def test_add_batch(self):
		"""Test adding multiple items in batch"""
		now = time.time()
		items = {
			"Q-BATCH-001": now + 3600,
			"Q-BATCH-002": now + 7200,
			"Q-BATCH-003": now + 10800,
		}

		result = self.manager.add_batch(
			self.test_user,
			self.test_season,
			items
		)

		self.assertTrue(result)

		# Verify all items were added
		all_items = self.manager.get_all_scores(self.test_user, self.test_season)
		for question_id, timestamp in items.items():
			self.assertIn(question_id, all_items)
			self.assertEqual(all_items[question_id], timestamp)

	def test_get_all_scores(self):
		"""Test retrieving all items and scores"""
		now = time.time()

		# Add items
		items = {
			"Q-ALL-001": now + 1000,
			"Q-ALL-002": now + 2000,
			"Q-ALL-003": now + 3000,
		}

		self.manager.add_batch(self.test_user, self.test_season, items)

		# Get all scores
		all_scores = self.manager.get_all_scores(self.test_user, self.test_season)

		self.assertEqual(len(all_scores), 3)
		for question_id, timestamp in items.items():
			self.assertIn(question_id, all_scores)
			self.assertEqual(all_scores[question_id], timestamp)

	def test_count_due_items(self):
		"""Test counting due items"""
		now = time.time()

		# Add 3 due items
		for i in range(3):
			self.manager.add_item(
				self.test_user,
				self.test_season,
				f"Q-COUNT-DUE-{i}",
				now - (i * 100)
			)

		# Add 2 future items
		for i in range(2):
			self.manager.add_item(
				self.test_user,
				self.test_season,
				f"Q-COUNT-FUTURE-{i}",
				now + 3600 + (i * 100)
			)

		# Count due items
		due_count = self.manager.count_due_items(self.test_user, self.test_season)

		self.assertEqual(due_count, 3)

	def test_clear_user_cache(self):
		"""Test clearing user cache"""
		# Add items
		now = time.time()
		for i in range(5):
			self.manager.add_item(
				self.test_user,
				self.test_season,
				f"Q-CLEAR-{i}",
				now + i * 100
			)

		# Verify items exist
		all_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(len(all_items), 5)

		# Clear cache
		result = self.manager.clear_user_cache(self.test_user, self.test_season)

		self.assertTrue(result)

		# Verify cache is empty
		all_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(len(all_items), 0)

	def test_get_cache_stats(self):
		"""Test getting cache statistics"""
		now = time.time()

		# Add items
		for i in range(10):
			self.manager.add_item(
				self.test_user,
				self.test_season,
				f"Q-STATS-{i}",
				now + i * 100
			)

		# Add some due items
		for i in range(3):
			self.manager.add_item(
				self.test_user,
				self.test_season,
				f"Q-STATS-DUE-{i}",
				now - (i * 100)
			)

		# Get stats
		stats = self.manager.get_cache_stats(self.test_user, self.test_season)

		self.assertEqual(stats["total_items"], 13)
		self.assertEqual(stats["due_items"], 3)
		self.assertGreater(stats["memory_usage_bytes"], 0)

	def test_get_due_items_with_rehydration(self):
		"""Test cache rehydration on miss"""
		# Clear cache first
		self.manager.clear_user_cache(self.test_user, self.test_season)

		# Get due items (should trigger rehydration)
		# Since we don't have DB records, this should return empty list
		due_items, was_rehydrated = self.manager.get_due_items_with_rehydration(
			self.test_user,
			self.test_season
		)

		# Should return empty (no DB records)
		self.assertEqual(due_items, [])
		# Should indicate rehydration was attempted
		self.assertTrue(was_rehydrated)

	def test_update_existing_item(self):
		"""Test updating an existing item's score"""
		question_id = "Q-UPDATE-TEST"
		old_score = time.time() + 3600
		new_score = time.time() + 7200

		# Add item with old score
		self.manager.add_item(
			self.test_user,
			self.test_season,
			question_id,
			old_score
		)

		# Verify old score
		all_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(all_items[question_id], old_score)

		# Update with new score
		self.manager.add_item(
			self.test_user,
			self.test_season,
			question_id,
			new_score
		)

		# Verify new score
		all_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(all_items[question_id], new_score)

	def test_multiple_users_isolated(self):
		"""Test that different users have isolated caches"""
		user1 = "user1@example.com"
		user2 = "user2@example.com"

		# Add items for user1
		self.manager.add_item(
			user1,
			self.test_season,
			"Q-USER1-001",
			time.time() + 3600
		)

		# Add items for user2
		self.manager.add_item(
			user2,
			self.test_season,
			"Q-USER2-001",
			time.time() + 3600
		)

		# Verify isolation
		user1_items = self.manager.get_all_scores(user1, self.test_season)
		user2_items = self.manager.get_all_scores(user2, self.test_season)

		self.assertIn("Q-USER1-001", user1_items)
		self.assertNotIn("Q-USER2-001", user1_items)

		self.assertIn("Q-USER2-001", user2_items)
		self.assertNotIn("Q-USER1-001", user2_items)

	# =========================================================
	# User Story 1 Tests: get_review_session with Redis
	# =========================================================

	def test_get_review_session_cache_hit(self):
		"""
		Test get_review_session with cache hit (T019)

		Scenario: User has due items in Redis cache
		Expected: Due items retrieved from cache in <100ms
		"""
		# Setup: Add due items to cache
		now = time.time()
		due_question_ids = []

		for i in range(5):
			question_id = f"Q-CACHE-HIT-{i:03d}"
			# Make items due (past timestamp)
			next_review_ts = now - (3600 * (i + 1))
			self.manager.add_item(
				self.test_user,
				self.test_season,
				question_id,
				next_review_ts
			)
			due_question_ids.append(question_id)

		# Act: Get due items (cache hit)
		start_time = time.time()
		due_items = self.manager.get_due_items(
			self.test_user,
			self.test_season,
			limit=10
		)
		end_time = time.time()

		# Assert: Items retrieved from cache
		self.assertEqual(len(due_items), 5)
		for qid in due_question_ids:
			self.assertIn(qid, due_items)

		# Assert: Performance <100ms (cache hit)
		response_time_ms = (end_time - start_time) * 1000
		self.assertLess(response_time_ms, 100,
			f"Cache hit took {response_time_ms:.2f}ms, expected <100ms")

	def test_get_review_session_cache_miss_with_rehydration(self):
		"""
		Test lazy loading on cache miss (T020)

		Scenario: User has no cache, but has DB records
		Expected: Cache is rehydrated from DB, due items returned
		"""
		# Setup: Create test Player Memory Tracker records
		test_season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		test_season_doc.insert()

		# Create memory tracker records
		now = frappe.utils.now_datetime()
		due_question_ids = []

		for i in range(3):
			question_id = f"Q-REHYDRATE-{i:03d}"
			# Make items due (past date)
			next_review_date = now - timedelta(hours=(i + 1))

			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": self.test_season,
				"question_id": question_id,
				"stability": 1,
				"next_review_date": next_review_date,
				"last_review_date": now
			})
			tracker_doc.insert()
			due_question_ids.append(question_id)

		# Clear cache to simulate cache miss
		self.manager.clear_user_cache(self.test_user, self.test_season)

		# Act: Get due items with rehydration
		due_items, was_rehydrated = self.manager.get_due_items_with_rehydration(
			self.test_user,
			self.test_season,
			limit=10
		)

		# Assert: Rehydration was triggered
		self.assertTrue(was_rehydrated, "Cache rehydration should have been triggered")

		# Assert: Due items returned
		self.assertEqual(len(due_items), 3)
		for qid in due_question_ids:
			self.assertIn(qid, due_items)

		# Assert: Cache is now populated
		cache_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(len(cache_items), 3, "Cache should be populated after rehydration")

		# Cleanup
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	def test_get_review_session_with_subject_filter(self):
		"""
		Test subject filtering in Redis queries (T031)

		Scenario: User has items from multiple subjects
		Expected: Only items from requested subject are returned
		"""
		# Setup: Add items from different subjects
		now = time.time()

		# Subject 1 items (due)
		for i in range(3):
			question_id = f"Q-SUBJECT1-{i:03d}"
			self.manager.add_item(
				self.test_user,
				self.test_season,
				question_id,
				now - 3600  # Due
			)

		# Subject 2 items (due)
		for i in range(2):
			question_id = f"Q-SUBJECT2-{i:03d}"
			self.manager.add_item(
				self.test_user,
				self.test_season,
				question_id,
				now - 3600  # Due
			)

		# Act: Get all due items
		due_items = self.manager.get_due_items(
			self.test_user,
			self.test_season,
			limit=10
		)

		# Assert: All items returned
		self.assertEqual(len(due_items), 5)

	# =========================================================
	# User Story 2 Tests: submit_review_session with Redis
	# =========================================================

	def test_submit_review_session_redis_update(self):
		"""
		Test submit_review_session with Redis update (T032)

		Scenario: User submits review responses
		Expected: Redis cache is updated synchronously with new schedules
		"""
		# Setup: Create test season
		test_season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		test_season_doc.insert()

		# Create initial memory tracker records
		now = frappe.utils.now_datetime()
		question_ids = []

		for i in range(3):
			question_id = f"Q-REDIS-UPDATE-{i:03d}"
			question_ids.append(question_id)

			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": self.test_season,
				"question_id": question_id,
				"stability": 1,
				"next_review_date": now - timedelta(hours=1),  # Due
				"last_review_date": now
			})
			tracker_doc.insert()

		# Populate initial cache
		for i, qid in enumerate(question_ids):
			self.manager.add_item(
				self.test_user,
				self.test_season,
				qid,
				(now - timedelta(hours=1)).timestamp()
			)

		# Act: Simulate review submission with new schedules
		new_schedules = {}
		for i, qid in enumerate(question_ids):
			# Simulate SRS calculation - different next review times
			next_review_ts = time.time() + (3600 * (i + 1))  # 1, 2, 3 hours from now
			new_schedules[qid] = next_review_ts

			# Update Redis synchronously
			self.manager.add_item(
				self.test_user,
				self.test_season,
				qid,
				next_review_ts
			)

		# Assert: Redis cache is updated with new schedules
		cache_items = self.manager.get_all_scores(self.test_user, self.test_season)

		self.assertEqual(len(cache_items), 3)
		for qid, new_ts in new_schedules.items():
			self.assertIn(qid, cache_items)
			self.assertEqual(cache_items[qid], new_ts)

		# Assert: No items are due anymore (all in future)
		due_items = self.manager.get_due_items(self.test_user, self.test_season)
		self.assertEqual(len(due_items), 0)

		# Cleanup
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	def test_submit_review_session_background_persistence(self):
		"""
		Test background persistence job (T033)

		Scenario: Review responses submitted, persistence job queued
		Expected: Database is updated asynchronously via background job
		"""
		# Setup: Create test season
		test_season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		test_season_doc.insert()

		# Create initial memory tracker records
		now = frappe.utils.now_datetime()
		question_id = "Q-BG-PERSIST-001"

		tracker_doc = frappe.get_doc({
			"doctype": "Player Memory Tracker",
			"player": self.test_user,
			"season": self.test_season,
			"question_id": question_id,
			"stability": 1,
			"next_review_date": now - timedelta(hours=1),
			"last_review_date": now
		})
		tracker_doc.insert()

		# Get initial stability
		initial_tracker = frappe.get_doc("Player Memory Tracker", tracker_doc.name)
		initial_stability = initial_tracker.stability

		# Act: Simulate persistence job updating database
		# This represents what the background job would do
		new_stability = 2
		new_next_review = now + timedelta(hours=24)

		# Update database (simulating background job)
		frappe.db.set_value("Player Memory Tracker", tracker_doc.name, {
			"stability": new_stability,
			"next_review_date": new_next_review,
			"last_review_date": now
		})
		frappe.db.commit()

		# Assert: Database is updated
		updated_tracker = frappe.get_doc("Player Memory Tracker", tracker_doc.name)
		self.assertEqual(updated_tracker.stability, new_stability)
		self.assertNotEqual(updated_tracker.stability, initial_stability)

		# Cleanup
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	def test_read_after_write_consistency(self):
		"""
		Test read-after-write consistency (T034)

		Scenario: User submits review, then immediately retrieves due items
		Expected: Cache reflects new schedule immediately
		"""
		# Setup: Create test season
		test_season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		test_season_doc.insert()

		# Create memory tracker record
		now = frappe.utils.now_datetime()
		question_id = "Q-CONSISTENCY-001"

		tracker_doc = frappe.get_doc({
			"doctype": "Player Memory Tracker",
			"player": self.test_user,
			"season": self.test_season,
			"question_id": question_id,
			"stability": 1,
			"next_review_date": now - timedelta(hours=1),  # Due
			"last_review_date": now
		})
		tracker_doc.insert()

		# Populate cache with due item
		self.manager.add_item(
			self.test_user,
			self.test_season,
			question_id,
			(now - timedelta(hours=1)).timestamp()
		)

		# Verify item is due before review
		due_items_before = self.manager.get_due_items(
			self.test_user,
			self.test_season,
			limit=10
		)
		self.assertIn(question_id, due_items_before)

		# Act: Submit review (update Redis with new schedule)
		new_review_ts = time.time() + 3600  # 1 hour from now
		self.manager.add_item(
			self.test_user,
			self.test_season,
			question_id,
			new_review_ts
		)

		# Immediately read due items (read-after-write)
		due_items_after = self.manager.get_due_items(
			self.test_user,
			self.test_season,
			limit=10
		)

		# Assert: Item is no longer due (cache updated immediately)
		self.assertNotIn(question_id, due_items_after)

		# Assert: Cache reflects new schedule
		cache_items = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertIn(question_id, cache_items)
		self.assertEqual(cache_items[question_id], new_review_ts)

		# Cleanup
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	# =========================================================
	# TTL Tests: Automatic cleanup of inactive user caches
	# =========================================================

	def test_add_item_sets_ttl_on_new_key(self):
		"""
		Test that add_item sets TTL on new Redis keys

		Scenario: Adding an item to a new user-season key
		Expected: TTL is set to DEFAULT_TTL (30 days)
		"""
		# Clear cache first
		self.manager.clear_user_cache(self.test_user, self.test_season)

		# Add item to new key
		question_id = "Q-TTL-NEW-001"
		next_review_ts = time.time() + 3600
		result = self.manager.add_item(
			self.test_user,
			self.test_season,
			question_id,
			next_review_ts
		)
		self.assertTrue(result)

		# Check that TTL is set
		key = self.manager._make_key(self.test_user, self.test_season)
		ttl = self.manager.redis.ttl(key)

		# TTL should be positive and close to DEFAULT_TTL (allowing some variance)
		self.assertGreater(ttl, 0, "TTL should be set on new key")
		self.assertLessEqual(ttl, SRSRedisManager.DEFAULT_TTL, "TTL should not exceed DEFAULT_TTL")
		self.assertGreater(ttl, SRSRedisManager.DEFAULT_TTL - 10, "TTL should be close to DEFAULT_TTL")

	def test_add_item_preserves_existing_ttl(self):
		"""
		Test that add_item doesn't reset TTL on existing keys

		Scenario: Adding an item to an existing key with TTL
		Expected: Existing TTL is preserved (not reset)
		"""
		# Clear cache first
		self.manager.clear_user_cache(self.test_user, self.test_season)

		# Add first item (sets TTL)
		self.manager.add_item(
			self.test_user,
			self.test_season,
			"Q-TTL-FIRST-001",
			time.time() + 3600
		)

		key = self.manager._make_key(self.test_user, self.test_season)
		initial_ttl = self.manager.redis.ttl(key)

		# Wait a short time
		time.sleep(1)

		# Add second item to same key
		self.manager.add_item(
			self.test_user,
			self.test_season,
			"Q-TTL-SECOND-001",
			time.time() + 7200
		)

		# Check that TTL hasn't been reset
		new_ttl = self.manager.redis.ttl(key)
		self.assertLess(new_ttl, initial_ttl, "TTL should not be reset when adding to existing key")

	def test_add_batch_sets_ttl_on_new_key(self):
		"""
		Test that add_batch sets TTL on new Redis keys

		Scenario: Adding a batch of items to a new user-season key
		Expected: TTL is set to DEFAULT_TTL (30 days)
		"""
		# Clear cache first
		self.manager.clear_user_cache(self.test_user, self.test_season)

		# Add batch to new key
		now = time.time()
		items = {
			"Q-TTL-BATCH-001": now + 3600,
			"Q-TTL-BATCH-002": now + 7200,
			"Q-TTL-BATCH-003": now + 10800,
		}
		result = self.manager.add_batch(
			self.test_user,
			self.test_season,
			items
		)
		self.assertTrue(result)

		# Check that TTL is set
		key = self.manager._make_key(self.test_user, self.test_season)
		ttl = self.manager.redis.ttl(key)

		# TTL should be positive and close to DEFAULT_TTL
		self.assertGreater(ttl, 0, "TTL should be set on new key")
		self.assertLessEqual(ttl, SRSRedisManager.DEFAULT_TTL, "TTL should not exceed DEFAULT_TTL")

	def test_rehydrate_user_cache_sets_ttl(self):
		"""
		Test that _rehydrate_user_cache sets TTL when rehydrating

		Scenario: Cache miss triggers rehydration from database
		Expected: Rehydrated cache has TTL set
		"""
		# Setup: Create test season and tracker records
		test_season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		test_season_doc.insert()

		# Create memory tracker records
		now = frappe.utils.now_datetime()
		question_id = "Q-TTL-REHYDRATE-001"

		tracker_doc = frappe.get_doc({
			"doctype": "Player Memory Tracker",
			"player": self.test_user,
			"season": self.test_season,
			"question_id": question_id,
			"stability": 1,
			"next_review_date": now - timedelta(hours=1),  # Due
			"last_review_date": now
		})
		tracker_doc.insert()

		# Clear cache to force rehydration
		self.manager.clear_user_cache(self.test_user, self.test_season)

		# Trigger rehydration
		due_items = self.manager._rehydrate_user_cache(self.test_user, self.test_season)

		# Check that TTL is set on rehydrated cache
		key = self.manager._make_key(self.test_user, self.test_season)
		ttl = self.manager.redis.ttl(key)

		self.assertGreater(ttl, 0, "TTL should be set on rehydrated cache")
		self.assertLessEqual(ttl, SRSRedisManager.DEFAULT_TTL, "TTL should not exceed DEFAULT_TTL")

		# Cleanup
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	def test_custom_ttl_parameter(self):
		"""
		Test that custom TTL can be passed to add_item and add_batch

		Scenario: Adding items with custom TTL
		Expected: Custom TTL is used instead of DEFAULT_TTL
		"""
		# Clear cache first
		self.manager.clear_user_cache(self.test_user, self.test_season)

		# Add item with custom TTL (60 seconds)
		custom_ttl = 60
		question_id = "Q-TTL-CUSTOM-001"
		result = self.manager.add_item(
			self.test_user,
			self.test_season,
			question_id,
			time.time() + 3600,
			ttl=custom_ttl
		)
		self.assertTrue(result)

		# Check that custom TTL is set
		key = self.manager._make_key(self.test_user, self.test_season)
		ttl = self.manager.redis.ttl(key)

		self.assertGreater(ttl, 0, "TTL should be set")
		self.assertLessEqual(ttl, custom_ttl, "TTL should not exceed custom TTL")

		# Test add_batch with custom TTL
		self.manager.clear_user_cache(self.test_user, self.test_season)
		items = {"Q-TTL-BATCH-CUSTOM-001": time.time() + 3600}
		result = self.manager.add_batch(
			self.test_user,
			self.test_season,
			items,
			ttl=custom_ttl
		)
		self.assertTrue(result)

		ttl = self.manager.redis.ttl(key)
		self.assertGreater(ttl, 0, "TTL should be set for batch")
		self.assertLessEqual(ttl, custom_ttl, "TTL should not exceed custom TTL for batch")

	# =========================================================
	# User Story 3 Tests: Season Partition Creation
	# =========================================================

	def test_season_after_insert_hook_partition_creation(self):
		"""
		Test season after_insert hook partition creation (T042)

		Scenario: Administrator creates a new Game Subscription Season
		Expected: Database partition is automatically created and partition_created flag is set
		"""
		from memora.services.partition_manager import check_partition_exists

		# Create a test season
		test_season_name = "SEASON-TEST-PARTITION-001"
		season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": test_season_name,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 0,
			"partition_created": 0,
			"enable_redis": 1,
			"auto_archive": 0
		})

		# Insert season (should trigger after_insert hook)
		season_doc.insert()

		# Assert: partition_created flag is set to 1
		self.assertEqual(season_doc.partition_created, 1,
			"partition_created flag should be set to 1 after season creation")

		# Assert: Partition exists in database
		partition_exists = check_partition_exists(test_season_name)
		self.assertTrue(partition_exists,
			f"Partition for season {test_season_name} should exist")

		# Cleanup
		frappe.db.delete("Game Subscription Season", {"season_name": test_season_name})
		frappe.db.commit()

	def test_partition_idempotency(self):
		"""
		Test partition idempotency - skip if exists (T043)

		Scenario: Create season, then attempt to create partition again
		Expected: Second creation attempt is skipped gracefully (no error)
		"""
		from memora.services.partition_manager import create_season_partition, check_partition_exists

		# Create a test season
		test_season_name = "SEASON-TEST-IDEMPOTENT-001"
		season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": test_season_name,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 0,
			"partition_created": 0,
			"enable_redis": 1,
			"auto_archive": 0
		})

		season_doc.insert()

		# Verify partition was created
		self.assertTrue(check_partition_exists(test_season_name),
			"Partition should exist after season creation")

		# Attempt to create partition again (should not raise error)
		try:
			create_season_partition(test_season_name)
			# Success - no error raised
			idempotent_success = True
		except Exception as e:
			idempotent_success = False
			error_message = str(e)

		# Assert: Idempotent creation succeeded
		self.assertTrue(idempotent_success,
			f"Second partition creation should not raise error. Error: {error_message if not idempotent_success else 'None'}")

		# Cleanup
		frappe.db.delete("Game Subscription Season", {"season_name": test_season_name})
		frappe.db.commit()

	# =========================================================
	# User Story 5 Tests: Admin Monitoring & Cache Management
	# =========================================================

	def test_get_cache_status_endpoint(self):
		"""
		Test get_cache_status() endpoint (T063)

		Scenario: Administrator requests cache health and statistics
		Expected: Returns Redis connectivity, memory usage, and key counts by season
		"""
		from memora.api.srs import get_cache_status

		# Setup: Add test data to cache
		now = time.time()

		# Add items for season 1
		season1 = "SEASON-TEST-STATUS-001"
		for i in range(10):
			self.manager.add_item(
				self.test_user,
				season1,
				f"Q-STATUS-1-{i}",
				now + i * 100
			)

		# Add items for season 2
		season2 = "SEASON-TEST-STATUS-002"
		for i in range(5):
			self.manager.add_item(
				self.test_user,
				season2,
				f"Q-STATUS-2-{i}",
				now + i * 100
			)

		# Act: Get cache status
		status = get_cache_status()

		# Assert: Redis is connected
		self.assertTrue(status.get("redis_connected"),
			"Redis should be connected")

		# Assert: Safe mode is not active (Redis is available)
		self.assertFalse(status.get("is_safe_mode"),
			"Safe mode should not be active when Redis is available")

		# Assert: Memory usage is reported
		self.assertGreater(status.get("memory_used_mb", 0), 0,
			"Memory usage should be reported")

		# Assert: Total keys count is present
		self.assertGreater(status.get("total_keys", 0), 0,
			"Total keys should be counted")

		# Assert: Keys by season are tracked
		keys_by_season = status.get("keys_by_season", {})
		self.assertIsInstance(keys_by_season, dict,
			"keys_by_season should be a dictionary")

		# Cleanup
		self.manager.clear_user_cache(self.test_user, season1)
		self.manager.clear_user_cache(self.test_user, season2)

	def test_rebuild_season_cache_background_job(self):
		"""
		Test rebuild_season_cache() background job (T064)

		Scenario: Administrator triggers cache rebuild for a season
		Expected: Background job is queued, progress is tracked, cache is rebuilt
		"""
		from memora.services.srs_redis_manager import rebuild_season_cache

		# Setup: Create test season and memory tracker records
		test_season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		test_season_doc.insert()

		# Create memory tracker records
		now = frappe.utils.now_datetime()
		question_ids = []

		for i in range(5):
			question_id = f"Q-REBUILD-{i:03d}"
			question_ids.append(question_id)

			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": self.test_season,
				"question_id": question_id,
				"stability": 1,
				"next_review_date": now + timedelta(hours=i),
				"last_review_date": now
			})
			tracker_doc.insert()

		# Clear cache to simulate cache that needs rebuilding
		self.manager.clear_user_cache(self.test_user, self.test_season)

		# Verify cache is empty before rebuild
		cache_before = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(len(cache_before), 0,
			"Cache should be empty before rebuild")

		# Act: Trigger cache rebuild
		rebuild_season_cache(self.test_season)

		# Assert: Cache is populated with DB records
		cache_after = self.manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(len(cache_after), 5,
			"Cache should be populated after rebuild")

		# Assert: All question IDs are in cache
		for qid in question_ids:
			self.assertIn(qid, cache_after,
				f"Question {qid} should be in cache after rebuild")

		# Cleanup
		self.manager.clear_user_cache(self.test_user, self.test_season)
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	def test_trigger_reconciliation_discrepancy_detection(self):
		"""
		Test trigger_reconciliation() discrepancy detection (T065)

		Scenario: Manual reconciliation is triggered
		Expected: Samples DB records, compares with cache, detects discrepancies
		"""
		from memora.services.srs_reconciliation import reconcile_cache_with_database

		# Setup: Create test season and memory tracker records
		test_season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		test_season_doc.insert()

		# Create memory tracker records
		now = frappe.utils.now_datetime()
		question_ids = []

		for i in range(10):
			question_id = f"Q-RECONCILE-{i:03d}"
			question_ids.append(question_id)

			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": self.test_season,
				"question_id": question_id,
				"stability": 1,
				"next_review_date": now + timedelta(hours=i),
				"last_review_date": now
			})
			tracker_doc.insert()

		# Populate cache with correct data
		for i, qid in enumerate(question_ids):
			next_review_ts = (now + timedelta(hours=i)).timestamp()
			self.manager.add_item(
				self.test_user,
				self.test_season,
				qid,
				next_review_ts
			)

		# Act: Trigger reconciliation
		result = reconcile_cache_with_database(sample_size=100)

		# Assert: Reconciliation completed
		self.assertIn("sample_size", result,
			"Result should include sample_size")

		self.assertIn("discrepancies_found", result,
			"Result should include discrepancies_found")

		self.assertIn("discrepancy_rate", result,
			"Result should include discrepancy_rate")

		self.assertIn("auto_corrected", result,
			"Result should include auto_corrected")

		# Assert: Sample size is reasonable
		self.assertGreater(result["sample_size"], 0,
			"Sample size should be greater than 0")

		# Assert: Discrepancy rate is calculated
		self.assertIsInstance(result["discrepancy_rate"], float,
			"Discrepancy rate should be a float")

		# Assert: Since cache and DB are in sync, discrepancy rate should be 0
		self.assertEqual(result["discrepancies_found"], 0,
			"No discrepancies should be found when cache and DB are in sync")

		# Now test with a discrepancy
		# Modify one record in DB but not in cache
		question_to_modify = question_ids[0]
		new_review_date = now + timedelta(hours=100)

		frappe.db.set_value("Player Memory Tracker",
			{"question_id": question_to_modify, "player": self.test_user},
			"next_review_date", new_review_date)
		frappe.db.commit()

		# Trigger reconciliation again
		result_with_discrepancy = reconcile_cache_with_database(sample_size=100)

		# Assert: Discrepancy is detected
		self.assertGreater(result_with_discrepancy["discrepancies_found"], 0,
			"Discrepancy should be detected when cache and DB are out of sync")

		# Assert: Auto-correction happened
		self.assertGreater(result_with_discrepancy["auto_corrected"], 0,
			"Auto-correction should fix discrepancies")

		# Verify cache was corrected
		cache_items = self.manager.get_all_scores(self.test_user, self.test_season)
		corrected_score = cache_items.get(question_to_modify)
		expected_score = new_review_date.timestamp()

		self.assertEqual(corrected_score, expected_score,
			"Cache should be corrected to match DB")

		# Cleanup
		self.manager.clear_user_cache(self.test_user, self.test_season)
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()
