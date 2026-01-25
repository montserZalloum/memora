"""
CDN Admin API Endpoints
Provides monitoring and management endpoints for CDN export operations.
"""

import frappe
from frappe.utils import now_datetime, add_to_date
from frappe.decorators import frappe_method


@frappe.whitelist()
def get_queue_status():
    """
    Get current queue status for monitoring dashboard.

    Returns:
        dict: Queue status with pending plans, dead letter count, and recent failures
    """
    try:
        from memora.services.cdn_export.batch_processor import get_queue_status as get_bp_status

        # Get queue status from batch processor
        status = get_bp_status()

        # Verify user has admin permissions
        frappe.only_for("System Manager")

        return status

    except Exception as e:
        frappe.log_error(f"Failed to get queue status: {str(e)}")
        return {
            'error': str(e),
            'pending_plans': 0,
            'dead_letter_count': 0,
            'recent_failures': []
        }


@frappe.whitelist()
def get_recent_failures(limit=20, days=7):
    """
    Get recent sync failures for dashboard display.

    Args:
        limit (int): Maximum number of failures to return
        days (int): Number of days to look back

    Returns:
        list: List of failed sync log entries
    """
    try:
        # Verify user has admin permissions
        frappe.only_for("System Manager")

        limit = int(limit)
        days = int(days)

        # Query recent failures
        failures = frappe.get_all(
            "CDN Sync Log",
            filters={
                "status": ["in", ["Failed", "Dead Letter"]],
                "creation": [">", add_to_date(now_datetime(), -days, "days")]
            },
            fields=[
                "name",
                "plan_id",
                "status",
                "error_message",
                "retry_count",
                "creation",
                "completed_at"
            ],
            limit=limit,
            order_by="creation desc"
        )

        return failures

    except Exception as e:
        frappe.log_error(f"Failed to get recent failures: {str(e)}")
        return []


@frappe.whitelist()
def retry_dead_letter(sync_log_name):
    """
    Manually retry a dead letter queue item.

    Args:
        sync_log_name (str): Name of the CDN Sync Log document

    Returns:
        dict: Result of retry operation
    """
    try:
        # Verify user has admin permissions
        frappe.only_for("System Manager")

        # Get the sync log
        sync_log = frappe.get_doc("CDN Sync Log", sync_log_name)

        if sync_log.status != "Dead Letter":
            return {
                'success': False,
                'message': 'Only dead letter items can be manually retried'
            }

        plan_id = sync_log.plan_id

        # Reset the sync log for retry
        sync_log.status = "Queued"
        sync_log.retry_count = 0
        sync_log.started_at = None
        sync_log.completed_at = None
        sync_log.error_message = None
        sync_log.triggered_by = "Manual"
        sync_log.save(ignore_permissions=True)

        # Add plan back to queue
        from memora.services.cdn_export.change_tracker import add_plan_to_fallback_queue
        add_plan_to_fallback_queue(plan_id)

        return {
            'success': True,
            'message': f'Plan {plan_id} queued for retry'
        }

    except Exception as e:
        frappe.log_error(f"Failed to retry dead letter item {sync_log_name}: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }


@frappe.whitelist()
def get_sync_history(plan_id=None, limit=50):
    """
    Get sync history for a specific plan or all plans.

    Args:
        plan_id (str): Optional plan ID to filter by
        limit (int): Maximum number of records to return

    Returns:
        list: List of sync log entries
    """
    try:
        # Verify user has admin permissions
        frappe.only_for("System Manager")

        filters = {}
        if plan_id:
            filters['plan_id'] = plan_id

        history = frappe.get_all(
            "CDN Sync Log",
            filters=filters,
            fields=[
                "name",
                "plan_id",
                "status",
                "started_at",
                "completed_at",
                "files_uploaded",
                "files_deleted",
                "error_message",
                "retry_count",
                "triggered_by",
                "creation"
            ],
            limit=int(limit),
            order_by="creation desc"
        )

        return history

    except Exception as e:
        frappe.log_error(f"Failed to get sync history: {str(e)}")
        return []


@frappe.whitelist()
def clear_dead_letter(plan_id=None):
    """
    Clear dead letter entries for a specific plan or all plans.

    Args:
        plan_id (str): Optional plan ID to filter by

    Returns:
        dict: Result of operation
    """
    try:
        # Verify user has admin permissions
        frappe.only_for("System Manager")

        filters = {"status": "Dead Letter"}
        if plan_id:
            filters['plan_id'] = plan_id

        # Get all dead letter items
        dead_letters = frappe.get_all(
            "CDN Sync Log",
            filters=filters,
            fields=["name"]
        )

        # Delete them
        deleted_count = 0
        for doc in dead_letters:
            try:
                frappe.delete_doc("CDN Sync Log", doc['name'], ignore_permissions=True)
                deleted_count += 1
            except Exception as e:
                frappe.log_error(f"Failed to delete dead letter {doc['name']}: {str(e)}")

        return {
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Cleared {deleted_count} dead letter items'
        }

    except Exception as e:
        frappe.log_error(f"Failed to clear dead letter: {str(e)}")
        return {
            'success': False,
            'message': str(e)
        }
