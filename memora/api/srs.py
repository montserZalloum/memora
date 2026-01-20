"""
SRS/Memory Algorithms Module

This module implements Spaced Repetition System algorithms for memory tracking.
All functions in this module are internal helpers (not public API).
"""

import frappe
from frappe.utils import add_days, now_datetime, cint
from memora.services.srs_archiver import SRSArchiver


def process_srs_batch(user, interactions, subject=None, topic=None):
    """
    Process a batch of interactions to update memory.

    Receives 'subject' to pass to the final function.

    Args:
        user: User ID
        interactions: List of interaction objects
        subject: Optional subject ID
        topic: Optional topic ID
    """
    for item in interactions:
        atom_id = item.get("question_id")
        if not atom_id: continue
        duration = item.get("duration_ms", item.get("time_spent_ms", 3000))
        attempts = item.get("attempts_count", 1)
        rating = infer_rating(duration, attempts)
        next_review_date = calculate_next_review(rating)

        # ✅ Pass topic
        update_memory_tracker(user, atom_id, rating, next_review_date, subject, topic)


def infer_rating(duration_ms, attempts):
    """
    Logic: Converts Time + Accuracy into a Memory Score.

    Ratings:
    1 = AGAIN (Fail) - Wrong answer, needs immediate drill.
    2 = HARD         - Correct but slow (> 5s).
    3 = GOOD         - Correct and steady (2s - 5s).
    4 = EASY         - Correct and instant (< 2s).
    """
    # If the user made a mistake (attempts > 1), it's a FAIL regardless of time.
    if attempts > 1:
        return 1

    # If correct on first try, judge by speed:
    if duration_ms < 2000:  # Less than 2 seconds
        return 4  # EASY

    if duration_ms < 5000:  # Less than 5 seconds
        return 3  # GOOD

    # More than 5 seconds
    return 2  # HARD


def calculate_next_review(rating):
    """
    Logic: Determines how many days to wait before the next review.

    Current Protocol (Fixed Intervals):
    1 (Fail) -> 0 Days (Review Tomorrow/ASAP)
    2 (Hard) -> 2 Days
    3 (Good) -> 4 Days
    4 (Easy) -> 7 Days
    """
    interval_map = {
        1: 0,  # Fail: Reset
        2: 2,  # Hard
        3: 4,  # Good
        4: 7   # Easy
    }

    days_to_add = interval_map.get(rating, 1)  # Default to 1 day if error

    # Return the actual DateTime object
    return add_days(now_datetime(), days_to_add)


def update_memory_tracker(user, atom_id, rating, next_date, subject=None, topic=None):
    """
    Update or create memory tracker record for a question.

    Args:
        user: User ID
        atom_id: Question ID
        rating: Memory score (1-4)
        next_date: Next review datetime
        subject: Optional subject ID
        topic: Optional topic ID
    """
    existing_tracker = frappe.db.get_value("Player Memory Tracker",
        {"player": user, "question_id": atom_id}, "name")

    values = {
        "stability": rating,
        "last_review_date": now_datetime(),
        "next_review_date": next_date
    }
    if subject: values["subject"] = subject
    if topic: values["topic"] = topic  # ✅ Save topic on update

    if existing_tracker:
        frappe.db.set_value("Player Memory Tracker", existing_tracker, values)
    else:
        doc = frappe.get_doc({
            "doctype": "Player Memory Tracker",
            "player": user,
            "question_id": atom_id,
            "subject": subject,
            "topic": topic,  # ✅ Save topic on creation
            "stability": rating,
            "last_review_date": now_datetime(),
            "next_review_date": next_date
        })
        doc.insert(ignore_permissions=True)


