# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Partition Manager Service

This module provides database partition management for Player Memory Tracker table.
Partitions are created automatically when new Game Subscription Seasons are created.
"""

import frappe

def create_season_partition(season_name: str) -> bool:
	"""
	Create a LIST partition for the Player Memory Tracker table.
	Safe to run even if table is not yet partitioned.
	"""
	if not season_name:
		frappe.throw("Season name cannot be empty", exc=frappe.ValidationError)

	# CHECK 1: Is the table partitioned?
	# If not, we skip this step. The setup_partitioning patch will handle it later.
	if not is_table_partitioned():
		frappe.logger().info(f"Skipping partition creation for {season_name} (Table not partitioned yet)")
		return True

	# 1. Sanitize partition name
	safe_partition_name = f"p_{season_name.replace('-', '_').replace('.', '_').replace(' ', '_').lower()[:50]}"
	escaped_season = frappe.db.escape(season_name)

	# SQL to create partition
	sql = f"""
		ALTER TABLE `tabPlayer Memory Tracker`
		ADD PARTITION (
			PARTITION {safe_partition_name} VALUES IN ({escaped_season})
		)
	"""

	try:
		frappe.db.sql(sql, as_dict=False)
		frappe.db.commit()
		frappe.logger().info(f"Created partition '{safe_partition_name}' for season '{season_name}'")
		return True

	except Exception as e:
		error_str = str(e)
		if "Duplicate partition name" in error_str or "already exists" in error_str:
			return True
		else:
			frappe.logger().error(f"Failed to create partition for season '{season_name}': {e}")
			raise e

def is_table_partitioned() -> bool:
	"""Check if the table is actually partitioned"""
	try:
		count = frappe.db.sql("""
			SELECT COUNT(*) FROM information_schema.PARTITIONS 
			WHERE TABLE_SCHEMA = DATABASE() 
			AND TABLE_NAME = 'tabPlayer Memory Tracker' 
			AND PARTITION_NAME IS NOT NULL
		""")[0][0]
		# If count > 1, it means we have partitions (other than the default table container)
		# Note: Unpartitioned InnoDB tables show 1 row in partitions table usually (p0 or null)
		# But to be safe, we rely on the setup patch to have run.
		# A safer check: does it have the partitions we expect?
		# Let's assume if count <= 1 it's not properly set up for our logic yet.
		return count > 1
	except:
		return False


def check_partition_exists(season_name: str) -> bool:
	"""
	Check if a partition exists for the given season.
	"""
	if not season_name:
		return False

	safe_partition_name = f"p_{season_name.replace('-', '_').replace('.', '_').replace(' ', '_').lower()[:50]}"

	sql = """
		SELECT COUNT(*) as count
		FROM information_schema.PARTITIONS
		WHERE
			TABLE_SCHEMA = DATABASE() AND
			TABLE_NAME = 'tabPlayer Memory Tracker' AND
			PARTITION_NAME = %s
	"""

	try:
		result = frappe.db.sql(sql, safe_partition_name, as_dict=True)
		return result and result[0].get('count', 0) > 0

	except Exception as e:
		frappe.logger().error(f"Error checking partition existence: {e}")
		return False


def get_all_partitions() -> list:
	"""Get all partitions for the Player Memory Tracker table."""
	sql = """
		SELECT PARTITION_NAME as partition_name, PARTITION_DESCRIPTION as season
		FROM information_schema.PARTITIONS
		WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tabPlayer Memory Tracker'
		AND PARTITION_NAME IS NOT NULL
		ORDER BY PARTITION_ORDINAL_POSITION
	"""
	try:
		return frappe.db.sql(sql, as_dict=True) or []
	except:
		return []


def get_partition_stats(season_name: str = None) -> list:
	"""Get statistics for partitions."""
	try:
		if season_name:
			safe_name = f"p_{season_name.replace('-', '_').replace('.', '_').replace(' ', '_').lower()[:50]}"
			sql = """
				SELECT PARTITION_NAME as partition_name, PARTITION_DESCRIPTION as season,
				TABLE_ROWS as table_rows, DATA_LENGTH as data_length, INDEX_LENGTH as index_length
				FROM information_schema.PARTITIONS
				WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tabPlayer Memory Tracker'
				AND PARTITION_NAME = %s
			"""
			return frappe.db.sql(sql, safe_name, as_dict=True) or []
		else:
			sql = """
				SELECT PARTITION_NAME as partition_name, PARTITION_DESCRIPTION as season,
				TABLE_ROWS as table_rows, DATA_LENGTH as data_length, INDEX_LENGTH as index_length
				FROM information_schema.PARTITIONS
				WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tabPlayer Memory Tracker'
				AND PARTITION_NAME IS NOT NULL
				ORDER BY PARTITION_ORDINAL_POSITION
			"""
			return frappe.db.sql(sql, as_dict=True) or []
	except:
		return []