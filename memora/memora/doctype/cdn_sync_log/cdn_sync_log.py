# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime


class CdnSyncLog(Document):
	def validate(self):
		self.validate_plan_id()
		self.validate_retry_count()
		self.validate_timestamps()

	def validate_plan_id(self):
		"""Validate that plan_id references an existing Academic Plan."""
		if self.plan_id:
			if not frappe.db.exists("Memora Academic Plan", self.plan_id):
				frappe.throw(_("Plan {0} does not exist").format(self.plan_id))

	def validate_retry_count(self):
		"""Validate that retry_count does not exceed 3."""
		if self.retry_count is not None and self.retry_count > 3:
			frappe.throw(_("Retry count cannot exceed 3"))

	def validate_timestamps(self):
		"""Validate that completed_at is >= started_at when both are present."""
		if self.started_at and self.completed_at:
			if self.completed_at < self.started_at:
				frappe.throw(_("Completed At must be after or equal to Started At"))

	def before_save(self):
		"""Ensure proper defaults before saving."""
		if not self.status:
			self.status = "Queued"
		if self.retry_count is None:
			self.retry_count = 0
		if self.files_uploaded is None:
			self.files_uploaded = 0
		if self.files_deleted is None:
			self.files_deleted = 0
		if self.is_fallback is None:
			self.is_fallback = 0

	def mark_as_processing(self):
		"""Mark the log as processing and set started_at."""
		self.status = "Processing"
		self.started_at = datetime.now()
		self.save()

	def mark_as_success(self, files_uploaded=0, files_deleted=0):
		"""Mark the log as success."""
		self.status = "Success"
		self.completed_at = datetime.now()
		self.files_uploaded = files_uploaded
		self.files_deleted = files_deleted
		self.save()

	def mark_as_failed(self, error_message):
		"""Mark the log as failed and increment retry count."""
		self.status = "Failed"
		self.completed_at = datetime.now()
		self.error_message = error_message
		self.retry_count = (self.retry_count or 0) + 1
		
		# Move to dead letter if retry count exceeds 3
		if self.retry_count >= 3:
			self.status = "Dead Letter"
		
		self.save()

	def mark_as_dead_letter(self, error_message):
		"""Mark the log as dead letter."""
		self.status = "Dead Letter"
		self.completed_at = datetime.now()
		self.error_message = error_message
		self.retry_count = 3
		self.save()

	@staticmethod
	def get_recent_failures(limit=10):
		"""Get recent failed sync logs."""
		return frappe.get_all(
			"CDN Sync Log",
			filters={
				"status": ["in", ["Failed", "Dead Letter"]]
			},
			fields=["name", "plan_id", "status", "error_message", "creation", "retry_count"],
			order_by="creation desc",
			limit=limit
		)

	@staticmethod
	def get_queue_status():
		"""Get current queue status."""
		queued = frappe.db.count("CDN Sync Log", {"status": "Queued"})
		processing = frappe.db.count("CDN Sync Log", {"status": "Processing"})
		dead_letter = frappe.db.count("CDN Sync Log", {"status": "Dead Letter"})
		
		return {
			"queued": queued,
			"processing": processing,
			"dead_letter": dead_letter
		}
