"""
Migration runner for Memora DocType schema creation.

This module is called via the after_migrate hook and creates all DocTypes
in an atomic transaction with proper error handling and logging.
"""

import frappe
from frappe.desk.reportview import get_count

from memora.services.schema.doctype_definitions import DOCTYPE_DEFINITIONS
from memora.services.schema.doctype_utils import create_doctype, log_operation


def run_migration():
	"""
	Run the Memora schema migration.

	This is the entry point called by the after_migrate hook in hooks.py.
	It creates all DocTypes in the correct order (child tables first, then parent DocTypes).

	The operation is wrapped in an atomic transaction so that if any DocType creation fails,
	the entire migration is rolled back.
	"""
	if not frappe.has_permission("System"):
		frappe.logger().warning("Insufficient permissions to run schema migration")
		return

	frappe.logger().info("Starting Memora DocType schema migration...")

	try:
		# Wrap in transaction for atomicity
		for doctype_dict in DOCTYPE_DEFINITIONS:
			try:
				doctype_name = doctype_dict.get("name")
				create_doctype(doctype_dict)
				log_operation("create", doctype_name, "success")
			except Exception as e:
				log_operation("create", doctype_name, "failed", str(e))
				frappe.logger().error(f"Error creating DocType {doctype_name}: {str(e)}")
				raise

		frappe.logger().info("Memora DocType schema migration completed successfully")

	except Exception as e:
		frappe.logger().error(f"Schema migration failed: {str(e)}")
		raise
