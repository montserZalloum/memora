# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from memora.services.cdn_export.local_storage import delete_content_directory


class MemoraAcademicPlan(Document):
	def on_trash(self):
		"""Delete local plan directory when plan is deleted."""
		plan_path = f"plans/{self.name}"
		delete_content_directory(plan_path)
