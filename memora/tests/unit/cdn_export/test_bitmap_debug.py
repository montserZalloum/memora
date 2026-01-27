"""
Comprehensive unit tests for debugging empty mappings in {subject.name}_b.json
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import sys
import os

# Add the memora directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))


class TestBitmapMappingsGeneration(unittest.TestCase):
	"""Debug tests for bitmap JSON mappings generation"""

	def _setup_bitmap_mocks(self):
		"""Helper to setup common mocks for bitmap tests"""
		patcher_frappe = patch("memora.services.cdn_export.json_generator.frappe")
		patcher_now = patch("memora.services.cdn_export.json_generator.now_datetime")

		mock_frappe = patcher_frappe.start()
		mock_now = patcher_now.start()

		# Setup datetime
		mock_dt = MagicMock()
		mock_dt.timestamp = Mock(return_value=1706270400)
		mock_dt.isoformat = Mock(return_value="2026-01-26T10:00:00")
		mock_now.return_value = mock_dt

		return {
			"frappe": (patcher_frappe, mock_frappe),
			"now": (patcher_now, mock_now),
		}

    def test_bitmap_full_hierarchy_with_lessons(self):
        """
        DEBUG TEST 1: Full hierarchy with tracks -> units -> topics -> lessons
        This tests the actual query flow to ensure all levels return data
        """
        # Setup mocks first before loading module
        mocks = self._setup_bitmap_mocks()

        # Now load module - it will import frappe which is already mocked
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'json_generator',
            '/home/corex/aurevia-bench/apps/memora/memora/services/cdn_export/json_generator.py'
        )
        json_generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(json_generator)
        generate_bitmap_json = json_generator.generate_bitmap_json

        try:
		try:
			mock_frappe = mocks["frappe"][1]

			# Setup mock subject
			subject_doc = Mock()
			subject_doc.name = "SUBJ-001"

			# Setup mock tracks
			track1 = Mock()
			track1.name = "TRACK-001"

			# Setup mock units
			unit1 = Mock()
			unit1.name = "UNIT-001"

			# Setup mock topics
			topic1 = Mock()
			topic1.name = "TOPIC-001"

			# Setup mock lessons
			lesson1 = Mock()
			lesson1.name = "LESSON-001"
			lesson1.parent_topic = "TOPIC-001"

			lesson2 = Mock()
			lesson2.name = "LESSON-002"
			lesson2.parent_topic = "TOPIC-001"

			# Mock get_all to return proper hierarchy
			def mock_get_all(doctype, filters=None, fields=None, order_by=None):
				if doctype == "Memora Track":
					print(f"[DEBUG] Querying Memora Track with filters: {filters}")
					return [track1]
				elif doctype == "Memora Unit":
					print(f"[DEBUG] Querying Memora Unit with filters: {filters}")
					return [unit1]
				elif doctype == "Memora Topic":
					print(f"[DEBUG] Querying Memora Topic with filters: {filters}")
					return [topic1]
				elif doctype == "Memora Lesson":
					print(f"[DEBUG] Querying Memora Lesson with filters: {filters}")
					if filters and "docstatus" in filters and filters["docstatus"] == 1:
						return [lesson1, lesson2]
					return []
				return []

			mock_frappe.get_all.side_effect = mock_get_all

			# Generate bitmap
			bitmap = generate_bitmap_json(subject_doc)

			# Debug output
			print(f"\n[DEBUG] Generated bitmap: {bitmap}")
			print(f"[DEBUG] Mappings count: {len(bitmap['mappings'])}")
			print(f"[DEBUG] Mappings keys: {list(bitmap['mappings'].keys())}")

			# Assertions
			self.assertIsNotNone(bitmap)
			self.assertEqual(bitmap["subject_id"], "SUBJ-001")
			self.assertEqual(bitmap["total_lessons"], 2)
			self.assertIn("mappings", bitmap)
			self.assertEqual(len(bitmap["mappings"]), 2, "Mappings should have 2 lessons")

			# Verify each lesson has bit_index and topic_id
			self.assertIn("LESSON-001", bitmap["mappings"])
			self.assertIn("bit_index", bitmap["mappings"]["LESSON-001"])
			self.assertIn("topic_id", bitmap["mappings"]["LESSON-001"])
			self.assertEqual(bitmap["mappings"]["LESSON-001"]["topic_id"], "TOPIC-001")

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_bitmap_no_tracks(self):
		"""
		DEBUG TEST 2: No tracks returned for subject
		Expected: mappings should be empty
		"""
		# Load module directly to avoid __init__.py importing frappe
		import importlib.util

		spec = importlib.util.spec_from_file_location(
			"json_generator",
			"/home/corex/aurevia-bench/apps/memora/memora/services/cdn_export/json_generator.py",
		)
		json_generator = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(json_generator)
		generate_bitmap_json = json_generator.generate_bitmap_json

		mocks = self._setup_bitmap_mocks()
		try:
			mock_frappe = mocks["frappe"][1]

			subject_doc = Mock()
			subject_doc.name = "SUBJ-002"

			def mock_get_all(doctype, filters=None, fields=None, order_by=None):
				if doctype == "Memora Track":
					print(f"[DEBUG] Querying Memora Track - returning empty list")
					return []
				print(f"[DEBUG] Querying {doctype} with filters: {filters}")
				return []

			mock_frappe.get_all.side_effect = mock_get_all

			bitmap = generate_bitmap_json(subject_doc)

			print(f"\n[DEBUG] Bitmap with no tracks: {bitmap}")
			print(f"[DEBUG] Mappings count: {len(bitmap['mappings'])}")

			self.assertIsNotNone(bitmap)
			self.assertEqual(bitmap["subject_id"], "SUBJ-002")
			self.assertEqual(bitmap["total_lessons"], 0)
			self.assertEqual(len(bitmap["mappings"]), 0)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_bitmap_no_units(self):
		"""
		DEBUG TEST 3: Tracks exist but no units
		Expected: mappings should be empty
		"""
		# Load module directly to avoid __init__.py importing frappe
		import importlib.util

		spec = importlib.util.spec_from_file_location(
			"json_generator",
			"/home/corex/aurevia-bench/apps/memora/memora/services/cdn_export/json_generator.py",
		)
		json_generator = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(json_generator)
		generate_bitmap_json = json_generator.generate_bitmap_json

		mocks = self._setup_bitmap_mocks()
		try:
			mock_frappe = mocks["frappe"][1]

			subject_doc = Mock()
			subject_doc.name = "SUBJ-003"

			track1 = Mock()
			track1.name = "TRACK-001"

			def mock_get_all(doctype, filters=None, fields=None, order_by=None):
				if doctype == "Memora Track":
					print(f"[DEBUG] Querying Memora Track - returning track")
					return [track1]
				elif doctype == "Memora Unit":
					print(f"[DEBUG] Querying Memora Unit - returning empty")
					return []
				print(f"[DEBUG] Querying {doctype}")
				return []

			mock_frappe.get_all.side_effect = mock_get_all

			bitmap = generate_bitmap_json(subject_doc)

			print(f"\n[DEBUG] Bitmap with no units: {bitmap}")
			print(f"[DEBUG] Mappings count: {len(bitmap['mappings'])}")

			self.assertIsNotNone(bitmap)
			self.assertEqual(bitmap["total_lessons"], 0)
			self.assertEqual(len(bitmap["mappings"]), 0)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_bitmap_no_topics(self):
		"""
		DEBUG TEST 4: Tracks and units exist but no topics
		Expected: mappings should be empty
		"""
		# Load module directly to avoid __init__.py importing frappe
		import importlib.util

		spec = importlib.util.spec_from_file_location(
			"json_generator",
			"/home/corex/aurevia-bench/apps/memora/memora/services/cdn_export/json_generator.py",
		)
		json_generator = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(json_generator)
		generate_bitmap_json = json_generator.generate_bitmap_json

		mocks = self._setup_bitmap_mocks()
		try:
			mock_frappe = mocks["frappe"][1]

			subject_doc = Mock()
			subject_doc.name = "SUBJ-004"

			track1 = Mock()
			track1.name = "TRACK-001"
			unit1 = Mock()
			unit1.name = "UNIT-001"

			def mock_get_all(doctype, filters=None, fields=None, order_by=None):
				if doctype == "Memora Track":
					return [track1]
				elif doctype == "Memora Unit":
					return [unit1]
				elif doctype == "Memora Topic":
					print(f"[DEBUG] Querying Memora Topic - returning empty")
					return []
				return []

			mock_frappe.get_all.side_effect = mock_get_all

			bitmap = generate_bitmap_json(subject_doc)

			print(f"\n[DEBUG] Bitmap with no topics: {bitmap}")
			print(f"[DEBUG] Mappings count: {len(bitmap['mappings'])}")

			self.assertEqual(bitmap["total_lessons"], 0)
			self.assertEqual(len(bitmap["mappings"]), 0)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_bitmap_lessons_not_submitted(self):
		"""
		DEBUG TEST 5: Lessons exist but docstatus is not 1 (not submitted)
		Expected: mappings should be empty (only submitted lessons included)
		"""
		# Load module directly to avoid __init__.py importing frappe
		import importlib.util

		spec = importlib.util.spec_from_file_location(
			"json_generator",
			"/home/corex/aurevia-bench/apps/memora/memora/services/cdn_export/json_generator.py",
		)
		json_generator = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(json_generator)
		generate_bitmap_json = json_generator.generate_bitmap_json

		mocks = self._setup_bitmap_mocks()
		try:
			mock_frappe = mocks["frappe"][1]

			subject_doc = Mock()
			subject_doc.name = "SUBJ-005"

			track1 = Mock()
			track1.name = "TRACK-001"
			unit1 = Mock()
			unit1.name = "UNIT-001"
			topic1 = Mock()
			topic1.name = "TOPIC-001"

			lesson1 = Mock()
			lesson1.name = "LESSON-001"
			lesson1.parent_topic = "TOPIC-001"

			def mock_get_all(doctype, filters=None, fields=None, order_by=None):
				if doctype == "Memora Track":
					return [track1]
				elif doctype == "Memora Unit":
					return [unit1]
				elif doctype == "Memora Topic":
					return [topic1]
				elif doctype == "Memora Lesson":
					print(f"[DEBUG] Querying Memora Lesson with filters: {filters}")
					# Return lesson even if docstatus is not 1
					return [lesson1]
				return []

			mock_frappe.get_all.side_effect = mock_get_all

			bitmap = generate_bitmap_json(subject_doc)

			print(f"\n[DEBUG] Bitmap with unsubmitted lessons: {bitmap}")
			print(f"[DEBUG] Mappings count: {len(bitmap['mappings'])}")

			# Lessons with docstatus != 1 should not be included
			self.assertEqual(bitmap["total_lessons"], 0)
			self.assertEqual(len(bitmap["mappings"]), 0)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_bitmap_multiple_topics_lessons(self):
		"""
		DEBUG TEST 6: Multiple topics and lessons
		Verify bit_index assignment and topic_id mapping
		"""
		# Load module directly to avoid __init__.py importing frappe
		import importlib.util

		spec = importlib.util.spec_from_file_location(
			"json_generator",
			"/home/corex/aurevia-bench/apps/memora/memora/services/cdn_export/json_generator.py",
		)
		json_generator = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(json_generator)
		generate_bitmap_json = json_generator.generate_bitmap_json

		mocks = self._setup_bitmap_mocks()
		try:
			mock_frappe = mocks["frappe"][1]

			subject_doc = Mock()
			subject_doc.name = "SUBJ-006"

			track1 = Mock()
			track1.name = "TRACK-001"
			unit1 = Mock()
			unit1.name = "UNIT-001"

			topic1 = Mock()
			topic1.name = "TOPIC-001"
			topic2 = Mock()
			topic2.name = "TOPIC-002"

			lesson1 = Mock()
			lesson1.name = "LESSON-001"
			lesson1.parent_topic = "TOPIC-001"

			lesson2 = Mock()
			lesson2.name = "LESSON-002"
			lesson2.parent_topic = "TOPIC-001"

			lesson3 = Mock()
			lesson3.name = "LESSON-003"
			lesson3.parent_topic = "TOPIC-002"

			def mock_get_all(doctype, filters=None, fields=None, order_by=None):
				if doctype == "Memora Track":
					return [track1]
				elif doctype == "Memora Unit":
					return [unit1]
				elif doctype == "Memora Topic":
					return [topic1, topic2]
				elif doctype == "Memora Lesson":
					if filters and filters.get("docstatus") == 1:
						return [lesson1, lesson2, lesson3]
					return []
				return []

			mock_frappe.get_all.side_effect = mock_get_all

			bitmap = generate_bitmap_json(subject_doc)

			print(f"\n[DEBUG] Bitmap with multiple topics/lessons: {bitmap}")
			print(f"[DEBUG] Mappings: {bitmap['mappings']}")

			self.assertEqual(bitmap["total_lessons"], 3)
			self.assertEqual(len(bitmap["mappings"]), 3)

			# Verify bit_index assignment
			self.assertEqual(bitmap["mappings"]["LESSON-001"]["bit_index"], 0)
			self.assertEqual(bitmap["mappings"]["LESSON-002"]["bit_index"], 1)
			self.assertEqual(bitmap["mappings"]["LESSON-003"]["bit_index"], 2)

			# Verify topic_id mapping
			self.assertEqual(bitmap["mappings"]["LESSON-001"]["topic_id"], "TOPIC-001")
			self.assertEqual(bitmap["mappings"]["LESSON-002"]["topic_id"], "TOPIC-001")
			self.assertEqual(bitmap["mappings"]["LESSON-003"]["topic_id"], "TOPIC-002")

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()


class TestBatchProcessorBitmapFlow(unittest.TestCase):
	"""Debug tests for batch processor bitmap generation flow"""

	def _setup_batch_processor_mocks(self):
		"""Helper to setup mocks for batch processor"""
		patcher_frappe = patch("memora.services.cdn_export.batch_processor.frappe")
		patcher_write = patch("memora.services.cdn_export.batch_processor.write_content_file")

		mock_frappe = patcher_frappe.start()
		mock_write = patcher_write.start()

		return {
			"frappe": (patcher_frappe, mock_frappe),
			"write": (patcher_write, mock_write),
		}

	def test_batch_processor_bitmap_generation(self):
		"""
		DEBUG TEST 7: Full batch processor flow for bitmap generation
		This tests the actual flow from batch_processor.py
		"""
		# Load module directly to avoid __init__.py importing frappe
		import importlib.util

		spec = importlib.util.spec_from_file_location(
			"batch_processor",
			"/home/corex/aurevia-bench/apps/memora/memora/services/cdn_export/batch_processor.py",
		)
		batch_processor = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(batch_processor)
		_generate_atomic_files_for_plan = batch_processor._generate_atomic_files_for_plan

		mocks = self._setup_batch_processor_mocks()
		try:
			mock_frappe = mocks["frappe"][1]
			mock_write = mocks["write"][1]

			# Setup plan subjects
			plan_subject1 = Mock()
			plan_subject1.subject = "SUBJ-001"

			# Setup subject doc
			subject_doc = Mock()
			subject_doc.name = "SUBJ-001"
			subject_doc.description = "Test Subject"

			# Setup tracks, units, topics, lessons hierarchy
			track1 = Mock()
			track1.name = "TRACK-001"
			unit1 = Mock()
			unit1.name = "UNIT-001"
			topic1 = Mock()
			topic1.name = "TOPIC-001"
			lesson1 = Mock()
			lesson1.name = "LESSON-001"
			lesson1.parent_topic = "TOPIC-001"

			# Mock frappe.get_doc
			def mock_get_doc(doctype, name):
				print(f"[DEBUG] get_doc called: {doctype}, {name}")
				if doctype == "Memora Subject":
					return subject_doc
				return Mock()

			# Mock frappe.get_all
			def mock_get_all(doctype, filters=None, fields=None, order_by=None):
				print(f"[DEBUG] get_all called: {doctype}, filters: {filters}")
				if doctype == "Memora Plan Subject":
					return [plan_subject1]
				elif doctype == "Memora Subject":
					return [Mock(name="SUBJ-001")]
				elif doctype == "Memora Track":
					return [track1]
				elif doctype == "Memora Unit":
					return [unit1]
				elif doctype == "Memora Topic":
					return [topic1]
				elif doctype == "Memora Lesson":
					if filters and filters.get("docstatus") == 1:
						print(f"[DEBUG] Returning lesson for bitmap")
						return [lesson1]
					return []
				return []

			mock_frappe.get_doc.side_effect = mock_get_doc
			mock_frappe.get_all.side_effect = mock_get_all
			mock_frappe.log_error = Mock()

			# Mock write_content_file to capture data
			written_files = {}

			def mock_write_file(path, data):
				print(f"[DEBUG] Writing file: {path}")
				print(f"[DEBUG] Data: {data}")
				written_files[path] = data
				return True, None

			mock_write.side_effect = mock_write_file

			# Generate files
			result = _generate_atomic_files_for_plan("PLAN-001")

			print(f"\n[DEBUG] Written files: {list(written_files.keys())}")

			# Check if bitmap was written
			bitmap_path = "plans/PLAN-001/SUBJ-001_b.json"
			self.assertIn(bitmap_path, written_files, f"Bitmap file {bitmap_path} should be written")

			bitmap_data = written_files[bitmap_path]
			print(f"[DEBUG] Bitmap data: {bitmap_data}")
			print(f"[DEBUG] Bitmap mappings: {bitmap_data.get('mappings', {})}")
			print(f"[DEBUG] Mappings count: {len(bitmap_data.get('mappings', {}))}")

			# Verify mappings are populated
			self.assertIn("mappings", bitmap_data)
			self.assertEqual(len(bitmap_data["mappings"]), 1, "Should have 1 lesson in mappings")
			self.assertIn("LESSON-001", bitmap_data["mappings"])
			self.assertEqual(bitmap_data["mappings"]["LESSON-001"]["bit_index"], 0)
			self.assertEqual(bitmap_data["mappings"]["LESSON-001"]["topic_id"], "TOPIC-001")

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()


if __name__ == "__main__":
	unittest.main(verbosity=2)
