# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

"""
Memora Player Wallet DocType

Persistent storage for player XP and streak data.
Synchronized from Redis cache via 15-minute batch job to reduce DB load.

Key Features:
- 1:1 relationship with Player Profile
- Non-negative constraints on XP and streak
- Automatic Redis cache population on creation
- Queued for batch sync on updates (FR-034)
- Cache cleanup on deletion

Fields:
- total_xp: Cumulative XP earned (non-negative)
- current_streak: Current consecutive day streak (non-negative)
- last_success_date: Date of last lesson completion with hearts > 0
- last_played_at: Timestamp of last player interaction (throttled writes)

Data Flow:
- Write: Redis (immediate) -> DB (15-min batch sync)
- Read: Redis (cache-first) -> DB (fallback on cache miss)
- Sync: Pending wallet queue -> Bulk SQL update (500-player chunks)

Performance: <1s wallet display, 90%+ DB write reduction.
"""

import frappe
from frappe.model.document import Document
from datetime import date
from memora.utils.redis_keys import get_wallet_key, get_pending_wallet_sync_key

class MemoraPlayerWallet(Document):
    def validate(self):
        self.validate_non_negative_xp()
        self.validate_non_negative_streak()
        self.validate_date_not_in_future()
    
    def validate_non_negative_xp(self):
        if self.total_xp < 0:
            frappe.throw(_("Total XP cannot be negative"))
    
    def validate_non_negative_streak(self):
        if self.current_streak < 0:
            self.current_streak = 0
    
    def validate_date_not_in_future(self):
        if self.last_success_date:
            last_date = date.fromisoformat(self.last_success_date)
            if last_date > date.today():
                frappe.throw(_("Last success date cannot be in the future"))
    
    def after_insert(self):
        self.populate_wallet_cache()
    
    def populate_wallet_cache(self):
        redis_client = frappe.cache()
        wallet_key = get_wallet_key(self.player)
        
        wallet_data = {
            "total_xp": self.total_xp,
            "current_streak": self.current_streak,
            "last_success_date": self.last_success_date or "",
            "last_played_at": self.last_played_at or ""
        }
        
        redis_client.hset(wallet_key, mapping=wallet_data)
    
    def on_update(self):
        redis_client = frappe.cache()
        redis_client.sadd(get_pending_wallet_sync_key(), self.player)
    
    def on_trash(self):
        self.cleanup_wallet_cache()
    
    def cleanup_wallet_cache(self):
        redis_client = frappe.cache()
        wallet_key = get_wallet_key(self.player)
        redis_client.delete(wallet_key)
        
        redis_client.srem(get_pending_wallet_sync_key(), self.player)
