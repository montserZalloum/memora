"""
Engine and commerce DocType definitions for Memora.

These handle interaction logging, FSRS memory state, and subscription transactions.
"""


def get_memora_interaction_log():
	"""Write-only audit trail of all question attempts."""
	return {
		"doctype": "DocType",
		"name": "Memora Interaction Log",
		"module": "Memora",
		"custom": 0,
		"fields": [
			{
				"fieldname": "player",
				"fieldtype": "Link",
				"label": "Player",
				"options": "Memora Player Profile",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "academic_plan",
				"fieldtype": "Link",
				"label": "Academic Plan",
				"options": "Memora Academic Plan",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "question_id",
				"fieldtype": "Data",
				"label": "Question ID",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "student_answer",
				"fieldtype": "Data",
				"label": "Student Answer",
			},
			{
				"fieldname": "correct_answer",
				"fieldtype": "Data",
				"label": "Correct Answer",
			},
			{
				"fieldname": "is_correct",
				"fieldtype": "Check",
				"label": "Is Correct",
				"default": 0,
			},
			{
				"fieldname": "time_taken",
				"fieldtype": "Int",
				"label": "Time Taken (seconds)",
			},
			{
				"fieldname": "timestamp",
				"fieldtype": "Datetime",
				"label": "Timestamp",
				"default": "now",
			},
		],
		"permissions": [
			{
				"role": "System Manager",
				"permlevel": 0,
				"read": 1,
				"write": 0,
				"create": 0,
				"delete": 0,
				"submit": 0,
				"cancel": 0,
			},
		],
	}


def get_memora_memory_state():
	"""FSRS algorithm state per player-question pair."""
	return {
		"doctype": "DocType",
		"name": "Memora Memory State",
		"module": "Memora",
		"custom": 0,
		"fields": [
			{
				"fieldname": "player",
				"fieldtype": "Link",
				"label": "Player",
				"options": "Memora Player Profile",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "question_id",
				"fieldtype": "Data",
				"label": "Question ID",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "stability",
				"fieldtype": "Float",
				"label": "Stability",
			},
			{
				"fieldname": "difficulty",
				"fieldtype": "Float",
				"label": "Difficulty",
			},
			{
				"fieldname": "next_review",
				"fieldtype": "Datetime",
				"label": "Next Review",
				"search_index": 1,
			},
			{
				"fieldname": "state",
				"fieldtype": "Select",
				"label": "State",
				"options": "New\nLearning\nReview\nRelearning",
				"default": "New",
			},
		],
		"permissions": [
			{
				"role": "System Manager",
				"permlevel": 0,
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1,
				"submit": 0,
				"cancel": 0,
			},
		],
	}


def get_memora_subscription_transaction():
	"""Payment records linking purchases to product grants."""
	return {
		"doctype": "DocType",
		"name": "Memora Subscription Transaction",
		"module": "Memora",
		"custom": 0,
		"autoname": "naming_series:",
		"naming_series": "SUB-TX-.YYYY.-",
		"fields": [
			{
				"fieldname": "naming_series",
				"fieldtype": "Select",
				"label": "Naming Series",
				"options": "SUB-TX-.YYYY.-",
				"reqd": 1,
			},
			{
				"fieldname": "player",
				"fieldtype": "Link",
				"label": "Player",
				"options": "Memora Player Profile",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "transaction_type",
				"fieldtype": "Select",
				"label": "Transaction Type",
				"options": "Purchase\nRenewal\nUpgrade",
				"reqd": 1,
			},
			{
				"fieldname": "payment_method",
				"fieldtype": "Select",
				"label": "Payment Method",
				"options": "Payment Gateway\nManual-Admin\nVoucher",
				"reqd": 1,
			},
			{
				"fieldname": "status",
				"fieldtype": "Select",
				"label": "Status",
				"options": "Pending Approval\nCompleted\nFailed\nCancelled",
				"default": "Pending Approval",
				"reqd": 1,
			},
			{
				"fieldname": "transaction_id",
				"fieldtype": "Data",
				"label": "Transaction ID",
			},
			{
				"fieldname": "amount",
				"fieldtype": "Currency",
				"label": "Amount",
			},
			{
				"fieldname": "receipt_image",
				"fieldtype": "Attach Image",
				"label": "Receipt Image",
			},
			{
				"fieldname": "related_grant",
				"fieldtype": "Link",
				"label": "Related Grant",
				"options": "Memora Product Grant",
				"search_index": 1,
			},
			{
				"fieldname": "erpnext_invoice",
				"fieldtype": "Link",
				"label": "ERPNext Invoice",
				"options": "Sales Invoice",
				"read_only": 1,
			},
		],
		"permissions": [
			{
				"role": "System Manager",
				"permlevel": 0,
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 1,
				"submit": 0,
				"cancel": 0,
			},
			{
				"role": "Sales Manager",
				"permlevel": 0,
				"read": 1,
				"write": 1,
				"create": 1,
				"delete": 0,
				"submit": 0,
				"cancel": 0,
			},
		],
	}


# Export all engine and commerce DocType definitions
ENGINE_COMMERCE_DOCTYPE_DEFINITIONS = [
	get_memora_interaction_log(),
	get_memora_memory_state(),
	get_memora_subscription_transaction(),
]
