"""
CDN Debug API Endpoints
Provides debugging and manual trigger endpoints for JSON generation and diagnostics.
"""

import frappe
import json
import os


@frappe.whitelist()

def generate_subject_json_now(subject_id, plan_id=None):
	"""
	Manually trigger JSON generation for a subject in a plan.
	Bypasses queue system for debugging purposes.

	Args:
		subject_id (str): Memora Subject ID
		plan_id (str, optional): Plan ID for override lookup

	Returns:
		dict: Generation results including JSON data and diagnostic info
	"""
	try:
		# Verify user is System Manager
		frappe.only_for("System Manager")

		frappe.log_error(
			f"[INFO] Debug: Manual JSON generation requested for subject {subject_id} in plan {plan_id}",
			"CDN Debug API"
		)

		# Get subject document
		subject_doc = frappe.get_doc("Memora Subject", subject_id)

		# Generate JSON
		from memora.services.cdn_export.json_generator import generate_subject_json
		from memora.services.cdn_export.access_calculator import calculate_access_level

		json_data = generate_subject_json(subject_doc, plan_id=plan_id)

		if json_data is None:
			# Subject was hidden by override
			frappe.log_error(
				f"[WARN] Subject {subject_id} is hidden by plan override",
				"CDN Debug API"
			)
			return {
				"success": False,
				"subject_id": subject_id,
				"error": "Subject is hidden by plan override",
				"access_level": None
			}

		# Get access level for diagnostics
		access_level = calculate_access_level(subject_doc, parent_access=None, plan_overrides={})

		# Count content
		num_tracks = len(json_data.get("tracks", []))
		num_units = sum(len(track.get("units", [])) for track in json_data.get("tracks", []))
		num_lessons = sum(
			len(lesson) for track in json_data.get("tracks", [])
			for unit in track.get("units", [])
			for topic in unit.get("topics", [])
			for lesson in topic.get("lessons", [])
		)

		# Write to local storage if plan_id provided
		written_files = []
		if plan_id:
			from memora.services.cdn_export.local_storage import write_content_file

			path = f"subjects/{subject_id}.json"
			success, error = write_content_file(path, json_data)

			if success:
				written_files.append(path)
				frappe.log_error(
					f"[INFO] Debug: Wrote JSON to {path}",
					"CDN Debug API"
				)
			else:
				frappe.log_error(
					f"[ERROR] Debug: Failed to write JSON to {path}: {error}",
					"CDN Debug API"
				)

		frappe.log_error(
			f"[INFO] Debug: Generated JSON for {subject_id} - {num_tracks} tracks, {num_units} units, {num_lessons} lessons",
			"CDN Debug API"
		)

		return {
			"success": True,
			"subject_id": subject_id,
			"plan_id": plan_id,
			"access_level": access_level,
			"title": subject_doc.title,
			"tracks": num_tracks,
			"units": num_units,
			"lessons": num_lessons,
			"files_written": written_files,
			"json_preview": {
				"id": json_data.get("id"),
				"title": json_data.get("title"),
				"access": json_data.get("access"),
				"num_tracks": num_tracks
			}
		}

	except frappe.PermissionError:
		frappe.throw("Only System Managers can access debug endpoints")
	except frappe.DoesNotExistError:
		frappe.log_error(
			f"[ERROR] Subject {subject_id} not found",
			"CDN Debug API"
		)
		return {
			"success": False,
			"subject_id": subject_id,
			"error": f"Subject {subject_id} not found"
		}
	except Exception as e:
		frappe.log_error(f"Debug endpoint error: {str(e)}", "CDN Debug API")
		return {
			"success": False,
			"subject_id": subject_id,
			"error": str(e)
		}


@frappe.whitelist()

