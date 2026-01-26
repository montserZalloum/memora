import frappe
from frappe.utils import now_datetime

QUEUE_KEY = "cdn_export:pending_plans"
LOCK_PREFIX = "cdn_export:lock:"
DEAD_LETTER_KEY = "cdn_export:dead_letter"

def add_plan_to_queue(plan_id):
	"""Add plan to rebuild queue (idempotent via Set)."""
	import frappe
	try:
		frappe.cache().sadd(QUEUE_KEY, plan_id)
		queue_size = frappe.cache().scard(QUEUE_KEY) or 0
		frappe.log_error(
			f"[INFO] Added plan {plan_id} to queue. Queue size: {queue_size}",
			"CDN Queue Management"
		)

		# Check threshold and trigger immediate processing if needed
		check_and_trigger_immediate_processing()
	except Exception as e:
		frappe.log_error(f"Redis queue error for plan {plan_id}: {str(e)}", "CDN Queue Error")
		add_plan_to_fallback_queue(plan_id)

def check_and_trigger_immediate_processing():
    """Check if queue size exceeds threshold and trigger immediate processing."""
    try:
        settings = frappe.get_single("CDN Settings")
        threshold = getattr(settings, 'batch_threshold', 50)

        # Get current queue size
        current_size = frappe.cache().scard(QUEUE_KEY) or 0

        if current_size >= threshold:
            # Trigger immediate processing by adding to queue for next scheduler run
            # This ensures the scheduler will process the batch immediately
            frappe.enqueue(
                "memora.services.cdn_export.batch_processor.process_pending_plans",
                timeout=600,  # 10 minutes timeout
                queue='long'
            )

    except Exception as e:
        frappe.log_error(f"Threshold check error: {str(e)}", "CDN Threshold Check Error")


def get_pending_plans(max_count=50):
    """Pop up to max_count plans from queue."""
    plans = []
    try:
        for _ in range(max_count):
            plan_id = frappe.cache().spop(QUEUE_KEY)
            if plan_id is None:
                break
            plans.append(plan_id.decode() if isinstance(plan_id, bytes) else plan_id)
    except Exception as e:
        frappe.log_error(f"Redis queue fetch error: {str(e)}", "CDN Queue Fetch Error")
        # Fallback to MariaDB if Redis fails
        fallback_plans = frappe.get_all(
            "CDN Sync Log",
            filters={"status": "Queued", "is_fallback": 1},
            pluck="plan_id",
            limit=max_count,
        )
        # To avoid processing the same plans again and again
        for plan_id in fallback_plans:
            frappe.db.set_value("CDN Sync Log", {"plan_id": plan_id, "is_fallback": 1}, "status", "Processing")
        return fallback_plans

    return plans

