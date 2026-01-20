"""
Shared utility functions for the Memora API.

This module contains helper functions that are used across multiple
domain modules to avoid code duplication.
"""

import time

import frappe
from frappe.utils import now_datetime, get_datetime


class SafeModeManager:
	"""
	Manages Safe Mode functionality for SRS when Redis is unavailable

	Safe Mode provides degraded service with rate limiting to prevent
	database overload during Redis outages.

	Rate Limits:
	- Global: 500 requests per minute
	- Per-user: 1 request per 30 seconds
	"""

	GLOBAL_LIMIT = 500  # requests per minute
	USER_LIMIT_SECONDS = 30  # seconds between requests per user
	GLOBAL_KEY = "safe_mode_global_requests"
	USER_KEY_PREFIX = "safe_mode_rate"

	def __init__(self):
		"""Initialize Safe Mode Manager"""
		self.redis_manager = None
		try:
			from memora.services.srs_redis_manager import SRSRedisManager
			self.redis_manager = SRSRedisManager()
		except Exception as e:
			# Import failed - will use Safe Mode
			frappe.log_error(
				f"Failed to initialize SRSRedisManager in SafeModeManager: {str(e)}",
				"SafeModeManager.__init__"
			)

	def is_safe_mode_active(self) -> bool:
		"""
		Check if Safe Mode is active (Redis unavailable)

		Returns:
			bool: True if Safe Mode is active, False otherwise
		"""
		if not self.redis_manager:
			# Redis manager not available - Safe Mode active
			return True

		# Check Redis connectivity
		try:
			return not self.redis_manager.is_available()
		except Exception:
			# Error checking Redis - assume Safe Mode
			return True

	def check_rate_limit(self, user: str) -> bool:
		"""
		Check if user is rate limited in Safe Mode

		Implements both global and per-user rate limiting.

		Args:
			user: User email or ID

		Returns:
			bool: True if request is allowed, False if rate limited
		"""
		now = time.time()

		# 1. Check global rate limit (500 req/min)
		global_count = frappe.cache().get(self.GLOBAL_KEY) or 0
		if global_count >= self.GLOBAL_LIMIT:
			# Global limit exceeded
			return False

		# 2. Check per-user rate limit (1 req/30s)
		user_key = f"{self.USER_KEY_PREFIX}:{user}"
		last_request = frappe.cache().get(user_key)

		if last_request and (now - last_request) < self.USER_LIMIT_SECONDS:
			# User rate limited
			return False

		# 3. Update counters atomically
		# Increment global counter
		new_global_count = frappe.cache().incr(self.GLOBAL_KEY)

		# Always ensure TTL is set on the global counter to prevent orphaned keys
		# This is idempotent and safe to call on every request
		# TTL only resets if key was newly created (incr returns 1) or has no TTL
		try:
			ttl = frappe.cache().ttl(self.GLOBAL_KEY)
			if ttl is None or ttl < 0:
				# No TTL set, set it now (60 seconds = 1 minute window)
				frappe.cache().expire(self.GLOBAL_KEY, 60)
		except Exception:
			# If TTL check fails, try to set expiry anyway as a safety measure
			if new_global_count == 1:
				frappe.cache().expire(self.GLOBAL_KEY, 60)

		# Update user's last request time
		frappe.cache().set(user_key, now, expires_in=self.USER_LIMIT_SECONDS)

		return True

	def get_global_request_count(self) -> int:
		"""
		Get current global request count for Safe Mode

		Returns:
			int: Number of requests in current minute
		"""
		return frappe.cache().get(self.GLOBAL_KEY) or 0

	def get_user_last_request(self, user: str) -> float:
		"""
		Get user's last Safe Mode request timestamp

		Args:
			user: User email or ID

		Returns:
			float: Unix timestamp of last request, or 0 if no requests
		"""
		user_key = f"{self.USER_KEY_PREFIX}:{user}"
		return frappe.cache().get(user_key) or 0

	def reset_user_rate_limit(self, user: str):
		"""
		Reset rate limit for a specific user (admin function)

		Args:
			user: User email or ID
		"""
		user_key = f"{self.USER_KEY_PREFIX}:{user}"
		frappe.cache().delete(user_key)

	def reset_global_rate_limit(self):
		"""
		Reset global rate limit counter (admin function)
		"""
		frappe.cache().delete(self.GLOBAL_KEY)





def get_user_active_subscriptions(user):
    """
    Get user's active subscriptions.

    Logic:
    1. Depends on the linked season's end date, not the subscription itself.
    2. Fetches the correct profile name for safety.

    Args:
        user: User ID

    Returns:
        List of access items with type, subject, and/or track fields
    """
    # 1. Safe profile name fetch (Best Practice)
    # This protects you if you decide to rename the profile in the future
    profile_name = frappe.db.get_value("Player Profile", {"user": user}, "name")

    if not profile_name:
        return []

    # 2. Smart query (SQL Join)
    # Join subscriptions table with seasons table to verify the date
    active_subs = frappe.db.sql("""
        SELECT
            sub.name, sub.type
        FROM
            `tabGame Player Subscription` sub
        JOIN
            `tabGame Subscription Season` season ON sub.linked_season = season.name
        WHERE
            sub.player = %s
            AND sub.status = 'Active'
            AND season.end_date >= CURDATE()
    """, (profile_name,), as_dict=True)

    # 3. Aggregate items (Items Retrieval)
    final_access_list = []

    for sub in active_subs:
        if sub.type == 'Global Access':
            final_access_list.append({"type": "Global"})
        else:
            # Fetch specific subjects from child table
            items = frappe.get_all("Game Subscription Access",
                filters={"parent": sub.name},
                fields=["type", "subject", "track"]
            )
            final_access_list.extend(items)

    return final_access_list


def check_subscription_access(active_subs, subject_id, track_id=None):
    """
    Check if user's subscriptions cover this subject or track.

    Args:
        active_subs: List from get_user_active_subscriptions()
        subject_id: Subject ID to check
        track_id: Optional track ID to check

    Returns:
        bool: True if user has access, False otherwise
    """
    for access in active_subs:
        # 1. Global subscription
        if access.get("type") == "Global":
            return True

        # 2. Subject subscription
        if access.get("type") == "Subject" and access.get("subject") == subject_id:
            return True

        # 3. Track subscription (if provided)
        if track_id and access.get("type") == "Track" and access.get("track") == track_id:
            return True

    return False
