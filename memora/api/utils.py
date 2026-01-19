"""
Shared utility functions for the Memora API.

This module contains helper functions that are used across multiple
domain modules to avoid code duplication.
"""

import frappe
from frappe.utils import now_datetime, get_datetime


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
