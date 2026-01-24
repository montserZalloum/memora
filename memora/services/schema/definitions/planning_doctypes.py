"""
Academic planning and commerce DocType definitions for Memora.

These handle academic planning (Season, Stream, Academic Plan) and
commerce integration (Product Grant).
"""


def get_memora_season():
	"""Academic period (e.g., 'Gen-2007', 'Fall-2026')."""
	return {
		"doctype": "DocType",
		"name": "Memora Season",
		"module": "Memora",
		"custom": 0,
		"autoname": "field:title",
		"fields": [
			{
				"fieldname": "title",
				"fieldtype": "Data",
				"label": "Title",
				"reqd": 1,
				"unique": 1,
				"search_index": 1,
			},
			{
				"fieldname": "is_published",
				"fieldtype": "Check",
				"label": "Is Published",
				"default": 0,
			},
			{
				"fieldname": "start_date",
				"fieldtype": "Date",
				"label": "Start Date",
			},
			{
				"fieldname": "end_date",
				"fieldtype": "Date",
				"label": "End Date",
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
				"role": "Academic Planner",
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


def get_memora_stream():
	"""Educational track type (Scientific, Literary, Industrial)."""
	return {
		"doctype": "DocType",
		"name": "Memora Stream",
		"module": "Memora",
		"custom": 0,
		"autoname": "field:title",
		"fields": [
			{
				"fieldname": "title",
				"fieldtype": "Data",
				"label": "Title",
				"reqd": 1,
				"unique": 1,
				"search_index": 1,
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
				"role": "Academic Planner",
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


def get_memora_academic_plan():
	"""Combines Season + Stream + Subjects with visibility overrides."""
	return {
		"doctype": "DocType",
		"name": "Memora Academic Plan",
		"module": "Memora",
		"custom": 0,
		"fields": [
			{
				"fieldname": "title",
				"fieldtype": "Data",
				"label": "Title",
				"reqd": 1,
			},
			{
				"fieldname": "season",
				"fieldtype": "Link",
				"label": "Season",
				"options": "Memora Season",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "stream",
				"fieldtype": "Link",
				"label": "Stream",
				"options": "Memora Stream",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "subjects",
				"fieldtype": "Table",
				"label": "Subjects",
				"options": "Memora Plan Subject",
			},
			{
				"fieldname": "overrides",
				"fieldtype": "Table",
				"label": "Overrides",
				"options": "Memora Plan Override",
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
				"role": "Academic Planner",
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


def get_memora_product_grant():
	"""Links ERPNext Item to Academic Plan for access control."""
	return {
		"doctype": "DocType",
		"name": "Memora Product Grant",
		"module": "Memora",
		"custom": 0,
		"fields": [
			{
				"fieldname": "item_code",
				"fieldtype": "Link",
				"label": "Item Code",
				"options": "Item",
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
				"fieldname": "grant_type",
				"fieldtype": "Select",
				"label": "Grant Type",
				"options": "Full Plan Access\nSpecific Components",
				"reqd": 1,
			},
			{
				"fieldname": "unlocked_components",
				"fieldtype": "Table",
				"label": "Unlocked Components",
				"options": "Memora Grant Component",
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


# Export all planning DocType definitions
PLANNING_DOCTYPE_DEFINITIONS = [
	get_memora_season(),
	get_memora_stream(),
	get_memora_academic_plan(),
	get_memora_product_grant(),
]
