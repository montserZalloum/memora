"""
Constants for Memora DocType schema creation
"""

# Mixin fields that are added to most DocTypes for content management
CONTENT_MIXIN_FIELDS = [
	{
		"fieldname": "is_published",
		"fieldtype": "Check",
		"label": "Is Published",
		"default": 0,
	},
	{
		"fieldname": "is_free_preview",
		"fieldtype": "Check",
		"label": "Is Free Preview",
		"default": 0,
	},
	{
		"fieldname": "sort_order",
		"fieldtype": "Int",
		"label": "Sort Order",
		"default": 0,
		"search_index": 1,
	},
	{
		"fieldname": "image",
		"fieldtype": "Attach Image",
		"label": "Image",
	},
	{
		"fieldname": "description",
		"fieldtype": "Small Text",
		"label": "Description",
	},
]
