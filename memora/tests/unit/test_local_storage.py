"""
Unit tests for Local Storage Manager.
Tests atomic file writes, versioning, and disk space management.
"""

import unittest
import tempfile
import shutil
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import frappe
from frappe.tests.utils import FrappeTestCase

from memora.services.cdn_export.local_storage import (
	write_content_file,
	file_exists,
	get_file_hash,
	check_disk_space,
	get_local_base_path,
	delete_content_file,
	delete_content_directory
)


class TestLocalStorage(unittest.TestCase):
	"""Test suite for local storage operations."""

	def setUp(self):
		"""Set up test fixtures."""
		self.test_dir = tempfile.mkdtemp()

	def tearDown(self):
		"""Clean up test fixtures."""
		if os.path.exists(self.test_dir):
			shutil.rmtree(self.test_dir)

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_write_content_file_creates_directory(self, mock_log_error, mock_get_base_path):
		"""Test that write_content_file creates necessary directories."""
		mock_get_base_path.return_value = self.test_dir
		test_data = {"test": "data"}
		test_path = "nested/directory/test.json"

		success, error = write_content_file(test_path, test_data)

		self.assertTrue(success, "File write should succeed")
		self.assertIsNone(error, "Error should be None")

		full_path = os.path.join(self.test_dir, test_path)
		self.assertTrue(os.path.exists(full_path), "File should exist")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_write_content_file_atomic_write(self, mock_log_error, mock_get_base_path):
		"""Test that write_content_file uses atomic writes."""
		mock_get_base_path.return_value = self.test_dir
		test_data = {"test": "data"}
		test_path = "atomic/test.json"

		success, error = write_content_file(test_path, test_data)

		self.assertTrue(success, "File write should succeed")
		self.assertIsNone(error, "Error should be None")

		full_path = os.path.join(self.test_dir, test_path)

		with open(full_path, 'r') as f:
			file_content = json.load(f)

		self.assertEqual(file_content, test_data, "File content should match input")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_write_content_file_creates_prev_version(self, mock_log_error, mock_get_base_path):
		"""Test that write_content_file creates .prev version on overwrite."""
		mock_get_base_path.return_value = self.test_dir
		test_data1 = {"version": 1}
		test_data2 = {"version": 2}
		test_path = "versioned/test.json"

		write_content_file(test_path, test_data1)
		write_content_file(test_path, test_data2)

		full_path = os.path.join(self.test_dir, test_path)
		prev_path = full_path + ".prev"

		self.assertTrue(os.path.exists(prev_path), ".prev file should exist")

		with open(prev_path, 'r') as f:
			prev_content = json.load(f)

		self.assertEqual(prev_content, test_data1, ".prev should contain old data")

		with open(full_path, 'r') as f:
			current_content = json.load(f)

		self.assertEqual(current_content, test_data2, "Current file should contain new data")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_write_content_file_fails_on_low_disk(self, mock_log_error, mock_get_base_path):
		"""Test that write_content_file fails gracefully on low disk space."""
		mock_get_base_path.return_value = self.test_dir
		test_data = {"test": "data"}
		test_path = "disk_test/test.json"

		success, error = write_content_file(test_path, test_data, require_min_disk_percent=99.99)

		self.assertFalse(success, "File write should fail on low disk space")
		self.assertIsNotNone(error, "Error should be set")
		self.assertIn("disk space", str(error).lower(), "Error should mention disk space")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_file_exists_returns_correct_value(self, mock_log_error, mock_get_base_path):
		"""Test that file_exists returns correct boolean values."""
		mock_get_base_path.return_value = self.test_dir
		test_data = {"test": "data"}
		test_path = "exists/test.json"

		self.assertFalse(file_exists(test_path), "File should not exist initially")

		write_content_file(test_path, test_data)

		self.assertTrue(file_exists(test_path), "File should exist after write")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_get_file_hash_returns_md5(self, mock_log_error, mock_get_base_path):
		"""Test that get_file_hash returns correct MD5 hash."""
		mock_get_base_path.return_value = self.test_dir
		test_data = {"test": "data", "number": 123}
		test_path = "hash/test.json"

		write_content_file(test_path, test_data)

		hash1 = get_file_hash(test_path)
		hash2 = get_file_hash(test_path)

		self.assertEqual(hash1, hash2, "Hash should be consistent")
		self.assertEqual(len(hash1), 32, "MD5 hash should be 32 characters")
		self.assertTrue(all(c in "0123456789abcdef" for c in hash1), "Hash should be hexadecimal")

		test_data2 = {"test": "different"}
		write_content_file(test_path, test_data2)

		hash3 = get_file_hash(test_path)
		self.assertNotEqual(hash1, hash3, "Different data should produce different hash")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_delete_content_file_removes_file_and_prev(self, mock_log_error, mock_get_base_path):
		"""Test that delete_content_file removes both the file and its .prev version."""
		mock_get_base_path.return_value = self.test_dir
		test_data1 = {"version": 1}
		test_data2 = {"version": 2}
		test_path = "delete/test.json"

		write_content_file(test_path, test_data1)
		write_content_file(test_path, test_data2)

		full_path = os.path.join(self.test_dir, test_path)
		prev_path = full_path + ".prev"

		self.assertTrue(os.path.exists(full_path), "File should exist")
		self.assertTrue(os.path.exists(prev_path), ".prev file should exist")

		success, error = delete_content_file(test_path)

		self.assertTrue(success, "Delete should succeed")
		self.assertIsNone(error, "Error should be None")
		self.assertFalse(os.path.exists(full_path), "File should be deleted")
		self.assertFalse(os.path.exists(prev_path), ".prev file should be deleted")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_delete_content_directory_removes_all(self, mock_log_error, mock_get_base_path):
		"""Test that delete_content_directory removes all files in a plan folder."""
		mock_get_base_path.return_value = self.test_dir
		plan_path = "plans/PLAN-001"

		write_content_file(f"{plan_path}/manifest.json", {"plan": "data"})
		write_content_file(f"{plan_path}/search_index.json", {"index": "data"})
		write_content_file(f"{plan_path}/subjects/SUB-001.json", {"subject": "data"})

		full_plan_path = os.path.join(self.test_dir, plan_path)
		self.assertTrue(os.path.exists(full_plan_path), "Plan directory should exist")
		self.assertTrue(os.path.exists(os.path.join(full_plan_path, "manifest.json")), "manifest.json should exist")
		self.assertTrue(os.path.exists(os.path.join(full_plan_path, "search_index.json")), "search_index.json should exist")
		self.assertTrue(os.path.exists(os.path.join(full_plan_path, "subjects", "SUB-001.json")), "SUB-001.json should exist")

		success, error = delete_content_directory(plan_path)

		self.assertTrue(success, "Delete should succeed")
		self.assertIsNone(error, "Error should be None")
		self.assertFalse(os.path.exists(full_plan_path), "Plan directory should be deleted")

	@patch('memora.services.cdn_export.local_storage.get_local_base_path')
	@patch('memora.services.cdn_export.local_storage.frappe.log_error')
	def test_delete_removes_empty_parent_dirs(self, mock_log_error, mock_get_base_path):
		"""Test that delete functions remove empty parent directories."""
		mock_get_base_path.return_value = self.test_dir
		plan_path = "plans/PLAN-001"

		write_content_file(f"{plan_path}/nested/deep/file.json", {"data": "test"})

		full_plan_path = os.path.join(self.test_dir, plan_path)
		nested_dir = os.path.join(full_plan_path, "nested")
		deep_dir = os.path.join(nested_dir, "deep")

		self.assertTrue(os.path.exists(deep_dir), "Deep directory should exist")
		self.assertTrue(os.path.exists(nested_dir), "Nested directory should exist")

		delete_content_directory(plan_path)

		self.assertFalse(os.path.exists(full_plan_path), "Plan directory should be deleted")
		self.assertFalse(os.path.exists(nested_dir), "Nested directory should be deleted")
		self.assertFalse(os.path.exists(deep_dir), "Deep directory should be deleted")

