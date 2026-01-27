# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from memora.services.cdn_export.local_storage import delete_content_file


class MemoraLesson(Document):
	def before_insert(self):
		"""Assign bit_index from subject's next_bit_index counter."""
		if self.bit_index == -1:
			topic = frappe.get_doc("Memora Topic", self.parent_topic)
			unit = frappe.get_doc("Memora Unit", topic.parent_unit)
			track = frappe.get_doc("Memora Track", unit.parent_track)
			subject = frappe.get_doc("Memora Subject", track.parent_subject)

			self.bit_index = subject.next_bit_index
			subject.next_bit_index += 1
			subject.save(ignore_permissions=True)

	def on_trash(self):
		"""Handle lesson deletion and trigger plan rebuild."""
		from memora.services.cdn_export.change_tracker import on_lesson_delete
		
		# Delegate to change tracker which handles both file deletion and plan rebuild
		on_lesson_delete(self)