def diagnose_subject_issue(subject_id):
	"""
	Run full diagnostics for why a subject might not have JSON generated.

	Args:
		subject_id (str): Memora Subject ID

	Returns:
		dict: Diagnostic information and recommendations
	"""
	try:
		# Verify user is System Manager
		frappe.only_for("System Manager")

		frappe.log_error(
			f"[INFO] Debug: Running diagnostics for subject {subject_id}",
			"CDN Debug API"
		)

		diagnostics = {
			"subject_id": subject_id,
			"issues": [],
			"recommendations": []
		}

		# Check if subject exists
		if not frappe.db.exists("Memora Subject", subject_id):
			diagnostics["issues"].append(f"Subject {subject_id} does not exist")
			return diagnostics

		subject = frappe.get_doc("Memora Subject", subject_id)
		diagnostics["subject"] = {
			"name": subject.name,
			"title": subject.title,
			"is_published": subject.is_published,
			"required_item": subject.required_item
		}

		# Check CDN Settings
		settings = frappe.get_single("CDN Settings")
		diagnostics["cdn_settings"] = {
			"enabled": settings.enabled,
			"local_fallback_mode": settings.local_fallback_mode
		}

		if not settings.enabled and not settings.local_fallback_mode:
			diagnostics["issues"].append("CDN is disabled AND local fallback mode is disabled")
			diagnostics["recommendations"].append("Enable either 'CDN Enabled' or 'Local Fallback Mode' in CDN Settings")

		# Check if subject is in any plan
		plans = frappe.db.get_all(
			"Memora Plan Subject",
			filters={"subject": subject_id},
			pluck="parent"
		)
		diagnostics["plans"] = plans

		if not plans:
			diagnostics["issues"].append("Subject is not in any Memora Academic Plan")
			diagnostics["recommendations"].append("Add the subject to a plan in Memora Academic Plan")

		# Check for plan overrides
		overrides = frappe.db.get_all(
			"Memora Plan Override",
			filters={"target_name": subject_id},
			fields=["parent", "action"]
		)
		diagnostics["overrides"] = overrides

		hidden_in_plans = [o.parent for o in overrides if o.action == "Hide"]
		if hidden_in_plans:
			diagnostics["issues"].append(f"Subject is hidden in these plans: {hidden_in_plans}")
			diagnostics["recommendations"].append("Check Memora Plan Override documents and remove 'Hide' actions")

		# Check if local JSON exists
		from memora.services.cdn_export.local_storage import get_local_base_path
		base_path = get_local_base_path()
		json_path = os.path.join(base_path, f"subjects/{subject_id}.json")
		json_exists = os.path.exists(json_path)

		diagnostics["local_json"] = {
			"exists": json_exists,
			"path": json_path if json_exists else None
		}

		if not json_exists and plans and not hidden_in_plans:
			diagnostics["recommendations"].append("JSON file should exist but doesn't - try running 'Trigger Plan Rebuild' for a plan containing this subject")

		# Check Redis queue
		try:
			queue_size = frappe.cache().scard("cdn_export:pending_plans") or 0
			diagnostics["redis_queue"] = {
				"size": queue_size,
				"accessible": True
			}
		except Exception as e:
			diagnostics["redis_queue"] = {
				"size": 0,
				"accessible": False,
				"error": str(e)
			}
			diagnostics["issues"].append("Cannot access Redis queue")
			diagnostics["recommendations"].append("Check that Redis is running and configured correctly")

		# Check CDN Sync Log
		sync_logs = frappe.db.get_all(
			"CDN Sync Log",
			filters={"status": ["!=", "Success"]},
			fields=["name", "plan_id", "status", "error_message"],
			limit_page_length=5,
			order_by="creation desc"
		)
		diagnostics["recent_failures"] = sync_logs

		if sync_logs:
			diagnostics["issues"].append(f"Found {len(sync_logs)} failed CDN sync attempts")
			diagnostics["recommendations"].append("Check CDN Sync Log for details on recent failures")

		# Summary
		if not diagnostics["issues"]:
			diagnostics["summary"] = "No issues found - subject should be generating JSON"
		else:
			diagnostics["summary"] = f"Found {len(diagnostics['issues'])} issue(s) preventing JSON generation"

		frappe.log_error(
			f"[INFO] Debug: Diagnostics for {subject_id}: {diagnostics['summary']}",
			"CDN Debug API"
		)

		return diagnostics

	except frappe.PermissionError:
		frappe.throw("Only System Managers can access debug endpoints")
	except Exception as e:
		frappe.log_error(f"Debug diagnostics error: {str(e)}", "CDN Debug API")
		return {
			"success": False,
			"subject_id": subject_id,
			"error": str(e)
		}


@frappe.whitelist()
def diagnose_query_failure(doctype, filters, fields):
	"""
	Diagnose SQL query failures by executing query and capturing full error details.

	This endpoint is part of User Story 1: System Administrator Diagnoses JSON Generation Failure.
	It captures exact SQL queries, error messages, and schema validation reports.

	Args:
		doctype (str): Target DocType to query
		filters (dict): Query filters (JSON string or dict)
		fields (list|str): Fields to retrieve (JSON array string or list)

	Returns:
		dict: QueryDiagnosticResult with query, error details, and schema validation
	"""
	try:
		# Verify user is System Manager
		frappe.only_for("System Manager")

		# Parse filters and fields if they come as JSON strings
		if isinstance(filters, str):
			filters = json.loads(filters)
		if isinstance(fields, str):
			fields = json.loads(fields)

		frappe.log_error(
			f"[DEBUG] diagnose_query_failure called for {doctype} with fields: {fields}",
			"CDN Diagnostic API"
		)

		# Call diagnostic utility
		from memora.utils.diagnostics import diagnose_query_failure as diagnose_util

		result = diagnose_util(doctype, filters, fields)

		return result

	except frappe.PermissionError:
		frappe.throw("Only System Managers can access diagnostic endpoints")
	except Exception as e:
		import traceback
		frappe.log_error(
			f"diagnose_query_failure endpoint error: {str(e)}\n{traceback.format_exc()}",
			"CDN Diagnostic API Error"
		)
		return {
			"success": False,
			"error": str(e),
			"traceback": traceback.format_exc()
		}


