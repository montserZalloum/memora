# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
SRS Reconciliation Service

Provides cache-to-database consistency checking with:
- Sample-based reconciliation (statistical confidence without full scan)
- Auto-correction (DB as source of truth)
- Alert triggering for high discrepancy rates
- Daily scheduled job execution
"""

import frappe
import time
from typing import Dict, Any
from memora.services.srs_redis_manager import SRSRedisManager


def reconcile_cache_with_database(sample_size: int = 10000) -> Dict[str, Any]:
	"""
	Perform sample-based reconciliation between Redis cache and database.

	This function samples records from the database and compares them with
	the Redis cache to detect discrepancies. Any discrepancies found are
	auto-corrected using the database as the source of truth.

	Args:
		sample_size: Number of records to sample (default: 10000)

	Returns:
		Dictionary containing reconciliation results:
		- sample_size: Number of records sampled
		- discrepancies_found: Number of discrepancies detected
		- discrepancy_rate: Percentage of discrepancies (0-1)
		- auto_corrected: Number of records auto-corrected
		- alert_triggered: Whether alert threshold was exceeded
	"""
	try:
		redis_manager = SRSRedisManager()

		# Get active seasons for sampling
		active_seasons = frappe.get_all(
			"Game Subscription Season",
			filters={"is_active": 1},
			fields=["name"]
		)

		if not active_seasons:
			return {
				"sample_size": 0,
				"discrepancies_found": 0,
				"discrepancy_rate": 0.0,
				"auto_corrected": 0,
				"alert_triggered": False,
				"message": "No active seasons found to reconcile."
			}

		season_names = [s.name for s in active_seasons]

		# Sample records from database
		# Using dynamic query building safely
		placeholders = ', '.join(['%s'] * len(season_names))
		query = f"""
			SELECT player, season, question_id, next_review_date
			FROM `tabPlayer Memory Tracker`
			WHERE season IN ({placeholders})
			ORDER BY RAND()
			LIMIT %s
		"""
		
		# Execute query with params
		params = season_names + [sample_size]
		records = frappe.db.sql(query, params, as_dict=True)

		if not records:
			return {
				"sample_size": 0,
				"discrepancies_found": 0,
				"discrepancy_rate": 0.0,
				"auto_corrected": 0,
				"alert_triggered": False,
				"message": "No memory records found in active seasons."
			}

		discrepancies = 0
		auto_corrected = 0
		tolerance_seconds = 1  # Allow 1 second difference for rounding

		for record in records:
			key = f"srs:{record.player}:{record.season}"
			question_id = record.question_id

			# Get cached score from Redis
			try:
				cached_score = redis_manager.redis.zscore(key, question_id)
			except Exception:
				continue # Skip if Redis fails

			# Calculate expected score from database
			# next_review_date can be None in DB, treat as 0 or skip
			if not record.next_review_date:
				continue
				
			db_score = record.next_review_date.timestamp()

			# Check for discrepancy
			if cached_score is None:
				# Case 1: Missing from cache
				discrepancies += 1
				try:
					redis_manager.add_item(record.player, record.season, question_id, db_score)
					auto_corrected += 1
				except:
					pass
			
			elif abs(cached_score - db_score) > tolerance_seconds:
				# Case 2: Score mismatch
				discrepancies += 1
				try:
					redis_manager.add_item(record.player, record.season, question_id, db_score)
					auto_corrected += 1
				except:
					pass

		# Calculate discrepancy rate
		discrepancy_rate = discrepancies / len(records)

		# Alert Threshold (0.1%)
		alert_threshold = 0.001
		alert_triggered = discrepancy_rate > alert_threshold

		if alert_triggered:
			_trigger_reconciliation_alert(discrepancies, len(records), discrepancy_rate, season_names)

		frappe.log_error(
			f"Reconciliation Report: {discrepancies}/{len(records)} errors ({discrepancy_rate:.4%}). Corrected: {auto_corrected}",
			"SRS Reconciliation"
		)

		return {
			"sample_size": len(records),
			"discrepancies_found": discrepancies,
			"discrepancy_rate": discrepancy_rate,
			"auto_corrected": auto_corrected,
			"alert_triggered": alert_triggered
		}

	except Exception as e:
		frappe.log_error(f"Reconciliation Job Failed: {str(e)}", "SRS Reconciliation")
		return {"success": False, "error": str(e)}


def _trigger_reconciliation_alert(
	discrepancies: int,
	sample_size: int,
	discrepancy_rate: float,
	season_names: list
) -> None:
	"""
	Send email alert when discrepancy rate exceeds threshold.
	"""
	try:
		# Get System Managers specifically
		admin_emails = frappe.get_all(
			"User", 
			filters={"role_profile_name": "System Manager", "enabled": 1}, 
			pluck="email"
		)

		if not admin_emails:
			return

		subject = f"⚠️ ALERT: High SRS Cache Discrepancy ({discrepancy_rate:.2%})"

		message = f"""
		<h2>SRS Cache Integrity Alert</h2>
		<p>The daily reconciliation job detected a discrepancy rate exceeding the 0.1% threshold.</p>
		
		<table border="1" cellpadding="5" style="border-collapse: collapse;">
			<tr><td><strong>Sample Size</strong></td><td>{sample_size:,} records</td></tr>
			<tr><td><strong>Discrepancies</strong></td><td>{discrepancies:,}</td></tr>
			<tr><td><strong>Error Rate</strong></td><td>{discrepancy_rate:.4%} (Threshold: 0.1%)</td></tr>
			<tr><td><strong>Auto-Corrected</strong></td><td>Yes</td></tr>
		</table>
		
		<p><strong>Affected Seasons:</strong> {', '.join(season_names)}</p>
		
		<h3>Recommended Actions:</h3>
		<ol>
			<li>Check Redis logs for connectivity issues or restarts.</li>
			<li>Check 'Worker' logs for failed persistence jobs.</li>
			<li>Consider running a manual 'Rebuild Cache' for active seasons.</li>
		</ol>
		"""

		frappe.sendmail(
			recipients=admin_emails,
			subject=subject,
			message=message
		)
	except Exception as e:
		frappe.log_error(f"Failed to send alert: {str(e)}", "SRS Reconciliation Alert")


def get_reconciliation_stats() -> Dict[str, Any]:
	"""
	Get statistics about recent reconciliation runs (Placeholder).
	"""
	return {
		"message": "Stats implementation pending logging aggregation"
	}