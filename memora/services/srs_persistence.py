# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
SRS Persistence Service

This module handles asynchronous database persistence for SRS review responses.
It provides background job processing with retry logic and audit logging.

Key Features:
- Async persistence via Frappe background jobs
- Exponential backoff retry logic
- Audit logging for all persistence operations
- Idempotent job design to prevent duplicate writes
- Race Condition Handling using DB constraints
"""

import frappe
import time
from typing import List, Dict, Any, Optional
from frappe.utils import now_datetime, getdate
from frappe.exceptions import DuplicateEntryError  # Added Import

class SRSPersistenceError(Exception):
	"""Custom exception for SRS persistence errors"""
	pass


class SRSPersistenceService:
	"""
	Service for asynchronous SRS data persistence
	"""

	MAX_RETRIES = 3
	RETRY_DELAY_BASE = 1  # seconds
	RETRY_DELAY_MAX = 60  # seconds
	IDEMPOTENCY_WINDOW = 300  # 5 minutes

	def __init__(self):
		"""Initialize the persistence service"""
		pass

	def persist_review_batch(
		self,
		responses: List[Dict[str, Any]],
		user: str,
		season: str,
		retry_count: int = 0
	) -> Dict[str, Any]:
		"""
		Persist a batch of review responses to the database
		"""
		try:
			processed_count = 0
			failed_count = 0
			errors = []

			for response in responses:
				try:
					question_id = response.get("question_id")
					if not question_id:
						errors.append(f"Missing question_id in response: {response}")
						failed_count += 1
						continue

					# --- CRITICAL FIX: Race Condition Handling ---
					# Try to INSERT first. If it fails (Duplicate), then UPDATE.
					
					operation_type = "insert"
					
					try:
						# Attempt to create assuming it doesn't exist
						tracker_doc = frappe.get_doc({
							"doctype": "Player Memory Tracker",
							"player": user,
							"season": season,
							"question_id": question_id,
							"stability": response.get("new_stability", 1),
							"next_review_date": response.get("new_next_review_date"),
							"last_review_date": now_datetime(),
							"subject": response.get("subject"),
							"topic": response.get("topic")
						})
						# ignore_permissions=True is safer for background jobs
						tracker_doc.insert(ignore_permissions=True)
						
					except DuplicateEntryError:
						# Race condition caught! Record was created by another process just now.
						frappe.db.rollback() # Required to clean the failed transaction
						operation_type = "update"

					# If we caught a duplicate error, OR if we logically want to update
					# We proceed to the update logic
					if operation_type == "update":
						# Fetch the existing record ID
						tracker_name = frappe.db.get_value(
							"Player Memory Tracker",
							{
								"player": user,
								"season": season,
								"question_id": question_id
							},
							"name"
						)

						if tracker_name:
							# Idempotency Check (Prevent duplicate processing of same event)
							tracker_data = frappe.db.get_value(
								"Player Memory Tracker",
								tracker_name,
								["modified"],
								as_dict=True
							)

							time_since_modified = (now_datetime() - tracker_data.modified).total_seconds()
							if time_since_modified < self.IDEMPOTENCY_WINDOW:
								frappe.logger().info(
									f"Skipping duplicate update for tracker {tracker_name} "
									f"(modified {time_since_modified:.0f}s ago)"
								)
								processed_count += 1
								continue

							# Perform Update
							frappe.db.set_value("Player Memory Tracker", tracker_name, {
								"stability": response.get("new_stability"),
								"next_review_date": response.get("new_next_review_date"),
								"last_review_date": now_datetime()
							})

					processed_count += 1

				except Exception as e:
					error_msg = f"Failed to persist question {response.get('question_id', 'unknown')}: {str(e)}"
					errors.append(error_msg)
					failed_count += 1
					frappe.log_error(error_msg, "SRSPersistenceService.persist_review_batch")

			# Commit the transaction
			frappe.db.commit()

			# Audit logging
			self._log_persistence_audit(
				user=user,
				season=season,
				processed_count=processed_count,
				failed_count=failed_count,
				errors=errors,
				retry_count=retry_count
			)

			return {
				"success": processed_count > 0,
				"processed_count": processed_count,
				"failed_count": failed_count,
				"errors": errors
			}

		except Exception as e:
			# Retry Logic with backoff
			if retry_count < self.MAX_RETRIES:
				delay = min(
					self.RETRY_DELAY_BASE * (2 ** retry_count),
					self.RETRY_DELAY_MAX
				)
				
				frappe.log_error(
					f"Persistence retry {retry_count + 1} for {user}: {str(e)}",
					"SRSPersistenceService"
				)

				frappe.enqueue(
					"memora.services.srs_persistence.persist_review_batch",
					responses=responses,
					user=user,
					season=season,
					retry_count=retry_count + 1,
					enqueue_after_commit=True,
					queue="long",
					timeout=300
				)
				return {"status": "retrying", "retry_count": retry_count + 1}
			else:
				error_msg = f"Max retries exceeded for {user}: {str(e)}"
				frappe.log_error(error_msg, "SRSPersistenceService")
				raise SRSPersistenceError(error_msg)

	def _log_persistence_audit(
		self,
		user: str,
		season: str,
		processed_count: int,
		failed_count: int,
		errors: List[str],
		retry_count: int = 0
	) -> None:
		"""Log audit information (only on errors or retries to save DB space)"""
		try:
			# LOGIC IMPROVEMENT: Don't log success of every single batch to DB, 
			# only log if something went wrong or it was a retry.
			# Otherwise System Log table will explode with 1M records.
			if failed_count > 0 or retry_count > 0:
				audit_log = frappe.get_doc({
					"doctype": "System Log",
					"method": "SRSPersistenceService.persist_review_batch",
					"message": f"SRS Audit: {user} | {season}",
					"error": f"Processed: {processed_count}, Failed: {failed_count}, Retries: {retry_count}. Errors: {str(errors)[:1000]}",
					"reference_doctype": "Player Memory Tracker",
					"reference_name": user
				})
				audit_log.insert(ignore_permissions=True)

		except Exception:
			# Fail silently on logging errors
			pass

	def persist_single_review(
		self,
		response: Dict[str, Any],
		user: str,
		season: str
	) -> bool:
		"""Convenience method for single-item persistence."""
		result = self.persist_review_batch(
			responses=[response],
			user=user,
			season=season
		)
		return result.get("success", False)

	def get_persistence_status(
		self,
		job_id: str
	) -> Optional[Dict[str, Any]]:
		"""Get the status of a persistence background job"""
		try:
			from rq.job import Job
			from rq import get_current_connection
			
			job = Job.fetch(job_id, connection=get_current_connection())
			if job:
				return {
					"job_id": job_id,
					"status": job.get_status(),
					"created_at": job.created_at,
					"result": job.result
				}
			return None
		except Exception:
			return None


# Global instance
_srs_persistence_service = SRSPersistenceService()


def persist_review_batch(
	responses: List[Dict[str, Any]],
	user: str,
	season: str,
	retry_count: int = 0
) -> Dict[str, Any]:
	return _srs_persistence_service.persist_review_batch(
		responses=responses,
		user=user,
		season=season,
		retry_count=retry_count
	)