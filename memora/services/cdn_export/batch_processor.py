import frappe
import json
import os
import time
from frappe.utils import now_datetime, add_to_date
from frappe import log_error
from .change_tracker import (
    get_pending_plans, acquire_lock, release_lock, move_to_dead_letter,
    add_plan_to_fallback_queue, add_plan_to_queue
)
from .json_generator import (
    get_content_paths_for_plan,
    get_atomic_content_paths_for_plan,
    generate_manifest_atomic,
    generate_subject_hierarchy,
    generate_bitmap_json,
    generate_topic_json,
    generate_lesson_json_shared,
)
from .cdn_uploader import get_cdn_client, upload_plan_files, upload_plan_files_from_local, get_cdn_base_url
from .local_storage import write_content_file, get_file_hash, get_local_base_path
from .dependency_resolver import get_affected_plan_ids

try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    log_error("jsonschema library not installed. JSON validation disabled.", "Missing Dependency")

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'schemas')

def process_pending_plans(max_plans=10):
    """
    Process up to max_plans from the pending queue.

    Args:
        max_plans (int): Maximum number of plans to process in one batch

    Returns:
        dict: Processing results summary
    """
    results = {
        'processed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }

    # Get pending plans
    pending_plans = get_pending_plans(max_plans)

    if not pending_plans:
        return results

    settings = frappe.get_single("CDN Settings")
    batch_threshold = getattr(settings, 'batch_threshold', 50)

    # Check if we've reached threshold and need immediate processing
    if len(pending_plans) >= batch_threshold:
        # Process all pending plans immediately
        max_plans = len(pending_plans)

    for plan_id in pending_plans[:max_plans]:
        try:
            # Acquire lock for this plan
            if not acquire_lock(plan_id):
                # Plan is already being processed
                results['skipped'] += 1
                continue
        except:
            try:
                release_lock(plan_id)
            except:
                pass
            continue

        try:
            # Create sync log entry
            sync_log = frappe.get_doc({
                'doctype': 'CDN Sync Log',
                'plan_id': plan_id,
                'status': 'Processing',
                'started_at': now_datetime(),
                'triggered_by': 'Scheduler'
            }).insert(ignore_permissions=True)

            # Process the plan
            success = _rebuild_plan(plan_id)

            if success:
                sync_log.status = 'Success'
                sync_log.completed_at = now_datetime()
                sync_log.save(ignore_permissions=True)
                results['processed'] += 1
            else:
                sync_log.status = 'Failed'
                sync_log.completed_at = now_datetime()
                sync_log.retry_count = (sync_log.retry_count or 0) + 1
                sync_log.save(ignore_permissions=True)

                # Exponential backoff schedule: [30s, 1m, 2m, 5m, 15m] (5 retries total)
                BACKOFF_SCHEDULE = [30, 60, 120, 300, 900]  # seconds
                
                if sync_log.retry_count >= len(BACKOFF_SCHEDULE):
                    # All retries exhausted - mark as Dead Letter and send alert
                    move_to_dead_letter(plan_id, f"Failed after {sync_log.retry_count} retries")
                    sync_log.status = 'Dead Letter'
                    sync_log.save(ignore_permissions=True)
                    
                    # Send alert to system managers
                    from .health_checker import send_sync_failure_alert
                    send_sync_failure_alert(sync_log.name)
                    
                    results['failed'] += 1
                else:
                    # Calculate next retry time using backoff schedule
                    delay_seconds = BACKOFF_SCHEDULE[sync_log.retry_count]
                    next_retry_at = add_to_date(now_datetime(), delay_seconds, 'seconds')

                    # Store retry schedule in sync log for visibility
                    sync_log.next_retry_at = next_retry_at
                    sync_log.save(ignore_permissions=True)

                    # Add back to queue for retry with fallback mechanism
                    add_plan_to_fallback_queue(plan_id)
                    results['failed'] += 1

        except Exception as e:
            log_error(f"Error processing plan {plan_id}: {str(e)}")
            results['errors'].append(f"Plan {plan_id}: {str(e)}")
            results['failed'] += 1

        finally:
            try:
                release_lock(plan_id)
            except:
                pass

    return results

def _generate_atomic_files_for_plan(plan_id):
	"""
	Generate all atomic JSON files for a plan (Phase 7: User Story 5).

	Uses existing write_content_file() which implements atomic writes with .tmp staging.

	Args:
		plan_id (str): Plan document name

	Returns:
		tuple: (success: bool, files_written: dict, errors: list)
	"""
	files_written = {}
	errors = []

	try:
		plan_doc = frappe.get_doc("Memora Academic Plan", plan_id)
		
		# 1. Generate manifest
		try:
			manifest_data = generate_manifest_atomic(plan_doc)
			manifest_path = f"plans/{plan_id}/manifest.json"
			success, error = write_content_file(manifest_path, manifest_data)
			if success:
				files_written[manifest_path] = manifest_data
				frappe.log_error(
					f"[INFO] Generated {manifest_path}",
					"Atomic File Generation"
				)
			else:
				errors.append(f"Manifest generation failed: {error}")
				raise Exception(f"Manifest write failed: {error}")
		except Exception as e:
			errors.append(f"Manifest generation error: {str(e)}")
			raise

		
		# 2. Generate hierarchies and bitmaps for plan subjects
		plan_subjects = frappe.get_all(
			"Memora Plan Subject",
			filters={"parent": plan_id},
			fields=["subject"]
		)
		
		subject_ids = [ps.subject for ps in plan_subjects]

		# Handle empty subject list
		if not subject_ids:
			frappe.log_error(
				f"[WARN] No subjects found for plan {plan_id}, skipping subject hierarchy/bitmap generation",
				"Atomic File Generation"
			)
			subjects = []
		else:
			subjects = frappe.get_all(
				"Memora Subject",
				filters={"name": ["in", subject_ids]},
				fields=["name"]
			)

		for subject in subjects:
			try:
				subject_doc = frappe.get_doc("Memora Subject", subject.name)
				frappe.log_error(
					f"[WARN] Subject log 1",
					"_generate_atomic_files_for_plan for subject in subjects"
				)
				# Generate hierarchy
				hierarchy_data = generate_subject_hierarchy(subject_doc, plan_id=plan_id)

				# Skip if subject is hidden by override
				if hierarchy_data is None:
					frappe.log_error(
						f"[WARN] Skipping hierarchy for {subject.name} - hidden by plan override",
						"Atomic File Generation"
					)
				else:
					hierarchy_path = f"plans/{plan_id}/{subject.name}_h.json"
					success, error = write_content_file(hierarchy_path, hierarchy_data)
					if success:
						files_written[hierarchy_path] = hierarchy_data
						frappe.log_error(
							f"[INFO] Generated {hierarchy_path}",
							"Atomic File Generation"
						)
					else:
						errors.append(f"Hierarchy generation failed for {subject.name}: {error}")
						raise Exception(error)

				# Generate bitmap
				bitmap_data = generate_bitmap_json(subject_doc)

				# Skip if bitmap is None (shouldn't happen, but be defensive)
				if bitmap_data is None:
					frappe.log_error(
						f"[WARN] Skipping bitmap for {subject.name} - no bitmap data",
						"Atomic File Generation"
					)
				else:
					bitmap_path = f"plans/{plan_id}/{subject.name}_b.json"
					success, error = write_content_file(bitmap_path, bitmap_data)
					if success:
						files_written[bitmap_path] = bitmap_data
						frappe.log_error(
							f"[INFO] Generated {bitmap_path}",
							"Atomic File Generation"
						)
					else:
						errors.append(f"Bitmap generation failed for {subject.name}: {error}")
						raise Exception(error)

			except Exception as e:
				errors.append(f"Subject {subject.name} generation failed: {str(e)}")
				raise

		# 3. Generate topics for plan subjects
		# Only proceed if we have subject_ids (guard against empty list)
		topics = []
		if subject_ids:
			tracks = frappe.get_all(
				"Memora Track",
				filters={"parent_subject": ["in", subject_ids]},
				fields=["name"]
			)
			track_ids = [t.name for t in tracks]

			if track_ids:
				units = frappe.get_all(
					"Memora Unit",
					filters={"parent_track": ["in", track_ids]},
					fields=["name"]
				)
				unit_ids = [u.name for u in units]

				if unit_ids:
					topics = frappe.get_all(
						"Memora Topic",
						filters={"parent_unit": ["in", unit_ids]},
						fields=["name"]
					)
				else:
					frappe.log_error(
						f"[WARN] No units found for plan {plan_id}, skipping topic generation",
						"Atomic File Generation"
					)
			else:
				frappe.log_error(
					f"[WARN] No tracks found for plan {plan_id}, skipping topic generation",
					"Atomic File Generation"
				)

		for topic in topics:
			try:
				topic_doc = frappe.get_doc("Memora Topic", topic.name)
				topic_data = generate_topic_json(topic_doc, plan_id=plan_id)

				# Skip if topic is hidden by override
				if topic_data is None:
					frappe.log_error(
						f"[WARN] Skipping topic {topic.name} - hidden by plan override",
						"Atomic File Generation"
					)
					continue

				topic_path = f"plans/{plan_id}/{topic.name}.json"
				success, error = write_content_file(topic_path, topic_data)
				if success:
					files_written[topic_path] = topic_data
					frappe.log_error(
						f"[INFO] Generated {topic_path}",
						"Atomic File Generation"
					)
				else:
					errors.append(f"Topic generation failed for {topic.name}: {error}")
					raise Exception(error)
			except Exception as e:
				errors.append(f"Topic {topic.name} generation failed: {str(e)}")
				raise

		# 4. Generate shared lessons for plan topics
		# Only proceed if we have topics (guard against empty list)
		lessons = []
		topic_ids = [t.name for t in topics]
		if topic_ids:
			lessons = frappe.get_all(
				"Memora Lesson",
				filters={"parent_topic": ["in", topic_ids]},
				fields=["name"]
			)
		else:
			frappe.log_error(
				f"[WARN] No topics found for plan {plan_id}, skipping lesson generation",
				"Atomic File Generation"
			)

		for lesson in lessons:
			try:
				lesson_doc = frappe.get_doc("Memora Lesson", lesson.name)
				lesson_data = generate_lesson_json_shared(lesson_doc)

				# Skip if lesson is None (shouldn't happen, but be defensive)
				if lesson_data is None:
					frappe.log_error(
						f"[WARN] Skipping lesson {lesson.name} - no lesson data",
						"Atomic File Generation"
					)
					continue

				lesson_path = f"lessons/{lesson.name}.json"
				success, error = write_content_file(lesson_path, lesson_data)
				if success:
					files_written[lesson_path] = lesson_data
					frappe.log_error(
						f"[INFO] Generated {lesson_path}",
						"Atomic File Generation"
					)
				else:
					errors.append(f"Lesson generation failed for {lesson.name}: {error}")
					raise Exception(error)
			except Exception as e:
				errors.append(f"Lesson {lesson.name} generation failed: {str(e)}")
				raise

		frappe.log_error(
			f"[INFO] Successfully generated {len(files_written)} atomic files for plan {plan_id}",
			"Atomic File Generation"
		)

		return True, files_written, []

	except Exception as e:
		frappe.log_error(
			f"Atomic file generation failed for {plan_id}: {'; '.join(errors)}",
			"Atomic File Generation Failure"
		)

		return False, {}, errors

def _rebuild_plan(plan_id):
	"""
	Rebuild all JSON files for a specific plan.

	Args:
		plan_id (str): Plan document name

	Returns:
		bool: True if successful, False otherwise
	"""
	try:
		# Get CDN settings
		settings = frappe.get_single("CDN Settings")
		
		# Check if we should generate local files (SOLUTION 0 FIX)
		should_generate_local = settings.local_fallback_mode or settings.enabled
		
		if not should_generate_local:
			frappe.log_error(
				f"[WARN] Skipping plan rebuild for {plan_id}: CDN disabled and local fallback mode disabled",
				"CDN Plan Rebuild"
			)
			return True
		
		# Always generate local JSON files, regardless of CDN status
		frappe.log_error(
			f"[INFO] Starting plan rebuild for {plan_id} - CDN enabled: {settings.enabled}, Local fallback: {settings.local_fallback_mode}",
			"CDN Plan Rebuild"
		)

		# Schema validation pre-flight check (T020)
		from memora.utils.diagnostics import validate_schema
		doctypes_to_validate = [
			"Memora Academic Plan",
			"Memora Subject",
			"Memora Track",
			"Memora Unit",
			"Memora Topic",
			"Memora Lesson",
			"Memora Lesson Stage",
			"Memora Plan Subject",
			"Memora Plan Override"
		]

		schema_issues = []
		for doctype in doctypes_to_validate:
			validation_result = validate_schema(doctype)
			if not validation_result["valid"]:
				schema_issues.append({
					"doctype": doctype,
					"missing_fields": validation_result.get("missing_in_db", []),
					"extra_fields": validation_result.get("extra_in_db", [])
				})

		if schema_issues:
			# Build summary for logging (limit length to avoid CharacterLengthExceededError)
			error_summary = []
			for issue in schema_issues:
				issue_details = []
				if issue["missing_fields"]:
					# Limit to first 5 missing fields to avoid huge logs
					missing_preview = issue["missing_fields"][:5]
					suffix = f" (+{len(issue['missing_fields']) - 5} more)" if len(issue["missing_fields"]) > 5 else ""
					issue_details.append(f"Missing: {missing_preview}{suffix}")
				if issue["extra_fields"]:
					# Limit to first 5 extra fields
					extra_preview = issue["extra_fields"][:5]
					suffix = f" (+{len(issue['extra_fields']) - 5} more)" if len(issue["extra_fields"]) > 5 else ""
					issue_details.append(f"Extra: {extra_preview}{suffix}")

				if issue_details:
					error_summary.append(f"{issue['doctype']}: {'; '.join(issue_details)}")

			error_msg = "Schema validation failed before JSON generation.\\n\\n"
			error_msg += "\\n".join(error_summary)
			error_msg += "\\n\\nSuggested action: Run 'bench migrate' to apply pending migrations."
			error_msg += "\\n\\nNote: This validation now properly handles Child Tables and Table-type fields."

			# Use title and message parameters separately to avoid title length issues
			frappe.log_error(
				title=f"Schema Validation Failed: Plan {plan_id}",
				message=error_msg[:10000]  # Limit to 10,000 chars to avoid DB errors
			)
			return False

		# Use atomic file generation (Phase 7: User Story 5)
		success, files_data, generation_errors = _generate_atomic_files_for_plan(plan_id)

		if not success or not files_data:
			frappe.log_error(
				f"[ERROR] Atomic file generation failed for plan {plan_id}: {'; '.join(generation_errors)}",
				"CDN Plan Rebuild"
			)
			return False

		frappe.log_error(
			f"[INFO] Atomically generated {len(files_data)} files for plan {plan_id}",
			"CDN Plan Rebuild"
		)
		
		# Only proceed with CDN operations if enabled
		if not settings.enabled:
			frappe.log_error(
				f"[INFO] CDN disabled - local JSON files generated for plan {plan_id}, skipping CDN upload",
				"CDN Plan Rebuild"
			)
			return True
		
		# Get CDN client for upload operations
		client = get_cdn_client(settings)
		bucket = settings.bucket_name

		# Build files_info with local paths
		base_path = get_local_base_path()
		files_info = {}
		
		for path, data in files_data.items():
			local_path = os.path.join(base_path, path)
			files_info[path] = {
				"local_path": local_path,
				"data": data
			}

		# Validate all generated JSON against schemas
		if JSONSCHEMA_AVAILABLE:
			validation_results = validate_all_json_files(files_data)
			if not validation_results['valid']:
				error_msg = f"JSON validation failed: {validation_results['errors']}"
				log_error(error_msg, "JSON Schema Validation Failed")
				return False

		# Upload all files from local storage
		uploaded_urls, upload_results, upload_errors = upload_plan_files_from_local(
			client, bucket, plan_id, files_info
		)

		if upload_errors:
			raise Exception(f"Upload errors: {'; '.join(upload_errors)}")

		# Get sync log to update with hash information
		sync_log = frappe.db.get_value(
			"CDN Sync Log",
			{"plan_id": plan_id, "status": "Processing"},
			"name"
		)
		
		if sync_log:
			sync_log_doc = frappe.get_doc("CDN Sync Log", sync_log)
			
			# Track local paths, local hashes, CDN hashes, and sync verification
			all_sync_verified = True
			
			for path, result in upload_results.items():
				if result["success"]:
					local_path = result["local_path"]
					cdn_hash = result["etag"]
					
					# Calculate local hash
					local_hash = get_file_hash(path)
					
					# Compare hashes
					sync_verified = (local_hash == cdn_hash)
					
					if not sync_verified:
						all_sync_verified = False
						frappe.log_error(
							f"Hash mismatch for {path}: local={local_hash}, cdn={cdn_hash}",
							"CDN Sync Hash Mismatch"
						)
			
			sync_log_doc.sync_verified = 1 if all_sync_verified else 0
			sync_log_doc.files_uploaded = len(uploaded_urls)
			sync_log_doc.save(ignore_permissions=True)

		# Purge CDN cache for uploaded files
		if uploaded_urls and settings.cloudflare_zone_id and settings.get_password('cloudflare_api_token'):
			try:
				from .cdn_uploader import purge_cdn_cache
				
				# Cloudflare API allows max 30 URLs per request, so batch them
				batch_size = 30
				purge_results = []
				
				for i in range(0, len(uploaded_urls), batch_size):
					url_batch = uploaded_urls[i:i + batch_size]
					purge_result = purge_cdn_cache(
						settings.cloudflare_zone_id,
						settings.get_password('cloudflare_api_token'),
						url_batch
					)
					purge_results.append(purge_result)
				
				# Log cache purge results
				frappe.log_error(
					f"[INFO] Cache purge completed for {len(uploaded_urls)} files in plan {plan_id}",
					"CDN Plan Rebuild"
				)
				
			except Exception as e:
				frappe.log_error(f"Cache purge failed for plan {plan_id}: {str(e)}", "CDN Cache Purge Failed")
				# Don't fail the build if cache purge fails - content is still updated

		return True

	except Exception as e:
		import traceback
		from pymysql.err import OperationalError

		# Enhanced error logging for debugging (User Story 1)
		error_type = type(e).__name__
		error_message = str(e)
		full_traceback = traceback.format_exc()

		# Build detailed error context
		error_context = f"""Plan rebuild failed for plan: {plan_id}

Error Type: {error_type}
Error Message: {error_message}

Full Traceback:
{full_traceback}
"""

		# For OperationalError (SQL errors), include additional SQL context
		if isinstance(e, OperationalError):
			# Try to extract SQL query information from the error
			error_context += f"""
SQL Error Details:
- This is a database OperationalError (likely a SQL query issue)
- Error code: {e.args[0] if e.args else 'N/A'}
- Error message: {e.args[1] if len(e.args) > 1 else 'N/A'}

Diagnostic Suggestion:
Use the diagnostic tools to identify the failing query:
1. Call diagnose_query_failure() for involved DocTypes
2. Run validate_schema() to check for missing database columns
3. Check Error Log for full SQL query details
"""

		# Log to Error Log DocType with title "CDN Plan Rebuild Error"
		frappe.log_error(error_context, "CDN Plan Rebuild Error")

		return False

def trigger_plan_rebuild(doctype, docname):
	"""
	Trigger a plan rebuild when content is changed.

	Args:
		doctype (str): The DocType that was changed
		docname (str): The document name that was changed
	"""
	try:
		frappe.log_error(
			f"[INFO] Rebuilding {doctype}/{docname}",
			"CDN Plan Rebuild"
		)

		# Get affected plans
		affected_plans = get_affected_plan_ids(doctype, docname)

		if not affected_plans:
			frappe.log_error(
				f"[WARN] No affected plans found for {doctype}/{docname}",
				"CDN Plan Rebuild"
			)
			return

		frappe.log_error(
			f"[INFO] Found {len(affected_plans)} affected plans for {doctype}/{docname}: {affected_plans}",
			"CDN Plan Rebuild"
		)

		# Check if we should process immediately (local_fallback_mode)
		settings = frappe.get_single("CDN Settings")
		local_fallback_mode = getattr(settings, 'local_fallback_mode', 0)

		if local_fallback_mode:
			# LOCAL FALLBACK MODE: Process immediately, bypass queue
			frappe.log_error(
				f"[INFO] Local fallback mode enabled - processing {len(affected_plans)} plans immediately (bypassing queue)",
				"CDN Plan Rebuild"
			)

			for plan_id in affected_plans:
				try:
					frappe.log_error(
						f"[INFO] Immediate rebuild starting for plan {plan_id}",
						"CDN Plan Rebuild"
					)
					success = _rebuild_plan(plan_id)
					if success:
						frappe.log_error(
							f"[INFO] Immediate rebuild succeeded for plan {plan_id}",
							"CDN Plan Rebuild"
						)
					else:
						frappe.log_error(
							f"[ERROR] Immediate rebuild failed for plan {plan_id}",
							"CDN Plan Rebuild Error"
						)
				except Exception as e:
					frappe.log_error(
						f"[ERROR] Exception during immediate rebuild for plan {plan_id}: {str(e)}",
						"CDN Plan Rebuild Error"
					)

			return  # Exit early - don't use queue at all

		# NORMAL MODE: Add to queue for batch processing
		# Add all affected plans to queue
		for plan_id in affected_plans:
			add_plan_to_queue(plan_id)

		# Check threshold and trigger immediate processing if needed
		threshold = getattr(settings, 'batch_threshold', 50)

		current_queue_size = frappe.cache().scard("cdn_export:pending_plans") or 0
		frappe.log_error(
			f"[INFO] Queue size after adding plans: {current_queue_size}, threshold: {threshold}",
			"CDN Plan Rebuild"
		)

		if current_queue_size >= threshold:
			# Process immediately if threshold reached
			frappe.log_error(
				f"[INFO] Threshold reached ({current_queue_size} >= {threshold}), processing immediately",
				"CDN Plan Rebuild"
			)
			process_pending_plans(1)  # Process just one to reduce queue

	except Exception as e:
		log_error(f"Failed to trigger plan rebuild for {doctype}/{docname}: {str(e)}", "CDN Plan Rebuild Failed")

def validate_json_schema(json_data, schema_name):
    """
    Validate JSON data against a JSON schema from the schemas directory.

    Args:
        json_data (dict): JSON data to validate
        schema_name (str): Name of the schema file (e.g., 'lesson.schema.json')

    Returns:
        tuple: (is_valid, errors) where is_valid is bool and errors is list of error messages
    """
    if not JSONSCHEMA_AVAILABLE:
        return True, []

    schema_path = os.path.join(SCHEMA_DIR, schema_name)

    if not os.path.exists(schema_path):
        log_error(f"Schema file not found: {schema_path}", "Schema Validation Error")
        return False, [f"Schema file not found: {schema_path}"]

    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)

        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(json_data))

        if errors:
            error_messages = []
            for error in errors:
                error_messages.append(f"{' -> '.join(str(p) for p in error.path)}: {error.message}")
            return False, error_messages

        return True, []

    except Exception as e:
        log_error(f"Schema validation failed: {str(e)}", "Schema Validation Error")
        return False, [str(e)]

