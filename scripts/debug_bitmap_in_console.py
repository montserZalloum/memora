"""
Copy-paste this script into your Frappe Console to debug bitmap generation

Access: http://x.conanacademy.com/app
Go to: > Console (or Developer Console)
"""

import frappe

print("\n" + "=" * 70)
print("BITMAP GENERATION DEBUG SCRIPT")
print("=" * 70)

# Step1: List all plans
print("\n[1] LISTING ALL ACADEMIC PLANS")
print("-" * 70)

plans = frappe.get_all(
	"Memora Academic Plan", fields=["name", "plan_name", "is_published"], order_by="modified desc", limit=10
)

for i, plan in enumerate(plans, 1):
	status = "✓" if plan.is_published else "✗"
	print(f"  {i}. {status} {plan.name} - {plan.plan_name}")

if not plans:
	print("  No plans found!")
	frappe.throw("No plans in database")

# Ask user which plan to debug
print("\n" + "=" * 70)
print("WHICH PLAN DO YOU WANT TO DEBUG?")
print("=" * 70)
print("Edit the variable below with plan name you want to debug:")
print("")
print("PLAN_NAME_TO_DEBUG = 'YOUR-PLAN-NAME-HERE'")
print("=" * 70)

# For automation, let's just pick first published plan
target_plan = None
for plan in plans:
	if plan.is_published:
		target_plan = plan
		break

if not target_plan and plans:
	target_plan = plans[0]

if target_plan:
	print(f"\n✓ Auto-selected plan: {target_plan.name} - {target_plan.plan_name}")
	plan_name = target_plan.name
else:
	print("\n✗ No plans found!")
	frappe.throw("No plans to debug")

# Step 2: Get plan subjects
print("\n[2] ANALYZING PLAN SUBJECTS")
print("-" * 70)

plan_subjects = frappe.get_all("Memora Plan Subject", filters={"parent": plan_name}, fields=["subject"])

print(f"Plan '{plan_name}' has {len(plan_subjects)} subject(s):\n")

for ps in plan_subjects:
	print(f"  Subject: {ps.subject}")

if not plan_subjects:
	print("\n✗ No subjects in plan! Bitmap files cannot be generated.")
	print("  Fix: Add subjects to this plan in Frappe Desk")
	frappe.throw("Plan has no subjects")

# Step 3: For each subject, check hierarchy
print("\n" + "=" * 70)
print("CHECKING HIERARCHY FOR EACH SUBJECT")
print("=" * 70)

all_subjects_ok = True

