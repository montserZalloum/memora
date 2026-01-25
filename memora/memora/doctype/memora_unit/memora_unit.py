# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

from memora.services.cdn_export.local_storage import delete_content_file


class MemoraUnit(Document):
	def on_trash(self):
		"""Delete local unit file when unit is deleted."""
		delete_content_file(f"units/{self.name}.json")
