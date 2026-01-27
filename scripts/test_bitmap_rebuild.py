"""
Script to rebuild plan and debug bitmap generation

Usage:
    bench --site [site-name] run python scripts/test_bitmap_rebuild.py [plan_name]
"""

import frappe
import json
import os


def rebuild_and_check_bitmap(plan_name):
	"""Rebuild plan and inspect bitmap file"""

	print("=" * 60)
	print(f"REBUILDING PLAN: {plan_name}")
	print("=" * 60)

	# 1. Get plan document
	try:
		plan = frappe.get_doc("Memora Academic Plan", plan_name)
		print(f"\n✓ Plan found: {plan.plan_name}")
		print(f"  Published: {plan.is_published}")
		print(f"  Access: {plan.access_level}")
	except Exception as e:
		print(f"\n✗ Plan not found: {e}")
		return

	# 2. Get plan subjects
	plan_subjects = frappe.get_all("Memora Plan Subject", filters={"parent": plan_name}, fields=["subject"])
	print(f"\n✓ Plan has {len(plan_subjects)} subject(s)")
	for ps in plan_subjects:
		print(f"  - {ps.subject}")

	if not plan_subjects:
		print("\n✗ No subjects in plan - nothing to rebuild")
		return

	# 3. Check bitmap generation BEFORE rebuild
	print("\n" + "=" * 60)
	print("CHECKING BITMAP DATA BEFORE REBUILD")
	print("=" * 60)

	for ps in plan_subjects:
		subject_name = ps.subject
		bitmap_path = f"plans/{plan_name}/{subject_name}_b.json"

		# Try to read existing bitmap file
		from memora.services.cdn_export.local_storage import file_exists, get_local_base_path

		base_path = get_local_base_path()
		full_path = os.path.join(base_path, bitmap_path)

		if file_exists(bitmap_path):
			with open(full_path, "r") as f:
				existing_bitmap = json.load(f)

			print(f"\n  Subject: {subject_name}")
			print(f"  Bitmap path: {bitmap_path}")
			print(f"  File exists: Yes")
			print(f"  total_lessons: {existing_bitmap.get('total_lessons', 0)}")
			print(f"  mappings count: {len(existing_bitmap.get('mappings', {}))}")
			if existing_bitmap.get("mappings"):
				print(f"  lessons: {list(existing_bitmap['mappings'].keys())}")
		else:
			print(f"\n  Subject: {subject_name}")
			print(f"  Bitmap path: {bitmap_path}")
			print(f"  File exists: No")

	# 4. Trigger rebuild
	print("\n" + "=" * 60)
	print("TRIGGERING PLAN REBUILD")
	print("=" * 60)

	try:
		plan.reload()  # Reload to get latest data
		result = plan.rebuild_plan()
		print(f"\n✓ Rebuild triggered")
		print(f"  Result: {result}")
	except Exception as e:
		print(f"\n✗ Rebuild failed: {e}")
		import traceback

		traceback.print_exc()
		return

	# 5. Check bitmap file AFTER rebuild
	print("\n" + "=" * 60)
	print("CHECKING BITMAP DATA AFTER REBUILD")
	print("=" * 60)

	all_successful = True
	for ps in plan_subjects:
		subject_name = ps.subject
		bitmap_path = f"plans/{plan_name}/{subject_name}_b.json"

		# Wait a moment for file write
		import time

		time.sleep(1)

		if file_exists(bitmap_path):
			with open(full_path, "r") as f:
				new_bitmap = json.load(f)

			print(f"\n  Subject: {subject_name}")
			print(f"  Bitmap path: {bitmap_path}")
			print(f"  File exists: Yes")
			print(f"  subject_id: {new_bitmap.get('subject_id', 'N/A')}")
			print(f"  version: {new_bitmap.get('version', 'N/A')}")
			print(f"  generated_at: {new_bitmap.get('generated_at', 'N/A')}")
			print(f"  total_lessons: {new_bitmap.get('total_lessons', 0)}")
			print(f"  mappings count: {len(new_bitmap.get('mappings', {}))}")

			mappings = new_bitmap.get("mappings", {})
			if mappings:
				print(f"  lessons: {list(mappings.keys())}")
				for lesson_id, lesson_data in mappings.items():
					print(
						f"    - {lesson_id}: bit_index={lesson_data.get('bit_index')}, topic_id={lesson_data.get('topic_id')}"
					)

				# Check if mappings is empty
				if len(mappings) == 0:
					print(f"\n  ⚠ WARNING: Mappings is empty!")
					print(f"    This means no lessons found in hierarchy")
					all_successful = False
				else:
					print(f"\n  ✓ SUCCESS: Bitmap has {len(mappings)} lesson(s) mapped")
			else:
				print(f"\n  ✗ ERROR: 'mappings' key missing or empty!")
				all_successful = False
		else:
			print(f"\n  Subject: {subject_name}")
			print(f"  Bitmap path: {bitmap_path}")
			print(f"  File exists: No")
			print(f"  ✗ ERROR: Bitmap file was not created!")
			all_successful = False

	# 6. Debug database queries
	print("\n" + "=" * 60)
	print("DATABASE QUERY DEBUG")
	print("=" * 60)

	for ps in plan_subjects:
		subject_name = ps.subject

		print(f"\n  Subject: {subject_name}")

		# Check tracks
		tracks = frappe.get_all(
			"Memora Track", filters={"parent_subject": subject_name}, fields=["name", "track_name"]
		)
		print(f"    Tracks: {len(tracks)}")
		for t in tracks:
			print(f"      - {t.name}: {t.track_name}")

			# Check units
			units = frappe.get_all(
				"Memora Unit", filters={"parent_track": t.name}, fields=["name", "unit_name"]
			)
			print(f"      Units: {len(units)}")
			for u in units:
				print(f"        - {u.name}: {u.unit_name}")

				# Check topics
				topics = frappe.get_all(
					"Memora Topic", filters={"parent_unit": u.name}, fields=["name", "topic_name"]
				)
				print(f"        Topics: {len(topics)}")
				for tp in topics:
					print(f"          - {tp.name}: {tp.topic_name}")

					# Check lessons (submitted only)
					lessons = frappe.get_all(
						"Memora Lesson",
						filters={"parent_topic": tp.name, "docstatus": 1},
						fields=["name", "lesson_name", "docstatus"],
						order_by="creation",
					)
					print(f"          Lessons (submitted, docstatus=1): {len(lessons)}")
					for l in lessons:
						print(f"            - {l.name}: {l.lesson_name} (docstatus={l.docstatus})")

					# Check all lessons including draft
					all_lessons = frappe.get_all(
						"Memora Lesson",
						filters={"parent_topic": tp.name},
						fields=["name", "lesson_name", "docstatus"],
					)
					print(f"          Lessons (all): {len(all_lessons)}")
					draft_count = sum(1 for l in all_lessons if l.docstatus == 0)
					submitted_count = sum(1 for l in all_lessons if l.docstatus == 1)
					print(f"          Draft: {draft_count}, Submitted: {submitted_count}")

	# Final summary
	print("\n" + "=" * 60)
	if all_successful:
		print("✓ ALL BITMAP FILES GENERATED SUCCESSFULLY")
	else:
		print("✗ SOME ISSUES DETECTED")
		print("\nIf mappings are empty, check:")
		print("  1. Are lessons submitted (docstatus=1)?")
		print("  2. Are tracks → units → topics → lessons linked correctly?")
		print("  3. Are any of the levels empty?")
	print("=" * 60)


if __name__ == "__main__":
	import sys

	plan_name = sys.argv[1] if len(sys.argv) > 1 else "TEST-PLAN-BITMAP-001"

	print("Bitmap Rebuild Debug Script")
	print(f"Target plan: {plan_name}")

	rebuild_and_check_bitmap(plan_name)
