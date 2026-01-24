"""
Educational content DocType definitions for Memora.

These represent the learning hierarchy: Subject > Track > Unit > Topic > Lesson > Lesson Stage.
"""

from memora.services.schema.constants import CONTENT_MIXIN_FIELDS


def get_memora_subject():
	"""Top-level educational category."""
	return {
		"doctype": "DocType",
		"name": "Memora Subject",
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
				"fieldname": "color_code",
				"fieldtype": "Data",
				"label": "Color Code",
			},
			*CONTENT_MIXIN_FIELDS,
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
				"role": "Content Manager",
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


def get_memora_track():
	"""Sub-category within a subject."""
	return {
		"doctype": "DocType",
		"name": "Memora Track",
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
				"fieldname": "parent_subject",
				"fieldtype": "Link",
				"label": "Parent Subject",
				"options": "Memora Subject",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "is_sold_separately",
				"fieldtype": "Check",
				"label": "Is Sold Separately",
				"default": 0,
			},
			*CONTENT_MIXIN_FIELDS,
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
				"role": "Content Manager",
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


def get_memora_unit():
	"""Learning module within a track."""
	return {
		"doctype": "DocType",
		"name": "Memora Unit",
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
				"fieldname": "parent_track",
				"fieldtype": "Link",
				"label": "Parent Track",
				"options": "Memora Track",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "badge_image",
				"fieldtype": "Attach Image",
				"label": "Badge Image",
			},
			*CONTENT_MIXIN_FIELDS,
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
				"role": "Content Manager",
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


def get_memora_topic():
	"""Specific topic within a unit."""
	return {
		"doctype": "DocType",
		"name": "Memora Topic",
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
				"fieldname": "parent_unit",
				"fieldtype": "Link",
				"label": "Parent Unit",
				"options": "Memora Unit",
				"reqd": 1,
				"search_index": 1,
			},
			*CONTENT_MIXIN_FIELDS,
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
				"role": "Content Manager",
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


def get_memora_lesson():
	"""Individual learning item containing multiple stages."""
	return {
		"doctype": "DocType",
		"name": "Memora Lesson",
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
				"fieldname": "parent_topic",
				"fieldtype": "Link",
				"label": "Parent Topic",
				"options": "Memora Topic",
				"reqd": 1,
				"search_index": 1,
			},
			{
				"fieldname": "stages",
				"fieldtype": "Table",
				"label": "Stages",
				"options": "Memora Lesson Stage",
			},
			*CONTENT_MIXIN_FIELDS,
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
				"role": "Content Manager",
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


# Export all content DocType definitions
CONTENT_DOCTYPE_DEFINITIONS = [
	get_memora_subject(),
	get_memora_track(),
	get_memora_unit(),
	get_memora_topic(),
	get_memora_lesson(),
]
