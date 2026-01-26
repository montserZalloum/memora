"""
Test data fixtures for CDN export testing.
Provides helper functions to create and cleanup test data.
"""

import frappe
from frappe.utils import now_datetime


def create_test_plan(plan_id=None, title="Test Academic Plan"):
	"""
	Create a test Memora Academic Plan document.

	Args:
		plan_id (str, optional): Custom plan ID. If None, auto-generated.
		title (str): Plan title

	Returns:
		frappe.Document: Created plan document
	"""
	plan_doc = frappe.get_doc({
		"doctype": "Memora Academic Plan",
		"title": title,
		"season": "Fall 2026",
		"grade": "Grade 10",
		"is_published": 1
	})

	if plan_id:
		plan_doc.name = plan_id

	plan_doc.insert(ignore_if_duplicate=True)
	frappe.db.commit()

	return plan_doc


def create_test_subject(subject_id=None, title="Test Subject", is_public=0, is_free_preview=0):
	"""
	Create a test Memora Subject document.

	Args:
		subject_id (str, optional): Custom subject ID. If None, auto-generated.
		title (str): Subject title
		is_public (int): 1 if public, 0 if authenticated
		is_free_preview (int): 1 if free preview, 0 otherwise

	Returns:
		frappe.Document: Created subject document
	"""
	subject_doc = frappe.get_doc({
		"doctype": "Memora Subject",
		"title": title,
		"description": f"Test description for {title}",
		"is_published": 1,
		"is_public": is_public,
		"is_free_preview": is_free_preview,
		"sort_order": 1,
		"color_code": "#3498db"
	})

	if subject_id:
		subject_doc.name = subject_id

	subject_doc.insert(ignore_if_duplicate=True)
	frappe.db.commit()

	return subject_doc


def create_test_track(track_id=None, title="Test Track", parent_subject=None):
	"""
	Create a test Memora Track document.

	Args:
		track_id (str, optional): Custom track ID
		title (str): Track title
		parent_subject (str): Parent subject ID

	Returns:
		frappe.Document: Created track document
	"""
	if not parent_subject:
		raise ValueError("parent_subject is required")

	track_doc = frappe.get_doc({
		"doctype": "Memora Track",
		"title": title,
		"description": f"Test description for {title}",
		"parent_subject": parent_subject,
		"sort_order": 1,
		"is_sold_separately": 0
	})

	if track_id:
		track_doc.name = track_id

	track_doc.insert(ignore_if_duplicate=True)
	frappe.db.commit()

	return track_doc


def link_subject_to_plan(plan_id, subject_id, sort_order=1):
	"""
	Link a subject to an academic plan via child table.

	Args:
		plan_id (str): Plan document name
		subject_id (str): Subject document name
		sort_order (int): Sort order for the subject in the plan

	Returns:
		frappe.Document: Updated plan document
	"""
	plan_doc = frappe.get_doc("Memora Academic Plan", plan_id)

	# Check if already linked
	existing = [row for row in plan_doc.subjects if row.subject == subject_id]
	if existing:
		return plan_doc

	# Add subject to plan
	plan_doc.append("subjects", {
		"subject": subject_id,
		"sort_order": sort_order
	})

	plan_doc.save(ignore_permissions=True)
	frappe.db.commit()

	return plan_doc


def cleanup_test_data(plan_id=None, subject_id=None, track_id=None):
	"""
	Clean up test data by deleting test documents.

	Args:
		plan_id (str, optional): Plan ID to delete
		subject_id (str, optional): Subject ID to delete
		track_id (str, optional): Track ID to delete

	Returns:
		dict: Summary of deleted documents
	"""
	deleted = {
		"plans": 0,
		"subjects": 0,
		"tracks": 0
	}

	try:
		if track_id and frappe.db.exists("Memora Track", track_id):
			frappe.delete_doc("Memora Track", track_id, force=True, ignore_permissions=True)
			deleted["tracks"] += 1

		if subject_id and frappe.db.exists("Memora Subject", subject_id):
			frappe.delete_doc("Memora Subject", subject_id, force=True, ignore_permissions=True)
			deleted["subjects"] += 1

		if plan_id and frappe.db.exists("Memora Academic Plan", plan_id):
			frappe.delete_doc("Memora Academic Plan", plan_id, force=True, ignore_permissions=True)
			deleted["plans"] += 1

		frappe.db.commit()

	except Exception as e:
		frappe.log_error(f"Error cleaning up test data: {str(e)}", "Test Data Cleanup Error")

	return deleted


def create_full_test_hierarchy(
	plan_id="TEST-PLAN-001",
	subject_id="TEST-SUBJECT-001",
	track_id="TEST-TRACK-001"
):
	"""
	Create a full test hierarchy: Plan -> Subject -> Track.

	Args:
		plan_id (str): Plan ID
		subject_id (str): Subject ID
		track_id (str): Track ID

	Returns:
		dict: Created documents {plan, subject, track}
	"""
	# Create plan
	plan = create_test_plan(plan_id=plan_id, title="Test Academic Plan")

	# Create subject
	subject = create_test_subject(
		subject_id=subject_id,
		title="Test Subject",
		is_public=0,
		is_free_preview=1
	)

	# Create track
	track = create_test_track(
		track_id=track_id,
		title="Test Track",
		parent_subject=subject_id
	)

	# Link subject to plan
	link_subject_to_plan(plan_id, subject_id, sort_order=1)

	return {
		"plan": plan,
		"subject": subject,
		"track": track
	}
