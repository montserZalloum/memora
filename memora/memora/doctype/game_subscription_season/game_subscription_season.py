# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from memora.services.partition_manager import create_season_partition

class GameSubscriptionSeason(Document):
    def before_rename(self, old, new, merge=False):
        frappe.throw(
            "Renaming Seasons is STRICTLY PROHIBITED due to Database Partitioning."
        )

    def after_insert(self):
        """
        After insert hook - Create database partition for new season.
        Uses background job to prevent ImplicitCommitError.
        """
        if self.season_name:
            # Use enqueue to run in background worker
            # This avoids blocking the UI and solves ImplicitCommitError
            frappe.enqueue(
                "memora.memora.doctype.game_subscription_season.game_subscription_season.create_partition_job",
                queue="short",
                season_name=self.season_name,
                doc_name=self.name
            )
            frappe.msgprint(f"Infrastructure creation queued for {self.season_name}. Check logs if status doesn't change.")

    def validate(self):
        """Validate season configuration before save."""
        
        # Prevent enabling auto_archive while season is active
        if self.is_active and self.auto_archive:
            frappe.throw(
                "Cannot enable 'Auto Archive' while season is active. Please deactivate first.",
                title="Configuration Error"
            )

        # Validate Season Name Pattern
        if self.season_name:
            import re
            # STRICT Pattern: SEASON-YYYY or SEASON-YYYY-NAME
            pattern = r'^SEASON-\d{4}(-[A-Z0-9_]+)?$'
            if not re.match(pattern, self.season_name):
                frappe.throw(
                    f"Season name must follow pattern 'SEASON-YYYY' or 'SEASON-YYYY-NAME'.<br>"
                    f"Invalid name: <b>{self.season_name}</b><br>"
                    f"Allowed characters: Uppercase letters, numbers, hyphens.",
                    title="Naming Convention"
                )

        # Date Validation
        if self.start_date and self.end_date and self.end_date < self.start_date:
            frappe.throw("End date cannot be before start date.", title="Date Error")

    def on_update(self):
        """Trigger cache rebuild when enable_redis changes."""
        if self.enable_redis:
            old_doc = self.get_doc_before_save()
            old_enable_redis = old_doc.enable_redis if old_doc else 0

            if old_enable_redis == 0 and self.enable_redis == 1:
                try:
                    from memora.services.srs_redis_manager import rebuild_season_cache
                    frappe.enqueue(
                        "memora.services.srs_redis_manager.rebuild_season_cache",
                        queue="srs_write",
                        job_name=f"cache_rebuild_{self.season_name}",
                        season_name=self.season_name,
                        enqueue_after_commit=True
                    )
                    frappe.msgprint(f"Cache rebuild queued for {self.season_name}.", alert=True)
                except Exception as e:
                    frappe.log_error(f"Cache rebuild trigger failed: {e}")


# --- Standalone Function for Background Job ---
def create_partition_job(season_name, doc_name):
    """
    This function runs in the background worker.
    """
    try:
        from memora.services.partition_manager import create_season_partition
        create_season_partition(season_name)
        
        # Update the flag silently
        frappe.db.set_value("Game Subscription Season", doc_name, "partition_created", 1)
        
    except Exception as e:
        # Critical Alert Logic
        error_msg = f"CRITICAL: Failed to create DB Partition for Season '{season_name}'"
        frappe.log_error(f"{error_msg}: {str(e)}")
        
        # Alert Admins
        try:
            managers = frappe.get_all("User", filters={"role_profile_name": "System Manager", "enabled": 1}, pluck="email")
            if managers:
                frappe.sendmail(
                    recipients=managers,
                    subject=f"URGENT: Partition Failure - {season_name}",
                    message=f"System failed to create storage partition for {season_name}. Error: {str(e)}"
                )
        except:
            pass


