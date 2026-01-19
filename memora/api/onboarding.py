"""
Onboarding Domain Module

This module handles student onboarding and academic profile setup.
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_academic_masters():
    """
    Fetch master data for onboarding.

    Update: Links streams to grades (Nested Streams).
    Returns JSON containing grades, and each grade contains list of allowed stream IDs.
    """
    try:
        # 1. Fetch streams (as complete reference - Master Data)
        # We need this so frontend knows stream name and number
        all_streams = frappe.get_all("Game Academic Stream",
            fields=["name", "stream_name"],
            order_by="creation asc"
        )

        # 2. Fetch grades with their allowed streams
        # We use get_all for fast fetch, then simple loop
        grades_list = frappe.get_all("Game Academic Grade",
            fields=["name", "grade_name"],
            order_by="creation asc"
        )

        enriched_grades = []
        for g in grades_list:
            # We need to access child table, so we use get_doc or custom query
            # Here we use direct query for better performance (instead of loading full document)
            allowed_streams = frappe.get_all("Game Grade Valid Stream",
                filters={"parent": g.name},
                pluck="stream"  # Returns list of IDs directly ['Scientific', 'Literary']
            )

            enriched_grades.append({
                "id": g.name,
                "name": g.grade_name,
                "allowed_streams": allowed_streams  # 👈 Filtered list
            })

        # 3. Current season
        active_season = frappe.db.get_value("Game Subscription Season",
            {"is_active": 1}, "name") or "2025"

        return {
            "grades": enriched_grades,
            "streams": all_streams,
            "current_season": active_season
        }

    except Exception as e:
        frappe.log_error("Get Masters Failed", frappe.get_traceback())
        return {"grades": [], "streams": [], "current_season": "2025"}


@frappe.whitelist()
def set_academic_profile(grade, stream=None):
    """
    Save student's choices.

    Update: Creates profile if it doesn't exist (for new users).
    """
    try:
        user = frappe.session.user

        # 1. Validate data (Validation)
        if not frappe.db.exists("Game Academic Grade", grade):
            frappe.throw("Invalid Grade Selected")

        if stream:
            # Verify stream is valid for this grade
            is_allowed = frappe.db.exists("Game Grade Valid Stream", {
                "parent": grade,
                "stream": stream
            })
            if not is_allowed:
                frappe.throw(f"Stream '{stream}' is not valid for Grade '{grade}'")

        # 2. Fetch active season
        season = frappe.db.get_value("Game Subscription Season", {"is_active": 1}, "name")

        # 3. Search for profile (Upsert Logic)
        profile_name = frappe.db.get_value("Player Profile", {"user": user}, "name")

        if profile_name:
            # ✅ Update case: Profile exists
            frappe.db.set_value("Player Profile", profile_name, {
                "current_grade": grade,
                "current_stream": stream if stream else None,
                "academic_year": season
            })
        else:
            # 🆕 Create case: New user without profile
            new_profile = frappe.get_doc({
                "doctype": "Player Profile",
                "user": user,
                "current_grade": grade,
                "current_stream": stream if stream else None,
                "academic_year": season,
                "total_xp": 0,
                "hearts": 5  # Default value for hearts
            })
            new_profile.insert(ignore_permissions=True)

        return {"status": "success", "message": "Academic profile saved successfully"}

    except Exception as e:
        frappe.log_error("Set Profile Failed", frappe.get_traceback())
        return {"status": "error", "message": str(e)}
