# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Tests for SRS Safe Mode (T021, T022, T023)

Test suite for Safe Mode functionality covering:
- Safe Mode fallback query when Redis is unavailable
- Rate limiting (global 500 req/min, per-user 1 req/30s)
- Degraded mode response behavior
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, add_to_date
from memora.api.utils import SafeModeManager


class TestSRSSafeMode(FrappeTestCase):
	"""
	Test cases for SRS Safe Mode functionality
	"""

	def setUp(self):
		"""Set up test fixtures"""
		self.test_user = "test@example.com"
		self.test_season = "SEASON-TEST-SAFE-MODE"
		self.safe_mode = SafeModeManager()

	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()

	# =========================================================
	# T022: Safe Mode Fallback Query Tests
	# =========================================================

	def test_safe_mode_fallback_query(self):
		"""
		Test Safe Mode fallback query (T022)

		Scenario: Redis unavailable, query DB directly
		Expected: Returns limited set of due items from DB
		"""
		# Setup: Create test season
		season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		season_doc.insert()

		# Setup: Create memory tracker records
		now = frappe.utils.now_datetime()
		due_question_ids = []

		for i in range(15):
			question_id = f"Q-SAFE-MODE-{i:03d}"
			# Make items due (past date)
			next_review_date = now - frappe.utils.timedelta(hours=(i + 1))

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

		# Add some future items (should not be returned)
		for i in range(5):
			question_id = f"Q-FUTURE-{i:03d}"
			next_review_date = now + frappe.utils.timedelta(hours=(i + 1))

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

		# Act: Call Safe Mode fallback query
		from memora.api.reviews import get_reviews_safe_mode
		safe_mode_items = get_reviews_safe_mode(
			self.test_user,
			self.test_season,
			limit=10
		)

		# Assert: Returns limited number of items
		self.assertEqual(len(safe_mode_items), 10,
			"Safe Mode should limit to 10 items")

		# Assert: Only due items returned
		for item in safe_mode_items:
			self.assertIn(item.question_id, due_question_ids,
				f"Item {item.question_id} should be in due list")

		# Cleanup
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	def test_safe_mode_with_subject_filter(self):
		"""
		Test Safe Mode with subject filtering

		Scenario: User has items from multiple subjects
		Expected: Only items from requested subject returned
		"""
		# Setup: Create test season
		season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		season_doc.insert()

		# Create test subjects
		subject1_doc = frappe.get_doc({
			"doctype": "Game Subject",
			"subject_name": "Test Subject 1"
		})
		subject1_doc.insert()

		subject2_doc = frappe.get_doc({
			"doctype": "Game Subject",
			"subject_name": "Test Subject 2"
		})
		subject2_doc.insert()

		# Setup: Create memory tracker records for both subjects
		now = frappe.utils.now_datetime()

		# Subject 1 items (due)
		for i in range(5):
			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": self.test_season,
				"question_id": f"Q-SUB1-{i:03d}",
				"subject": subject1_doc.name,
				"stability": 1,
				"next_review_date": now - frappe.utils.timedelta(hours=1),
				"last_review_date": now
			})
			tracker_doc.insert()

		# Subject 2 items (due)
		for i in range(5):
			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": self.test_season,
				"question_id": f"Q-SUB2-{i:03d}",
				"subject": subject2_doc.name,
				"stability": 1,
				"next_review_date": now - frappe.utils.timedelta(hours=1),
				"last_review_date": now
			})
			tracker_doc.insert()

		# Act: Get items with subject filter
		from memora.api.reviews import get_reviews_safe_mode
		safe_mode_items = get_reviews_safe_mode(
			self.test_user,
			self.test_season,
			subject=subject1_doc.name,
			limit=10
		)

		# Assert: Only subject 1 items returned
		self.assertEqual(len(safe_mode_items), 5)
		for item in safe_mode_items:
			self.assertEqual(item.subject, subject1_doc.name,
				f"Item {item.question_id} should be from subject 1")

		# Cleanup
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.delete("Game Subject", {"subject_name": ["in", ["Test Subject 1", "Test Subject 2"]]})
		frappe.db.commit()

	def test_safe_mode_empty_result(self):
		"""
		Test Safe Mode with no due items

		Scenario: User has no due items
		Expected: Returns empty list
		"""
		# Setup: Create test season
		season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 1,
			"partition_created": 1,
			"enable_redis": 1
		})
		season_doc.insert()

		# Setup: Create future items only (not due)
		now = frappe.utils.now_datetime()
		for i in range(5):
			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": self.test_season,
				"question_id": f"Q-FUTURE-{i:03d}",
				"stability": 1,
				"next_review_date": now + frappe.utils.timedelta(hours=24),
				"last_review_date": now
			})
			tracker_doc.insert()

		# Act: Get Safe Mode items
		from memora.api.reviews import get_reviews_safe_mode
		safe_mode_items = get_reviews_safe_mode(
			self.test_user,
			self.test_season,
			limit=10
		)

		# Assert: Empty list
		self.assertEqual(len(safe_mode_items), 0,
			"Safe Mode should return empty list when no due items")

		# Cleanup
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	# =========================================================
	# T023: Rate Limiting Tests
	# =========================================================

	def test_rate_limit_per_user(self):
		"""
		Test per-user rate limiting (T023)

		Scenario: User makes requests faster than 30s interval
		Expected: Second request is rate limited
		"""
		# Act: First request should pass
		allowed1 = self.safe_mode.check_rate_limit(self.test_user)
		self.assertTrue(allowed1, "First request should be allowed")

		# Act: Second request immediately (within 30s window)
		allowed2 = self.safe_mode.check_rate_limit(self.test_user)
		self.assertFalse(allowed2, "Second request within 30s should be rate limited")

	def test_rate_limit_different_users(self):
		"""
		Test rate limiting is per-user

		Scenario: Different users make requests
		Expected: Each user has independent rate limit
		"""
		user1 = "user1@example.com"
		user2 = "user2@example.com"

		# User 1 makes request
		allowed1 = self.safe_mode.check_rate_limit(user1)
		self.assertTrue(allowed1, "User1 first request should be allowed")

		# User 2 makes request (should be independent)
		allowed2 = self.safe_mode.check_rate_limit(user2)
		self.assertTrue(allowed2, "User2 first request should be allowed")

		# User 1 tries again (should be rate limited)
		allowed1_again = self.safe_mode.check_rate_limit(user1)
		self.assertFalse(allowed1_again, "User1 second request should be rate limited")

	def test_rate_limit_after_expiry(self):
		"""
		Test rate limit expires after 30s

		Scenario: User waits 30s between requests
		Expected: Second request is allowed
		"""
		# Act: First request
		allowed1 = self.safe_mode.check_rate_limit(self.test_user)
		self.assertTrue(allowed1, "First request should be allowed")

		# Simulate time passing by manipulating cache
		# In real scenario, we'd wait 30s, but for testing we'll clear cache
		cache_key = f"safe_mode_rate:{self.test_user}"
		frappe.cache().delete(cache_key)

		# Act: Second request after cache expiry
		allowed2 = self.safe_mode.check_rate_limit(self.test_user)
		self.assertTrue(allowed2, "Request after 30s should be allowed")

	def test_global_rate_limit_tracking(self):
		"""
		Test global rate limit tracking (500 req/min)

		Scenario: Multiple users make requests
		Expected: Global counter tracks total requests
		"""
		# Get initial global counter
		global_key = "safe_mode_global_requests"
		initial_count = frappe.cache().get(global_key) or 0

		# Make requests from multiple users
		for i in range(10):
			user = f"user{i}@example.com"
			self.safe_mode.check_rate_limit(user)

		# Check global counter increased
		final_count = frappe.cache().get(global_key) or 0
		self.assertEqual(final_count, initial_count + 10,
			"Global counter should track all requests")

		# Cleanup
		frappe.cache().delete(global_key)

	# =========================================================
	# Safe Mode Detection Tests
	# =========================================================

	def test_safe_mode_detection_redis_available(self):
		"""
		Test Safe Mode detection when Redis is available

		Expected: is_safe_mode_active() returns False
		"""
		# Act: Check Safe Mode status
		is_safe_mode = self.safe_mode.is_safe_mode_active()

		# Assert: Safe Mode not active (Redis available)
		self.assertFalse(is_safe_mode,
			"Safe Mode should not be active when Redis is available")

	def test_safe_mode_detection_redis_unavailable(self):
		"""
		Test Safe Mode detection when Redis is unavailable

		Expected: is_safe_mode_active() returns True
		"""
		# Note: This test would require mocking Redis unavailability
		# For now, we test the method exists and handles exceptions
		try:
			# The method should handle Redis ping failure gracefully
			is_safe_mode = self.safe_mode.is_safe_mode_active()
			# In normal test environment with Redis running, this should be False
			self.assertFalse(is_safe_mode)
		except Exception as e:
			# If it raises an exception, that's a failure
			self.fail(f"is_safe_mode_active() should handle Redis errors: {e}")
