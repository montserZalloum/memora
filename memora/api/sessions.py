"""
Session & Gameplay Domain Module

This module handles gameplay session submission and lesson content retrieval.
"""

import frappe
import json
from frappe import _
from .srs import process_srs_batch
from .leaderboard import update_subject_progression


@frappe.whitelist()
def get_lesson_details(lesson_id):
    """
    Get lesson content with stages.

    Args:
        lesson_id: Lesson ID

    Returns:
        Lesson details with stages configuration
    """
    try:
        if not lesson_id:
            frappe.throw(_("Lesson ID is missing"))

        if not frappe.db.exists({"doctype": "Game Lesson", "name": lesson_id, "is_published": 1}):
            # You can return error or Null based on how you want to handle frontend
            frappe.throw(_("Lesson not found or access denied."))

        doc = frappe.get_doc("Game Lesson", lesson_id)

        return {
            "name": doc.name,
            "title": doc.title,
            "xp_reward": doc.xp_reward,
            "stages": [
                {
                    "id": s.name,
                    "title": s.title,
                    "type": s.type.lower(),
                    "config": frappe.parse_json(s.config) if s.config else {}
                } for s in doc.stages
            ]
        }

    except frappe.ValidationError as e:
        # Handle specific validation errors from Frappe logic
        frappe.throw(e)
    except Exception as e:
        frappe.log_error(title=f"get_lesson_details failed: {lesson_id}", message=frappe.get_traceback())
        frappe.throw(_("Failed to load lesson content."))


@frappe.whitelist()
def submit_session(session_meta, gamification_results, interactions):
    """
    Submit gameplay session.

    Archives gameplay session, updates XP, subject progression,
    and SRS memory tracking. All updates happen within
    a single database transaction.

    Args:
        session_meta: Session metadata (lesson_id, etc.)
        gamification_results: XP and score data
        interactions: List of question interactions

    Returns:
        Success message
    """
    try:
        user = frappe.session.user

        if isinstance(session_meta, str): session_meta = json.loads(session_meta)
        if isinstance(interactions, str): interactions = json.loads(interactions)
        if isinstance(gamification_results, str): gamification_results = json.loads(gamification_results)

        lesson_id = session_meta.get('lesson_id')
        if not lesson_id: frappe.throw("Missing lesson_id")

        xp_earned = gamification_results.get('xp_earned', 0)
        score = gamification_results.get('score', 0)

        # 1. Discover Subject & Topic (Subject & Topic Lookup) 🕵️‍♂️
        # We fetch topic from lesson, and subject from track/unit
        data = frappe.db.sql("""
            SELECT l.topic, t.subject
            FROM `tabGame Lesson` l
            LEFT JOIN `tabGame Unit` u ON l.unit = u.name
            LEFT JOIN `tabGame Learning Track` t ON u.learning_track = t.name
            WHERE l.name = %s
        """, (lesson_id,), as_dict=True)

        current_subject = None
        current_topic = None

        if data:
            current_subject = data[0].subject
            current_topic = data[0].topic

        # 2. Archive session
        doc = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": user,
            "lesson": lesson_id,
            "xp_earned": xp_earned,
            "score": score,
            "raw_data": json.dumps(interactions, ensure_ascii=False)
        })
        doc.insert(ignore_permissions=True)

        # 3. Update global XP
        if xp_earned > 0:
            frappe.db.sql("UPDATE `tabPlayer Profile` SET total_xp = total_xp + %s WHERE user = %s", (xp_earned, user))

        # 4. Update subject points (Leaderboard)
        if current_subject and xp_earned > 0:
            update_subject_progression(user, current_subject, xp_earned)

        # 5. Update memory (SRS) - we pass subject and topic ✅
        if interactions and isinstance(interactions, list):
            process_srs_batch(user, interactions, current_subject, current_topic)

        frappe.db.commit()

        return {"status": "success", "message": "Session Saved ✅"}

    except Exception as e:
        frappe.log_error("submit_session failed", frappe.get_traceback())
        frappe.throw(str(e))
