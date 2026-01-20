# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Fix NULL Seasons Patch

This patch sets the season field for existing Player Memory Tracker records
that have NULL values. This is required before applying LIST partitioning
since partitioning requires the partition key to be NOT NULL.
"""

import frappe

def execute():
	"""
	Set season for existing NULL records.
	"""
	frappe.log("Starting fix_null_seasons patch...")
	
	table_name = "tabPlayer Memory Tracker"
	
	# 1. Check if there are records to fix
	# Using direct SQL count is faster than fetching records
	null_count = frappe.db.sql(
		f"SELECT COUNT(*) FROM `{table_name}` WHERE season IS NULL OR season = ''",
		as_list=True
	)[0][0]
	
	if null_count == 0:
		frappe.log("No NULL seasons found. Patch complete.")
		return

	# 2. Get or create a default season
	# We use 'SEASON-0000-DEFAULT' to satisfy the new Regex validation (^SEASON-\d{4})
	default_season_name = "SEASON-0000-DEFAULT"
	
	if not frappe.db.exists("Game Subscription Season", default_season_name):
		try:
			doc = frappe.get_doc({
				"doctype": "Game Subscription Season",
				"season_name": default_season_name,
				"start_date": "2000-01-01", # Dummy dates
				"end_date": "2000-12-31",
				"is_active": 0,
				"partition_created": 0,
				"enable_redis": 0,
				"auto_archive": 0,
				"description": "System created season for legacy data cleanup"
			})
			
			# CRITICAL FIX: Correct way to bypass validation logic
			doc.flags.ignore_validate = True
			doc.insert(ignore_permissions=True)
			
			frappe.log(f"Created default season: {default_season_name}")
			
		except Exception as e:
			frappe.log_error(f"Failed to create default season: {e}")
			# If we can't create the season, we can't fix the data, so we must stop.
			raise e

	# 3. Bulk Update
	# Using a single SQL query is much faster and safer than looping in Python
	frappe.db.sql(f"""
		UPDATE `{table_name}`
		SET season = %s, modified = NOW()
		WHERE season IS NULL OR season = ''
	""", (default_season_name,))
	
	frappe.db.commit()
	frappe.log(f"fix_null_seasons patch complete. Updated {null_count} records.")