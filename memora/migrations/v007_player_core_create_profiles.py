# Migration Script: Player Core - Create Player Profiles for Existing Users
"""
Purpose: Create Player Profiles and Wallets for existing Frappe Users who don't have one yet.
         This ensures backward compatibility after deploying Player Core feature.

Run: bench --site your-site.local migrate
Author: Memora Development Team
Date: 2026-01-26
"""

import frappe


def execute():
    """
    Create Player Profiles for existing Users who don't have one.

    This migration:
    1. Finds all enabled User documents with user_type = "System User" (students)
    2. Checks if they already have a Player Profile
    3. Creates Player Profile (and Wallet via after_insert hook) for missing ones
    4. Logs summary of migrated users

    Note: Device authorization is NOT added during migration.
          Students must login to auto-authorize their first device.
    """
    frappe.log("Player Core Migration: Starting profile creation for existing users")

    # Find all Student users (System User type with enabled flag)
    student_users = frappe.get_all(
        "User",
        filters={
            "enabled": 1,
            "user_type": "System User"
        },
        fields=["name", "first_name", "last_name"]
    )

    frappe.log(f"Player Core Migration: Found {len(student_users)} enabled users")

    migrated_count = 0
    skipped_count = 0

    for user in student_users:
        # Check if Player Profile already exists
        existing_profile = frappe.db.exists(
            "Memora Player Profile",
            {"user": user["name"]}
        )

        if existing_profile:
            skipped_count += 1
            continue

        # Create Player Profile
        # Note: We set minimal required fields; admin can update grade/stream/season later
        profile = frappe.get_doc({
            "doctype": "Memora Player Profile",
            "user": user["name"],
            "grade": "Unassigned",
            "season": "2025-2026",
            "academic_plan": "Default Plan"
        })

        profile.insert(ignore_permissions=True)
        migrated_count += 1

        frappe.log(f"Player Core Migration: Created profile for {user['name']}")

    # Commit all changes
    frappe.db.commit()

    frappe.log(
        f"Player Core Migration Complete: "
        f"{migrated_count} profiles created, {skipped_count} skipped"
    )

    return {
        "migrated": migrated_count,
        "skipped": skipped_count
    }
