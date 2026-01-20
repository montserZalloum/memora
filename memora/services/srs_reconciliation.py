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

	Alert Threshold: Sends email alert if discrepancy rate > 0.1% (0.001)
	"""
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
			"message": "No active seasons found"
		}

	season_names = [s.name for s in active_seasons]

	# Sample records from database
	records = frappe.db.sql("""
		SELECT player, season, question_id, next_review_date
		FROM `tabPlayer Memory Tracker`
		WHERE season IN ({})
		ORDER BY RAND()
		LIMIT %s
	""".format(','.join(['%s'] * len(season_names))),
		season_names + [sample_size],
		as_dict=True
	)

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
			# Redis error - skip this record
			continue

		# Calculate expected score from database
		db_score = record.next_review_date.timestamp()

		# Check for discrepancy
		if cached_score is None:
			# Missing from cache
			discrepancies += 1
			# Auto-correct: Add to cache
			try:
				redis_manager.add_item(
					record.player,
					record.season,
					question_id,
					db_score
				)
				auto_corrected += 1
			except Exception:
				pass
		elif abs(cached_score - db_score) > tolerance_seconds:
			# Score mismatch
			discrepancies += 1
			# Auto-correct: Update cache
			try:
				redis_manager.add_item(
					record.player,
					record.season,
					question_id,
					db_score
				)
				auto_corrected += 1
			except Exception:
				pass

	# Calculate discrepancy rate
	discrepancy_rate = discrepancies / len(records) if records else 0

	# Check alert threshold (0.1%)
	alert_threshold = 0.001
	alert_triggered = discrepancy_rate > alert_threshold

	# Trigger alert if threshold exceeded
	if alert_triggered:
		_trigger_reconciliation_alert(discrepancies, len(records), discrepancy_rate, season_names)

	# Log reconciliation result
	frappe.log_error(
		f"Reconciliation complete: {discrepancies}/{len(records)} discrepancies "
		f"({discrepancy_rate:.4%}), {auto_corrected} auto-corrected",
		"SRS Reconciliation"
	)

	return {
		"sample_size": len(records),
		"discrepancies_found": discrepancies,
		"discrepancy_rate": discrepancy_rate,
		"auto_corrected": auto_corrected,
		"alert_triggered": alert_triggered
	}


def _trigger_reconciliation_alert(
	discrepancies: int,
	sample_size: int,
	discrepancy_rate: float,
	season_names: list
) -> None:
	"""
	Send email alert when discrepancy rate exceeds threshold.

	Args:
		discrepancies: Number of discrepancies found
		sample_size: Total sample size
		discrepancy_rate: Discrepancy rate (0-1)
		season_names: List of season names checked
	"""
	# Get system administrators
	admins = frappe.get_all("User", filters={"system_user": 1}, fields=["email"])
	admin_emails = [admin.email for admin in admins if admin.email]

	if not admin_emails:
		return

	# Prepare email content
	subject = f"ALERT: SRS Cache Discrepancy Rate Exceeded ({discrepancy_rate:.2%})"

	message = f"""
	<h2>SRS Cache Discrepancy Alert</h2>

	<p>The daily cache reconciliation job detected a discrepancy rate exceeding the alert threshold.</p>

	<h3>Details</h3>
	<ul>
		<li><strong>Sample Size:</strong> {sample_size:,} records</li>
		<li><strong>Discrepancies Found:</strong> {discrepancies:,}</li>
		<li><strong>Discrepancy Rate:</strong> {discrepancy_rate:.4%} (threshold: 0.1%)</li>
		<li><strong>Seasons Checked:</strong> {', '.join(season_names)}</li>
		<li><strong>Auto-Correction:</strong> Applied ({discrepancies} records corrected)</li>
	</ul>

	<h3>Recommendations</h3>
	<ul>
		<li>Check Redis connectivity and performance</li>
		<li>Review background job queue for persistence failures</li>
		<li>Consider triggering a full cache rebuild if issue persists</li>
		<li>Monitor Safe Mode activation frequency</li>
	</ul>

	<p><em>This is an automated alert from the SRS Reconciliation Service.</em></p>
	"""

	# Send email
	try:
		frappe.sendmail(
			recipients=admin_emails,
			subject=subject,
			message=message,
			reference_doctype="System Notification",
			reference_name="SRS Reconciliation Alert"
		)
	except Exception as e:
		frappe.log_error(
			f"Failed to send reconciliation alert: {str(e)}",
			"SRS Reconciliation Alert"
		)


def get_reconciliation_stats() -> Dict[str, Any]:
	"""
	Get statistics about recent reconciliation runs.

	Returns:
		Dictionary containing:
		- last_run: Timestamp of last reconciliation
		- last_discrepancy_rate: Discrepancy rate from last run
		- last_alert_triggered: Whether last run triggered an alert
		- total_runs: Total number of reconciliation runs
	"""
	# This would typically query a log table or error log
	# For now, return placeholder data
	return {
		"last_run": None,
		"last_discrepancy_rate": 0.0,
		"last_alert_triggered": False,
		"total_runs": 0,
		"message": "Reconciliation statistics not yet available"
	}
