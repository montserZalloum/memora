"""
Leaderboard Domain Module

This module handles leaderboard retrieval and user ranking.
"""

import frappe
import math


def update_subject_progression(user, subject_name, xp_earned):
    """
    Update player's points in a specific subject.

    Args:
        user: User ID
        subject_name: Subject name/ID
        xp_earned: XP points to add
    """
    record_name = f"SUB-SCR-{user}-{subject_name}"

    if frappe.db.exists("Player Subject Score", record_name):
        frappe.db.sql("""
            UPDATE `tabPlayer Subject Score`
            SET total_xp = total_xp + %s
            WHERE name = %s
        """, (xp_earned, record_name))
    else:
        frappe.get_doc({
            "doctype": "Player Subject Score",
            "player": user,
            "subject": subject_name,
            "total_xp": xp_earned,
            "level": 1,
            "name": record_name
        }).insert(ignore_permissions=True)


@frappe.whitelist()
def get_leaderboard(subject=None, period='all_time'):
    """
    Get leaderboard (cumulative or weekly / global or by subject).

    - Supports level calculation.
    - Supports time filtering (Weekly).
    - Includes user's rank even if not in top 50.

    Args:
        subject: Optional subject filter
        period: 'all_time' or 'weekly'

    Returns:
        Leaderboard data with user rank info
    """
    try:
        user = frappe.session.user
        limit = 50

        leaderboard = []
        user_rank_info = {}

        # =========================================================
        # 🅰️ Scenario 1: Cumulative Ranking (All Time) - Fastest ⚡
        # =========================================================
        if period == 'all_time':
            if subject:
                # Specific subject
                query = """
                    SELECT t.player as user_id, t.total_xp, u.full_name, u.user_image
                    FROM `tabPlayer Subject Score` t
                    JOIN `tabUser` u ON t.player = u.name
                    WHERE t.subject = %s AND t.total_xp > 0
                    ORDER BY t.total_xp DESC LIMIT %s
                """
                params = [subject, limit]
            else:
                # Global
                query = """
                    SELECT t.user as user_id, t.total_xp, u.full_name, u.user_image
                    FROM `tabPlayer Profile` t
                    JOIN `tabUser` u ON t.user = u.name
                    WHERE t.total_xp > 0
                    ORDER BY t.total_xp DESC LIMIT %s
                """
                params = [limit]

        # =========================================================
        # 🅱️ Scenario 2: Weekly Ranking (Weekly) - Aggregative 📊
        # =========================================================
        else:
            # Here we aggregate points from session logs for last 7 days
            # We use Monday as week start, or last 7 moving days (easier)
            date_condition = "creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)"

            # Subject filtering for sessions
            # Note: Session doesn't have direct Subject in old design,
            # but we can rely on you wanting to add it, or use Join with Lesson.
            # For simplicity and speed now: we'll assume weekly "global" only or needs Log modification
            # ** Smart Solution:** We'll use weekly "global" for now.

            subject_join = ""
            subject_filter = ""
            if subject:
                 # This requires Gameplay Session to have Subject or complex Join
                 # We'll leave for future to avoid slowness, and return global temporarily or empty
                 pass

            query = f"""
                SELECT t.player as user_id, SUM(t.xp_earned) as total_xp, u.full_name, u.user_image
                FROM `tabGameplay Session` t
                JOIN `tabUser` u ON t.player = u.name
                WHERE {date_condition}
                GROUP BY t.player
                ORDER BY total_xp DESC
                LIMIT %s
            """
            params = [limit]

        # Execute query
        top_players = frappe.db.sql(query, tuple(params), as_dict=True)


        for idx, player in enumerate(top_players):
            current_xp = int(player.total_xp)
            # Calculate level with same formula
            level = int(0.07 * math.sqrt(current_xp)) + 1 if current_xp > 0 else 1

            leaderboard.append({
                "rank": idx + 1,
                "name": player.full_name or "Unknown Hero",
                "avatar": player.user_image,
                "xp": current_xp,
                "level": level,  # ✅ Now we send level
                "isCurrentUser": (player.user_id == user)
            })

        # ============================================
        # 3. Current User Ranking (User Rank)
        # ============================================
        # Search in list first
        current_user_in_top = next((item for item in leaderboard if item["isCurrentUser"]), None)

        if current_user_in_top:
            user_rank_info = current_user_in_top
        else:
            # If not in top 50, return their personal data but without precise Rank (for speed)
            # Or return Rank = "+50"

            # Fetch my points
            my_xp = 0
            if period == 'all_time':
                if subject:
                    my_xp = frappe.db.get_value("Player Subject Score", {"player": user, "subject": subject}, "total_xp") or 0
                else:
                    my_xp = frappe.db.get_value("Player Profile", {"user": user}, "total_xp") or 0
            else:
                 # Calculate my weekly points
                 my_xp = frappe.db.sql(f"""
                    SELECT SUM(xp_earned) FROM `tabGameplay Session`
                    WHERE player = %s AND {date_condition}
                 """, (user,))[0][0] or 0

            my_level = int(0.07 * math.sqrt(my_xp)) + 1 if my_xp > 0 else 1
            user_doc = frappe.get_doc("User", user)

            user_rank_info = {
                "rank": "50+",
                "name": user_doc.full_name,
                "avatar": user_doc.user_image,
                "xp": int(my_xp),
                "level": my_level,
                "isCurrentUser": True
            }


        return {
            "leaderboard": leaderboard,
            "userRank": user_rank_info
        }

    except Exception as e:
        frappe.log_error("Leaderboard Error", frappe.get_traceback())
        return {"leaderboard": [], "userRank": {}}
