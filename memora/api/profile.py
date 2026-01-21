"""
Profile Domain Module

This module handles player profile data and statistics.
"""

import frappe
import math
from frappe import _
from frappe.utils import getdate, add_days, nowdate
from .utils import get_user_active_subscriptions


@frappe.whitelist()
def get_player_profile():
    """
    Get basic player profile data when opening app.

    Update: Added grade and stream to verify onboarding.
    """
    try:
        user = frappe.session.user

        # Fetch profile data including new academic fields
        profile = frappe.db.get_value("Player Profile", {"user": user},
            ["total_xp", "gems_balance", "current_grade", "current_stream"],
            as_dict=True
        )

        if not profile:
            # In case of very new user without profile yet
            return {
                "xp": 0,
                "gems": 0,
                "current_grade": None,
                "current_stream": None
            }

        return {
            "xp": int(profile.total_xp or 0),
            "gems": int(profile.gems_balance or 0),
            # 👇 These are fields frontend expects
            "current_grade": profile.current_grade,
            "current_stream": profile.current_stream
        }

    except Exception as e:
        frappe.log_error("Get Player Profile Failed", frappe.get_traceback())
        return {}


@frappe.whitelist()
def get_full_profile_stats(subject=None):
    """
    API to fetch profile statistics.

    - If subject is passed: returns level and memory status for that subject only.
    - If subject is not passed: returns general level and total memory status.
    """
    try:
        user = frappe.session.user

        # 1. Basic data
        user_doc = frappe.get_doc("User", user)

        # 2. Level and XP logic (general vs specific)
        if subject:
            # Fetch subject points (for leaderboard)
            score_data = frappe.db.get_value("Player Subject Score",
                {"player": user, "subject": subject},
                ["total_xp", "level"], as_dict=True) or {"total_xp": 0, "level": 1}

            current_xp = score_data.get("total_xp", 0)
            # Calculate level based on subject points
            if current_xp == 0:
                level = 1
            else:
                level = int(0.07 * math.sqrt(current_xp)) + 1
        else:
            # Fetch general points (Global Profile)
            profile = frappe.db.get_value("Player Profile", {"user": user},
                ["total_xp", "gems_balance"], as_dict=True) or {"total_xp": 0, "gems_balance": 0}

            current_xp = profile.get("total_xp", 0)
            if current_xp == 0:
                level = 1
            else:
                level = int(0.07 * math.sqrt(current_xp)) + 1

        # Level limits (RPG Curve)
        xp_start_of_level = int(((level - 1) / 0.07) ** 2)
        xp_next_level_goal = int((level / 0.07) ** 2)

        xp_needed = xp_next_level_goal - xp_start_of_level
        xp_progress_in_level = current_xp - xp_start_of_level

        next_level_percentage = 0
        if xp_needed > 0:
            next_level_percentage = (xp_progress_in_level / xp_needed) * 100

        # Titles
        titles = ["مستكشف مبتدئ", "مغامر تاريخي", "حارس الذاكرة", "أستاذ الزمان", "أسطورة الأردن"]
        title_index = min(level - 1, len(titles) - 1)
        level_title = titles[title_index]


        # 3. Streak (always general) 🔥
        activity_dates = frappe.db.sql("""
            SELECT DISTINCT DATE(creation) as activity_date
            FROM `tabGameplay Session`
            WHERE player = %s
            ORDER BY activity_date DESC
            LIMIT 30
        """, (user,), as_list=True)

        streak = 0
        if activity_dates:
            today = getdate(nowdate())
            yesterday = add_days(today, -1)
            dates = [getdate(d[0]) for d in activity_dates]

            if dates[0] == today or dates[0] == yesterday:
                streak = 1
                for i in range(1, len(dates)):
                    expected_date = add_days(dates[i-1], -1)
                    if dates[i] == expected_date:
                        streak += 1
                    else:
                        break


        # 4. Weekly activity (general) 📊
        weekly_data_raw = frappe.db.sql("""
            SELECT DATE(creation) as day, SUM(xp_earned) as daily_xp
            FROM `tabGameplay Session`
            WHERE player = %s AND creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(creation)
        """, (user,), as_dict=True)

        xp_map = {getdate(d.day): d.daily_xp for d in weekly_data_raw}
        days_ar = {'Sat': 'سبت', 'Sun': 'أحد', 'Mon': 'إثنين', 'Tue': 'ثلاثاء', 'Wed': 'أربعاء', 'Thu': 'خميس', 'Fri': 'جمعة'}

        weekly_activity = []
        for i in range(6, -1, -1):
            date_cursor = add_days(getdate(nowdate()), -i)
            day_en = date_cursor.strftime("%a")
            weekly_activity.append({
                "day": days_ar.get(day_en, day_en),
                "full_date": date_cursor.strftime("%Y-%m-%d"),
                "xp": xp_map.get(date_cursor, 0),
                "isToday": date_cursor == getdate(nowdate())
            })


        # 5. Memory status (Mastery) - filtered by subject 🧠
        # Build query condition
        conditions = "player = %s"
        params = [user]

        if subject:
            conditions += " AND subject = %s"
            params.append(subject)

        mastery_raw = frappe.db.sql(f"""
            SELECT stability, COUNT(*) as count
            FROM `tabPlayer Memory Tracker`
            WHERE {conditions}
            GROUP BY stability
        """, tuple(params), as_dict=True)

        mastery_map = {row.stability: row.count for row in mastery_raw}
        total_learned = sum(mastery_map.values())

        stats_mastery = {
            "new": mastery_map.get(1, 0),
            "learning": mastery_map.get(2, 0),
            "mature": mastery_map.get(3, 0) + mastery_map.get(4, 0)
        }

        return {
            "fullName": user_doc.full_name or user_doc.username,
            "avatarUrl": user_doc.user_image,
            "level": level,
            "levelTitle": level_title,
            "nextLevelProgress": int(next_level_percentage),
            "xpInLevel": int(xp_progress_in_level),
            "xpToNextLevel": int(xp_needed),
            "streak": streak,
            "gems": 0,  # Gems removed
            "totalXP": int(current_xp),
            "totalLearned": total_learned,
            "weeklyActivity": weekly_activity,
            "mastery": stats_mastery
        }

    except Exception as e:
        frappe.log_error("Get Profile Stats Error", frappe.get_traceback())
        return {}


@frappe.whitelist()
def get_player_login_info():
    # 1. جيب اليوزر الحالي
    current_user = frappe.session.user
    
    if current_user == 'Guest':
        return {"is_logged_in": False}

    # 2. جيب البيانات من Player Profile
    # بنبحث عن البروفايل اللي مربوط باليوزر الحالي
    # frappe.db.get_value (Doctype, Filters, Fields, as_dict)
    
    player_data = frappe.db.get_value(
        "Player Profile", 
        {"user": current_user},  # <-- تأكد أن اسم الحقل في الدوكتايب هو user
        ["total_xp", "current_grade", "current_stream", "season"],
        as_dict=True
    )

    # حالة لو اليوزر مسجل بس لسه ما عنده Player Profile
    if not player_data:
        player_data = {
            "total_xp": 0,
            "current_grade": None,
            "current_stream": None,
            "season": None
        }

    # 3. ضيف الإيميل للداتا ورجع النتيجة
    player_data['email'] = current_user
    player_data['is_logged_in'] = True
    
    return player_data