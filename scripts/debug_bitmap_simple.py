"""
Copy-paste this into Frappe Console to debug bitmap

Access: http://x.conanacademy.com/app
Then click on ">" (Console/Developer Console)
"""

import frappe

print("\n" + "=" * 70)
print("BITMAP GENERATION DEBUG")
print("=" * 70)

# 1. List plans
print("\n[1] PLANS:")
plans = frappe.get_all(
	"Memora Academic Plan", fields=["name", "plan_name", "is_published"], order_by="modified desc", limit=10
)

for i, plan in enumerate(plans, 1):
	status = "✓" if plan.is_published else "✗"
	print(f"  {i}. {status} {plan.name}")

if not plans:
	print("  No plans!")
else:
	plan_name = plans[0].name
	print(f"\n✓ Selected: {plan_name}")

	# 2. Get plan subjects
	print("\n[2] SUBJECTS:")
	plan_subjects = frappe.get_all("Memora Plan Subject", filters={"parent": plan_name}, fields=["subject"])

	for ps in plan_subjects:
		print(f"  - {ps.subject}")

	if not plan_subjects:
		print("  ✗ No subjects!")
	else:
		# 3. Check hierarchy
		print("\n[3] HIERARCHY:")
		for ps in plan_subjects:
			subject_name = ps.subject
			print(f"\n  Subject: {subject_name}")

			# Tracks
			tracks = frappe.get_all(
				"Memora Track", filters={"parent_subject": subject_name}, fields=["name", "track_name"]
			)
			print(f"    Tracks: {len(tracks)}")
			for t in tracks:
				print(f"      ✓ {t.name}")

			if not tracks:
				print("      ✗ NO TRACKS - bitmap will be empty!")
				continue

			# Units
			for track in tracks:
				units = frappe.get_all(
					"Memora Unit", filters={"parent_track": track.name}, fields=["name", "unit_name"]
				)
				print(f"    Units in {track.name}: {len(units)}")
				for u in units:
					print(f"      ✓ {u.name}")

				if not units:
					print("      ✗ NO UNITS - bitmap will be empty!")
					continue

				# Topics
				for unit in units:
					topics = frappe.get_all(
						"Memora Topic", filters={"parent_unit": unit.name}, fields=["name", "topic_name"]
					)
					print(f"    Topics in {unit.name}: {len(topics)}")
					for tp in topics:
						print(f"      ✓ {tp.name}")

					if not topics:
						print("      ✗ NO TOPICS - bitmap will be empty!")
						continue

					# Lessons
					for topic in topics:
						lessons_submitted = frappe.get_all(
							"Memora Lesson",
							filters={"parent_topic": topic.name, "docstatus": 1},
							fields=["name", "lesson_name"],
						)

						print(f"    Lessons (submitted) in {topic.name}: {len(lessons_submitted)}")
						for l in lessons_submitted:
							print(f"      ✓ {l.name}")

						if not lessons_submitted:
							print("      ✗ NO SUBMITTED LESSONS - bitmap will be empty!")

		# 4. Check bitmap files
		print("\n[4] BITMAP FILES:")
		from memora.services.cdn_export.local_storage import get_local_base_path, file_exists
		import json, os

		base_path = get_local_base_path()
		for ps in plan_subjects:
			subject_name = ps.subject
			bitmap_path = f"plans/{plan_name}/{subject_name}_b.json"

			if file_exists(bitmap_path):
				full_path = os.path.join(base_path, bitmap_path)
				with open(full_path, "r") as f:
					data = json.load(f)
				print(f"\n  {subject_name}:")
				print(f"    total_lessons: {data.get('total_lessons', 0)}")
				print(f"    mappings: {len(data.get('mappings', {}))}")
				if not data.get("mappings"):
					print("    ✗ MAPPINGS EMPTY!")
			else:
				print(f"\n  {subject_name}: ✗ FILE MISSING - rebuild plan!")

		# 5. Rebuild command
		print("\n" + "=" * 70)
		print("To rebuild this plan, run in console:")
		print(f"  frappe.get_doc('Memora Academic Plan', '{plan_name}').rebuild_plan()")
		print("=" * 70)
