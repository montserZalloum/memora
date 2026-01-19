"""
Daily Quests Domain Module

This module generates daily quests based on user's review needs and activity.
"""

import frappe
from frappe.utils import getdate, nowdate


@frappe.whitelist()
def get_daily_quests(subject=None):
    """
    Return daily quests.

    Update: Returns separate review quests per subject due.
    """
    try:
        user = frappe.session.user
        quests = []

        # =================================================
        # 1. Review quests (separated by subject) 🧠
        # =================================================

        # Build additional condition if we want to filter specific subject (optional)
        subject_condition = ""
        params = [user]

        if subject:
            subject_condition = "AND subject = %s"
            params.append(subject)

        # Smart query that aggregates reviews per subject
        reviews_by_subject = frappe.db.sql(f"""
            SELECT subject, COUNT(*) as count
            FROM `tabPlayer Memory Tracker`
            WHERE player = %s AND next_review_date <= NOW() {subject_condition}
            GROUP BY subject
        """, tuple(params), as_dict=True)

        # Did they play review today? (generally)
        # Note: For better accuracy in future, we can store subject in Session to verify precisely
        played_review_today = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabGameplay Session`
            WHERE player = %s AND lesson = 'مراجعة الذاكرة' AND DATE(creation) = CURDATE()
        """, (user,))[0][0]

        # Build review cards
        if played_review_today > 0 and not reviews_by_subject:
            # Case: Finished everything for today
            quests.append({
                "id": "quest_review_done",
                "type": "review",
                "title": "أنعش ذاكرتك",
                "description": "أنجزت مراجعاتك لليوم، أحسنت!",
                "icon": "brain",
                "progress": 1, "target": 1,
                "status": "completed",
                "isUrgent": False
            })
        else:
            # Display card for each due subject
            for row in reviews_by_subject:
                # Handle old subjects without Subject (we call them "عام")
                subj_name = row.subject if row.subject else "عام"

                quests.append({
                    "id": f"quest_review_{subj_name}",  # Unique ID per subject
                    "type": "review",
                    "title": f"مراجعة {subj_name}",
                    "description": f"لديك {row.count} معلومة تحتاج للتثبيت!",
                    "icon": "brain",
                    "progress": 0,
                    "target": row.count,
                    "reward": {"type": "xp", "amount": row.count * 10},
                    "status": "active",
                    "isUrgent": True,
                    "meta": { "subject": row.subject }  # 👈 We send subject name to make it easy for frontend to use
                })

        # =================================================
        # 2. General quests (streak + points) 🔥🏆
        # =================================================

        # Did they play anything today?
        played_today_any = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabGameplay Session`
            WHERE player = %s AND DATE(creation) = CURDATE()
        """, (user,))[0][0]

        # Today's points
        today_xp = frappe.db.sql("""
            SELECT SUM(xp_earned) FROM `tabGameplay Session`
            WHERE player = %s AND DATE(creation) = CURDATE()
        """, (user,))[0][0] or 0

        # Streak quest
        quests.append({
            "id": "quest_streak",
            "type": "streak",
            "title": "شعلة النشاط",
            "description": "أكمل درساً واحداً اليوم.",
            "icon": "flame",
            "progress": 1 if played_today_any > 0 else 0,
            "target": 1,
            "reward": {"type": "xp", "amount": 100},
            "status": "completed" if played_today_any > 0 else "active",
            "isUrgent": False
        })

        # Points quest
        target_xp = 200
        quests.append({
            "id": "quest_xp",
            "type": "xp_goal",
            "title": "تحدي النقاط اليومي",
            "description": f"اجمع {target_xp} نقطة خبرة اليوم.",
            "icon": "trophy",
            "progress": int(today_xp),
            "target": target_xp,
            "reward": {"type": "xp", "amount": 150},
            "status": "completed" if today_xp >= target_xp else "active",
            "isUrgent": False
        })

        return quests

    except Exception as e:
        frappe.log_error("Get Daily Quests Failed", frappe.get_traceback())
        return []
