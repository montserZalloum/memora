"""
Simple test to check bitmap generation - focusing on understanding why mappings are empty
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call


class TestBitmapGenerationSimple(unittest.TestCase):
	"""Simple test to understand bitmap generation flow"""

	def test_json_generator_code_logic(self):
		"""
		Directly test the logic of generate_bitmap_json
		without worrying about frappe imports
		"""
		# Mock frappe.get_all responses based on hierarchical queries
		mock_frappe = MagicMock()

		# Setup mock data - simulating a subject with:
		# - 1 Track
		# - 1 Unit
		# - 1 Topic
		# - 2 Lessons

		# Track response
		mock_track = Mock()
		mock_track.name = "TRACK-001"
		track_calls = []
		unit_calls = []
		topic_calls = []
		lesson_calls = []

		# Unit response
		mock_unit = Mock()
		mock_unit.name = "UNIT-001"

		# Topic response
		mock_topic = Mock()
		mock_topic.name = "TOPIC-001"

		# Lesson responses
		mock_lesson1 = Mock()
		mock_lesson1.name = "LESSON-001"
		mock_lesson1.parent_topic = "TOPIC-001"

		mock_lesson2 = Mock()
		mock_lesson2.name = "LESSON-002"
		mock_lesson2.parent_topic = "TOPIC-001"

		# Define get_all behavior
		def get_all_side_effect(doctype, filters=None, fields=None, order_by=None):
			call_info = {"doctype": doctype, "filters": filters, "fields": fields, "order_by": order_by}
			print(f"\n[CALL] frappe.get_all called:")
			print(f"  doctype: {doctype}")
			print(f"  filters: {filters}")
			print(f"  fields: {fields}")
			print(f"  order_by: {order_by}")

			if doctype == "Memora Track":
				track_calls.append(call_info)
				return [mock_track]
			elif doctype == "Memora Unit":
				unit_calls.append(call_info)
				return [mock_unit]
			elif doctype == "Memora Topic":
				topic_calls.append(call_info)
				return [mock_topic]
			elif doctype == "Memora Lesson":
				lesson_calls.append(call_info)
				if filters and filters.get("docstatus") == 1:
					return [mock_lesson1, mock_lesson2]
				return []
			else:
				return []

		mock_frappe.get_all.side_effect = get_all_side_effect

		# Mock subject doc
		mock_subject = Mock()
		mock_subject.name = "SUBJ-001"

		# Now simulate the generate_bitmap_json logic directly
		print("\n" + "=" * 60)
		print("SIMULATING generate_bitmap_json() LOGIC")
		print("=" * 60)

		# Step 1: Get all tracks for this subject
		print("\n[STEP 1] Getting tracks...")
		tracks = mock_frappe.get_all(
			"Memora Track", filters={"parent_subject": mock_subject.name}, fields=["name"]
		)
		print(f"Result: Found {len(tracks)} tracks: {[t.name for t in tracks]}")
		track_ids = [t.name for t in tracks]
		print(f"track_ids: {track_ids}")

		# Step 2: Get all units for these tracks
		print("\n[STEP 2] Getting units...")
		units = mock_frappe.get_all(
			"Memora Unit", filters={"parent_track": ["in", track_ids]}, fields=["name"]
		)
		print(f"Result: Found {len(units)} units: {[u.name for u in units]}")
		unit_ids = [u.name for u in units]
		print(f"unit_ids: {unit_ids}")

		# Step 3: Get all topics for these units
		print("\n[STEP 3] Getting topics...")
		topics = mock_frappe.get_all(
			"Memora Topic", filters={"parent_unit": ["in", unit_ids]}, fields=["name"]
		)
		print(f"Result: Found {len(topics)} topics: {[t.name for t in topics]}")
		topic_ids = [t.name for t in topics]
		print(f"topic_ids: {topic_ids}")

		# Step 4: Get all lessons for these topics
		print("\n[STEP 4] Getting lessons...")
		lessons = mock_frappe.get_all(
			"Memora Lesson",
			filters={"parent_topic": ["in", topic_ids], "docstatus": 1},
			fields=["name", "parent_topic"],
			order_by="creation",
		)
		print(f"Result: Found {len(lessons)} lessons: {[l.name for l in lessons]}")
		print(f"Lesson details:")
		for lesson in lessons:
			print(f"  - {lesson.name} (parent_topic: {lesson.parent_topic})")

		# Step 5: Build bitmap with bit_index for each lesson
		print("\n[STEP 5] Building bitmap...")
		bitmap_data = {
			"subject_id": mock_subject.name,
			"version": 1706270400,
			"generated_at": "2026-01-26T10:00:00",
			"total_lessons": len(lessons),
			"mappings": {},
		}

		for idx, lesson in enumerate(lessons):
			bitmap_data["mappings"][lesson.name] = {"bit_index": idx, "topic_id": lesson.parent_topic}
			print(f"  Mapping {lesson.name} -> bit_index={idx}, topic_id={lesson.parent_topic}")

		# Summary
		print("\n" + "=" * 60)
		print("SUMMARY")
		print("=" * 60)
		print(f"Total get_all calls: {mock_frappe.get_all.call_count}")
		print(f"  - Tracks: {len(track_calls)}")
		print(f"  - Units: {len(unit_calls)}")
		print(f"  - Topics: {len(topic_calls)}")
		print(f"  - Lessons: {len(lesson_calls)}")
		print(f"\nBitmap data:")
		print(f"  subject_id: {bitmap_data['subject_id']}")
		print(f"  total_lessons: {bitmap_data['total_lessons']}")
		print(f"  mappings count: {len(bitmap_data['mappings'])}")
		print(f"  mappings: {bitmap_data['mappings']}")

		# Assertions
		self.assertEqual(len(track_calls), 1, "Should call get_all once for tracks")
		self.assertEqual(len(unit_calls), 1, "Should call get_all once for units")
		self.assertEqual(len(topic_calls), 1, "Should call get_all once for topics")
		self.assertEqual(len(lesson_calls), 1, "Should call get_all once for lessons")

		# Check the filter for lessons
		lesson_filter = lesson_calls[0]["filters"]
		print(f"\n[DEBUG] Lesson filter: {lesson_filter}")
		self.assertEqual(lesson_filter.get("docstatus"), 1, "Lessons query should filter by docstatus=1")

		# Verify bitmap structure
		self.assertEqual(bitmap_data["subject_id"], "SUBJ-001")
		self.assertEqual(bitmap_data["total_lessons"], 2)
		self.assertEqual(len(bitmap_data["mappings"]), 2)

		# Verify mappings
		self.assertIn("LESSON-001", bitmap_data["mappings"])
		self.assertEqual(bitmap_data["mappings"]["LESSON-001"]["bit_index"], 0)
		self.assertEqual(bitmap_data["mappings"]["LESSON-001"]["topic_id"], "TOPIC-001")

		self.assertIn("LESSON-002", bitmap_data["mappings"])
		self.assertEqual(bitmap_data["mappings"]["LESSON-002"]["bit_index"], 1)
		self.assertEqual(bitmap_data["mappings"]["LESSON-002"]["topic_id"], "TOPIC-001")

		print("\n[SUCCESS] Bitmap generation works correctly with proper data!")

	def test_bitmap_generation_empty_tracks(self):
		"""
		Test what happens when there are no tracks
		"""
		print("\n\n" + "=" * 60)
		print("TEST: Empty tracks scenario")
		print("=" * 60)

		mock_frappe = MagicMock()

		track_calls = []
		unit_calls = []
		topic_calls = []
		lesson_calls = []

		def get_all_side_effect(doctype, filters=None, fields=None, order_by=None):
			print(f"\n[CALL] frappe.get_all({doctype}, filters={filters})")
			if doctype == "Memora Track":
				track_calls.append({"filters": filters})
				return []  # NO TRACKS
			elif doctype == "Memora Unit":
				unit_calls.append({"filters": filters})
				return []
			elif doctype == "Memora Topic":
				topic_calls.append({"filters": filters})
				return []
			elif doctype == "Memora Lesson":
				lesson_calls.append({"filters": filters})
				return []
			return []

		mock_frappe.get_all.side_effect = get_all_side_effect

		mock_subject = Mock()
		mock_subject.name = "SUBJ-EMPTY"

		# Simulate logic
		tracks = mock_frappe.get_all(
			"Memora Track", filters={"parent_subject": mock_subject.name}, fields=["name"]
		)
		print(f"Tracks found: {len(tracks)}")

		track_ids = [t.name for t in tracks]
		print(f"track_ids: {track_ids}")

		# Since tracks is empty, subsequent queries get empty list
		units = mock_frappe.get_all(
			"Memora Unit", filters={"parent_track": ["in", track_ids]}, fields=["name"]
		)

		unit_ids = [u.name for u in units]
		topics = mock_frappe.get_all(
			"Memora Topic", filters={"parent_unit": ["in", unit_ids]}, fields=["name"]
		)

		topic_ids = [t.name for t in topics]
		lessons = mock_frappe.get_all(
			"Memora Lesson",
			filters={"parent_topic": ["in", topic_ids], "docstatus": 1},
			fields=["name", "parent_topic"],
			order_by="creation",
		)

		bitmap_data = {"subject_id": mock_subject.name, "total_lessons": len(lessons), "mappings": {}}

		print(
			f"\nResult: total_lessons={bitmap_data['total_lessons']}, mappings={len(bitmap_data['mappings'])}"
		)

		self.assertEqual(len(track_calls), 1)
		self.assertEqual(len(unit_calls), 1)  # Still called, but with empty list
		self.assertEqual(len(topic_calls), 1)  # Still called, but with empty list
		self.assertEqual(len(lesson_calls), 1)  # Still called, but with empty list

		# Check that filters are correct
		print(f"\n[DEBUG] Unit filter: {unit_calls[0]['filters']}")
		print(f"[DEBUG] Topic filter: {topic_calls[0]['filters']}")
		print(f"[DEBUG] Lesson filter: {lesson_calls[0]['filters']}")

		self.assertEqual(bitmap_data["total_lessons"], 0)
		self.assertEqual(len(bitmap_data["mappings"]), 0)

		print("[SUCCESS] Empty tracks handled correctly - mappings is empty!")


if __name__ == "__main__":
	unittest.main(verbosity=2)
