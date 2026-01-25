"""
Health Checker for CDN Export.

Monitors the health of local storage and CDN sync.
"""
import frappe
import os
import random
from datetime import datetime
from .local_storage import check_disk_space, get_local_base_path, file_exists


def is_business_hours():
    """
    Check if current time is within business hours.
    
    Business hours: 8am-6pm (08:00-18:00), Monday-Friday
    
    Returns:
        bool: True if within business hours, False otherwise
    """
    now = datetime.now()
    return 8 <= now.hour < 18 and now.weekday() < 5


def hourly_health_check():
    """
    Quick health check for scheduler (business hours only).
    
    Behavior:
    1. Skip if outside business hours (8am-6pm Mon-Fri)
    2. Check disk space
    3. Sample 100 random files for existence
    4. Send alert if disk space below 10%
    
    Returns:
        dict: Health check report
    """
    # Skip if outside business hours
    if not is_business_hours():
        return {
            'timestamp': datetime.now().isoformat(),
            'skipped': True,
            'reason': 'Outside business hours',
            'status': 'skipped'
        }
    
    # Check disk space
    disk_ok, disk_free_percent = check_disk_space()
    
    # Alert if disk space is critical
    if not disk_ok:
        send_disk_alert(disk_free_percent)
    
    # Sample random files
    sample_result = _sample_random_files(100)
    
    # Determine overall status
    status = 'healthy'
    if not disk_ok:
        status = 'critical'
    elif sample_result['missing']:
        status = 'warning'
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'disk_free_percent': disk_free_percent,
        'disk_ok': disk_ok,
        'sample_files_checked': sample_result['sampled'],
        'missing_files': sample_result['missing'],
        'status': status
    }
    
    # Log the health check
    frappe.logger.info(f"Hourly health check: {status} - Disk: {disk_free_percent:.1f}% - Missing: {len(sample_result['missing'])}")
    
    return report


def daily_full_scan():
    """
    Comprehensive filesystem scan.
    
    Behavior:
    1. Check disk space
    2. Query all expected files from database
    3. Verify each file exists
    4. Identify orphan files
    5. Queue regeneration for missing files
    6. Send alert if disk space below 10%
    
    Returns:
        dict: Full scan report
    """
    # Check disk space
    disk_ok, disk_free_percent = check_disk_space()
    
    # Alert if disk space is critical
    if not disk_ok:
        send_disk_alert(disk_free_percent)
    
    # Get expected files from database
    expected_files = _get_expected_files_from_db()
    
    # Verify files exist
    missing_files = _verify_files_exist(expected_files)
    
    # Find orphan files (files that exist but have no database record)
    orphan_files = _find_orphan_files(expected_files)
    
    # Queue regeneration for missing files
    if missing_files:
        _queue_regeneration_for_missing_files(missing_files)
    
    # Determine overall status
    status = 'healthy'
    if not disk_ok:
        status = 'critical'
    elif missing_files or orphan_files:
        status = 'warning'
    
    # Determine action taken
    action_taken = None
    if missing_files:
        action_taken = f'Queued regeneration for {len(missing_files)} missing files'
    elif orphan_files:
        action_taken = f'Found {len(orphan_files)} orphan files'
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'disk_free_percent': disk_free_percent,
        'disk_ok': disk_ok,
        'total_files_expected': len(expected_files),
        'total_files_found': len(expected_files) - len(missing_files),
        'missing_files': missing_files,
        'orphan_files': orphan_files,
        'status': status,
        'action_taken': action_taken
    }
    
    # Log the scan
    frappe.logger.info(
        f"Daily scan: {status} - Disk: {disk_free_percent:.1f}% - "
        f"Expected: {len(expected_files)} - Missing: {len(missing_files)} - Orphans: {len(orphan_files)}"
    )
    
    return report


def send_disk_alert(free_percent):
    """
    Send disk space alert to System Managers.
    
    Parameters:
        free_percent (float): Current free disk percentage
    """
    subject = f"[Memora] Low Disk Space Warning: {free_percent:.1f}% remaining"
    message = f"""
    Disk space on the server is critically low ({free_percent:.1f}% remaining).

    Content generation has been paused to prevent data corruption.

    Please free up disk space and manually resume operations.
    
    System: {frappe.local.site if hasattr(frappe, 'local') else 'unknown'}
    """
    
    # Get system managers
    system_managers = frappe.get_all(
        "Has Role",
        filters={"role": "System Manager", "parenttype": "User"},
        pluck="parent"
    )
    
    for user in system_managers:
        # Send email
        frappe.sendmail(
            recipients=[user],
            subject=subject,
            message=message
        )
        
        # Send in-app notification
        frappe.publish_realtime(
            event="msgprint",
            message=subject,
            user=user
        )
    
    frappe.logger.error(f"Disk space alert sent: {free_percent:.1f}% remaining")


