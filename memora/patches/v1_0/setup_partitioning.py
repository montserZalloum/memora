# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Setup Partitioning Patch

This patch applies LIST COLUMNS partitioning to the Player Memory Tracker table.
CRITICAL CHANGE: It is now IDEMPOTENT. It checks if partitioning exists first.
If exists, it DOES NOTHING. This prevents destroying dynamic partitions during migrate.
"""

import frappe

def execute():
	"""
	Apply LIST partitioning to Player Memory Tracker table
	"""
	frappe.log("Starting setup_partitioning patch...")

	table_name = "tabPlayer Memory Tracker"

	# --- SECURITY CHECK: STOP IF ALREADY PARTITIONED ---
	# We check if the table has more than 1 partition entry in information_schema.
	# Standard InnoDB tables usually have 1 entry (p0 or NULL). Partitioned tables have many.
	try:
		partition_count = frappe.db.sql(f"""
			SELECT COUNT(*) FROM information_schema.PARTITIONS 
			WHERE TABLE_SCHEMA = DATABASE() 
			AND TABLE_NAME = '{table_name}' 
			AND PARTITION_NAME IS NOT NULL
		""")[0][0]

		# If we find actual named partitions (more than just the default container)
		if partition_count > 1:
			frappe.log("✅ Table is already partitioned. Skipping setup to preserve dynamic partitions.")
			return
	except Exception as e:
		frappe.log(f"Warning checking partitions: {e}")

	# ========================================================
	# IF WE REACH HERE, THE TABLE IS NOT PARTITIONED YET
	# ========================================================

	# Step 1: Verify no NULL seasons
	null_count = frappe.db.sql(
		f"SELECT COUNT(*) FROM `{table_name}` WHERE season IS NULL OR season = ''",
		as_list=True
	)[0][0]

	if null_count > 0:
		frappe.throw(
			f"Cannot apply partitioning: {null_count} records have NULL season. "
			"Run fix_null_seasons patch first."
		)

	# Step 2: Remove existing partitioning (Safe here because we checked above)
	try:
		frappe.db.sql(f"ALTER TABLE `{table_name}` REMOVE PARTITIONING")
	except:
		pass

	# Step 3: Update Primary Key
	try:
		frappe.log("Updating Primary Key to composite (name, season)...")
		frappe.db.sql(f"ALTER TABLE `{table_name}` MODIFY `season` VARCHAR(140) NOT NULL")
		frappe.db.sql(f"ALTER TABLE `{table_name}` DROP PRIMARY KEY, ADD PRIMARY KEY (name, season)")
	except Exception as e:
		frappe.log(f"PK Update Note: {str(e)}")

	# Step 4: Get existing seasons from DATA
	seasons = frappe.db.sql(
		"""
		SELECT DISTINCT season
		FROM `tabPlayer Memory Tracker`
		WHERE season IS NOT NULL AND season != ''
		ORDER BY season
		""",
		as_list=True
	)
	seasons = [s[0] for s in seasons if s[0]]

	# Step 5: Build partition definitions
	partition_defs = []
	
	# A. From Data
	for season in seasons:
		escaped_season = frappe.db.escape(season)
		safe_name = season.replace("-", "_").replace(" ", "_").replace(".", "_").lower()[:50]
		partition_defs.append(f"PARTITION p_{safe_name} VALUES IN ({escaped_season})")

	# B. Safety for Empty
	if not any("p_empty" in p for p in partition_defs):
		partition_defs.append("PARTITION p_empty VALUES IN ('')")

	# C. Future Placeholders (Only needed for fresh install)
	future_years = ["SEASON-2026", "SEASON-2027", "SEASON-2028"]
	for future_season in future_years:
		if future_season not in seasons:
			escaped = frappe.db.escape(future_season)
			safe_name = future_season.replace("-", "_").lower()
			partition_defs.append(f"PARTITION p_{safe_name} VALUES IN ({escaped})")

	# Step 6: Apply Partitioning
	if partition_defs:
		partition_sql = ",\n\t\t\t".join(partition_defs)
		try:
			sql = f"""
				ALTER TABLE `{table_name}`
				PARTITION BY LIST COLUMNS(season) (
					{partition_sql}
				)
			"""
			frappe.db.sql(sql)
			frappe.log(f"Successfully applied LIST partitioning. Created {len(partition_defs)} partitions.")

		except Exception as e:
			frappe.log_error(f"Partitioning Failed: {e}")
			raise e

	# Step 7: Update flags
	frappe.db.sql("UPDATE `tabGame Subscription Season` SET partition_created = 1")
	frappe.log("setup_partitioning patch complete.")