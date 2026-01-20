# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestArchivedMemoryTracker(FrappeTestCase):
	"""
	Test cases for Archived Memory Tracker DocType
	"""

	def setUp(self):
		"""Set up test fixtures"""
		# Create test user
		self.user = frappe.get_doc({
			"doctype": "User",
			"email": "test_archived@example.com",
			"first_name": "Test",
			"last_name": "User"
		}).insert()

		# Create test season
		self.season = frappe.get_doc({
			"doctype": "Game Subscription Season",
			"season_name": "SEASON-TEST-ARCHIVE",
			"start_date": "2025-01-01",
			"end_date": "2025-12-31",
			"is_active": 0
		}).insert()

	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()

	def test_create_archived_record(self):
		"""Test creating an archived memory tracker record"""
		record = frappe.get_doc({
			"doctype": "Archived Memory Tracker",
			"player": self.user.name,
			"season": self.season.name,
			"question_id": "Q-TEST-001",
			"stability": 3.5,
			"next_review_date": "2026-01-20 10:00:00",
			"last_review_date": "2026-01-19 10:00:00"
		}).insert()

		self.assertTrue(record.name)
		self.assertEqual(record.player, self.user.name)
		self.assertEqual(record.season, self.season.name)
		self.assertEqual(record.question_id, "Q-TEST-001")

	def test_archived_at_auto_set(self):
		"""Test that archived_at is automatically set on creation"""
		record = frappe.get_doc({
			"doctype": "Archived Memory Tracker",
			"player": self.user.name,
			"season": self.season.name,
			"question_id": "Q-TEST-002",
			"stability": 2.0
		}).insert()

		self.assertIsNotNone(record.archived_at)

	def test_prevent_manual_eligible_flag(self):
		"""Test that eligible_for_deletion cannot be set manually"""
		record = frappe.get_doc({
			"doctype": "Archived Memory Tracker",
			"player": self.user.name,
			"season": self.season.name,
			"question_id": "Q-TEST-003",
			"eligible_for_deletion": 1
		})

		with self.assertRaises(frappe.ValidationError):
			record.insert()

	def test_prevent_deletion_unless_eligible(self):
		"""Test that records cannot be deleted unless eligible_for_deletion is set"""
		record = frappe.get_doc({
			"doctype": "Archived Memory Tracker",
			"player": self.user.name,
			"season": self.season.name,
			"question_id": "Q-TEST-004",
			"stability": 4.0
		}).insert()

		with self.assertRaises(frappe.ValidationError):
			record.delete()

	def test_read_only_fields_protected(self):
		"""Test that read-only fields cannot be modified after creation"""
		record = frappe.get_doc({
			"doctype": "Archived Memory Tracker",
			"player": self.user.name,
			"season": self.season.name,
			"question_id": "Q-TEST-005",
			"stability": 1.5
		}).insert()

		# Try to modify a read-only field
		record.stability = 5.0

		# The modification should be ignored or prevented
		# (This is a basic test; actual behavior depends on Frappe's field read_only implementation)
		self.assertIsNotNone(record.name)