def create_memory_tracker(user, atom_id, rating):
    """
    Create a new memory tracker record for a question.

    Called when student sees the question for the first time,
    or when discovering a new ID.

    Args:
        user: User ID
        atom_id: Question ID
        rating: Initial memory score (1-4)

    Returns:
        Name of created tracker record
    """
    # Determine next review date based on initial rating
    # 1: tomorrow, 2: 3 days, 3: week, 4: 2 weeks
    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days = interval_map.get(rating, 1)  # Default to one day

    doc = frappe.get_doc({
        "doctype": "Player Memory Tracker",
        "player": user,
        "question_id": atom_id,  # Ensure this matches the DocType field name
        "stability": rating,
        "last_review_date": now_datetime(),
        "next_review_date": add_days(now_datetime(), days)
    })

    doc.insert(ignore_permissions=True)
    return doc.name


def update_srs_after_review(user, question_id, is_correct, duration_ms, subject=None, topic=None):
    """
    Update memory tracker status after review session.

    Fixed variable count (added topic) and removed duplicate logic.

    Args:
        user: User ID
        question_id: Question ID
        is_correct: Whether answer was correct
        duration_ms: Time taken to answer
        subject: Optional subject ID
        topic: Optional topic ID
    """
    # 1. Fetch current record
    tracker_name = frappe.db.get_value("Player Memory Tracker",
        {"player": user, "question_id": question_id}, "name")

    current_stability = 0
    if tracker_name:
        current_stability = cint(frappe.db.get_value("Player Memory Tracker", tracker_name, "stability"))

    # 2. Rating algorithm (Speed Bonus)
    new_stability = current_stability

    if is_correct:
        if duration_ms < 2000:
            new_stability = min(current_stability + 2, 4)  # Very fast
        elif duration_ms > 6000:
            new_stability = max(current_stability, 1)  # Slow
        else:
            new_stability = min(current_stability + 1, 4)  # Normal

        if new_stability < 1: new_stability = 1
    else:
        new_stability = 1  # Error

    # 3. Calculate next date
    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days_to_add = interval_map.get(new_stability, 1)
    new_date = add_days(now_datetime(), days_to_add)

    # 4. Storage (once and correctly)
    # Pass topic to helper function
    update_memory_tracker(user, question_id, new_stability, new_date, subject, topic)

    # 5. Cleanup parent records
    if ":" in question_id:
        parent_id = question_id.rsplit(":", 1)[0]
        parent_tracker = frappe.db.get_value("Player Memory Tracker",
            {"player": user, "question_id": parent_id}, "name")

        if parent_tracker:
            frappe.db.set_value("Player Memory Tracker", parent_tracker,
                "next_review_date", new_date)


# =========================================================
# User Story 4: Archive API Endpoints
# =========================================================

@frappe.whitelist()
def archive_season(season_name: str, confirm: bool = False):
    """
    Archive a season's data to cold storage (T060)

    This endpoint requires explicit confirmation to prevent accidental archiving.
    It copies all Player Memory Tracker records to Archived Memory Tracker,
    deletes original records, and clears Redis cache.

    Args:
        season_name: Name of season to archive
        confirm: Must be True to proceed with archiving

    Returns:
        dict: Result with success status and archived_count

    Raises:
        PermissionError: If user doesn't have System Manager role
        ValueError: If season is active or doesn't exist
    """
    # Check permissions (System Manager only)
    if not frappe.has_permission("Game Subscription Season", "write"):
        frappe.throw(
            "You don't have permission to archive seasons. "
            "This action requires System Manager role.",
            frappe.PermissionError
        )

    # Require explicit confirmation
    if not confirm:
        frappe.throw(
            "Confirmation required. Set confirm=True to proceed with archiving.",
            ValueError
        )

    # Initialize archiver
    archiver = SRSArchiver()

    # Perform archiving
    result = archiver.archive_season(season_name)

    if result.get("success"):
        frappe.msgprint(
            f"Successfully archived {result.get('archived_count', 0)} records "
            f"for season {season_name}",
            alert=True,
            indicator="green"
        )
    else:
        frappe.msgprint(
            f"Failed to archive season: {result.get('error', 'Unknown error')}",
            alert=True,
            indicator="red"
        )

    return result


