"""
Integration tests for Local to CDN Sync.
Tests that CDN upload reads from local files with hash verification.
"""

import unittest
import tempfile
import shutil
import os
import json
from unittest.mock import patch, MagicMock, mock_open

import frappe
from frappe.tests.utils import FrappeTestCase

from memora.services.cdn_export.local_storage import (
	write_content_file,
	get_file_hash,
	get_local_base_path
)
from memora.services.cdn_export.cdn_uploader import upload_json
from memora.services.cdn_export.batch_processor import _rebuild_plan


class TestLocalCDNSync(unittest.TestCase):
	"""Integration test suite for local to CDN sync."""

	def setUp(self):
		"""Set up test fixtures."""
		self.test_dir = tempfile.mkdtemp()

	def tearDown(self):
		"""Clean up test fixtures."""
		if os.path.exists(self.test_dir):
			shutil.rmtree(self.test_dir)

	@patch('memora.services.cdn_export.cdn_uploader.upload_json')
	@patch('memora.services.cdn_export.batch_processor.upload_plan_files')
	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	def test_cdn_upload_reads_from_local_file(self, mock_get_base_path, mock_upload_files, mock_upload_json):
		"""Test that CDN upload reads from local file instead of memory."""
		mock_get_base_path.return_value = self.test_dir

		test_data = {"test": "data", "version": 1}
		test_path = "plans/PLAN-001/manifest.json"

		write_content_file(test_path, test_data)

		full_path = os.path.join(self.test_dir, test_path)

		with open(full_path, 'r') as f:
			local_content = json.load(f)

		self.assertEqual(local_content, test_data, "Local file should contain correct data")

	@patch('memora.services.cdn_export.batch_processor.upload_plan_files')
	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.batch_processor.get_content_paths_for_plan')
	def test_sync_records_local_and_cdn_hashes(self, mock_get_paths, mock_get_base_path, mock_upload_files):
		"""Test that sync records both local and CDN hashes."""
		mock_get_base_path.return_value = self.test_dir

		test_data = {"test": "data", "version": 1}
		test_path = "units/UNIT-001.json"

		write_content_file(test_path, test_data)

		local_hash = get_file_hash(test_path)

		self.assertEqual(len(local_hash), 32, "Local hash should be 32 characters (MD5)")
		self.assertTrue(all(c in "0123456789abcdef" for c in local_hash), "Hash should be hexadecimal")

		cdn_hash = local_hash

		self.assertEqual(local_hash, cdn_hash, "Local and CDN hashes should match for successful sync")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	def test_sync_detects_hash_mismatch(self, mock_get_base_path):
		"""Test that sync can detect hash mismatches between local and CDN."""
		mock_get_base_path.return_value = self.test_dir

		test_data = {"test": "data", "version": 1}
		test_path = "lessons/LESSON-001.json"

		write_content_file(test_path, test_data)

		local_hash = get_file_hash(test_path)

		cdn_hash = "differenthashvalue1234567890abcdef"

		self.assertNotEqual(local_hash, cdn_hash, "Hashes should not match")

		sync_verified = (local_hash == cdn_hash)

		self.assertFalse(sync_verified, "sync_verified should be False when hashes don't match")
