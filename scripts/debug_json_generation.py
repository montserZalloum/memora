#!/usr/bin/env python3
"""
Diagnostic script to identify the exact failing query in JSON generation.
Run with: bench --site {site_name} execute memora.scripts.debug_json_generation.run_diagnostics
"""

import frappe
from frappe.utils import now_datetime, add_to_date
import traceback


def run_diagnostics(plan_id="37q5969lug", subject_id="qunhaa99lf"):
	"""
	Run comprehensive diagnostics on JSON generation functions.

	Args:
		plan_id: ID of plan to test (default: 37q5969lug)
		subject_id: ID of subject to test (default: qunhaa99lf)
	"""
	print("="*80)
	print("JSON GENERATION DIAGNOSTIC TOOL")
	print("="*80)
	print(f"Plan ID: {plan_id}")
	print(f"Subject ID: {subject_id}")
	print("="*80)

	# Test 1: Get Error Logs
	print("\n" + "="*80)
	print("TEST 1: Recent Error Logs")
	print("="*80)
	try:
		logs = frappe.db.get_all(
			"Error Log",
			filters={"creation": [">", add_to_date(now_datetime(), minutes=-30)]},
			fields=["name", "title", "creation"],
			order_by="creation desc",
			limit=10
		)

		print(f"Found {len(logs)} error logs in last 30 minutes")
		for log in logs:
			if "Unknown column" in log.title or "CDN" in log.title:
				doc = frappe.get_doc("Error Log", log.name)
				print(f"\n{'-'*80}")
				print(f"Title: {doc.title}")
				print(f"Time: {doc.creation}")
				print(f"\nError (first 1000 chars):")
				print(doc.error[:1000])
	except Exception as e:
		print(f"❌ Error retrieving logs: {e}")
		traceback.print_exc()

	# Test 2: Manifest Generation
	print("\n" + "="*80)
	print("TEST 2: Generate Manifest")
	print("="*80)
	try:
		plan_doc = frappe.get_doc("Memora Academic Plan", plan_id)
		from memora.services.cdn_export.json_generator import generate_manifest
		manifest = generate_manifest(plan_doc)
		print(f"✅ SUCCESS: Generated manifest with {len(manifest.get('subjects', []))} subjects")
		print(f"Subjects in manifest: {[s['id'] for s in manifest.get('subjects', [])]}")
	except Exception as e:
		print(f"❌ FAILED: {e}")
		traceback.print_exc()

	# Test 3: Search Index Generation
	print("\n" + "="*80)
	print("TEST 3: Generate Search Index")
	print("="*80)
	try:
		from memora.services.cdn_export.search_indexer import generate_search_index
		search_index = generate_search_index(plan_id)
		print(f"✅ SUCCESS: Generated search index")
		print(f"Total lessons: {search_index.get('total_lessons', 0)}")
		print(f"Is sharded: {search_index.get('is_sharded', False)}")
	except Exception as e:
		print(f"❌ FAILED: {e}")
		traceback.print_exc()

	# Test 4: Subject JSON Generation
	print("\n" + "="*80)
	print("TEST 4: Generate Subject JSON")
	print("="*80)
	try:
		subject_doc = frappe.get_doc("Memora Subject", subject_id)
		from memora.services.cdn_export.json_generator import generate_subject_json
		subject_json = generate_subject_json(subject_doc, plan_id=plan_id)

		if subject_json:
			print(f"✅ SUCCESS: Generated subject JSON")
			print(f"Tracks: {len(subject_json.get('tracks', []))}")
			for track in subject_json.get('tracks', []):
				print(f"  - Track {track['id']}: {len(track.get('units', []))} units")
		else:
			print(f"⚠️  WARNING: Function returned None (possibly hidden by override)")
	except Exception as e:
		print(f"❌ FAILED: {e}")
		traceback.print_exc()

	# Test 5: Schema Validation
	print("\n" + "="*80)
	print("TEST 5: Schema Validation")
	print("="*80)

	doctypes_to_check = [
		"Memora Academic Plan",
		"Memora Subject",
		"Memora Track",
		"Memora Unit",
		"Memora Topic",
		"Memora Lesson",
		"Memora Plan Subject",
		"Memora Lesson Stage",
		"Memora Plan Override"
	]

	for doctype in doctypes_to_check:
		try:
			meta = frappe.get_meta(doctype)
			table_name = f"tab{doctype}"

			# Get expected fields
			expected_fields = {f.fieldname for f in meta.fields}

			# Get actual columns
			columns = frappe.db.sql(f"DESCRIBE `{table_name}`", as_dict=True)
			actual_columns = {col['Field'] for col in columns}

			# Find mismatches
			missing = expected_fields - actual_columns
			extra = actual_columns - expected_fields

			if missing or extra:
				print(f"\n⚠️  {doctype}:")
				if missing:
					print(f"   Missing in DB: {list(missing)}")
				if extra:
					print(f"   Extra in DB: {list(extra)[:5]}...")  # Show first 5
			else:
				print(f"✅ {doctype}: Schema valid")
		except Exception as e:
			print(f"❌ {doctype}: Error checking schema - {e}")

	# Test 6: Full Rebuild
	print("\n" + "="*80)
	print("TEST 6: Full Plan Rebuild")
	print("="*80)
	try:
		from memora.services.cdn_export.batch_processor import _rebuild_plan
		success = _rebuild_plan(plan_id)
		if success:
			print(f"✅ SUCCESS: Plan rebuild completed")
		else:
			print(f"❌ FAILED: Plan rebuild returned False")
	except Exception as e:
		print(f"❌ FAILED: Plan rebuild threw exception: {e}")
		traceback.print_exc()

	print("\n" + "="*80)
	print("DIAGNOSTIC COMPLETE")
	print("="*80)


if __name__ == "__main__":
	# If running directly via bench execute
	run_diagnostics()
