"""
Wallet Engine Service

Manages XP accumulation and streak tracking with cache-first strategy.
Provides wallet read/write operations with Redis caching and batch sync queueing.

Key Functions:
- update_streak(): Update streak based on consecutive day logic
- add_xp(): Award XP with immediate Redis update
- get_wallet(): Cache-first wallet read
- get_wallet_safe(): Wallet read with Redis fallback to DB
- update_last_played_at(): Update timestamp with 15-min throttle

Streak Logic (server UTC time):
- First lesson: 0 → 1
- Next day (consecutive): N → N+1
- Same day: No change
- Gap > 1 day: Reset to 1 (not 0)

Wallet Sync Pattern:
- Write to Redis immediately (cache-first)
- Queue user for batch sync to DB (15-min interval)
- Throttle last_played_at DB writes (15-min per user)

Performance: <1s wallet display, <2ms streak updates.
"""

import frappe
from datetime import date, datetime
from memora.utils.redis_keys import get_wallet_key, get_pending_wallet_sync_key, get_last_played_at_synced_key


def update_streak(user_id, hearts_earned):
	"""
	FR-022 through FR-028: Streak calculation logic

	Args:
	    user_id (str): Frappe User.name
	    hearts_earned (int): Hearts from lesson (must be > 0 for streak update)

	Returns:
	    dict: Streak update result with old_streak, new_streak, streak_action
	"""
	# Only update streak if student earned hearts (successful lesson)
	if hearts_earned <= 0:
		return {"streak_action": "no_update", "reason": "hearts <= 0"}

	redis_client = frappe.cache()
	wallet_key = get_wallet_key(user_id)

	# Get current wallet state from Redis cache
	wallet = redis_client.hgetall(wallet_key)
	current_streak = int(wallet.get("current_streak", 0))
	last_success_date = wallet.get("last_success_date")

	# Use server UTC time to prevent client manipulation (FR-027)
	today = date.today()
	today_str = today.isoformat()

	# Streak state machine (FR-028):
	# 1. First lesson ever: streak 0 -> 1
	# 2. Same day: no change (FR-025 - only once per day)
	# 3. Next day (consecutive): increment (FR-023)
	# 4. Gap > 1 day: reset to 1, not 0 (FR-024 - for UX)
	if not last_success_date:
		# First lesson completion
		new_streak = 1
		action = "first_completion"
	elif last_success_date == today_str:
		# Already completed lesson today - maintain current streak
		new_streak = current_streak
		action = "maintained"
	elif is_consecutive_day(last_success_date, today):
		# Next consecutive day - increment streak
		new_streak = current_streak + 1
		action = "incremented"
	else:
		# Gap detected - reset streak to 1 (not 0 for better UX)
		new_streak = 1
		action = "reset"

	# Atomic update of streak and last_success_date in Redis
	streak_data = {"current_streak": new_streak, "last_success_date": today_str}
	for key, value in streak_data.items():
		redis_client.hset(wallet_key, key, value)

	# Queue for batch sync to MariaDB (FR-034)
	redis_client.sadd(get_pending_wallet_sync_key(), user_id)

	frappe.logger().info(f"Streak {action} for {user_id}: {current_streak} -> {new_streak}")

	return {
		"old_streak": current_streak,
		"new_streak": new_streak,
		"streak_action": action,
		"last_success_date": today_str,
	}


def is_consecutive_day(last_date_str, today):
	"""
	Check if today is exactly 1 day after last_date

	Args:
	    last_date_str (str): Last success date in YYYY-MM-DD format
	    today (date): Today's date object

	Returns:
	    bool: True if consecutive day, False otherwise
	"""
	last_date = date.fromisoformat(last_date_str)
	return (today - last_date).days == 1


