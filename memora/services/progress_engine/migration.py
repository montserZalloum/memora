"""
Migration script for progress engine bitset feature.

Backfills bit_index for existing lessons and converts passed_lessons_data
to bitmap format.
"""

import frappe


def backfill_bit_indices():
	"""Backfill bit_index for existing lessons.
	
	This function assigns sequential bit indices to all existing lessons
	based on their subject hierarchy.
	"""
	print("Starting bit_index backfill...")
	
	subjects = frappe.get_all("Memora Subject", fields=["name", "next_bit_index"])
	
	for subject in subjects:
		print(f"\nProcessing subject: {subject.name}")
		
		tracks = frappe.get_all(
			"Memora Track",
			filters={"parent_subject": subject.name},
			fields=["name"]
		)
		
		for track in tracks:
			units = frappe.get_all(
				"Memora Unit",
				filters={"parent_track": track.name},
				fields=["name"]
			)
			
			for unit in units:
				topics = frappe.get_all(
					"Memora Topic",
					filters={"parent_unit": unit.name},
					fields=["name"]
				)
				
				for topic in topics:
					lessons = frappe.get_all(
						"Memora Lesson",
						filters={"parent_topic": topic.name},
						fields=["name", "bit_index"],
						order_by="creation asc"
					)
					
					for lesson in lessons:
						if lesson.bit_index == -1:
							bitmap_index = subject.next_bit_index
							subject_doc = frappe.get_doc("Memora Subject", subject.name)
							subject_doc.next_bit_index = bitmap_index + 1
							subject_doc.save(ignore_permissions=True)
							
							lesson_doc = frappe.get_doc("Memora Lesson", lesson.name)
							lesson_doc.bit_index = bitmap_index
							lesson_doc.save(ignore_permissions=True)
							
							print(f"  Set bit_index={bitmap_index} for lesson {lesson.name}")
	
	print("\n✓ Bit index backfill complete")


def convert_passed_lessons_to_bitsets():
	"""Convert existing passed_lessons_data JSON to bitmap format.
	
	This function migrates data from the old JSON format to the new
	base64-encoded bitmap format.
	"""
	print("\nStarting passed_lessons_data to bitmap conversion...")
	
	progress_records = frappe.get_all(
		"Memora Structure Progress",
		fields=["name", "passed_lessons_data", "player", "subject"]
	)
	
	for progress in progress_records:
		if progress.passed_lessons_data:
			try:
				import json
				passed_lessons = json.loads(progress.passed_lessons_data)
				
				if isinstance(passed_lessons, list) and passed_lessons:
					from memora.services.progress_engine.bitmap_manager import set_bit, encode_bitmap_for_mariadb
					
					bitmap = b''
					for lesson_id in passed_lessons:
						lesson_doc = frappe.get_doc("Memora Lesson", lesson_id)
						if lesson_doc.bit_index >= 0:
							bitmap = set_bit(bitmap, lesson_doc.bit_index)
					
					bitmap_base64 = encode_bitmap_for_mariadb(bitmap)
					
					progress_doc = frappe.get_doc("Memora Structure Progress", progress.name)
					progress_doc.passed_lessons_bitset = bitmap_base64
					progress_doc.save(ignore_permissions=True)
					
					print(f"  Converted progress for {progress.player} / {progress.subject}")
			except Exception as e:
				print(f"  ✗ Error converting progress {progress.name}: {e}")
	
	print("\n✓ Passed lessons data conversion complete")


def run_migration():
	"""Run all migration steps."""
	print("=" * 50)
	print("Progress Engine Migration")
	print("=" * 50)
	
	backfill_bit_indices()
	convert_passed_lessons_to_bitsets()
	
	print("\n" + "=" * 50)
	print("Migration complete!")
	print("=" * 50)


if __name__ == "__main__":
	import frappe
	frappe.init(site="site1.local")
	frappe.connect()
	try:
		run_migration()
	finally:
		frappe.destroy()