for ps in plan_subjects:
	subject_name = ps.subject
	print(f"\n{'=' * 70}")
	print(f"SUBJECT: {subject_name}")
	print(f"{'=' * 70}")

	# Check tracks
	tracks = frappe.get_all(
		"Memora Track", filters={"parent_subject": subject_name}, fields=["name", "track_name"]
	)
	print(f"\n  Tracks: {len(tracks)}")
	for t in tracks:
		print(f"    ✓ {t.name} - {t.track_name}")

	if not tracks:
		print(f"    ✗ NO TRACKS - Bitmap will have empty mappings!")
		print(f"      Fix: Create tracks under this subject")
		all_subjects_ok = False
		continue

	# Check units for each track
	for track in tracks:
		units = frappe.get_all(
			"Memora Unit", filters={"parent_track": track.name}, fields=["name", "unit_name"]
		)
		print(f"\n  Units in {track.name}: {len(units)}")
		for u in units:
			print(f"    ✓ {u.name} - {u.unit_name}")

		if not units:
			print(f"    ✗ NO UNITS - Bitmap will have empty mappings!")
			print(f"      Fix: Create units under track '{track.name}'")
			all_subjects_ok = False
			continue

		# Check topics for each unit
		for unit in units:
			topics = frappe.get_all(
				"Memora Topic", filters={"parent_unit": unit.name}, fields=["name", "topic_name"]
			)
			print(f"\n  Topics in {unit.name}: {len(topics)}")
			for tp in topics:
				print(f"    ✓ {tp.name} - {tp.topic_name}")

			if not topics:
				print(f"    ✗ NO TOPICS - Bitmap will have empty mappings!")
				print(f"      Fix: Create topics under unit '{unit.name}'")
				all_subjects_ok = False
				continue

			# Check lessons for each topic
			for topic in topics:
				lessons_all = frappe.get_all(
					"Memora Lesson",
					filters={"parent_topic": topic.name},
					fields=["name", "lesson_name", "docstatus"],
				)

				lessons_submitted = frappe.get_all(
					"Memora Lesson",
					filters={
						"parent_topic": topic.name,
						"docstatus": 1,  # Only submitted
					},
					fields=["name", "lesson_name", "docstatus"],
				)

				draft_count = sum(1 for l in lessons_all if l.docstatus == 0)
				submitted_count = len(lessons_submitted)

				print(f"\n  Lessons in {topic.name}:")
				print(f"    Total: {len(lessons_all)} (Draft: {draft_count}, Submitted: {submitted_count})")

				for l in lessons_submitted:
					print(f"    ✓ {l.name} - {l.lesson_name} (docstatus={l.docstatus})")

				for l in lessons_all:
					if l.docstatus == 0:
						print(f"    ✗ {l.name} - {l.lesson_name} (DRAFT - not included in bitmap!)")

				if not lessons_submitted:
					print(f"    ✗ NO SUBMITTED LESSONS - Bitmap will have empty mappings!")
					print(f"      Fix: Submit lessons under topic '{topic.name}'")
					print(f"      In Frappe Desk: Open Lesson → Submit button")
					all_subjects_ok = False

# Step 4: Check existing bitmap files
print("\n" + "=" * 70)
print("CHECKING EXISTING BITMAP FILES")
print("=" * 70)

from memora.services.cdn_export.local_storage import get_local_base_path, file_exists
import json
import os

base_path = get_local_base_path()

for ps in plan_subjects:
	subject_name = ps.subject
	bitmap_path = f"plans/{plan_name}/{subject_name}_b.json"

	if file_exists(bitmap_path):
		full_path = os.path.join(base_path, bitmap_path)
		with open(full_path, "r") as f:
			bitmap_data = json.load(f)

		print(f"\n  Subject: {subject_name}")
		print(f"  Path: {bitmap_path}")
		print(f"  total_lessons: {bitmap_data.get('total_lessons', 'N/A')}")
		print(f"  mappings count: {len(bitmap_data.get('mappings', {}))}")

		if bitmap_data.get("mappings"):
			print(f"  Lessons: {list(bitmap_data['mappings'].keys())}")
		else:
			print(f"  ⚠ MAPPINGS IS EMPTY!")
	else:
		print(f"\n  Subject: {subject_name}")
		print(f"  Path: {bitmap_path}")
		print(f"  ✗ FILE DOES NOT EXIST - Run plan rebuild!")

# Step 5: Summary and recommendations
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if all_subjects_ok:
	print("\n✓ All subjects have complete hierarchy with submitted lessons!")
	print("\nIf bitmap still has empty mappings, try:")
	print("  1. Clear Frappe cache: bench clear-cache")
	print("  2. Rebuild plan again: plan.rebuild_plan()")
	print("  3. Check Frappe Error Log for any errors")
else:
	print("\n✗ Issues detected in hierarchy!")
	print("\nFix the issues above, then:")
	print("  1. Submit all draft lessons (docstatus=1)")
	print("  2. Rebuild the plan: plan.rebuild_plan()")
	print("  3. Check bitmap file again")

print("\n" + "=" * 70)
print("To rebuild this plan, run:")
print(f"  frappe.get_doc('Memora Academic Plan', '{plan_name}').rebuild_plan()")
print("=" * 70 + "\n")
