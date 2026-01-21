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
    Returns: Grades (with allowed streams & seasons), All Streams, and All Seasons.
    """
    try:
        # 1. جلب قائمة كل المسارات (Master Data)
        all_streams = frappe.get_all("Game Academic Stream",
            fields=["name", "stream_name"],
            order_by="creation asc"
        )

        # 2. جلب قائمة كل المواسم (Master Data)
        all_seasons = frappe.get_all("Game Subscription Season",
            fields=["name", "title"],
            order_by="creation desc"
        )

        # 3. جلب الصفوف وتطعيمها بالمسارات والمواسم المسموحة
        grades_list = frappe.get_all("Game Academic Grade",
            fields=["name", "grade_name"],
            order_by="creation asc"
        )

        enriched_grades = []
        for g in grades_list:
            # جلب المسارات المسموحة لهذا الصف
            allowed_streams = frappe.get_all("Game Grade Valid Stream",
                filters={"parent": g.name},
                pluck="stream"
            )

            # جلب المواسم التي تحتوي على خطة دراسية لهذا الصف
            allowed_seasons = frappe.get_all("Game Academic Plan",
                filters={"grade": g.name},
                pluck="season",
                distinct=True
            )

            enriched_grades.append({
                "id": g.name,
                "name": g.grade_name,
                "allowed_streams": allowed_streams,
                "allowed_seasons": allowed_seasons
            })

        return {
            "grades": enriched_grades,
            "streams": all_streams,
            "seasons": all_seasons
        }

    except Exception as e:
        frappe.log_error("Get Masters Failed", frappe.get_traceback())
        return {
            "grades": [], 
            "streams": [], 
            "seasons": [],
            "error": str(e)
        }


@frappe.whitelist()
def set_academic_profile(grade, stream=None, season=None):
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


        # 3. Search for profile (Upsert Logic)
        profile_name = frappe.db.get_value("Player Profile", {"user": user}, "name")

        if profile_name:
            # ✅ Update case: Profile exists
            frappe.db.set_value("Player Profile", profile_name, {
                "current_grade": grade,
                "current_stream": stream if stream else None,
                "season": season
            })
        else:
            # 🆕 Create case: New user without profile
            new_profile = frappe.get_doc({
                "doctype": "Player Profile",
                "user": user,
                "current_grade": grade,
                "current_stream": stream if stream else None,
                "season": season,
                "total_xp": 0,
                "hearts": 5  # Default value for hearts
            })
            new_profile.insert(ignore_permissions=True)

        return {"status": "success", "message": "Academic profile saved successfully"}

    except Exception as e:
        frappe.log_error("Set Profile Failed", frappe.get_traceback())
        return {"status": "error", "message": str(e)}
