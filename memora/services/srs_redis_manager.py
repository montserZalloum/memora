# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
SRS Redis Manager

This module provides a wrapper around Redis for managing SRS (Spaced Repetition System)
schedules using Redis Sorted Sets (ZSET). Each user's review schedule is stored
as a sorted set with question IDs as members and next review timestamps as scores.

Key Format: srs:{user_email}:{season_name}
Score: Unix timestamp (float) of next_review_date
Member: question_id (string)
"""

import frappe
import redis
import time
from typing import List, Optional, Dict, Tuple, Any
from collections import defaultdict


class SRSRedisManager:
	"""
	Manages Redis Sorted Sets for SRS scheduling

	This class provides methods for:
	- Adding/updating review schedules (ZADD)
	- Retrieving due items (ZRANGEBYSCORE)
	- Removing items (ZREM)
	- Health checking
	- Batch operations
	"""

	# Default TTL for user-season keys (30 days in seconds)
	# Keys are automatically expired after this period for inactive users
	DEFAULT_TTL = 30 * 24 * 60 * 60  # 30 days

	# Default Redis URL if not configured
	DEFAULT_REDIS_URL = "redis://localhost:13000"

	def __init__(self):
		"""Initialize Redis connection"""
		self.redis = self._get_redis_connection()

	def _get_redis_connection(self):
		"""
		Get Redis connection from Frappe config dynamically.
		Priority:
		1. 'srs_redis_cache' key in site_config (Specific for this feature)
		2. 'redis_cache' key in site_config (Standard Frappe Cache)
		3. Fallback to localhost
		"""
		try:
			# 1. Check for specific SRS Redis config first
			redis_url = frappe.conf.get("srs_redis_cache")
			
			# 2. Fallback to standard Frappe Redis cache
			if not redis_url:
				redis_url = frappe.conf.get("redis_cache")
			
			# 3. Ultimate Fallback (Safety Net)
			if not redis_url:
				redis_url = "redis://localhost:13000"

			return redis.from_url(redis_url, decode_responses=True)

		except Exception as e:
			frappe.log_error(
				f"Failed to connect to Redis: {str(e)}",
				"SRSRedisManager"
			)
			raise

	def _set_ttl_if_new(self, key: str, ttl: int) -> None:
		"""
		Set TTL on a Redis key only if it doesn't already have one

		This prevents resetting TTL on active users when they add new items.

		Args:
			key: Redis key to set TTL on
			ttl: Time-to-live in seconds
		"""
		# Only set expiry if key doesn't already have one (-1 means no expiry set)
		if self.redis.ttl(key) == -1:
			self.redis.expire(key, ttl)

	def _make_key(self, user: str, season: str) -> str:
		"""
		Generate Redis key for user-season combination

		Args:
			user: User email or ID
			season: Season name

		Returns:
			str: Redis key in format srs:{user}:{season}
		"""
		return f"srs:{user}:{season}"

	def is_available(self) -> bool:
		"""
		Check if Redis is available

		Returns:
			bool: True if Redis is responsive, False otherwise
		"""
		try:
			self.redis.ping()
			return True
		except Exception:
			return False

	def add_item(self, user: str, season: str, question_id: str, next_review_ts: float, ttl: Optional[int] = None) -> bool:
		"""
		Add or update a question's review schedule in Redis

		Args:
			user: User email or ID
			season: Season name
			question_id: UUID of the question
			next_review_ts: Unix timestamp of next review date
			ttl: Time-to-live in seconds for the key (defaults to DEFAULT_TTL if not set)

		Returns:
			bool: True if successful, False otherwise
		"""
		try:
			key = self._make_key(user, season)
			self.redis.zadd(key, {question_id: next_review_ts})

			# Set TTL for automatic cleanup of inactive users
			self._set_ttl_if_new(key, ttl if ttl is not None else self.DEFAULT_TTL)

			return True
		except Exception as e:
			frappe.log_error(
				f"Failed to add item to Redis: {str(e)}",
				"SRSRedisManager.add_item"
			)
			return False

	def get_due_items(self, user: str, season: str, limit: int = 20) -> List[str]:
		"""
		Get question IDs due for review

		Args:
			user: User email or ID
			season: Season name
			limit: Maximum number of items to return

		Returns:
			List[str]: List of question IDs due for review
		"""
		try:
			key = self._make_key(user, season)
			now = time.time()
			items = self.redis.zrangebyscore(key, "-inf", now, start=0, num=limit)
			return items if items else []
		except Exception as e:
			frappe.log_error(
				f"Failed to get due items from Redis: {str(e)}",
				"SRSRedisManager.get_due_items"
			)
			return []

	def remove_item(self, user: str, season: str, question_id: str) -> bool:
		"""
		Remove a question from the review schedule

		Args:
			user: User email or ID
			season: Season name
			question_id: UUID of the question

		Returns:
			bool: True if successful, False otherwise
		"""
		try:
			key = self._make_key(user, season)
			self.redis.zrem(key, question_id)
			return True
		except Exception as e:
			frappe.log_error(
				f"Failed to remove item from Redis: {str(e)}",
				"SRSRedisManager.remove_item"
			)
			return False

	def add_batch(self, user: str, season: str, items: Dict[str, float], ttl: Optional[int] = None) -> bool:
		"""
		Add multiple items to the review schedule in a single operation

		Args:
			user: User email or ID
			season: Season name
			items: Dictionary mapping question_id -> next_review_ts
			ttl: Time-to-live in seconds for the key (defaults to DEFAULT_TTL if not set)

		Returns:
			bool: True if successful, False otherwise
		"""
		try:
			key = self._make_key(user, season)
			self.redis.zadd(key, items)

			# Set TTL for automatic cleanup of inactive users
			self._set_ttl_if_new(key, ttl if ttl is not None else self.DEFAULT_TTL)

			return True
		except Exception as e:
			frappe.log_error(
				f"Failed to add batch to Redis: {str(e)}",
				"SRSRedisManager.add_batch"
			)
			return False

	def get_all_scores(self, user: str, season: str) -> Dict[str, float]:
		"""
		Get all items and their scores for a user-season combination

		Args:
			user: User email or ID
			season: Season name

		Returns:
			Dict[str, float]: Dictionary mapping question_id -> next_review_ts
		"""
		try:
			key = self._make_key(user, season)
			items = self.redis.zrange(key, 0, -1, withscores=True)
			return dict(items) if items else {}
		except Exception as e:
			frappe.log_error(
				f"Failed to get all scores from Redis: {str(e)}",
				"SRSRedisManager.get_all_scores"
			)
			return {}

	def count_due_items(self, user: str, season: str) -> int:
		"""
		Count the number of items due for review

		Args:
			user: User email or ID
			season: Season name

		Returns:
			int: Number of due items
		"""
		try:
			key = self._make_key(user, season)
			now = time.time()
			return self.redis.zcount(key, "-inf", now)
		except Exception as e:
			frappe.log_error(
				f"Failed to count due items in Redis: {str(e)}",
				"SRSRedisManager.count_due_items"
			)
			return 0

	def _rehydrate_user_cache(self, user: str, season: str) -> List[str]:
		"""
		Lazy load user's review schedule from database on cache miss

		This method is called when Redis cache is empty for a user-season pair.
		It loads records from the database and populates Redis.

		Args:
			user: User email or ID
			season: Season name

		Returns:
			List[str]: List of question IDs that are currently due
		"""
		try:
			# Fetch all records for this user-season
			# Note: In future optimization phases, we might want to filter this 
			# to only upcoming reviews (e.g., next 30 days) to save RAM.
			records = frappe.get_all(
				"Player Memory Tracker",
				filters={
					"player": user,
					"season": season
				},
				fields=["question_id", "next_review_date"]
			)

			if not records:
				return []

			# Build batch update
			items = {}
			due_items = []
			now = time.time()

			for record in records:
				if record.next_review_date:
					score = record.next_review_date.timestamp()
					items[record.question_id] = score

					# Track due items for immediate return
					if score <= now:
						due_items.append(record.question_id)

			# Batch add to Redis with TTL
			if items:
				self.add_batch(user, season, items, ttl=self.DEFAULT_TTL)

			return due_items

		except Exception as e:
			frappe.log_error(
				f"Failed to rehydrate user cache: {str(e)}",
				"SRSRedisManager._rehydrate_user_cache"
			)
			return []

	def get_due_items_with_rehydration(
		self,
		user: str,
		season: str,
		limit: int = 20
	) -> Tuple[List[str], bool]:
		"""
		Get due items with automatic cache rehydration on miss

		Args:
			user: User email or ID
			season: Season name
			limit: Maximum number of items to return

		Returns:
			Tuple[List[str], bool]: (due_items, was_rehydrated)
		"""
		items = self.get_due_items(user, season, limit)

		# Cache miss detection: Check if key exists to distinguish between
		# "cache is empty" vs "no items are due"
		if not items:
			key = self._make_key(user, season)
			key_exists = self.redis.exists(key)

			if not key_exists:
				# True cache miss - try rehydration
				items = self._rehydrate_user_cache(user, season)
				if items:
					# Return only requested limit after rehydration
					# The full set is in Redis now, so we just return the slice requested
					items = items[:limit]
					return items, True

		return items, False

	def clear_user_cache(self, user: str, season: str) -> bool:
		"""
		Clear all review schedule data for a user-season pair

		Args:
			user: User email or ID
			season: Season name

		Returns:
			bool: True if successful, False otherwise
		"""
		try:
			key = self._make_key(user, season)
			self.redis.delete(key)
			return True
		except Exception as e:
			frappe.log_error(
				f"Failed to clear user cache: {str(e)}",
				"SRSRedisManager.clear_user_cache"
			)
			return False

	def get_cache_stats(self, user: str, season: str) -> Dict:
		"""
		Get statistics about a user's cache

		Args:
			user: User email or ID
			season: Season name

		Returns:
			Dict: Statistics including total_items, due_items, memory_usage_bytes
		"""
		try:
			key = self._make_key(user, season)
			total_items = self.redis.zcard(key)
			due_items = self.count_due_items(user, season)
			memory_usage = self.redis.memory_usage(key) if total_items > 0 else 0

			return {
				"total_items": total_items,
				"due_items": due_items,
				"memory_usage_bytes": memory_usage
			}
		except Exception as e:
			frappe.log_error(
				f"Failed to get cache stats: {str(e)}",
				"SRSRedisManager.get_cache_stats"
			)
			return {
				"total_items": 0,
				"due_items": 0,
				"memory_usage_bytes": 0
			}


def rebuild_season_cache(season_name: str, batch_size: int = 1000) -> Dict[str, Any]:
	"""
	Rebuild Redis cache for an entire season with progress tracking.

	This is a background job that rebuilds cache by loading all
	Player Memory Tracker records for a season and populating Redis.
	
	OPTIMIZATION: Uses Keyset Pagination (Seek Method) instead of OFFSET
	to ensure O(1) performance regardless of table size (1B+ records compatible).

	Args:
		season_name: Name of season to rebuild cache for
		batch_size: Number of records to process per batch (default: 1000)

	Returns:
		Dictionary with rebuild results:
		- total_records: Total records processed
		- total_users: Number of unique users
		- total_keys: Number of Redis keys created
		- status: "completed" or "failed"
	"""
	try:
		# Get total record count for progress tracking
		# Note: This might be slow on first run but useful for UI progress bars
		total_records = frappe.db.count(
			"Player Memory Tracker",
			filters={"season": season_name}
		)

		if total_records == 0:
			return {
				"total_records": 0,
				"total_users": 0,
				"total_keys": 0,
				"status": "completed",
				"message": "No records found for season"
			}

		processed = 0
		users_processed = set()
		keys_created = 0
		
		# Keyset Pagination Cursor
		last_name = ""

		# Process using seek method (WHERE name > last_name)
		while True:
			# Fetch batch of records efficiently using primary key index
			records = frappe.db.sql("""
				SELECT name, player, question_id, next_review_date
				FROM `tabPlayer Memory Tracker`
				WHERE season = %s AND name > %s
				ORDER BY name ASC
				LIMIT %s
			""", (season_name, last_name, batch_size), as_dict=True)

			if not records:
				break

			# Update cursor for next iteration
			last_name = records[-1].name

			# Group records by user for batch insertion
			by_user = defaultdict(list)
			for record in records:
				by_user[record.player].append(record)
				users_processed.add(record.player)

			# Batch insert to Redis
			redis_manager = SRSRedisManager()
			for user, items in by_user.items():
				redis_items = {}
				for item in items:
					if item.next_review_date:
						redis_items[item.question_id] = item.next_review_date.timestamp()

				if redis_items:
					redis_manager.add_batch(
						user,
						season_name,
						redis_items,
						ttl=SRSRedisManager.DEFAULT_TTL
					)
					keys_created += 1

			processed += len(records)

			# Publish progress (only every 5% to reduce overhead)
			if total_records > 0 and processed % (batch_size * 5) == 0:
				progress_percent = int((processed / total_records) * 100)
				frappe.publish_progress(
					progress_percent,
					title=f"Rebuilding cache for {season_name}",
					description=f"Processed {processed:,} of {total_records:,} records"
				)

		# Log completion
		frappe.log_error(
			f"Cache rebuild completed for {season_name}: "
			f"{processed} records, {len(users_processed)} users, {keys_created} keys",
			"SRS Cache Rebuild"
		)

		return {
			"total_records": processed,
			"total_users": len(users_processed),
			"total_keys": keys_created,
			"status": "completed"
		}

	except Exception as e:
		frappe.log_error(
			f"Cache rebuild failed for {season_name}: {str(e)}",
			"SRS Cache Rebuild"
		)
		return {
			"total_records": processed if 'processed' in locals() else 0,
			"total_users": len(users_processed) if 'users_processed' in locals() else 0,
			"total_keys": keys_created if 'keys_created' in locals() else 0,
			"status": "failed",
			"error": str(e)
		}