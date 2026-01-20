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
from frappe.utils import now_datetime, add_days, cint
from typing import Dict, List
from memora.services.srs_redis_manager import SRSRedisManager


class SRSArchiver:
	"""
	Manages archiving of old season data

	This class provides methods for:
	- Archiving season data to cold storage
	- Cleaning up Redis cache
	- Flagging old records for deletion
	- Processing auto-archive jobs
	"""

	# Retention period for archived records (3 years in days)
	RETENTION_DAYS = 3 * 365

	def __init__(self):
		"""Initialize archiver with Redis manager"""
		self.redis_manager = SRSRedisManager()

	def archive_season(self, season_name: str) -> Dict:
		"""
		Archive all memory tracker records for a season

		This method:
		1. Copies all Player Memory Tracker records to Archived Memory Tracker
		2. Deletes records from Player Memory Tracker
		3. Clears Redis cache for the season

		Args:
			season_name: Name of the season to archive

		Returns:
			Dict: Result with success status and archived_count
		"""
		try:
			# Verify season exists
			season_doc = frappe.get_doc("Game Subscription Season", season_name)
			if not season_doc:
				return {
					"success": False,
					"error": f"Season {season_name} not found"
				}

			# Prevent archiving active seasons
			if season_doc.is_active:
				return {
					"success": False,
					"error": f"Cannot archive active season {season_name}"
				}

			# Get all memory tracker records for this season
			tracker_records = frappe.get_all(
				"Player Memory Tracker",
				filters={"season": season_name},
				fields=[
					"name",
					"player",
					"season",
					"question_id",
					"stability",
					"next_review_date",
					"last_review_date",
					"subject",
					"topic"
				]
			)

			if not tracker_records:
				return {
					"success": True,
					"archived_count": 0,
					"message": f"No records to archive for season {season_name}"
				}

			archived_count = 0
			now = now_datetime()

			# Copy records to Archived Memory Tracker
			for record in tracker_records:
				try:
					archived_doc = frappe.get_doc({
						"doctype": "Archived Memory Tracker",
						"player": record.player,
						"season": record.season,
						"question_id": record.question_id,
						"stability": record.stability,
						"next_review_date": record.next_review_date,
						"last_review_date": record.last_review_date,
						"subject": record.subject,
						"topic": record.topic,
						"archived_at": now,
						"eligible_for_deletion": 0
					})
					archived_doc.insert(ignore_permissions=True)
					archived_count += 1
				except Exception as e:
					frappe.log_error(
						f"Failed to archive record {record.name}: {str(e)}",
						"SRSArchiver.archive_season"
					)
					continue

			if archived_count == 0:
				return {
					"success": False,
					"error": "Failed to archive any records"
				}

			# Delete records from Player Memory Tracker
			try:
				frappe.db.delete("Player Memory Tracker", {"season": season_name})
				frappe.db.commit()
			except Exception as e:
				frappe.log_error(
					f"Failed to delete records from Player Memory Tracker: {str(e)}",
					"SRSArchiver.archive_season"
				)
				return {
					"success": False,
					"error": f"Failed to delete records: {str(e)}"
				}

			# Clear Redis cache for this season
			self._clear_season_cache(season_name)

			frappe.msgprint(
				f"Successfully archived {archived_count} records for season {season_name}",
				alert=True
			)

			return {
				"success": True,
				"archived_count": archived_count,
				"season": season_name
			}

		except Exception as e:
			frappe.log_error(
				f"Failed to archive season {season_name}: {str(e)}",
				"SRSArchiver.archive_season"
			)
			return {
				"success": False,
				"error": str(e)
			}

	def _clear_season_cache(self, season_name: str) -> None:
		"""
		Clear Redis cache for all users in a season

		This uses SCAN to find all cache keys for the season
		and DELETE to remove them.

		Args:
			season_name: Name of the season
		"""
		try:
			# Build pattern for season cache keys
			pattern = f"srs:*:{season_name}"

			# Use SCAN to find all matching keys
			keys_to_delete = []
			for key in self.redis_manager.redis.scan_iter(match=pattern, count=1000):
				keys_to_delete.append(key)

			# Delete all matching keys
			if keys_to_delete:
				self.redis_manager.redis.delete(*keys_to_delete)

			frappe.logger().info(
				f"Cleared {len(keys_to_delete)} cache keys for season {season_name}"
			)

		except Exception as e:
			frappe.log_error(
				f"Failed to clear cache for season {season_name}: {str(e)}",
				"SRSArchiver._clear_season_cache"
			)

	def process_auto_archive(self) -> Dict:
		"""
		Process auto-archive for eligible seasons

		This scheduled job finds seasons marked for auto-archive
		that are inactive and past their end date, then archives them.

		Returns:
			Dict: Result with success status and archived_seasons count
		"""
		try:
			today = frappe.utils.today()

			# Find seasons eligible for auto-archive:
			# - auto_archive is enabled
			# - is_active is False (not active)
			# - end_date is in the past
			eligible_seasons = frappe.get_all(
				"Game Subscription Season",
				filters={
					"auto_archive": 1,
					"is_active": 0,
					"end_date": ["<", today]
				},
				fields=["name", "season_name", "end_date"]
			)

			if not eligible_seasons:
				return {
					"success": True,
					"archived_seasons": 0,
					"message": "No seasons eligible for auto-archive"
				}

			archived_seasons = 0
			failed_seasons = []

			for season in eligible_seasons:
				try:
					result = self.archive_season(season.season_name)
					if result.get("success"):
						archived_seasons += 1
						# Update season to indicate it has been archived
						frappe.db.set_value(
							"Game Subscription Season",
							season.name,
							"auto_archive", 0
						)
					else:
						failed_seasons.append({
							"season": season.season_name,
							"error": result.get("error", "Unknown error")
						})
				except Exception as e:
					frappe.log_error(
						f"Failed to auto-archive season {season.season_name}: {str(e)}",
						"SRSArchiver.process_auto_archive"
					)
					failed_seasons.append({
						"season": season.season_name,
						"error": str(e)
					})

			frappe.db.commit()

			result = {
				"success": True,
				"archived_seasons": archived_seasons,
				"failed_seasons": failed_seasons
			}

			if archived_seasons > 0:
				frappe.logger().info(
					f"Auto-archived {archived_seasons} seasons"
				)

			return result

		except Exception as e:
			frappe.log_error(
				f"Failed to process auto-archive: {str(e)}",
				"SRSArchiver.process_auto_archive"
			)
			return {
				"success": False,
				"error": str(e)
			}

	def flag_eligible_for_deletion(self) -> Dict:
		"""
		Flag archived records eligible for deletion (3+ years old)

		This scheduled job finds Archived Memory Tracker records
		that are older than 3 years and marks them for deletion.

		Returns:
			Dict: Result with success status and flagged_count
		"""
		try:
			# Calculate cutoff date (3 years ago)
			cutoff_date = add_days(now_datetime(), -self.RETENTION_DAYS)

			# Find archived records older than 3 years
			old_records = frappe.get_all(
				"Archived Memory Tracker",
				filters={
					"archived_at": ["<", cutoff_date],
					"eligible_for_deletion": 0
				},
				fields=["name", "player", "season", "question_id", "archived_at"]
			)

			if not old_records:
				return {
					"success": True,
					"flagged_count": 0,
					"message": "No records eligible for deletion"
				}

			flagged_count = 0

			# Flag records for deletion
			for record in old_records:
				try:
					frappe.db.set_value(
						"Archived Memory Tracker",
						record.name,
						"eligible_for_deletion",
						1
					)
					flagged_count += 1
				except Exception as e:
					frappe.log_error(
						f"Failed to flag record {record.name} for deletion: {str(e)}",
						"SRSArchiver.flag_eligible_for_deletion"
					)
					continue

			frappe.db.commit()

			result = {
				"success": True,
				"flagged_count": flagged_count,
				"cutoff_date": cutoff_date
			}

			if flagged_count > 0:
				frappe.logger().info(
					f"Flagged {flagged_count} archived records for deletion"
				)

			return result

		except Exception as e:
			frappe.log_error(
				f"Failed to flag records for deletion: {str(e)}",
				"SRSArchiver.flag_eligible_for_deletion"
			)
			return {
				"success": False,
				"error": str(e)
			}

	def get_archive_status(self, season_name: str) -> Dict:
		"""
		Get archive status for a season

		Args:
			season_name: Name of the season

		Returns:
			Dict: Archive status with counts and metadata
		"""
		try:
			# Get season info
			season_doc = frappe.get_doc("Game Subscription Season", season_name)

			# Count records in Player Memory Tracker
			active_count = frappe.db.count(
				"Player Memory Tracker",
				{"season": season_name}
			)

			# Count records in Archived Memory Tracker
			archived_count = frappe.db.count(
				"Archived Memory Tracker",
				{"season": season_name}
			)

			# Count records eligible for deletion
			deletion_count = frappe.db.count(
				"Archived Memory Tracker",
				{
					"season": season_name,
					"eligible_for_deletion": 1
				}
			)

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
			frappe.log_error(
				f"Failed to get archive status for {season_name}: {str(e)}",
				"SRSArchiver.get_archive_status"
			)
			return {
				"success": False,
				"error": str(e)
			}

	def delete_eligible_records(self, season_name: str = None, confirm: bool = False) -> Dict:
		"""
		Delete archived records marked for deletion

		This is a destructive operation and requires explicit confirmation.

		Args:
			season_name: Optional season filter (if None, deletes all eligible records)
			confirm: Must be True to proceed with deletion

		Returns:
			Dict: Result with success status and deleted_count
		"""
		if not confirm:
			return {
				"success": False,
				"error": "Confirmation required. Set confirm=True to proceed."
			}

		try:
			# Build filters
			filters = {"eligible_for_deletion": 1}
			if season_name:
				filters["season"] = season_name

			# Get records to delete
			records_to_delete = frappe.get_all(
				"Archived Memory Tracker",
				filters=filters,
				fields=["name"]
			)

			if not records_to_delete:
				return {
					"success": True,
					"deleted_count": 0,
					"message": "No records eligible for deletion"
				}

			# Delete records
			for record in records_to_delete:
				try:
					frappe.db.delete("Archived Memory Tracker", record.name)
				except Exception as e:
					frappe.log_error(
						f"Failed to delete record {record.name}: {str(e)}",
						"SRSArchiver.delete_eligible_records"
					)
					continue

			frappe.db.commit()

			return {
				"success": True,
				"deleted_count": len(records_to_delete),
				"season": season_name
			}

		except Exception as e:
			frappe.log_error(
				f"Failed to delete eligible records: {str(e)}",
				"SRSArchiver.delete_eligible_records"
			)
			return {
				"success": False,
				"error": str(e)
			}


# --- Module-Level Wrapper Functions (Required for Hooks) ---

def process_auto_archive():
	"""
	Wrapper function for scheduled auto-archive job.
	This allows hooks.py to call the method on an instance.
	"""
	archiver = SRSArchiver()
	return archiver.process_auto_archive()


def flag_eligible_for_deletion():
	"""
	Wrapper function for scheduled retention flagging job.
	This allows hooks.py to call the method on an instance.
	"""
	archiver = SRSArchiver()
	return archiver.flag_eligible_for_deletion()