@frappe.whitelist()
def get_error_logs(minutes=30, search=None):
	"""
	Retrieve recent error logs related to CDN export operations.

	This endpoint is part of User Story 1: System Administrator Diagnoses JSON Generation Failure.
	It helps administrators view recent CDN-related errors with full context.

	Args:
		minutes (int): How many minutes back to search (default: 30)
		search (str, optional): Search term to filter errors by title or error content

	Returns:
		dict: List of error logs with name, title, error, creation fields
	"""
	try:
		# Verify user is System Manager
		frappe.only_for("System Manager")

		# Parse minutes to int if string
		if isinstance(minutes, str):
			minutes = int(minutes)

		frappe.log_error(
			f"[DEBUG] get_error_logs called: minutes={minutes}, search={search}",
			"CDN Diagnostic API"
		)

		# Call diagnostic utility
		from memora.utils.diagnostics import get_recent_error_logs

		error_logs = get_recent_error_logs(minutes, search)

		return {
			"success": True,
			"count": len(error_logs),
			"minutes": minutes,
			"search_term": search,
			"logs": error_logs
		}

	except frappe.PermissionError:
		frappe.throw("Only System Managers can access diagnostic endpoints")
	except Exception as e:
		import traceback
		frappe.log_error(
			f"get_error_logs endpoint error: {str(e)}\n{traceback.format_exc()}",
			"CDN Diagnostic API Error"
		)
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def test_json_function(function_name, plan_id, subject_id=None, unit_id=None, lesson_id=None):
	"""
	Test a JSON generation function in isolation to identify which component is failing.

	This endpoint is part of User Story 2: Developer Isolates Failing JSON Generation Component.
	It allows testing each function (manifest, search index, subject JSON) separately.

	Args:
		function_name (str): Name of function to test (generate_manifest, generate_subject_json, generate_search_index)
		plan_id (str): Academic plan ID
		subject_id (str, optional): Subject ID (required for generate_subject_json)
		unit_id (str, optional): Unit ID (for future expansion)
		lesson_id (str, optional): Lesson ID (for future expansion)

	Returns:
		dict: JSONGenerationTestResult with function_name, success, output_data, error, execution_time_ms
	"""
	try:
		# Verify user is System Manager
		frappe.only_for("System Manager")

		frappe.log_error(
			f"[DEBUG] test_json_function called: function={function_name}, plan={plan_id}, subject={subject_id}",
			"CDN Diagnostic API"
		)

		# Call diagnostic utility
		from memora.utils.diagnostics import test_json_function as test_json_util

		result = test_json_util(
			function_name,
			plan_id=plan_id,
			subject_id=subject_id,
			unit_id=unit_id,
			lesson_id=lesson_id
		)

		return result

	except frappe.PermissionError:
		frappe.throw("Only System Managers can access diagnostic endpoints")
	except Exception as e:
		import traceback
		frappe.log_error(
			f"test_json_function endpoint error: {str(e)}\n{traceback.format_exc()}",
			"CDN Diagnostic API Error"
		)
		return {
			"success": False,
			"error": str(e),
			"traceback": traceback.format_exc()
		}


@frappe.whitelist()
def audit_queries(function_name, plan_id, subject_id=None):
	"""
	Audit all SQL queries executed during a JSON generation function call.

	This endpoint is part of User Story 3: Developer Traces Dynamic Query Construction.
	It captures all database queries to help identify queries referencing non-existent columns.

	Args:
		function_name (str): Name of function to audit (generate_manifest, generate_subject_json, generate_search_index)
		plan_id (str): Academic plan ID
		subject_id (str, optional): Subject ID (required for generate_subject_json)

	Returns:
		dict: Query audit results with query_count, queries list, function_success status
	"""
	try:
		# Verify user is System Manager
		frappe.only_for("System Manager")

		frappe.log_error(
			f"[DEBUG] audit_queries called: function={function_name}, plan={plan_id}, subject={subject_id}",
			"CDN Diagnostic API"
		)

		# Call diagnostic utility
		from memora.utils.diagnostics import audit_queries_for_function

		result = audit_queries_for_function(function_name, plan_id, subject_id)

		return result

	except frappe.PermissionError:
		frappe.throw("Only System Managers can access diagnostic endpoints")
	except Exception as e:
		import traceback
		frappe.log_error(
			f"audit_queries endpoint error: {str(e)}\n{traceback.format_exc()}",
			"CDN Diagnostic API Error"
		)
		return {
			"success": False,
			"error": str(e),
			"traceback": traceback.format_exc()
		}


@frappe.whitelist()
def validate_schema_api(doctype):
	"""
	Validate database schema matches DocType definition.
	API endpoint for schema validation diagnostic tool.

	Args:
		doctype (str): DocType name to validate

	Returns:
		dict: Schema validation report with valid flag and field mismatches
	"""
	try:
		# Verify user is System Manager
		frappe.only_for("System Manager")

		from memora.utils.diagnostics import validate_schema

		validation_result = validate_schema(doctype)

		return {
			"success": True,
			"doctype": doctype,
			"validation": validation_result
		}

	except Exception as e:
		import traceback
		frappe.log_error(
			f"validate_schema endpoint error: {str(e)}\n{traceback.format_exc()}",
			"CDN Diagnostic API Error"
		)
		return {
			"success": False,
			"error": str(e),
			"traceback": traceback.format_exc()
		}