@frappe.whitelist()
def get_archive_status(season_name: str):
    """
    Get archive status for a season

    Returns information about active and archived records for a season.

    Args:
        season_name: Name of season

    Returns:
        dict: Archive status with counts and metadata
    """
    # Check permissions
    if not frappe.has_permission("Game Subscription Season", "read"):
        frappe.throw(
            "You don't have permission to view archive status.",
            frappe.PermissionError
        )

    archiver = SRSArchiver()
    result = archiver.get_archive_status(season_name)

    return result


@frappe.whitelist()
def delete_eligible_archived_records(season_name: str = None, confirm: bool = False):
    """
    Delete archived records marked for deletion

    This is a destructive operation and requires explicit confirmation.
    Only records older than 3 years can be deleted.

    Args:
        season_name: Optional season filter (if None, deletes all eligible records)
        confirm: Must be True to proceed with deletion

    Returns:
        dict: Result with success status and deleted_count

    Raises:
        PermissionError: If user doesn't have System Manager role
        ValueError: If confirmation not provided
    """
    # Check permissions (System Manager only)
    if not frappe.has_permission("Archived Memory Tracker", "delete"):
        frappe.throw(
            "You don't have permission to delete archived records. "
            "This action requires System Manager role.",
            frappe.PermissionError
        )

    # Require explicit confirmation
    if not confirm:
        frappe.throw(
            "Confirmation required. Set confirm=True to proceed with deletion.",
            ValueError
        )

    # Initialize archiver
    archiver = SRSArchiver()

    # Perform deletion
    result = archiver.delete_eligible_records(season_name, confirm=True)

    if result.get("success"):
        frappe.msgprint(
            f"Successfully deleted {result.get('deleted_count', 0)} archived records",
            alert=True,
            indicator="green"
        )
    else:
        frappe.msgprint(
            f"Failed to delete records: {result.get('error', 'Unknown error')}",
            alert=True,
            indicator="red"
        )

    return result


# =========================================================
# User Story 5: Admin Monitoring & Cache Management
# =========================================================

@frappe.whitelist()
def get_cache_status() -> dict:
    """
    Get cache health and statistics (T071)

    Returns Redis connectivity status, memory usage, and key counts
    by season. Useful for monitoring dashboard.

    Returns:
        dict: Cache status with:
        - redis_connected: bool - Whether Redis is available
        - is_safe_mode: bool - Whether Safe Mode is active
        - memory_used_mb: float - Total Redis memory usage in MB
        - total_keys: int - Total number of SRS cache keys
        - keys_by_season: dict - Key counts per season
    """
    from memora.services.srs_redis_manager import SRSRedisManager
    from memora.api.utils import SafeModeManager

    redis_manager = SRSRedisManager()

    # Check Redis connectivity
    redis_connected = redis_manager.is_available()
    is_safe_mode = SafeModeManager.is_safe_mode_active()

    # Get memory usage
    memory_used_mb = 0.0
    if redis_connected:
        try:
            memory_used_bytes = redis_manager.redis.info("memory").get("used_memory", 0)
            memory_used_mb = memory_used_bytes / (1024 * 1024)
        except Exception:
            memory_used_mb = 0.0

    # Count total SRS keys (pattern: srs:*)
    total_keys = 0
    keys_by_season = {}

    if redis_connected:
        try:
            cursor = 0
            pattern = "srs:*"
            while True:
                cursor, keys = redis_manager.redis.scan(
                    cursor, match=pattern, count=1000
                )
                total_keys += len(keys)

                # Count by season
                for key in keys:
                    # Extract season from key (format: srs:user:season)
                    parts = key.split(":")
                    if len(parts) == 3:
                        season = parts[2]
                        keys_by_season[season] = keys_by_season.get(season, 0) + 1

                if cursor == 0:
                    break
        except Exception as e:
            frappe.log_error(
                f"Failed to count Redis keys: {str(e)}",
                "get_cache_status"
            )

    return {
        "redis_connected": redis_connected,
        "is_safe_mode": is_safe_mode,
        "memory_used_mb": round(memory_used_mb, 2),
        "total_keys": total_keys,
        "keys_by_season": keys_by_season
    }


