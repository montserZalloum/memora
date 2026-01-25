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
from .json_generator import get_content_paths_for_plan
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
        if not settings.enabled:
            return True  # Not an error, just disabled

        # Get CDN client
        client = get_cdn_client(settings)
        bucket = settings.bucket_name

        # Generate all files for this plan (also writes to local storage)
        files_data = get_content_paths_for_plan(plan_id)

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
                frappe.logger.info(f"Cache purge completed for {len(uploaded_urls)} files in plan {plan_id}")
                
            except Exception as e:
                frappe.log_error(f"Cache purge failed for plan {plan_id}: {str(e)}", "CDN Cache Purge Failed")
                # Don't fail the build if cache purge fails - content is still updated

        return True

    except Exception as e:
        log_error(f"Plan rebuild failed for {plan_id}: {str(e)}", "CDN Plan Rebuild Failed")
        return False

def trigger_plan_rebuild(doctype, docname):
    """
    Trigger a plan rebuild when content is changed.

    Args:
        doctype (str): The DocType that was changed
        docname (str): The document name that was changed
    """
    try:
        # Get affected plans
        affected_plans = get_affected_plan_ids(doctype, docname)

        if not affected_plans:
            return

        # Add all affected plans to queue
        for plan_id in affected_plans:
            add_plan_to_queue(plan_id)

        # Check threshold and trigger immediate processing if needed
        settings = frappe.get_single("CDN Settings")
        threshold = getattr(settings, 'batch_threshold', 50)

        current_queue_size = frappe.cache().scard("cdn_export:pending_plans") or 0
        if current_queue_size >= threshold:
            # Process immediately if threshold reached
            process_pending_plans(1)  # Process just one to reduce queue

    except Exception as e:
        log_error(f"Failed to trigger plan rebuild for {doctype}/{docname}: {str(e)}")

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