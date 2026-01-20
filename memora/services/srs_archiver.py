# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
SRS Archiver

This module provides functionality for archiving old season data to cold storage.
It handles:
- Copying Player Memory Tracker records to Archived Memory Tracker
- Deleting archived records from Player Memory Tracker
- Clearing Redis cache for archived seasons
- Flagging records eligible for deletion (3+ years old)
- Auto-archiving seasons marked for archival
"""

import frappe
from frappe.utils import now_datetime, add_days
from typing import Dict, List
from memora.services.srs_redis_manager import SRSRedisManager

class SRSArchiver:
	"""
	Manages archiving of old season data using transactional SQL operations
	for maximum performance and data integrity.
	"""

	# Retention period for archived records (3 years in days)
	RETENTION_DAYS = 3 * 365

	def __init__(self):
		"""Initialize archiver with Redis manager"""
		self.redis_manager = SRSRedisManager()

	def archive_season(self, season_name: str) -> Dict:
		"""
		Archive all memory tracker records for a season safely.
		
		Uses database transactions to ensure data is strictly moved (copied then deleted)
		without duplication or data loss.

		Args:
			season_name: Name of the season to archive

		Returns:
			Dict: Result with success status and archived_count
		"""
		try:
			# 1. Validation
			season_doc = frappe.get_doc("Game Subscription Season", season_name)
			if not season_doc:
				return {"success": False, "error": f"Season {season_name} not found"}
			
			if season_doc.is_active:
				return {"success": False, "error": f"Cannot archive active season {season_name}"}

			# Start Transaction
			frappe.db.begin()

			# 2. Check if data exists
			count = frappe.db.count("Player Memory Tracker", {"season": season_name})
			if count == 0:
				frappe.db.rollback()
				return {"success": True, "archived_count": 0, "message": f"No records to archive for {season_name}"}

			# 3. Bulk Copy (INSERT INTO ... SELECT)
			# This is much faster than Python loops and preserves all metadata
			frappe.db.sql("""
				INSERT INTO `tabArchived Memory Tracker`
				(name, player, season, question_id, stability, next_review_date, 
				 last_review_date, subject, topic, archived_at, eligible_for_deletion, 
				 creation, modified, modified_by, owner, docstatus, idx)
				SELECT 
				 name, player, season, question_id, stability, next_review_date, 
				 last_review_date, subject, topic, NOW(), 0,
				 creation, modified, modified_by, owner, docstatus, idx
				FROM `tabPlayer Memory Tracker`
				WHERE season = %s
			""", (season_name,))

			# 4. Bulk Delete from Source
			frappe.db.sql("""
				DELETE FROM `tabPlayer Memory Tracker`
				WHERE season = %s
			""", (season_name,))

			# 5. Commit Transaction
			# Only commit if both Copy and Delete succeeded
			frappe.db.commit()

			# 6. Clear Cache (After successful commit)
			self._clear_season_cache(season_name)

			frappe.msgprint(
				f"Successfully archived {count} records for season {season_name}",
				alert=True
			)

			return {
				"success": True,
				"archived_count": count,
				"season": season_name
			}

		except Exception as e:
			# Rollback changes if any error occurs
			frappe.db.rollback()
			frappe.log_error(
				f"Failed to archive season {season_name}: {str(e)}",
				"SRSArchiver.archive_season"
			)
			return {"success": False, "error": str(e)}

	def _clear_season_cache(self, season_name: str) -> None:
		"""
		Clear Redis cache for all users in a season using batched deletion
		"""
		try:
			pattern = f"srs:*:{season_name}"
			keys_to_delete = []
			
			# Scan and delete in batches to avoid memory spikes
			for key in self.redis_manager.redis.scan_iter(match=pattern, count=1000):
				keys_to_delete.append(key)
				if len(keys_to_delete) >= 1000:
					self.redis_manager.redis.delete(*keys_to_delete)
					keys_to_delete = []
			
			# Delete remaining keys
			if keys_to_delete:
				self.redis_manager.redis.delete(*keys_to_delete)

			frappe.logger().info(f"Cleared cache for season {season_name}")

		except Exception as e:
			frappe.log_error(f"Failed to clear cache: {str(e)}", "SRSArchiver._clear_season_cache")

	def process_auto_archive(self) -> Dict:
		"""
		Process auto-archive for eligible seasons
		"""
		try:
			today = frappe.utils.today()
			
			# Get eligible seasons
			eligible_seasons = frappe.get_all(
				"Game Subscription Season",
				filters={
					"auto_archive": 1,
					"is_active": 0,
					"end_date": ["<", today]
				},
				pluck="season_name"
			)

			if not eligible_seasons:
				return {"success": True, "archived_seasons": 0}

			archived_count = 0
			failed_list = []

			for season_name in eligible_seasons:
				result = self.archive_season(season_name)
				if result.get("success"):
					archived_count += 1
					# Disable auto_archive flag after success
					frappe.db.set_value("Game Subscription Season", {"season_name": season_name}, "auto_archive", 0)
				else:
					failed_list.append({"season": season_name, "error": result.get("error")})

			return {
				"success": True,
				"archived_seasons": archived_count,
				"failed_seasons": failed_list
			}

		except Exception as e:
			frappe.log_error(f"Auto-archive error: {str(e)}", "SRSArchiver.process_auto_archive")
			return {"success": False, "error": str(e)}

	def flag_eligible_for_deletion(self) -> Dict:
		"""
		Flag archived records eligible for deletion (3+ years old)
		Uses Bulk SQL Update for performance.
		"""
		try:
			cutoff_date = add_days(now_datetime(), -self.RETENTION_DAYS)

			# Bulk Update
			frappe.db.sql("""
				UPDATE `tabArchived Memory Tracker`
				SET eligible_for_deletion = 1
				WHERE archived_at < %s AND eligible_for_deletion = 0
			""", (cutoff_date,))
			
			# Get count of affected rows (approximation)
			flagged_count = int(frappe.db.sql("SELECT ROW_COUNT()")[0][0])
			
			frappe.db.commit()

			if flagged_count > 0:
				frappe.logger().info(f"Flagged {flagged_count} records for deletion (older than {cutoff_date})")

			return {
				"success": True,
				"flagged_count": flagged_count,
				"cutoff_date": cutoff_date
			}

		except Exception as e:
			frappe.log_error(f"Flagging error: {str(e)}", "SRSArchiver.flag_eligible_for_deletion")
			return {"success": False, "error": str(e)}

	def get_archive_status(self, season_name: str) -> Dict:
		"""Get archive status for a season"""
		try:
			season_doc = frappe.get_doc("Game Subscription Season", season_name)
			
			active_count = frappe.db.count("Player Memory Tracker", {"season": season_name})
			archived_count = frappe.db.count("Archived Memory Tracker", {"season": season_name})
			deletion_count = frappe.db.count("Archived Memory Tracker", {"season": season_name, "eligible_for_deletion": 1})

			return {
				"season": season_name,
				"is_active": season_doc.is_active,
				"auto_archive": season_doc.auto_archive,
				"end_date": season_doc.end_date,
				"active_records": active_count,
				"archived_records": archived_count,
				"eligible_for_deletion": deletion_count,
				"total_records": active_count + archived_count
			}
		except Exception as e:
			return {"success": False, "error": str(e)}

	def delete_eligible_records(self, season_name: str = None, confirm: bool = False) -> Dict:
		"""
		Delete archived records marked for deletion.
		"""
		if not confirm:
			return {"success": False, "error": "Confirmation required"}

		try:
			conditions = "eligible_for_deletion = 1"
			if season_name:
				# Use db.escape to prevent SQL injection in manual query construction
				conditions += f" AND season = {frappe.db.escape(season_name)}"

			# Bulk Delete
			frappe.db.sql(f"""
				DELETE FROM `tabArchived Memory Tracker`
				WHERE {conditions}
			""")
			
			deleted_count = int(frappe.db.sql("SELECT ROW_COUNT()")[0][0])
			frappe.db.commit()

			return {"success": True, "deleted_count": deleted_count}

		except Exception as e:
			frappe.log_error(f"Deletion error: {str(e)}", "SRSArchiver.delete_eligible_records")
			return {"success": False, "error": str(e)}


# --- Module-Level Wrapper Functions (Required for Hooks) ---

def process_auto_archive():
	"""Wrapper for scheduled auto-archive job."""
	SRSArchiver().process_auto_archive()

def flag_eligible_for_deletion():
	"""Wrapper for scheduled retention flagging job."""
	SRSArchiver().flag_eligible_for_deletion()