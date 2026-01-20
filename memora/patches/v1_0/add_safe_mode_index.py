# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Add Safe Mode Index Patch

This patch creates a composite index on Player Memory Tracker for
Safe Mode fallback queries. The index covers (player, season, next_review_date)
which is the query pattern used when Redis cache is unavailable.

Index: idx_pmt_player_season_review
Columns: player, season, next_review_date
Purpose: Optimize Safe Mode fallback queries
"""

import frappe


def execute():
	"""
	Create composite index for Safe Mode queries

	This patch:
	1. Checks if index already exists
	2. Creates composite index if not present
	3. Logs index creation status
	"""
	frappe.log("Starting add_safe_mode_index patch...")

	table_name = "tabPlayer Memory Tracker"
	index_name = "idx_pmt_player_season_review"

	# Check if index already exists
	existing_indexes = frappe.db.sql(
		f"""
		SHOW INDEX FROM `{table_name}`
		WHERE Key_name = %s
		""",
		(index_name,),
		as_list=True
	)

	if existing_indexes:
		frappe.log(f"Index {index_name} already exists. Skipping.")
		return

	# Create composite index
	try:
		sql = f"""
			CREATE INDEX {index_name}
			ON `{table_name}` (player, season, next_review_date)
		"""

		frappe.db.sql(sql)
		frappe.log(f"Successfully created index: {index_name}")

		# Verify index was created
		verification = frappe.db.sql(
			f"""
			SHOW INDEX FROM `{table_name}`
			WHERE Key_name = %s
			""",
			(index_name,),
			as_list=True
		)

		if verification:
			frappe.log(f"Index verified: {index_name}")
		else:
			frappe.log_error(
				f"Index creation verification failed for {index_name}",
				"add_safe_mode_index"
			)

	except Exception as e:
		frappe.log_error(
			f"Failed to create Safe Mode index: {str(e)}",
			"add_safe_mode_index"
		)
		raise

	frappe.log("add_safe_mode_index patch complete.")
