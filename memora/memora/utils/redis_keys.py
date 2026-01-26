"""
Redis key pattern constants for Player Core feature

Key patterns follow namespace format: {type}:{identifier}:{subkey}

Types:
- player: Player-specific data
- active_session: Active session tracking
- wallet: Wallet data (XP, streak, etc.)
- pending_wallet_sync: Queue for batch sync
- rate_limit: Rate limiting counters
"""

PLAYER_DEVICES_KEY = "player:{user_id}:devices"
ACTIVE_SESSION_KEY = "active_session:{user_id}"
WALLET_KEY = "wallet:{user_id}"
PENDING_WALLET_SYNC_KEY = "pending_wallet_sync"
RATE_LIMIT_KEY = "rate_limit:{user_id}:{function_name}"
LAST_PLAYED_AT_SYNCED_KEY = "last_played_at_synced:{user_id}"


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
