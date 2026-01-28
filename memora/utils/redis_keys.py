"""
Redis key pattern constants for Player Core feature

All keys are namespaced under the `memora:` prefix to avoid collisions
with other apps or Frappe internals.

Key patterns follow namespace format: memora:{type}:{identifier}:{subkey}
"""

PLAYER_DEVICES_KEY = "memora:player:{user_id}:devices"
ACTIVE_SESSION_KEY = "memora:active_session:{user_id}"
WALLET_KEY = "memora:wallet:{user_id}"
PENDING_WALLET_SYNC_KEY = "memora:pending_wallet_sync"
RATE_LIMIT_KEY = "memora:rate_limit:{user_id}:{function_name}"
LAST_PLAYED_AT_SYNCED_KEY = "memora:last_played_at_synced:{user_id}"
SESSION_METADATA_KEY = "memora:session:{session_id}"
PLAYER_SNAPSHOT_KEY = "memora:player_snapshot:{user_id}"


def get_player_devices_key(user_id):
    """Get Redis key for player's authorized devices set"""
    return PLAYER_DEVICES_KEY.format(user_id=user_id)


def get_active_session_key(user_id):
    """Get Redis key for player's active session"""
    return ACTIVE_SESSION_KEY.format(user_id=user_id)


def get_wallet_key(user_id):
    """Get Redis key for player's wallet hash"""
    return WALLET_KEY.format(user_id=user_id)


def get_rate_limit_key(user_id, function_name):
    """Get Redis key for rate limiting counter"""
    return RATE_LIMIT_KEY.format(user_id=user_id, function_name=function_name)


def get_pending_wallet_sync_key():
    """Get Redis key for global pending wallet sync queue (SET)"""
    return PENDING_WALLET_SYNC_KEY


def get_last_played_at_synced_key(user_id):
    """Get Redis key for last_played_at throttle tracking (STRING with TTL)"""
    return LAST_PLAYED_AT_SYNCED_KEY.format(user_id=user_id)


def get_session_metadata_key(session_id):
    """Get Redis key for session metadata hash"""
    return SESSION_METADATA_KEY.format(session_id=session_id)


def get_player_snapshot_key(user_id):
    """Get Redis key for cached player data snapshot (24h TTL)"""
    return PLAYER_SNAPSHOT_KEY.format(user_id=user_id)