def get_wallet(user_id):
	"""
	FR-019a: Cache-first wallet read

	Args:
	    user_id (str): Frappe User.name

	Returns:
	    dict: Wallet data with total_xp, current_streak, last_success_date, last_played_at
	"""
	redis_client = frappe.cache()
	wallet_key = get_wallet_key(user_id)

	wallet_data = redis_client.hgetall(wallet_key)

	if not wallet_data:
		profile_name = frappe.db.get_value("Memora Player Profile", {"user": user_id}, "name")

		if not profile_name:
			frappe.throw("Player profile not found")

		wallet_doc = frappe.get_doc("Memora Player Wallet", {"player": profile_name})

		wallet_data = {
			"total_xp": wallet_doc.total_xp,
			"current_streak": wallet_doc.current_streak,
			"last_success_date": wallet_doc.last_success_date or "",
			"last_played_at": wallet_doc.last_played_at or "",
		}

		for key, value in wallet_data.items():
			redis_client.hset(wallet_key, key, value)

	return wallet_data


def add_xp(user_id, xp_amount):
	"""
	FR-031: Award XP to student with immediate Redis update

	Args:
	    user_id (str): Frappe User.name
	    xp_amount (int): XP to add (must be positive)

	Returns:
	    int: New total XP after increment

	Raises:
	    frappe.ValidationError: If xp_amount is negative
	"""
	if xp_amount < 0:
		frappe.throw("XP amount cannot be negative", exc_type="ValidationError")

	redis_client = frappe.cache()
	wallet_key = get_wallet_key(user_id)

	new_total_xp = redis_client.hincrby(wallet_key, "total_xp", xp_amount)

	redis_client.sadd(get_pending_wallet_sync_key(), user_id)

	frappe.logger().info(f"XP awarded to {user_id}: +{xp_amount}, new total: {new_total_xp}")

	return new_total_xp


def get_wallet_safe(user_id):
	"""
	FR-019a: Cache-first wallet read with Redis fallback to DB

	Args:
	    user_id (str): Frappe User.name

	Returns:
	    dict: Wallet data with total_xp, current_streak, last_success_date, last_played_at
	"""
	redis_client = frappe.cache()
	wallet_key = get_wallet_key(user_id)

	try:
		wallet_data = redis_client.hgetall(wallet_key)
		if wallet_data:
			frappe.logger().debug(f"Cache hit for wallet: {user_id}")
			return wallet_data
	except Exception as e:
		frappe.log_error(f"Redis error reading wallet for {user_id}: {str(e)}")

	profile_name = frappe.db.get_value("Memora Player Profile", {"user": user_id}, "name")

	if not profile_name:
		frappe.throw("Player profile not found")

	wallet_doc = frappe.get_doc("Memora Player Wallet", {"player": profile_name})

	wallet_data = {
		"total_xp": wallet_doc.total_xp,
		"current_streak": wallet_doc.current_streak,
		"last_success_date": wallet_doc.last_success_date or "",
		"last_played_at": wallet_doc.last_played_at or "",
	}

	try:
		for key, value in wallet_data.items():
			redis_client.hset(wallet_key, key, value)
	except Exception as e:
		frappe.log_error(f"Redis error populating cache for {user_id}: {str(e)}")

	frappe.logger().debug(f"Cache miss for wallet: {user_id}, loaded from DB")

	return wallet_data


def update_last_played_at(user_id):
	"""
	FR-029: Record timestamp of last student interaction
	FR-030: Update with each authenticated API request
	FR-031: Throttle DB writes to every 15 minutes per student
	FR-032: Cache updates immediately even when DB write is throttled

	Args:
	    user_id (str): Frappe User.name

	Returns:
	    dict: Update result with timestamp and throttle status
	"""
	redis_client = frappe.cache()
	wallet_key = get_wallet_key(user_id)
	throttle_key = get_last_played_at_synced_key(user_id)

	now = datetime.utcnow()
	now_str = now.isoformat()

	# Update cache immediately (FR-032)
	redis_client.hset(wallet_key, "last_played_at", now_str)

	sync_required = False
	throttle_info = "throttled"

	# Check throttle: Only queue for DB sync if 15+ minutes since last write
	if not redis_client.exists(throttle_key):
		redis_client.setex(throttle_key, 900, "1")  # 900 seconds = 15 minutes
		redis_client.sadd(get_pending_wallet_sync_key(), user_id)
		sync_required = True
		throttle_info = "sync_queued"

	frappe.logger().info(
		f"Last played at updated for {user_id}: {now_str}, "
		f"sync_required={sync_required}, status={throttle_info}"
	)

	return {"timestamp": now_str, "sync_required": sync_required, "throttle_status": throttle_info}
