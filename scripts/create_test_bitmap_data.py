"""
Create test data for debugging bitmap generation

This script creates:
- 1 Academic Plan
- 1 Subject
- 1 Track
- 1 Unit
- 1 Topic
- 2 Lessons (submitted)

All linked together to test bitmap generation
"""

import frappe


def create_test_data():
	"""Create complete test hierarchy for bitmap generation testing"""

	print("=" * 60)
	print("CREATING TEST DATA FOR BITMAP GENERATION")
	print("=" * 60)

	# 1. Create Academic Plan
	print("\n[1] Creating Academic Plan...")
	plan_name = "TEST-PLAN-BITMAP-001"

	if frappe.db.exists("Memora Academic Plan", plan_name):
		print(f"  Plan {plan_name} already exists, deleting...")
		frappe.delete_doc("Memora Academic Plan", plan_name)

	plan = frappe.get_doc(
		{
			"doctype": "Memora Academic Plan",
			"plan_name": "Test Bitmap Plan",
			"description": "Test plan for debugging bitmap generation",
			"is_published": 1,
			"access_level": "Public",
		}
	)
	plan.insert()
	print(f"  Created: {plan.name}")

	# 2. Create Subject
	print("\n[2] Creating Subject...")
	subject_name = "TEST-SUBJECT-MATH-001"

	if frappe.db.exists("Memora Subject", subject_name):
		print(f"  Subject {subject_name} already exists, deleting...")
		frappe.delete_doc("Memora Subject", subject_name)

	subject = frappe.get_doc(
		{
			"doctype": "Memora Subject",
			"subject_name": "Mathematics",
			"description": "Test Mathematics subject for bitmap testing",
		}
	)
	subject.insert()
	print(f"  Created: {subject.name}")

	# 3. Link Subject to Plan (Memora Plan Subject)
	print("\n[3] Linking Subject to Plan...")
	plan_subject = frappe.get_doc(
		{
			"doctype": "Memora Plan Subject",
			"parent": plan_name,
			"parenttype": "Memora Academic Plan",
			"parentfield": "subjects",
			"subject": subject_name,
		}
	)
	plan_subject.insert()
	print(f"  Linked: {plan_name} → {subject_name}")

	# 4. Create Track
	print("\n[4] Creating Track...")
	track_name = "TEST-TRACK-ALGEBRA-001"

	if frappe.db.exists("Memora Track", track_name):
		print(f"  Track {track_name} already exists, deleting...")
		frappe.delete_doc("Memora Track", track_name)

	track = frappe.get_doc(
		{
			"doctype": "Memora Track",
			"track_name": "Algebra Basics",
			"parent_subject": subject_name,
			"description": "Track for bitmap testing",
		}
	)
	track.insert()
	print(f"  Created: {track.name}")

	# 5. Create Unit
	print("\n[5] Creating Unit...")
	unit_name = "TEST-UNIT-EQUATIONS-001"

	if frappe.db.exists("Memora Unit", unit_name):
		print(f"  Unit {unit_name} already exists, deleting...")
		frappe.delete_doc("Memora Unit", unit_name)

	unit = frappe.get_doc(
		{
			"doctype": "Memora Unit",
			"unit_name": "Linear Equations",
			"parent_track": track_name,
			"description": "Unit for bitmap testing",
		}
	)
	unit.insert()
	print(f"  Created: {unit.name}")

	# 6. Create Topic
	print("\n[6] Creating Topic...")
	topic_name = "TEST-TOPIC-SIMPLE-001"

	if frappe.db.exists("Memora Topic", topic_name):
		print(f"  Topic {topic_name} already exists, deleting...")
		frappe.delete_doc("Memora Topic", topic_name)

	topic = frappe.get_doc(
		{
			"doctype": "Memora Topic",
			"topic_name": "Simple Equations",
			"parent_unit": unit_name,
			"description": "Topic for bitmap testing",
		}
	)
	topic.insert()
	print(f"  Created: {topic.name}")

	# 7. Create Lessons (2 lessons, both submitted)
	print("\n[7] Creating Lessons...")

	for i in range(1, 3):
		lesson_name = f"TEST-LESSON-LESSON{i:03d}-001"

		if frappe.db.exists("Memora Lesson", lesson_name):
			print(f"  Lesson {lesson_name} already exists, deleting...")
			frappe.delete_doc("Memora Lesson", lesson_name)

		lesson = frappe.get_doc(
			{
				"doctype": "Memora Lesson",
				"lesson_name": f"Lesson {i} - Variables",
				"parent_topic": topic_name,
				"description": f"Test lesson {i} for bitmap generation",
				"content_type": "Video",
				"duration_minutes": 10 + i * 5,
				"docstatus": 0,  # Start as draft
			}
		)
		lesson.insert()
		print(f"  Created draft: {lesson.name}")

		# Submit the lesson (docstatus=1 is required for bitmap)
		lesson.submit()
		print(f"  Submitted: {lesson.name} (docstatus={lesson.docstatus})")

	# Summary
	print("\n" + "=" * 60)
	print("TEST DATA CREATED SUCCESSFULLY")
	print("=" * 60)
	print(f"\nHierarchy created:")
	print(f"  Plan:     {plan_name}")
	print(f"  Subject:   {subject_name}")
	print(f"  Track:     {track_name}")
	print(f"  Unit:      {unit_name}")
	print(f"  Topic:     {topic_name}")
	print(f"  Lessons:   TEST-LESSON-LESSON001-001, TEST-LESSON-LESSON002-001")
	print(f"\nExpected bitmap file: plans/{plan_name}/{subject_name}_b.json")
	print(f"Expected mappings: 2 lessons")
	print("\nTo rebuild the plan, run:")
	print(f"  frappe.get_doc('Memora Academic Plan', '{plan_name}').rebuild_plan()")
	print("=" * 60)

	return {
		"plan_name": plan_name,
		"subject_name": subject_name,
		"track_name": track_name,
		"unit_name": unit_name,
		"topic_name": topic_name,
	}


def verify_test_data(plan_name):
	"""Verify the test data exists in database"""
	print("\n" + "=" * 60)
	print("VERIFYING TEST DATA")
	print("=" * 60)

	# Check plan
	plan = frappe.db.exists("Memora Academic Plan", plan_name)
	print(f"\nPlan '{plan_name}' exists: {bool(plan)}")

	if plan:
		# Get plan subjects
		plan_subjects = frappe.get_all(
			"Memora Plan Subject", filters={"parent": plan_name}, fields=["subject"]
		)
		print(f"Plan subjects: {len(plan_subjects)}")

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

						# Check lessons
						lessons = frappe.get_all(
							"Memora Lesson",
							filters={
								"parent_topic": tp.name,
								"docstatus": 1,  # Only submitted lessons
							},
							fields=["name", "lesson_name"],
						)
						print(f"          Lessons (submitted): {len(lessons)}")
						for l in lessons:
							print(f"            - {l.name}: {l.lesson_name}")

	print("\n" + "=" * 60)


if __name__ == "__main__":
	try:
		import sys

		if len(sys.argv) > 1 and sys.argv[1] == "--verify":
			plan_name = sys.argv[2] if len(sys.argv) > 2 else "TEST-PLAN-BITMAP-001"
			verify_test_data(plan_name)
		else:
			data = create_test_data()
			print("\n\nTo verify data, run:")
			print(f"  python3 {sys.argv[0]} --verify {data['plan_name']}")
	except Exception as e:
		print(f"\nERROR: {e}")
		import traceback

		traceback.print_exc()
