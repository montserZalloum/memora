
REDIS_KEY_PREFIXES = {
    "player_devices": "player:{user_id}:devices",
    "active_session": "active_session:{user_id}",
    "wallet": "wallet:{player_id}",
    "session_metadata": "session:{session_id}",
    "pending_wallet_sync": "pending_wallet_sync",
    "last_played_at_synced": "last_played_at_synced:{player_id}",
}

def get_player_devices_key(user_id):
    return REDIS_KEY_PREFIXES["player_devices"].format(user_id=user_id)

def get_active_session_key(user_id):
    return REDIS_KEY_PREFIXES["active_session"].format(user_id=user_id)

def get_wallet_key(player_id):
    return REDIS_KEY_PREFIXES["wallet"].format(player_id=player_id)

def get_session_metadata_key(session_id):
    return REDIS_KEY_PREFIXES["session_metadata"].format(session_id=session_id)

def get_pending_wallet_sync_key():
    return REDIS_KEY_PREFIXES["pending_wallet_sync"]

def get_last_played_at_synced_key(player_id):
    return REDIS_KEY_PREFIXES["last_played_at_synced"].format(player_id=player_id)