def validate_all_json_files(files_data):
    """
    Validate all JSON files against their respective schemas.

    Args:
        files_data (dict): Dictionary of {path: json_data} to validate

    Returns:
        dict: Validation results with 'valid' flag and 'errors' dictionary
    """
    validation_results = {
        'valid': True,
        'errors': {},
        'valid_count': 0,
        'invalid_count': 0
    }

    schema_mapping = {
        'manifest.json': 'manifest.schema.json',
        'subject.json': 'subject.schema.json',
        'unit.json': 'unit.schema.json',
        'lesson.json': 'lesson.schema.json',
        'search_index.json': 'search_index.schema.json'
    }

    for path, json_data in files_data.items():
        schema_name = None
        for key, schema in schema_mapping.items():
            if key in path:
                schema_name = schema
                break

        if not schema_name:
            continue

        is_valid, errors = validate_json_schema(json_data, schema_name)

        if is_valid:
            validation_results['valid_count'] += 1
        else:
            validation_results['valid'] = False
            validation_results['invalid_count'] += 1
            validation_results['errors'][path] = errors

    return validation_results

def get_queue_status():
    """
    Get current queue status for monitoring.

    Returns:
        dict: Queue status information
    """
    try:
        redis_queue_size = frappe.cache().scard("cdn_export:pending_plans") or 0

        # Get dead letter count
        dead_letter_count = frappe.cache().hlen("cdn_export:dead_letter") or 0

        # Get recent failures
        recent_failures = frappe.get_all(
            "CDN Sync Log",
            filters={
                "status": ["in", ["Failed", "Dead Letter"]],
                "creation": [">", frappe.utils.add_to_date(now_datetime(), -1, "day")]
            },
            fields=["plan_id", "status", "error_message", "creation"],
            limit=10,
            order_by="creation desc"
        )

        return {
            'pending_plans': redis_queue_size,
            'dead_letter_count': dead_letter_count,
            'recent_failures': recent_failures,
            'last_processed': now_datetime().isoformat()
        }

    except Exception as e:
        log_error(f"Failed to get queue status: {str(e)}")
        return {
            'error': str(e),
            'pending_plans': 0,
            'dead_letter_count': 0,
            'recent_failures': []
        }