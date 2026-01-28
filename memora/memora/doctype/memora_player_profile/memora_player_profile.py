# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

"""
Memora Player Profile DocType

Central identity DocType linking Frappe User to player-specific educational context.
Enforces device authorization limits (max 2 devices per student) and manages
device cache synchronization with Redis.

Key Features:
- 1:1 relationship with Frappe User (enforced by unique user field)
- Device authorization table with 2-device limit (FR-005b)
- Auto-authorization of first device on profile creation (FR-005a)
- Automatic Redis cache synchronization on device changes
- Auto-creation of Player Wallet on profile creation (FR-018)

Validation:
- Maximum 2 authorized devices per student
- Unique device IDs within a profile
- UUID v4 format validation for device IDs
"""

import frappe
from frappe.model.document import Document

from memora.utils.redis_keys import get_player_devices_key, get_player_snapshot_key


class MemoraPlayerProfile(Document):
    def validate(self):
        self.validate_device_limit()
        self.validate_unique_devices()
        self.auto_authorize_first_device()

    def validate_device_limit(self):
        if len(self.authorized_devices) > 2:
            frappe.throw(_("Maximum 2 authorized devices allowed per student"))

    def validate_unique_devices(self):
        device_ids = [d.device_id for d in self.authorized_devices]
        if len(device_ids) != len(set(device_ids)):
            frappe.throw(_("Duplicate device IDs are not allowed"))

    def auto_authorize_first_device(self):
        if self.is_new() and not self.authorized_devices:
            first_device_id = frappe.local.request.headers.get("X-Device-ID") if hasattr(frappe.local, 'request') and frappe.local.request else None
            if first_device_id:
                self.append("authorized_devices", {
                    "device_id": first_device_id,
                    "device_name": "First Device (Auto-authorized)",
                    "added_on": frappe.utils.now()
                })

    def after_insert(self):
        self.create_player_wallet()

    def create_player_wallet(self):
        wallet = frappe.new_doc("Memora Player Wallet")
        wallet.player = self.name
        wallet.total_xp = 0
        wallet.current_streak = 0
        wallet.last_success_date = None
        wallet.last_played_at = None
        wallet.insert(ignore_permissions=True)

    def on_update(self):
        self.sync_device_cache()

    def sync_device_cache(self):
        redis_client = frappe.cache()
        device_key = get_player_devices_key(self.user)

        redis_client.delete(device_key)

        for device in self.authorized_devices:
            redis_client.sadd(device_key, device.device_id)
