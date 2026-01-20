# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Tests for SRS Archiver

Test suite for SRSArchiver class covering:
- Season data archiving (copy to Archived Memory Tracker)
- Cache cleanup after archiving
- Retention flagging (3+ years)
- Auto-archive scheduled job
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from datetime import timedelta, datetime
from memora.services.srs_archiver import SRSArchiver


class TestSRSArchiver(FrappeTestCase):
	"""
	Test cases for SRSArchiver
	"""

	def setUp(self):
		"""Set up test fixtures"""
		self.archiver = SRSArchiver()
		self.test_user = "test@example.com"
		self.test_season = "SEASON-TEST-ARCHIVE"

		# Create test season
		self.season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": self.test_season,
			"start_date": frappe.utils.today(),
			"end_date": frappe.utils.add_days(frappe.utils.today(), 365),
			"is_active": 0,  # Inactive season
			"partition_created": 1,
			"enable_redis": 1,
			"auto_archive": 1
		})
		self.season_doc.insert()

	def tearDown(self):
		"""Clean up test data"""
		# Delete test records
		frappe.db.delete("Player Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Archived Memory Tracker", {"player": self.test_user})
		frappe.db.delete("Game Subscription Season", {"season_name": self.test_season})
		frappe.db.commit()

	def test_archive_season_data_migration(self):
		"""
		Test archive_season() data migration (T051)

		Scenario: Season has memory tracker records
		Expected: Records copied to Archived Memory Tracker and deleted from Player Memory Tracker
		"""
		# Setup: Create memory tracker records
		now = frappe.utils.now_datetime()
		question_ids = []

		for i in range(3):
			question_id = f"Q-ARCHIVE-{i:03d}"
			question_ids.append(question_id)

			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": self.test_season,
				"question_id": question_id,
				"stability": 2,
				"next_review_date": now + timedelta(days=2),
				"last_review_date": now
			})
			tracker_doc.insert()

		# Verify records exist in Player Memory Tracker
		player_tracker_count = frappe.db.count("Player Memory Tracker", {
			"player": self.test_user,
			"season": self.test_season
		})
		self.assertEqual(player_tracker_count, 3, "Should have 3 records before archiving")

		# Act: Archive season
		result = self.archiver.archive_season(self.test_season)

		# Assert: Archive successful
		self.assertTrue(result["success"], "Archive should succeed")
		self.assertEqual(result["archived_count"], 3, "Should archive 3 records")

		# Assert: Records deleted from Player Memory Tracker
		player_tracker_count = frappe.db.count("Player Memory Tracker", {
			"player": self.test_user,
			"season": self.test_season
		})
		self.assertEqual(player_tracker_count, 0, "Should have 0 records after archiving")

		# Assert: Records copied to Archived Memory Tracker
		archived_count = frappe.db.count("Archived Memory Tracker", {
			"player": self.test_user,
			"season": self.test_season
		})
		self.assertEqual(archived_count, 3, "Should have 3 archived records")

		# Assert: Archived records have correct data
		for question_id in question_ids:
			archived_doc = frappe.get_doc("Archived Memory Tracker", {
				"player": self.test_user,
				"season": self.test_season,
				"question_id": question_id
			})
			self.assertIsNotNone(archived_doc, f"Archived record should exist for {question_id}")
			self.assertEqual(archived_doc.stability, 2, "Stability should be preserved")
			self.assertIsNotNone(archived_doc.archived_at, "archived_at should be set")

	def test_archive_season_cache_cleanup(self):
		"""
		Test cache cleanup after archiving (T052)

		Scenario: Season has data in Redis cache
		Expected: Cache is cleared after archiving
		"""
		# Setup: Add items to Redis cache
		from memora.services.srs_redis_manager import SRSRedisManager

		redis_manager = SRSRedisManager()
		now = frappe.utils.now_datetime()

		# Add cache items
		for i in range(5):
			question_id = f"Q-CACHE-{i:03d}"
			next_review_ts = (now + timedelta(hours=i)).timestamp()
			redis_manager.add_item(self.test_user, self.test_season, question_id, next_review_ts)

		# Verify cache exists
		cache_items = redis_manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(len(cache_items), 5, "Should have 5 cache items before archiving")

		# Act: Archive season (should clear cache)
		result = self.archiver.archive_season(self.test_season)

		# Assert: Archive successful
		self.assertTrue(result["success"], "Archive should succeed")

		# Assert: Cache is cleared
		cache_items = redis_manager.get_all_scores(self.test_user, self.test_season)
		self.assertEqual(len(cache_items), 0, "Cache should be empty after archiving")

	def test_archive_season_with_multiple_users(self):
		"""
		Test archiving season with multiple users

		Scenario: Season has records from multiple users
		Expected: All users' records are archived
		"""
		# Setup: Create records for multiple users
		users = ["user1@example.com", "user2@example.com", "user3@example.com"]
		now = frappe.utils.now_datetime()

		for user in users:
			for i in range(2):
				question_id = f"Q-{user.split('@')[0]}-{i:03d}"
				tracker_doc = frappe.get_doc({
					"doctype": "Player Memory Tracker",
					"player": user,
					"season": self.test_season,
					"question_id": question_id,
					"stability": 1,
					"next_review_date": now + timedelta(days=1),
					"last_review_date": now
				})
				tracker_doc.insert()

		# Verify records exist
		total_records = frappe.db.count("Player Memory Tracker", {"season": self.test_season})
		self.assertEqual(total_records, 6, "Should have 6 records before archiving")

		# Act: Archive season
		result = self.archiver.archive_season(self.test_season)

		# Assert: All records archived
		self.assertTrue(result["success"], "Archive should succeed")
		self.assertEqual(result["archived_count"], 6, "Should archive 6 records")

		# Assert: All records deleted from Player Memory Tracker
		total_records = frappe.db.count("Player Memory Tracker", {"season": self.test_season})
		self.assertEqual(total_records, 0, "Should have 0 records after archiving")

	def test_archive_season_empty_season(self):
		"""
		Test archiving season with no records

		Scenario: Season has no memory tracker records
		Expected: Archive succeeds with 0 records
		"""
		# Act: Archive empty season
		result = self.archiver.archive_season(self.test_season)

		# Assert: Archive successful
		self.assertTrue(result["success"], "Archive should succeed")
		self.assertEqual(result["archived_count"], 0, "Should archive 0 records")

	def test_flag_eligible_for_deletion(self):
		"""
		Test retention flagging (3+ years) (T053)

		Scenario: Archived records older than 3 years
		Expected: Records flagged for deletion
		"""
		# Setup: Create archived records with different ages
		now = frappe.utils.now_datetime()

		# Record older than 3 years (eligible)
		old_record = frappe.get_doc({
			"doctype": "Archived Memory Tracker",
			"player": self.test_user,
			"season": self.test_season,
			"question_id": "Q-OLD-001",
			"stability": 2,
			"next_review_date": now,
			"last_review_date": now,
			"archived_at": now - timedelta(days=1100),  # 3+ years ago
			"eligible_for_deletion": 0
		})
		old_record.insert()

		# Record younger than 3 years (not eligible)
		new_record = frappe.get_doc({
			"doctype": "Archived Memory Tracker",
			"player": self.test_user,
			"season": self.test_season,
			"question_id": "Q-NEW-001",
			"stability": 2,
			"next_review_date": now,
			"last_review_date": now,
			"archived_at": now - timedelta(days=365),  # 1 year ago
			"eligible_for_deletion": 0
		})
		new_record.insert()

		# Act: Flag eligible records
		result = self.archiver.flag_eligible_for_deletion()

		# Assert: Flagging successful
		self.assertTrue(result["success"], "Flagging should succeed")
		self.assertEqual(result["flagged_count"], 1, "Should flag 1 record")

		# Assert: Old record is flagged
		old_record.reload()
		self.assertEqual(old_record.eligible_for_deletion, 1, "Old record should be flagged")

		# Assert: New record is not flagged
		new_record.reload()
		self.assertEqual(new_record.eligible_for_deletion, 0, "New record should not be flagged")

	def test_process_auto_archive(self):
		"""
	 Test process_auto_archive() scheduled job

		Scenario: Seasons marked for auto-archive
		Expected: Eligible seasons are archived
		"""
		# Setup: Create another season with auto_archive enabled
		season2 = "SEASON-TEST-AUTO-ARCHIVE"
		season_doc = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": season2,
			"start_date": frappe.utils.add_days(frappe.utils.today(), -400),
			"end_date": frappe.utils.add_days(frappe.utils.today(), -30),
			"is_active": 0,  # Inactive
			"partition_created": 1,
			"enable_redis": 1,
			"auto_archive": 1
		})
		season_doc.insert()

		# Add memory tracker records for season2
		now = frappe.utils.now_datetime()
		for i in range(2):
			question_id = f"Q-AUTO-{i:03d}"
			tracker_doc = frappe.get_doc({
				"doctype": "Player Memory Tracker",
				"player": self.test_user,
				"season": season2,
				"question_id": question_id,
				"stability": 1,
				"next_review_date": now + timedelta(days=1),
				"last_review_date": now
			})
			tracker_doc.insert()

		# Act: Process auto-archive
		result = self.archiver.process_auto_archive()

		# Assert: Auto-archive successful
		self.assertTrue(result["success"], "Auto-archive should succeed")
		self.assertGreater(result["archived_seasons"], 0, "Should archive at least 1 season")

		# Assert: Season2 is archived
		player_tracker_count = frappe.db.count("Player Memory Tracker", {
			"season": season2
		})
		self.assertEqual(player_tracker_count, 0, "Season2 should be archived")

		# Cleanup
		frappe.db.delete("Archived Memory Tracker", {"season": season2})
		frappe.db.delete("Game Subscription Season", {"season_name": season2})
		frappe.db.commit()

	def test_archive_season_preserves_data_integrity(self):
		"""
		Test that archived data preserves all fields

		Scenario: Memory tracker with all fields populated
		Expected: Archived record has all fields preserved
		"""
		# Setup: Create memory tracker with all fields
		now = frappe.utils.now_datetime()
		question_id = "Q-INTEGRITY-001"

		# Create subject and topic
		subject_doc = frappe.get_doc({
			"doctype": "Game Subject",
			"subject_name": "Test Subject"
		})
		subject_doc.insert()

		topic_doc = frappe.get_doc({
			"doctype": "Game Topic",
			"topic_name": "Test Topic",
			"subject": subject_doc.name
		})
		topic_doc.insert()

		tracker_doc = frappe.get_doc({
			"doctype": "Player Memory Tracker",
			"player": self.test_user,
			"season": self.test_season,
			"question_id": question_id,
			"stability": 3,
			"next_review_date": now + timedelta(days=7),
			"last_review_date": now,
			"subject": subject_doc.name,
			"topic": topic_doc.name
		})
		tracker_doc.insert()

		# Act: Archive season
		result = self.archiver.archive_season(self.test_season)

		# Assert: Archive successful
		self.assertTrue(result["success"], "Archive should succeed")

		# Assert: Archived record has all fields
		archived_doc = frappe.get_doc("Archived Memory Tracker", {
			"player": self.test_user,
			"season": self.test_season,
			"question_id": question_id
		})
		self.assertIsNotNone(archived_doc, "Archived record should exist")
		self.assertEqual(archived_doc.stability, 3, "Stability should be preserved")
		self.assertEqual(archived_doc.subject, subject_doc.name, "Subject should be preserved")
		self.assertEqual(archived_doc.topic, topic_doc.name, "Topic should be preserved")
		self.assertIsNotNone(archived_doc.archived_at, "archived_at should be set")

		# Cleanup
		frappe.db.delete("Archived Memory Tracker", {"question_id": question_id})
		frappe.db.delete("Game Topic", {"name": topic_doc.name})
		frappe.db.delete("Game Subject", {"name": subject_doc.name})
		frappe.db.commit()
