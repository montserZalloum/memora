"""
Utility functions for DocType creation and management
"""

import frappe
from frappe.model.document import Document


def create_doctype(doctype_dict):
	"""
	Create a DocType programmatically.

	Args:
		doctype_dict (dict): DocType configuration with fields, properties, etc.

	Returns:
		frappe.model.document.Document: Created DocType document
	"""
	# Check if DocType already exists
	if frappe.db.exists("DocType", doctype_dict.get("name")):
		frappe.logger().info(f"DocType {doctype_dict.get('name')} already exists, skipping creation")
		return frappe.get_doc("DocType", doctype_dict.get("name"))

	# Create new DocType document
	doc = frappe.get_doc(doctype_dict)
	doc.insert(ignore_permissions=True)
	frappe.logger().info(f"Created DocType: {doc.name}")
	return doc


def log_operation(operation, doctype_name, status, message=""):
	"""
	Log schema operations for debugging and audit trails.

	Args:
		operation (str): Operation type (e.g., 'create', 'update', 'delete')
		doctype_name (str): Name of the DocType
		status (str): Status of the operation ('success', 'failed', 'skipped')
		message (str): Additional message
	"""
	log_msg = f"[{operation.upper()}] {doctype_name}: {status}"
	if message:
		log_msg += f" - {message}"
	frappe.logger().info(log_msg)
