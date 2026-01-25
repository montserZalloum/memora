# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

import frappe
from memora.services.cdn_export.local_storage import delete_content_file, delete_content_directory


class MemoraSubject(Document):
	def on_trash(self):
		"""Delete local subject files when subject is deleted."""
		subject_id = self.name

		delete_content_file(f"subjects/{subject_id}.json")

		plan_subjects = frappe.get_all(
			"Memora Plan Subject",
			filters={"subject": subject_id},
			pluck="parent"
		)

		for plan_id in plan_subjects:
			delete_content_file(f"plans/{plan_id}/search/{subject_id}.json")
