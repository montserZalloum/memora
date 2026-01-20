# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ArchivedMemoryTracker(Document):
	"""
	Archived Memory Tracker DocType Controller

	This DocType stores archived SRS memory tracker records from inactive seasons.
	All fields except eligible_for_deletion are read-only and set by the system.
	"""

	def validate(self):
		"""
		Validate that eligible_for_deletion can only be set by system
		"""
		if self.has_value_changed("eligible_for_deletion") and not frappe.flags.in_migrate:
			frappe.throw(
				"eligible_for_deletion can only be set by the system during retention checks"
			)

	def before_save(self):
		"""
		Ensure archived_at is set on creation
		"""
		if self.is_new() and not self.archived_at:
			self.archived_at = frappe.utils.now()

	def on_trash(self):
		"""
		Prevent deletion of archived records unless explicitly eligible
		"""
		if not self.eligible_for_deletion and not frappe.flags.in_migrate:
			frappe.throw(
				"Cannot delete archived records. Use the retention flagging process "
				"to mark records for deletion after 3+ years."
			)