@frappe.whitelist()
def rebuild_season_cache(season_name: str) -> dict:
    """
    Trigger full cache rebuild for a season (T072)

    This is an administrative utility to rebuild Redis cache for an
    entire season. Runs as background job with progress tracking.
    Requires System Manager role.

    Args:
        season_name: Name of season to rebuild

    Returns:
        dict: Result with:
        - status: "started" or "error"
        - job_id: Background job ID
        - estimated_records: Number of records to process

    Raises:
        PermissionError: If user doesn't have System Manager role
        ValueError: If season doesn't exist
    """
    # Check permissions (System Manager only)
    if not frappe.has_permission("Game Subscription Season", "write"):
        frappe.throw(
            "You don't have permission to rebuild cache. "
            "This action requires System Manager role.",
            frappe.PermissionError
        )

    # Validate season exists
    season_exists = frappe.db.exists("Game Subscription Season", season_name)
    if not season_exists:
        frappe.throw(
            f"Season '{season_name}' not found.",
            ValueError
        )

    # Get estimated record count
    estimated_records = frappe.db.count(
        "Player Memory Tracker",
        filters={"season": season_name}
    )

    # Enqueue background job
    from memora.services.srs_redis_manager import rebuild_season_cache as rebuild_func

    job = frappe.enqueue(
        "memora.services.srs_redis_manager.rebuild_season_cache",
        queue="srs_write",
        job_name=f"cache_rebuild_{season_name}_{frappe.utils.now()}",
        season_name=season_name,
        enqueue_after_commit=True
    )

    frappe.msgprint(
        f"Cache rebuild job started for {season_name}. "
        f"Estimated {estimated_records:,} records to process.",
        alert=True,
        indicator="blue"
    )

    return {
        "status": "started",
        "job_id": job.id,
        "estimated_records": estimated_records
    }


@frappe.whitelist()
def trigger_reconciliation(sample_size: int = 10000, season: str = None) -> dict:
    """
    Trigger manual cache-DB reconciliation (T073)

    Runs reconciliation check immediately instead of waiting for scheduled job.
    Returns discrepancy report with auto-correction applied.

    Args:
        sample_size: Number of records to sample (default: 10000)
        season: Optional - limit to specific season

    Returns:
        dict: Reconciliation results with:
        - sample_size: Number of records sampled
        - discrepancies_found: Number of discrepancies detected
        - discrepancy_rate: Percentage of discrepancies (0-1)
        - auto_corrected: Number of records auto-corrected
        - alert_triggered: Whether alert threshold was exceeded

    Raises:
        PermissionError: If user doesn't have System Manager role
    """
    # Check permissions (System Manager only)
    if not frappe.has_permission("Game Subscription Season", "write"):
        frappe.throw(
            "You don't have permission to trigger reconciliation. "
            "This action requires System Manager role.",
            frappe.PermissionError
        )

    # Validate sample_size
    if sample_size < 100 or sample_size > 100000:
        frappe.throw(
            "Sample size must be between 100 and 100000",
            ValueError
        )

    # If season specified, validate it exists
    if season:
        season_exists = frappe.db.exists("Game Subscription Season", season)
        if not season_exists:
            frappe.throw(
                f"Season '{season}' not found.",
                ValueError
            )

    # Run reconciliation
    from memora.services.srs_reconciliation import reconcile_cache_with_database

    result = reconcile_cache_with_database(sample_size=sample_size)

    # Log result
    if result.get("alert_triggered"):
        frappe.msgprint(
            f"Reconciliation completed with {result.get('discrepancy_rate', 0):.2%} "
            f"discrepancy rate. Alert triggered!",
            alert=True,
            indicator="red"
        )
    else:
        frappe.msgprint(
            f"Reconciliation completed. "
            f"{result.get('discrepancies_found', 0)} discrepancies found, "
            f"{result.get('auto_corrected', 0)} auto-corrected.",
            alert=True,
            indicator="green"
        )

    return result