def send_sync_failure_alert(sync_log_name):
    """
    Send alert when CDN sync retries are exhausted.
    
    Parameters:
        sync_log_name (str): CDN Sync Log document name
    """
    sync_log = frappe.get_doc("CDN Sync Log", sync_log_name)
    subject = f"[Memora] CDN Sync Failed: {sync_log.plan_id} (Dead Letter)"
    message = f"""
    CDN sync for plan {sync_log.plan_id} has failed after {sync_log.retry_count} retry attempts.
    
    Sync Log: {sync_log_name}
    Plan: {sync_log.plan_id}
    Error: {sync_log.error_message or 'Unknown error'}
    
    The sync has been marked as Dead Letter. Please investigate manually.
    
    System: {frappe.local.site if hasattr(frappe, 'local') else 'unknown'}
    """
    
    # Get system managers
    system_managers = frappe.get_all(
        "Has Role",
        filters={"role": "System Manager", "parenttype": "User"},
        pluck="parent"
    )
    
    for user in system_managers:
        # Send email
        frappe.sendmail(
            recipients=[user],
            subject=subject,
            message=message
        )
        
        # Send in-app notification
        frappe.publish_realtime(
            event="msgprint",
            message=subject,
            user=user
        )
    
    frappe.logger.error(f"Sync failure alert sent for {sync_log_name}")


def _sample_random_files(sample_count=100):
    """
    Sample random files from local storage for health check.
    
    Parameters:
        sample_count (int): Number of files to sample
    
    Returns:
        dict: {'sampled': int, 'missing': list}
    """
    base_path = get_local_base_path()
    
    if not os.path.exists(base_path):
        return {'sampled': 0, 'missing': []}
    
    # Collect all JSON files
    all_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.json') and not file.endswith('.prev'):
                rel_path = os.path.relpath(os.path.join(root, file), base_path)
                all_files.append(rel_path)
    
    # Sample random files
    if len(all_files) <= sample_count:
        sampled_files = all_files
    else:
        sampled_files = random.sample(all_files, sample_count)
    
    # Check which files are missing
    missing_files = []
    for file_path in sampled_files:
        if not file_exists(file_path):
            missing_files.append(file_path)
    
    return {'sampled': len(sampled_files), 'missing': missing_files}


def _get_expected_files_from_db():
    """
    Query database to get list of expected files.
    
    Returns:
        list: List of relative file paths expected to exist
    """
    expected_files = []
    
    # Get all published plans
    plans = frappe.get_all(
        "Memora Academic Plan",
        filters={"published": 1},
        pluck="name"
    )
    
    for plan_id in plans:
        # Add manifest.json
        expected_files.append(f"plans/{plan_id}/manifest.json")
        
        # Add search index
        expected_files.append(f"plans/{plan_id}/search_index.json")
        
        # Get subjects for this plan
        plan_doc = frappe.get_doc("Memora Academic Plan", plan_id)
        for subject_row in plan_doc.subjects:
            subject_id = subject_row.subject
            
            # Add subject file
            expected_files.append(f"plans/{plan_id}/subjects/{subject_id}.json")
            
            # Add search entry
            expected_files.append(f"plans/{plan_id}/search/{subject_id}.json")
            
            # Get tracks for this subject
            subject_doc = frappe.get_doc("Memora Subject", subject_id)
            for track in subject_doc.tracks:
                track_id = track.track
                
                # Get units for this track
                track_doc = frappe.get_doc("Memora Track", track_id)
                for unit in track_doc.units:
                    unit_id = unit.unit
                    expected_files.append(f"units/{unit_id}.json")
                    
                    # Get lessons for this unit
                    unit_doc = frappe.get_doc("Memora Unit", unit_id)
                    for lesson in unit_doc.lessons:
                        lesson_id = lesson.lesson
                        expected_files.append(f"lessons/{lesson_id}.json")
    
    return expected_files


def _verify_files_exist(expected_files):
    """
    Check which expected files actually exist on filesystem.
    
    Parameters:
        expected_files (list): List of file paths to check
    
    Returns:
        list: List of missing file paths
    """
    missing_files = []
    
    for file_path in expected_files:
        if not file_exists(file_path):
            missing_files.append(file_path)
    
    return missing_files


def _find_orphan_files(expected_files):
    """
    Find files that exist on filesystem but have no database record.
    
    Parameters:
        expected_files (list): List of expected file paths
    
    Returns:
        list: List of orphan file paths
    """
    base_path = get_local_base_path()
    orphan_files = []
    
    if not os.path.exists(base_path):
        return orphan_files
    
    # Convert expected files to set for faster lookup
    expected_set = set(expected_files)
    
    # Collect all JSON files from filesystem
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.json') and not file.endswith('.prev'):
                rel_path = os.path.relpath(os.path.join(root, file), base_path)
                
                # Check if file is not in expected set
                if rel_path not in expected_set:
                    orphan_files.append(rel_path)
    
    return orphan_files


def _queue_regeneration_for_missing_files(missing_files):
    """
    Queue regeneration for missing files.
    
    This extracts plan IDs from missing file paths and adds them to the CDN export queue.
    
    Parameters:
        missing_files (list): List of missing file paths
    """
    from .change_tracker import add_plan_to_queue
    
    # Extract unique plan IDs from missing file paths
    plan_ids = set()
    for file_path in missing_files:
        # Parse plan ID from path
        # Expected format: plans/{plan_id}/...
        parts = file_path.split('/')
        if len(parts) >= 2 and parts[0] == 'plans':
            plan_ids.add(parts[1])
    
    # Add plans to queue for regeneration
    for plan_id in plan_ids:
        add_plan_to_queue(plan_id)
    
    frappe.logger.info(f"Queued regeneration for {len(plan_ids)} plans due to missing files")
