"""
Wallet Synchronization Service

Manages batch synchronization of wallet updates from Redis to MariaDB.
Processes pending wallet updates in chunks to reduce DB load by 90%+.

Key Functions:
- sync_pending_wallets(): Main sync job (runs every 15 minutes)
- _bulk_update_wallets(): Bulk SQL update using CASE statements
- trigger_wallet_sync(): Manual sync trigger for admin testing
- chunk_list(): Utility to split lists into chunks

Sync Pattern:
1. Read pending user IDs from Redis SET
2. Chunk into groups of 500 players
3. Bulk read wallet data from Redis
4. Bulk update MariaDB using SQL CASE (optimal performance)
5. Remove synced users from pending queue

Error Handling:
- Chunk-level errors are logged and retried
- Failed chunks are re-added to pending queue
- Critical errors are logged but don't crash the scheduler

Performance: <5min for 50k players, 90%+ DB write reduction.
"""

import frappe
import time


def chunk_list(lst, chunk_size):
    """
    Split a list into chunks of specified size

    Args:
        lst (list): List to chunk
        chunk_size (int): Maximum items per chunk

    Returns:
        list: List of chunks (each chunk is a list)
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def sync_pending_wallets():
    """
    FR-033: Sync pending wallet updates from Redis to MariaDB
    FR-034: Maintain pending wallet synchronization queue
    FR-035: Run every 15 minutes (scheduled via hooks.py)
    FR-036: Process in chunks of 500 players maximum
    FR-037: Reduce DB write operations by 90%+ through batching

    This job syncs:
    - total_xp
    - current_streak
    - last_success_date
    - last_played_at

    Returns:
        dict: Sync results with count and duration

    Raises:
        Exception: Logs errors but does not fail entire job
    """
    redis_client = frappe.cache()
    start_time = time.time()

    try:
        pending_users = redis_client.smembers("pending_wallet_sync")

        if not pending_users:
            frappe.logger().info("No pending wallet syncs")
            return {
                "synced": 0,
                "duration": 0,
                "errors": 0
            }

        chunks = chunk_list(list(pending_users), 500)
        synced_count = 0
        error_count = 0
        failed_chunks = []

        for chunk in chunks:
            try:
                wallet_updates = []

                for user_id in chunk:
                    wallet_key = f"wallet:{user_id}"
                    wallet_data = redis_client.hgetall(wallet_key)

                    if not wallet_data:
                        continue

                    profile_name = frappe.db.get_value(
                        "Memora Player Profile",
                        {"user": user_id},
                        "name"
                    )

                    if not profile_name:
                        continue

                    wallet_updates.append({
                        "name": profile_name,
                        "total_xp": int(wallet_data.get("total_xp", 0)),
                        "current_streak": int(wallet_data.get("current_streak", 0)),
                        "last_success_date": wallet_data.get("last_success_date") or None,
                        "last_played_at": wallet_data.get("last_played_at") or None
                    })

                if wallet_updates:
                    _bulk_update_wallets(wallet_updates)
                    synced_count += len(wallet_updates)

                redis_client.srem("pending_wallet_sync", *chunk)

            except Exception as e:
                error_count += len(chunk)
                failed_chunks.append(chunk)
                frappe.log_error(
                    f"Wallet sync error for chunk: {str(e)}",
                    "Wallet Sync Error"
                )

        frappe.db.commit()

        duration = time.time() - start_time

        frappe.logger().info(
            f"Wallet sync completed: {synced_count} players, "
            f"{duration:.2f}s, {error_count} errors"
        )

        if failed_chunks:
            for chunk in failed_chunks:
                redis_client.sadd("pending_wallet_sync", *chunk)

        return {
            "synced": synced_count,
            "duration": duration,
            "errors": error_count
        }

    except Exception as e:
        frappe.log_error(
            f"Critical wallet sync failure: {str(e)}",
            "Wallet Sync Critical Error"
        )
        return {
            "synced": 0,
            "duration": time.time() - start_time,
            "errors": 1
        }


def _bulk_update_wallets(wallet_updates):
    """
    Bulk update wallets to MariaDB using SQL CASE statement for optimal performance

    Args:
        wallet_updates (list): List of dicts with wallet update data

    Raises:
        Exception: If SQL update fails
    """
    if not wallet_updates:
        return

    table = "`tabMemora Player Wallet`"

    cases = {
        "total_xp": [],
        "current_streak": [],
        "last_success_date": [],
        "last_played_at": []
    }

    names = []

    for update in wallet_updates:
        name = frappe.db.escape(update["name"])
        names.append(f"'{name}'")

        total_xp = update["total_xp"]
        current_streak = update["current_streak"]
        last_success_date = f"'{update['last_success_date']}'" if update["last_success_date"] else "NULL"
        last_played_at = f"'{update['last_played_at']}'" if update["last_played_at"] else "NULL"

        cases["total_xp"].append(f"WHEN name = '{name}' THEN {total_xp}")
        cases["current_streak"].append(f"WHEN name = '{name}' THEN {current_streak}")
        cases["last_success_date"].append(f"WHEN name = '{name}' THEN {last_success_date}")
        cases["last_played_at"].append(f"WHEN name = '{name}' THEN {last_played_at}")

    sql = f"""
        UPDATE {table}
        SET
            total_xp = CASE {' '.join(cases["total_xp"])} ELSE total_xp END,
            current_streak = CASE {' '.join(cases["current_streak"])} ELSE current_streak END,
            last_success_date = CASE {' '.join(cases["last_success_date"])} ELSE last_success_date END,
            last_played_at = CASE {' '.join(cases["last_played_at"])} ELSE last_played_at END,
            modified = NOW()
        WHERE name IN ({', '.join(names)})
    """

    frappe.db.sql(sql)


def trigger_wallet_sync(force=False):
    """
    Manually trigger wallet sync for admin testing

    Args:
        force (bool): If True, skip Redis queue and sync all active users

    Returns:
        dict: Sync results

    Raises:
        frappe.PermissionError: If user is not System Manager
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Only System Manager can trigger manual wallet sync", exc_type="PermissionError")

    redis_client = frappe.cache()

    if force:
        frappe.logger().info("Force sync triggered - syncing all active users")
        profiles = frappe.get_all(
            "Memora Player Profile",
            filters={"enabled": 1},
            fields=["user"]
        )
        redis_client.sadd("pending_wallet_sync", *[p["user"] for p in profiles])

    result = sync_pending_wallets()

    return {
        "message": "Manual wallet sync completed",
        "force": force,
        **result
    }
