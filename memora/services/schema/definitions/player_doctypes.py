"""
Player profile and wallet DocType definitions for Memora.

These handle player identity, devices, and gamification data.
"""


def get_memora_player_profile():
	"""Player game identity separate from Frappe User."""
	return {
		"doctype": "DocType",
		"name": "Memora Player Profile",
		"module": "Memora",
		"custom": 0,
		"fields": [
			{
				"fieldname": "user",
				"fieldtype": "Link",
				"label": "User",
				"options": "User",
				"reqd": 1,
				"unique": 1,
				"search_index": 1,
			},
			{
				"fieldname": "display_name",
				"fieldtype": "Data",
				"label": "Display Name",
			},
			{
				"fieldname": "avatar",
				"fieldtype": "Attach Image",
				"label": "Avatar",
			},
			{
				"fieldname": "current_plan",
				"fieldtype": "Link",
				"label": "Current Plan",
				"options": "Memora Academic Plan",
				"search_index": 1,
			},
			{
				"fieldname": "devices",
				"fieldtype": "Table",
				"label": "Devices",
				"options": "Memora Player Device",
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


def get_memora_player_wallet():
	"""High-velocity XP and streak data for gamification."""
	return {
		"doctype": "DocType",
		"name": "Memora Player Wallet",
		"module": "Memora",
		"custom": 0,
		"fields": [
			{
				"fieldname": "player",
				"fieldtype": "Link",
				"label": "Player",
				"options": "Memora Player Profile",
				"reqd": 1,
				"unique": 1,
				"search_index": 1,
			},
			{
				"fieldname": "total_xp",
				"fieldtype": "Int",
				"label": "Total XP",
				"default": 0,
			},
			{
				"fieldname": "current_streak",
				"fieldtype": "Int",
				"label": "Current Streak",
				"default": 0,
			},
			{
				"fieldname": "last_played_at",
				"fieldtype": "Datetime",
				"label": "Last Played At",
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


# Export all player DocType definitions
PLAYER_DOCTYPE_DEFINITIONS = [
	get_memora_player_profile(),
	get_memora_player_wallet(),
]
