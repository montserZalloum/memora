"""
Device Authorization Service

Manages device authorization and device list cache for Player Core.
Provides device authorization checks, device management, and Redis cache synchronization.

Key Functions:
- is_device_authorized(): Check if device is authorized for user (O(1) Redis lookup)
- add_authorized_device(): Add new device to authorized list (max 2 per user)
- remove_authorized_device(): Remove device and invalidate sessions
- rebuild_device_cache(): Rebuild Redis cache from database (for recovery)

Security: All device operations require proper authorization and logging.
Performance: O(1) Redis SISMEMBER for authorization checks.
"""

import frappe
import uuid
from memora.services import session_manager
from memora.utils.redis_keys import get_player_devices_key

def is_device_authorized(user_id, device_id):
    """
    FR-010: Check device authorization in <2ms (Redis)

    Args:
        user_id (str): Frappe User.name
        device_id (str): UUID v4 device identifier

    Returns:
        bool: True if device is authorized
    """
    redis_client = frappe.cache()
    device_key = get_player_devices_key(user_id)

    return redis_client.sismember(device_key, device_id)


def add_authorized_device(player_profile, device_id, device_name):
    """
    FR-009: Admin-only device addition
    FR-005b: Enforce 2-device limit

    Args:
        player_profile (str): Player Profile DocType name
        device_id (str): UUID v4
        device_name (str): Human-readable name

    Raises:
        frappe.ValidationError: If device limit exceeded or UUID invalid
    """
    try:
        uuid.UUID(device_id, version=4)
    except ValueError:
        frappe.throw("Invalid device ID format. Must be UUID v4.")

    profile = frappe.get_doc("Memora Player Profile", player_profile)

    if len(profile.authorized_devices) >= 2:
        frappe.throw("Maximum 2 authorized devices allowed per student")

    profile.append("authorized_devices", {
        "device_id": device_id,
        "device_name": device_name,
        "added_on": frappe.utils.now()
    })

    profile.save(ignore_permissions=True)

    redis_client = frappe.cache()
    redis_client.sadd(get_player_devices_key(profile.user), device_id)

    frappe.logger().info(f"Device authorized for {profile.user}: {device_name} ({device_id})")


def remove_authorized_device(player_profile, device_id):
    """
    Remove device from authorized list and invalidate session

    Args:
        player_profile (str): Player Profile DocType name
        device_id (str): UUID v4 to remove

    Raises:
        frappe.ValidationError: If device not found
    """
    profile = frappe.get_doc("Memora Player Profile", player_profile)

    device_found = False
    for device in profile.authorized_devices:
        if device.device_id == device_id:
            device_found = True
            profile.remove(device)
            break

    if not device_found:
        frappe.throw("Device not found in authorized list")

    profile.save(ignore_permissions=True)

    redis_client = frappe.cache()
    redis_client.srem(get_player_devices_key(profile.user), device_id)

    session_manager.invalidate_session(profile.user)

    frappe.logger().info(f"Device removed for {profile.user}: {device_id}, session invalidated")


def rebuild_device_cache():
    """
    Rebuild Redis device cache from database for all players

    Used for cache recovery after Redis failure or data corruption.
    Idempotent - safe to run multiple times.
    """
    redis_client = frappe.cache()

    profiles = frappe.get_all("Memora Player Profile", fields=["name", "user"])

    for profile in profiles:
        device_key = get_player_devices_key(profile.user)
        redis_client.delete(device_key)

        devices = frappe.get_all("Memora Authorized Device",
            filters={"parent": profile.name},
            fields=["device_id"]
        )

        for device in devices:
            redis_client.sadd(device_key, device.device_id)

    frappe.logger().info(f"Rebuilt device cache for {len(profiles)} players")
