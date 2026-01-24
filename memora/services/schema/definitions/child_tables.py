"""
Child table DocType definitions for Memora.

These must be created before parent DocTypes that reference them.
"""


def get_memora_lesson_stage():
	"""Child table for lesson stages within a lesson."""
	return {
		"doctype": "DocType",
		"name": "Memora Lesson Stage",
		"module": "Memora",
		"custom": 0,
		"is_table": 1,
		"istable": 1,
		"fields": [
			{
				"fieldname": "title",
				"fieldtype": "Data",
				"label": "Title",
				"reqd": 1,
			},
			{
				"fieldname": "type",
				"fieldtype": "Select",
				"label": "Type",
				"options": "Video\nQuestion\nText\nInteractive",
				"reqd": 1,
			},
			{
				"fieldname": "config",
				"fieldtype": "JSON",
				"label": "Configuration",
			},
		],
		"permissions": [],
	}


def get_memora_plan_subject():
	"""Child table for subjects in an academic plan."""
	return {
		"doctype": "DocType",
		"name": "Memora Plan Subject",
		"module": "Memora",
		"custom": 0,
		"is_table": 1,
		"istable": 1,
		"fields": [
			{
				"fieldname": "subject",
				"fieldtype": "Link",
				"label": "Subject",
				"options": "Memora Subject",
				"reqd": 1,
			},
			{
				"fieldname": "sort_order",
				"fieldtype": "Int",
				"label": "Sort Order",
				"default": 0,
			},
		],
		"permissions": [],
	}


def get_memora_plan_override():
	"""Child table for visibility overrides in an academic plan."""
	return {
		"doctype": "DocType",
		"name": "Memora Plan Override",
		"module": "Memora",
		"custom": 0,
		"is_table": 1,
		"istable": 1,
		"fields": [
			{
				"fieldname": "target_doctype",
				"fieldtype": "Link",
				"label": "Target DocType",
				"options": "DocType",
				"reqd": 1,
			},
			{
				"fieldname": "target_name",
				"fieldtype": "Dynamic Link",
				"label": "Target Name",
				"options": "target_doctype",
				"reqd": 1,
			},
			{
				"fieldname": "action",
				"fieldtype": "Select",
				"label": "Action",
				"options": "Hide\nRename\nSet Free\nSet Sold Separately",
				"reqd": 1,
			},
			{
				"fieldname": "override_value",
				"fieldtype": "Data",
				"label": "Override Value",
			},
		],
		"permissions": [],
	}


def get_memora_grant_component():
	"""Child table for specific components unlocked by a product grant."""
	return {
		"doctype": "DocType",
		"name": "Memora Grant Component",
		"module": "Memora",
		"custom": 0,
		"is_table": 1,
		"istable": 1,
		"fields": [
			{
				"fieldname": "target_doctype",
				"fieldtype": "Link",
				"label": "Target DocType",
				"options": "DocType",
				"reqd": 1,
			},
			{
				"fieldname": "target_name",
				"fieldtype": "Dynamic Link",
				"label": "Target Name",
				"options": "target_doctype",
				"reqd": 1,
			},
		],
		"permissions": [],
	}


def get_memora_player_device():
	"""Child table for player devices."""
	return {
		"doctype": "DocType",
		"name": "Memora Player Device",
		"module": "Memora",
		"custom": 0,
		"is_table": 1,
		"istable": 1,
		"fields": [
			{
				"fieldname": "device_id",
				"fieldtype": "Data",
				"label": "Device ID",
				"reqd": 1,
			},
			{
				"fieldname": "device_name",
				"fieldtype": "Data",
				"label": "Device Name",
			},
			{
				"fieldname": "is_trusted",
				"fieldtype": "Check",
				"label": "Is Trusted",
				"default": 0,
			},
		],
		"permissions": [],
	}


# Export all child table definitions
CHILD_TABLE_DEFINITIONS = [
	get_memora_lesson_stage(),
	get_memora_plan_subject(),
	get_memora_plan_override(),
	get_memora_grant_component(),
	get_memora_player_device(),
]