def add_plan_to_fallback_queue(plan_id):
    """Fallback when Redis unavailable."""
    try:
        if not frappe.db.exists("CDN Sync Log", {"plan_id": plan_id, "is_fallback": 1}):
            frappe.get_doc({
                "doctype": "CDN Sync Log",
                "plan_id": plan_id,
                "status": "Queued",
                "is_fallback": 1
            }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Error adding plan {plan_id} to fallback queue: {str(e)}", "Fallback Queue Error")

def acquire_lock(plan_id, ttl_seconds=300):
    """Acquire exclusive lock for plan build."""
    lock_key = f"{LOCK_PREFIX}{plan_id}"
    return frappe.cache().set(lock_key, now_datetime(), ex=ttl_seconds, nx=True)

def release_lock(plan_id):
    """Release plan build lock."""
    frappe.cache().delete(f"{LOCK_PREFIX}{plan_id}")

def move_to_dead_letter(plan_id, error_msg):
    """Move failed plan to dead-letter queue."""
    frappe.cache().hset(DEAD_LETTER_KEY, plan_id, error_msg)

# Document Event Handlers

def on_content_delete(doc, method=None):
    """
    Handle content deletion (on_trash and after_delete events).
    Queue affected plans for rebuild to remove deleted content from CDN.
    """
    from .batch_processor import trigger_plan_rebuild
    trigger_plan_rebuild(doc.doctype, doc.name)

def on_content_restore(doc, method=None):
    """
    Handle content restoration from trash.
    Treat restore as new insert - queue affected plans for rebuild.
    """
    from .batch_processor import trigger_plan_rebuild
    trigger_plan_rebuild(doc.doctype, doc.name)

def on_subject_update(doc, method=None):
	"""Handle Memora Subject updates."""
	import frappe
	frappe.log_error(
		f"[INFO] Subject update hook triggered for {doc.name} (title: {doc.title})",
		"CDN Document Events"
	)
	from .batch_processor import trigger_plan_rebuild
	trigger_plan_rebuild("Memora Subject", doc.name)

def on_subject_delete(doc, method=None):
    """Handle Memora Subject deletion."""
    on_content_delete(doc, method)

def on_track_update(doc, method=None):
    """Handle Memora Track updates."""
    from .batch_processor import trigger_plan_rebuild
    trigger_plan_rebuild("Memora Track", doc.name)

def on_track_delete(doc, method=None):
    """Handle Memora Track deletion."""
    on_content_delete(doc, method)

def on_unit_update(doc, method=None):
    """Handle Memora Unit updates."""
    from .batch_processor import trigger_plan_rebuild
    trigger_plan_rebuild("Memora Unit", doc.name)

def on_unit_delete(doc, method=None):
    """Handle Memora Unit deletion."""
    on_content_delete(doc, method)

def on_topic_update(doc, method=None):
    """Handle Memora Topic updates."""
    from .batch_processor import trigger_plan_rebuild
    trigger_plan_rebuild("Memora Topic", doc.name)

def on_topic_delete(doc, method=None):
    """Handle Memora Topic deletion."""
    on_content_delete(doc, method)

def on_lesson_update(doc, method=None):
    """Handle Memora Lesson updates."""
    from .batch_processor import trigger_plan_rebuild
    trigger_plan_rebuild("Memora Lesson", doc.name)

def on_lesson_delete(doc, method=None):
    """Handle Memora Lesson deletion."""
    on_content_delete(doc, method)

def on_lesson_stage_update(doc, method=None):
    """Handle Memora Lesson Stage updates."""
    from .batch_processor import trigger_plan_rebuild
    trigger_plan_rebuild("Memora Lesson Stage", doc.name)

def on_lesson_stage_delete(doc, method=None):
    """Handle Memora Lesson Stage deletion."""
    on_content_delete(doc, method)

def on_plan_update(doc, method=None):
    """Handle Memora Academic Plan updates."""
    from .batch_processor import trigger_plan_rebuild
    trigger_plan_rebuild("Memora Academic Plan", doc.name)

def on_plan_delete(doc, method=None):
    """Handle Memora Academic Plan deletion by removing plan folder from CDN."""
    try:
        settings = frappe.get_single("CDN Settings")
        if not settings.enabled:
            return

        from .cdn_uploader import delete_plan_folder
        success_count, error_count, errors = delete_plan_folder(settings, doc.name)

        if errors:
            frappe.log_error(
                f"Failed to delete plan folder for {doc.name}: {', '.join(errors)}",
                "CDN Plan Folder Deletion Failed"
            )
    except Exception as e:
        frappe.log_error(
            f"Error deleting plan folder for {doc.name}: {str(e)}",
            "CDN Plan Folder Deletion Error"
        )

def on_override_update(doc, method=None):
    """Handle Memora Plan Override updates or deletions."""
    from .batch_processor import trigger_plan_rebuild
    # The parent field in a child table points to the parent document name
    if hasattr(doc, 'parent') and doc.parent:
        trigger_plan_rebuild("Memora Academic Plan", doc.parent)
