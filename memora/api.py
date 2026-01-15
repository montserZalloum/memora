import frappe
import json
from frappe import _
import math
from frappe.utils import now_datetime, add_days, get_datetime, getdate, nowdate, cint
import random

@frappe.whitelist()
def get_subjects():
    try:
        # 1. جلب المواضيع المنشورة فقط
        subjects = frappe.get_all("Game Subject", 
            fields=["name", "title", "icon"], 
            filters={"is_published": 1},
            order_by="creation asc"
        )
        
        # 2. إضافة إحصائيات بسيطة لكل موضوع (اختياري لكنه رائع للواجهة)
        # for subject in subjects:
        #     # حساب عدد الدروس الكلي في هذا الموضوع
        #     # نقوم بالبحث عن الوحدات التابعة للموضوع، ثم الدروس التابعة لتلك الوحدات
        #     units = frappe.get_all("Game Unit", filters={"subject": subject.name}, pluck="name")
            
        #     if units:
        #         lesson_count = frappe.db.count("Game Lesson", filters={"unit": ["in", units]})
        #     else:
        #         lesson_count = 0
                
        #     subject["total_lessons"] = lesson_count
            
        return subjects

    except Exception as e:
        frappe.log_error(title="get_subjects failed", message=frappe.get_traceback())
        frappe.throw("تعذر تحميل المواضيع حالياً.")


@frappe.whitelist()
def get_game_tracks(subject):
    try:
        if not subject: return []
        
        # جلب المسارات المرتبطة بالمادة
        # الترتيب: الافتراضي أولاً، ثم حسب الترتيب أو الإنشاء
        tracks = frappe.get_all("Game Learning Track", 
            filters={"subject": subject},
            fields=["name", "track_name", "is_default", "unlock_level", "icon", "description"],
            order_by="is_default desc, creation asc"
        )
        
        return tracks
    except Exception as e:
        return []
        

@frappe.whitelist()
def get_map_data(subject, track=None):
    try:
        if not subject:
            frappe.throw("الرجاء تحديد الموضوع (Subject)")

        user = frappe.session.user
        
        subject_info = frappe.db.get_value("Game Subject", 
            {"name": subject, "is_published": 1}, 
            ["name", "title", "icon"], as_dict=True)
            
        if not subject_info:
            frappe.throw("الموضوع غير موجود")

        # ---------------------------------------------------------
        # 🆕 منطق اختيار المسار
        # ---------------------------------------------------------
        # إذا لم يرسل الفرونت اند المسار، نأتي بالمسار الافتراضي
        if not track:
            track = frappe.db.get_value("Game Learning Track", 
                {"subject": subject, "is_default": 1}, "name")
        
        # حماية إضافية: إذا لم يوجد أي مسار (حالة نادرة)، لا نكمل
        if not track:
             frappe.throw("لا يوجد مسار تعليمي متاح لهذه المادة.")

        track_info = frappe.db.get_value("Game Learning Track", track, ["is_linear"], as_dict=True)
        is_linear = track_info.is_linear if track_info else 1
        # ---------------------------------------------------------

        completed_lessons = frappe.get_all("Gameplay Session", 
            filters={"player": user}, 
            fields=["lesson"], 
            pluck="lesson",
        )
        
        # 🆕 الفلترة بناءً على المسار المختار
        units = frappe.get_all("Game Unit", 
            filters={
                "subject": subject,
                "learning_track": track # <--- الفلتر هنا
            }, 
            fields=["name", "title", "`order`"], 
            order_by="`order` asc, creation asc"
        )
        
        full_map = []
        
        for unit in units:
            lessons = frappe.get_all("Game Lesson", 
                filters={"unit": unit.name}, 
                fields=["name", "title", "xp_reward"],
                order_by="creation asc" 
            )
            
            for lesson in lessons:
                status = "locked"
                
                if lesson.name in completed_lessons:
                    status = "completed"
                # الحالة 2: المسار "حر" (Non-Linear) -> كل شيء متاح ما لم يكن مكتملاً
                elif not is_linear:
                    status = "available"
                elif not full_map or full_map[-1]["status"] == "completed":
                    status = "available"
                
                
                full_map.append({
                    "id": lesson.name,
                    "title": lesson.title,
                    "unit_title": unit.title,
                    "subject_title": subject_info.title,
                    "status": status,
                    "xp": lesson.xp_reward,
                    "track": track # مفيد للفرونت اند للتأكد
                })
                    
        return full_map

    except Exception as e:
        frappe.log_error(title="get_map_data failed", message=frappe.get_traceback())
        frappe.throw("تعذر تحميل خريطة الدروس.")


@frappe.whitelist()
def get_lesson_details(lesson_id):
    try:
        if not lesson_id:
            frappe.throw(_("Lesson ID is missing"))
            
        if not frappe.db.exists({"doctype": "Game Lesson", "name": lesson_id, "is_published": 1}):
            # يمكنك إرجاع خطأ أو Null حسب رغبتك في التعامل مع الفرونت
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
    try:
        user = frappe.session.user
        
        # 1. تحويل JSON إلى Python (في حال وصل كنص)
        if isinstance(session_meta, str): session_meta = json.loads(session_meta)
        if isinstance(interactions, str): interactions = json.loads(interactions)
        if isinstance(gamification_results, str): gamification_results = json.loads(gamification_results)

        lesson_id = session_meta.get('lesson_id')
        if not lesson_id: frappe.throw("Missing lesson_id")

        # استخراج النتائج (تم إزالة الجواهر)
        xp_earned = gamification_results.get('xp_earned', 0)
        score = gamification_results.get('score', 0)

        # ---------------------------------------------------------
        # 🕵️‍♂️ اكتشاف المادة (Subject Lookup)
        # ---------------------------------------------------------
        # نبحث عن المادة التابعة لهذا الدرس عبر التسلسل:
        # Lesson -> Unit -> Learning Track -> Subject
        subject_data = frappe.db.sql("""
            SELECT t.subject 
            FROM `tabGame Lesson` l
            LEFT JOIN `tabGame Unit` u ON l.unit = u.name
            LEFT JOIN `tabGame Learning Track` t ON u.learning_track = t.name
            WHERE l.name = %s
        """, (lesson_id,))
        
        # إذا وجدنا المادة نأخذها، وإلا نعتبرها None
        current_subject = subject_data[0][0] if subject_data and subject_data[0][0] else None

        # ---------------------------------------------------------
        # 2. أرشفة الجلسة (Logging)
        # ---------------------------------------------------------
        doc = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": user,
            "lesson": lesson_id,
            "xp_earned": xp_earned,
            "score": score,
            "raw_data": json.dumps(interactions, ensure_ascii=False)
        })
        doc.insert(ignore_permissions=True)
        
        # ---------------------------------------------------------
        # 3. تحديث البروفايل العام (Global XP)
        # ---------------------------------------------------------
        if xp_earned > 0:
            frappe.db.sql("""
                UPDATE `tabPlayer Profile`
                SET total_xp = total_xp + %s
                WHERE user = %s
            """, (xp_earned, user))

        # ---------------------------------------------------------
        # 🆕 4. تحديث نقاط المادة (Subject XP - Leaderboard)
        # ---------------------------------------------------------
        if current_subject and xp_earned > 0:
            update_subject_progression(user, current_subject, xp_earned)

        # ---------------------------------------------------------
        # 5. تحديث الذاكرة (SRS) مع المادة
        # ---------------------------------------------------------
        if interactions and isinstance(interactions, list):
            # نمرر current_subject للدالة لكي تخزنه في الـ Tracker
            process_srs_batch(user, interactions, current_subject)

        frappe.db.commit() 

        return {
            "status": "success", 
            "message": "Session Saved. XP & SRS Updated. ✅"
        }

    except Exception as e:
        frappe.log_error(title="submit_session failed", message=frappe.get_traceback())
        frappe.throw(f"Error: {str(e)}")

# =========================================================
# 🧠 THE BRAIN: SRS Algorithms
# =========================================================

def process_srs_batch(user, interactions, subject=None):
    """
    معالجة مجموعة من التفاعلات لتحديث الذاكرة.
    تستقبل 'subject' لتمريره للدالة النهائية.
    """
    for item in interactions:
        atom_id = item.get("question_id")
        if not atom_id: continue
            
        duration = item.get("duration_ms", item.get("time_spent_ms", 3000))
        attempts = item.get("attempts_count", 1)
        
        # استنتاج التقييم
        rating = infer_rating(duration, attempts)
        next_review_date = calculate_next_review(rating)
        
        # ✅ التعديل هنا: تمرير subject للدالة التالية
        update_memory_tracker(user, atom_id, rating, next_review_date, subject)


def infer_rating(duration_ms, attempts):
    """
    Logic: Converts Time + Accuracy into a Memory Score.
    
    Ratings:
    1 = AGAIN (Fail) - Wrong answer, needs immediate drill.
    2 = HARD         - Correct but slow (> 5s).
    3 = GOOD         - Correct and steady (2s - 5s).
    4 = EASY         - Correct and instant (< 2s).
    """
    # If the user made a mistake (attempts > 1), it's a FAIL regardless of time.
    if attempts > 1:
        return 1
    
    # If correct on first try, judge by speed:
    if duration_ms < 2000: # Less than 2 seconds
        return 4 # EASY
    
    if duration_ms < 5000: # Less than 5 seconds
        return 3 # GOOD
    
    # More than 5 seconds
    return 2 # HARD


def calculate_next_review(rating):
    """
    Logic: Determines how many days to wait before the next review.
    
    Current Protocol (Fixed Intervals):
    1 (Fail) -> 0 Days (Review Tomorrow/ASAP)
    2 (Hard) -> 2 Days
    3 (Good) -> 4 Days
    4 (Easy) -> 7 Days
    """
    interval_map = {
        1: 0, # Fail: Reset
        2: 2, # Hard
        3: 4, # Good
        4: 7  # Easy
    }
    
    days_to_add = interval_map.get(rating, 1) # Default to 1 day if error
    
    # Return the actual DateTime object
    return add_days(now_datetime(), days_to_add)


def update_memory_tracker(user, atom_id, rating, next_date, subject=None):
    """تحديث سجل الذاكرة مع دعم المادة"""
    existing_tracker = frappe.db.get_value("Player Memory Tracker", 
        {"player": user, "question_id": atom_id}, "name")

    if existing_tracker:
        values = {
            "stability": rating,
            "last_review_date": now_datetime(),
            "next_review_date": next_date
        }
        if subject: values["subject"] = subject
        frappe.db.set_value("Player Memory Tracker", existing_tracker, values)
    else:
        doc = frappe.get_doc({
            "doctype": "Player Memory Tracker",
            "player": user,
            "question_id": atom_id,
            "subject": subject,
            "stability": rating,
            "last_review_date": now_datetime(),
            "next_review_date": next_date
        })
        doc.insert(ignore_permissions=True)


@frappe.whitelist()
def get_player_profile():
    try:
        user = frappe.session.user
        
        # تجاهل الزوار (Guest) - لا ننشئ لهم بروفايلات
        if user == "Guest":
            return {"xp": 0, "gems": 0, "hearts": 5}

        # 1. البحث عن بروفايل اللاعب
        profile = frappe.db.get_value("Player Profile", {"user": user}, 
            ["name", "total_xp", "gems_balance"], 
            as_dict=True
        )
        
        if not profile:
            # 🐣 إنشاء بروفايل جديد
            new_doc = frappe.get_doc({
                "doctype": "Player Profile",
                "user": user,
                "total_xp": 0,
                "gems_balance": 50
            })
            new_doc.insert(ignore_permissions=True)
            
            # 🚨 هذا هو السطر المفقود!
            # بما أننا نستخدم GET request، يجب أن نجبر الداتابيز على الحفظ
            frappe.db.commit()
            
            return {
                "xp": 0,
                "gems": 50,
                "hearts": 5
            }
        
        return {
            "xp": profile.total_xp,
            "gems": profile.gems_balance,
            "hearts": 5
        }

    except Exception as e:
        frappe.log_error(title="get_player_profile failed", message=frappe.get_traceback())
        return {"xp": 0, "gems": 0, "hearts": 5}


@frappe.whitelist()
def get_full_profile_stats(subject=None):
    """
    API لجلب إحصائيات البروفايل.
    - إذا تم تمرير subject: نرجع المستوى وحالة الذاكرة لتلك المادة فقط.
    - إذا لم يتم تمرير subject: نرجع المستوى العام وحالة الذاكرة الكلية.
    """
    try:
        user = frappe.session.user
        
        # 1. البيانات الأساسية
        user_doc = frappe.get_doc("User", user)
        
        # 2. منطق المستوى والـ XP (عام vs مخصص)
        if subject:
            # جلب نقاط المادة (للمتصدرين)
            score_data = frappe.db.get_value("Player Subject Score", 
                {"player": user, "subject": subject}, 
                ["total_xp", "level"], as_dict=True) or {"total_xp": 0, "level": 1}
            
            current_xp = score_data.get("total_xp", 0)
            # نحسب المستوى بناءً على نقاط المادة
            if current_xp == 0:
                level = 1
            else:
                level = int(0.07 * math.sqrt(current_xp)) + 1
        else:
            # جلب النقاط العامة (Global Profile)
            profile = frappe.db.get_value("Player Profile", {"user": user}, 
                ["total_xp", "gems_balance"], as_dict=True) or {"total_xp": 0, "gems_balance": 0}
            
            current_xp = profile.get("total_xp", 0)
            if current_xp == 0:
                level = 1
            else:
                level = int(0.07 * math.sqrt(current_xp)) + 1

        # حدود المستوى (RPG Curve)
        xp_start_of_level = int(((level - 1) / 0.07) ** 2)
        xp_next_level_goal = int((level / 0.07) ** 2)
        
        xp_needed = xp_next_level_goal - xp_start_of_level
        xp_progress_in_level = current_xp - xp_start_of_level
        
        next_level_percentage = 0
        if xp_needed > 0:
            next_level_percentage = (xp_progress_in_level / xp_needed) * 100

        # الألقاب
        titles = ["مستكشف مبتدئ", "مغامر تاريخي", "حارس الذاكرة", "أستاذ الزمان", "أسطورة الأردن"]
        title_index = min(level - 1, len(titles) - 1)
        level_title = titles[title_index]


        # 3. الستريك (دائماً عام) 🔥
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


        # 4. النشاط الأسبوعي (عام) 📊
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


        # 5. حالة الذاكرة (Mastery) - مفلترة حسب المادة 🧠
        # بناء شرط الاستعلام
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
            "gems": 0, # تم إزالة الجواهر
            "totalXP": int(current_xp),
            "totalLearned": total_learned,
            "weeklyActivity": weekly_activity,
            "mastery": stats_mastery
        }

    except Exception as e:
        frappe.log_error("Get Profile Stats Error", frappe.get_traceback())
        return {}



@frappe.whitelist()
def get_daily_quests(subject=None):
    """
    إرجاع المهام اليومية.
    التحديث: يقوم بإرجاع مهام مراجعة منفصلة لكل مادة مستحقة.
    """
    try:
        user = frappe.session.user
        quests = []

        # =================================================
        # 1. مهام المراجعة (مفصلة حسب المادة) 🧠
        # =================================================
        
        # بناء شرط إضافي في حال أردنا فلترة مادة محددة (اختياري)
        subject_condition = ""
        params = [user]
        
        if subject:
            subject_condition = "AND subject = %s"
            params.append(subject)

        # استعلام ذكي يجمع المراجعات لكل مادة
        reviews_by_subject = frappe.db.sql(f"""
            SELECT subject, COUNT(*) as count 
            FROM `tabPlayer Memory Tracker`
            WHERE player = %s AND next_review_date <= NOW() {subject_condition}
            GROUP BY subject
        """, tuple(params), as_dict=True)

        # هل لعب مراجعة اليوم؟ (بشكل عام)
        # ملاحظة: لتحسين الدقة مستقبلاً، يمكننا تخزين المادة في الـ Session للتحقق بدقة
        played_review_today = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabGameplay Session`
            WHERE player = %s AND lesson = 'مراجعة الذاكرة' AND DATE(creation) = CURDATE()
        """, (user,))[0][0]

        # بناء كروت المراجعة
        if played_review_today > 0 and not reviews_by_subject:
            # حالة: أنهى كل شيء لليوم
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
            # عرض كارد لكل مادة مستحقة
            for row in reviews_by_subject:
                # التعامل مع المواد القديمة التي ليس لها Subject (نسميها "عام")
                subj_name = row.subject if row.subject else "عام"
                
                quests.append({
                    "id": f"quest_review_{subj_name}", # ID فريد لكل مادة
                    "type": "review",
                    "title": f"مراجعة {subj_name}",
                    "description": f"لديك {row.count} معلومة تحتاج للتثبيت!",
                    "icon": "brain",
                    "progress": 0,
                    "target": row.count,
                    "reward": {"type": "xp", "amount": row.count * 10},
                    "status": "active",
                    "isUrgent": True,
                    "meta": { "subject": row.subject } # 👈 نرسل اسم المادة ليسهل على الفرونت استخدامه
                })

        # =================================================
        # 2. المهام العامة (الستريك + النقاط) 🔥🏆
        # =================================================
        
        # هل لعب أي شيء اليوم؟
        played_today_any = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabGameplay Session`
            WHERE player = %s AND DATE(creation) = CURDATE()
        """, (user,))[0][0]

        # نقاط اليوم
        today_xp = frappe.db.sql("""
            SELECT SUM(xp_earned) FROM `tabGameplay Session`
            WHERE player = %s AND DATE(creation) = CURDATE()
        """, (user,))[0][0] or 0

        # مهمة الستريك
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

        # مهمة النقاط
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



@frappe.whitelist()
def get_review_session():
    """
    يولد جلسة مراجعة ذكية (Lightning Round).
    التحديثات المعمارية:
    1. يعتمد على ID السطر (Child Row Name) بدلاً من الترتيب، لمنع مشاكل الحذف والترتيب.
    2. يقوم بالتنظيف الذاتي (Self-Healing) للسجلات اليتيمة.
    3. يتحقق من أن الدرس منشور (is_published).
    """
    try:
        user = frappe.session.user
        
        # 1. جلب العناصر المستحقة للمراجعة
        due_items = frappe.db.sql("""
            SELECT name, question_id, stability 
            FROM `tabPlayer Memory Tracker`
            WHERE player = %s AND next_review_date <= NOW()
            ORDER BY next_review_date ASC
            LIMIT 15
        """, (user,), as_dict=True)
        
        if not due_items:
            return []

        quiz_cards = []
        # قائمة لتعقب السجلات الفاسدة لحذفها دفعة واحدة
        corrupt_tracker_ids = []

        for item in due_items:
            raw_id = item.question_id
            target_atom_index = None
            
            # 2. تحليل الـ ID (نتوقع: STAGE_ROW_NAME:ATOM_INDEX)
            # مثال: a1b2c3d4:0
            if ":" in raw_id:
                # نستخدم rsplit للفصل من اليمين لضمان أخذ الرقم الأخير
                parts = raw_id.rsplit(":", 1)
                stage_row_name = parts[0]
                if parts[1].isdigit():
                    target_atom_index = int(parts[1])
                else:
                    target_atom_index = None
            else:
                stage_row_name = raw_id
                target_atom_index = None

            # 3. البحث عن المرحلة مباشرة (Direct Lookup)
            # نبحث في جدول المراحل الفرعي باستخدام الـ Hash الخاص بها
            stage_data = frappe.db.get_value("Game Lesson Stage", stage_row_name, 
                ["config", "type", "parent"], as_dict=True)
            
            if not stage_data:
                # 🚨 المرحلة غير موجودة! (ربما حُذفت أو الـ ID قديم بتنسيق Lesson-Stage)
                corrupt_tracker_ids.append(item.name)
                continue
                
            # 4. جلب الدرس الأب (Parent Lesson)
            # الحقل parent في الجدول الفرعي يحتوي على اسم الدرس
            lesson_id = stage_data.parent
            
            # التحقق من وجود الدرس ونشره
            lesson_status = frappe.db.get_value("Game Lesson", lesson_id, "is_published")
            if lesson_status is None:
                # الدرس الأب محذوف
                corrupt_tracker_ids.append(item.name)
                continue
            
            if lesson_status == 0:
                # الدرس موجود لكنه غير منشور (Draft)، نتجاوزه ولا نحذفه
                continue

            # 5. تجهيز البيانات
            # نحتاج وثيقة الدرس كاملة لجلب "المموهات" (Distractors) من مراحل أخرى
            lesson_doc = frappe.get_doc("Game Lesson", lesson_id)
            config = frappe.parse_json(stage_data.config)
            
            # =========================================================
            # 🅰️ التحويل: REVEAL -> QUIZ
            # =========================================================
            if stage_data.type == 'Reveal':
                highlights = config.get('highlights', [])
                
                # تجميع بنك المموهات من نفس الدرس
                lesson_distractor_pool = []
                for s in lesson_doc.stages:
                    if s.type == 'Reveal':
                        s_conf = frappe.parse_json(s.config) if s.config else {}
                        for h in s_conf.get('highlights', []):
                            lesson_distractor_pool.append(h['word'])
                
                for idx, highlight in enumerate(highlights):
                    # الفلتر الذري: هل هذا هو السؤال المطلوب؟
                    if target_atom_index is not None and target_atom_index != idx:
                        continue
                        
                    correct_word = highlight['word']
                    question_text = config.get('sentence', '').replace(correct_word, "____")
                    
                    distractors = [w for w in lesson_distractor_pool if w != correct_word]
                    distractors = list(set(distractors)) # إزالة التكرار
                    random.shuffle(distractors)
                    selected_distractors = distractors[:3]
                    
                    while len(selected_distractors) < 3: selected_distractors.append("...") 

                    options = selected_distractors + [correct_word]
                    random.shuffle(options)
                    
                    # الـ ID الجديد
                    atom_id = f"{stage_row_name}:{idx}"

                    quiz_cards.append({
                        "id": atom_id,
                        "type": "quiz",
                        "question": question_text,
                        "correct_answer": correct_word,
                        "options": options,
                        "origin_type": "reveal"
                    })

            # =========================================================
            # 🅱️ التحويل: MATCHING -> QUIZ
            # =========================================================
            elif stage_data.type == 'Matching':
                pairs = config.get('pairs', [])
                
                for idx, pair in enumerate(pairs):
                    if target_atom_index is not None and target_atom_index != idx:
                        continue

                    question_text = pair.get('right')
                    correct_answer = pair.get('left')
                    
                    distractors = [p.get('left') for p in pairs if p.get('left') != correct_answer]
                    random.shuffle(distractors)
                    selected_distractors = distractors[:3]
                    
                    while len(selected_distractors) < 3: selected_distractors.append("...")

                    options = selected_distractors + [correct_answer]
                    random.shuffle(options)
                    
                    atom_id = f"{stage_row_name}:{idx}"
                    
                    quiz_cards.append({
                        "id": atom_id,
                        "type": "quiz",
                        "question": f"ما هو المرادف لـ: {question_text}؟",
                        "correct_answer": correct_answer,
                        "options": options,
                        "origin_type": "matching"
                    })

        # 🧹 تنفيذ التنظيف الذاتي
        if corrupt_tracker_ids:
            # حذف السجلات الفاسدة دفعة واحدة
            frappe.db.delete("Player Memory Tracker", {"name": ["in", corrupt_tracker_ids]})

        random.shuffle(quiz_cards)
        return quiz_cards[:10]

    except Exception as e:
        frappe.log_error("Get Review Session Failed", frappe.get_traceback())
        return []


@frappe.whitelist()
def submit_review_session(session_data):
    """
    النسخة النهائية للمراجعة:
    - تستخدم ID "مراجعة الذاكرة".
    - تستخرج 'subject' من الـ Meta لتحديث الـ SRS ونقاط المادة.
    """
    try:
        user = frappe.session.user
        
        # 1. فك التغليف
        if isinstance(session_data, str):
            data = json.loads(session_data)
        else:
            data = session_data
            
        interactions = data.get('answers', []) 
        session_meta = data.get('session_meta', {})
        total_combo = data.get('total_combo', 0)
        completion_time_ms = data.get('completion_time_ms', 0)
        
        # استخراج المادة (يجب أن يرسلها الفرونت)
        current_subject = session_meta.get('subject')

        # 2. حساب الجوائز
        correct_count = sum(1 for item in interactions if item.get('is_correct'))
        max_combo = int(total_combo)
        
        base_xp = correct_count * 10
        combo_bonus = max_combo * 2
        total_xp = base_xp + combo_bonus
        
        # 3. تحديث الذاكرة (SRS) - مع تمرير المادة
        for item in interactions:
            question_id = item.get('question_id')
            is_correct = item.get('is_correct')
            duration = item.get('time_spent_ms') or item.get('duration_ms') or 3000
            
            if question_id:
                # نمرر current_subject لتخزينه في الـ Tracker
                update_srs_after_review(user, question_id, is_correct, duration, current_subject)

        # 4. تسجيل الجلسة (Log)
        full_log_data = {
            "meta": session_meta,
            "interactions": interactions,
            "stats": {
                "correct": correct_count,
                "combo": max_combo,
                "time_ms": completion_time_ms
            }
        }

        doc = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": user,
            "lesson": "مراجعة الذاكرة",
            "xp_earned": total_xp,
            "score": total_xp,
            "raw_data": json.dumps(full_log_data, ensure_ascii=False)
        })
        doc.insert(ignore_permissions=True)

        # 5. التحديثات المالية والنقاط
        if total_xp > 0:
            # أ. تحديث البروفايل العام
            frappe.db.sql("""
                UPDATE `tabPlayer Profile`
                SET total_xp = total_xp + %s
                WHERE user = %s
            """, (total_xp, user))
            
            # ب. تحديث نقاط المادة (للمتصدرين) ✅
            if current_subject:
                update_subject_progression(user, current_subject, total_xp)

        frappe.db.commit()

        return {
            "status": "success",
            "xp_earned": total_xp,
            "new_stability_counts": get_mastery_counts(user)
        }

    except Exception as e:
        frappe.log_error("Submit Review Failed", frappe.get_traceback())
        return {"status": "error", "message": str(e)}


def update_srs_after_review(user, question_id, is_correct, duration_ms, subject=None):
    """
    تحديث حالة الذاكرة (SRS) مع منطق بونص السرعة وتنظيف السجلات الأب.
    """
    # 1. جلب السجل الحالي لمعرفة المستوى السابق
    tracker_name = frappe.db.get_value("Player Memory Tracker", 
        {"player": user, "question_id": question_id}, "name")
    
    current_stability = 0
    if tracker_name:
        current_stability = cint(frappe.db.get_value("Player Memory Tracker", tracker_name, "stability"))

    # 2. خوارزمية التقييم (SRS Logic)
    new_stability = current_stability
    
    if is_correct:
        # ✅ إجابة صحيحة
        if duration_ms < 2000: 
            # 🚀 سريع جداً (Easy) -> قفزة مزدوجة
            new_stability = min(current_stability + 2, 4)
        elif duration_ms > 6000:
            # 🐢 بطيء (Hard) -> لا زيادة في المتانة، يبقى كما هو
            new_stability = max(current_stability, 1) # نضمن ألا يقل عن 1
        else:
            # 👌 متوسط (Good) -> خطوة واحدة
            new_stability = min(current_stability + 1, 4)
        
        # ضمان الحد الأدنى 1 عند النجاح
        if new_stability < 1: new_stability = 1
            
    else:
        # ❌ خطأ (Fail) -> تصفير الذاكرة
        new_stability = 1 
    
    # 3. حساب الموعد القادم
    # الخريطة: 1=غداً، 2=3أيام، 3=أسبوع، 4=أسبوعين
    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days_to_add = interval_map.get(new_stability, 1)
    
    new_date = add_days(now_datetime(), days_to_add)
    
    # 4. التخزين في قاعدة البيانات
    # نستخدم الدالة المساعدة لضمان توحيد آلية الحفظ (Insert/Update)
    update_memory_tracker(user, question_id, new_stability, new_date, subject)

    # =========================================================
    # 🧹 CLEANUP: ترحيل موعد الأب ليختفي من المهام
    # =========================================================
    # عند حل سؤال فرعي (مثل ...:0)، نقوم بتأجيل السجل الأصلي القديم 
    # (الذي بدون لاحقة) لنفس التاريخ، لكي لا يظهر كتكرار في المراجعات.
    if ":" in question_id:
        parent_id = question_id.rsplit(":", 1)[0]
        parent_tracker = frappe.db.get_value("Player Memory Tracker", 
            {"player": user, "question_id": parent_id}, "name")
            
        if parent_tracker:
            frappe.db.set_value("Player Memory Tracker", parent_tracker, 
                "next_review_date", new_date)


def get_mastery_counts(user):
    # دالة مساعدة لتحديث الواجهة
    data = frappe.db.sql("""
        SELECT stability, COUNT(*) as count 
        FROM `tabPlayer Memory Tracker` 
        WHERE player = %s GROUP BY stability
    """, (user,), as_dict=True)
    mastery_map = {row.stability: row.count for row in data}
    return {
        "new": mastery_map.get(1, 0),
        "learning": mastery_map.get(2, 0),
        "mature": mastery_map.get(3, 0) + mastery_map.get(4, 0)
    }


def create_memory_tracker(user, atom_id, rating):
    """
    إنشاء سجل ذاكرة جديد لسؤال معين.
    يتم استدعاؤها عندما يرى الطالب السؤال لأول مرة، أو عند اكتشاف ID جديد.
    """
    # تحديد موعد المراجعة القادم بناءً على التقييم الأولي
    # 1: غداً، 2: 3 أيام، 3: أسبوع، 4: أسبوعين
    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days = interval_map.get(rating, 1) # الافتراضي يوم واحد
    
    doc = frappe.get_doc({
        "doctype": "Player Memory Tracker",
        "player": user,
        "question_id": atom_id, # تأكد أن هذا يطابق اسم الحقل في الـ DocType
        "stability": rating,
        "last_review_date": now_datetime(),
        "next_review_date": add_days(now_datetime(), days)
    })
    
    doc.insert(ignore_permissions=True)
    return doc.name



def update_subject_progression(user, subject_name, xp_earned):
    """تحديث نقاط الطالب في مادة معينة"""
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
    جلب قائمة المتصدرين (تراكمي أو أسبوعي / عام أو حسب المادة).
    - يدعم حساب الـ Level.
    - يدعم الفلترة الزمنية (Weekly).
    """
    try:
        user = frappe.session.user
        limit = 50
        
        leaderboard = []
        user_rank_info = {}

        # =========================================================
        # 🅰️ السيناريو 1: الترتيب التراكمي (All Time) - الأسرع ⚡
        # =========================================================
        if period == 'all_time':
            if subject:
                # مادة محددة
                query = """
                    SELECT t.player as user_id, t.total_xp, u.full_name, u.user_image 
                    FROM `tabPlayer Subject Score` t
                    JOIN `tabUser` u ON t.player = u.name
                    WHERE t.subject = %s AND t.total_xp > 0
                    ORDER BY t.total_xp DESC LIMIT %s
                """
                params = [subject, limit]
            else:
                # عام (Global)
                query = """
                    SELECT t.user as user_id, t.total_xp, u.full_name, u.user_image 
                    FROM `tabPlayer Profile` t
                    JOIN `tabUser` u ON t.user = u.name
                    WHERE t.total_xp > 0
                    ORDER BY t.total_xp DESC LIMIT %s
                """
                params = [limit]

        # =========================================================
        # 🅱️ السيناريو 2: الترتيب الأسبوعي (Weekly) - تجميعي 📊
        # =========================================================
        else:
            # هنا نجمع النقاط من سجل الجلسات لآخر 7 أيام
            # نستخدم Monday كبداية الأسبوع، أو آخر 7 أيام متحركة (الأسهل)
            date_condition = "creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
            
            # فلترة المادة للجلسات
            # ملاحظة: الجلسة لا تحتوي على Subject مباشر في التصميم القديم،
            # لكننا نعتمد على أنك قد ترغب بإضافته، أو نستخدم Join مع الدرس.
            # للتبسيط والسرعة الآن: سنفترض الأسبوعي "عام" فقط أو يحتاج تعديل Log
            # ** الحل الذكي:** سنعتمد الأسبوعي "عام" (Global) حالياً.
            
            subject_join = ""
            subject_filter = ""
            if subject:
                 # هذا يتطلب أن يكون Gameplay Session يحتوي على Subject أو Join معقد
                 # سنتركه للمستقبل لتجنب البطء، وسنرجع العام مؤقتاً أو فارغ
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

        # تنفيذ الاستعلام
        top_players = frappe.db.sql(query, tuple(params), as_dict=True)

        
        for idx, player in enumerate(top_players):
            current_xp = int(player.total_xp)
            # حساب المستوى بنفس المعادلة
            level = int(0.07 * math.sqrt(current_xp)) + 1 if current_xp > 0 else 1
            
            leaderboard.append({
                "rank": idx + 1,
                "name": player.full_name or "Unknown Hero",
                "avatar": player.user_image,
                "xp": current_xp,
                "level": level, # ✅ الآن نرسل المستوى
                "isCurrentUser": (player.user_id == user)
            })

        # ============================================
        # 3. ترتيب المستخدم الحالي (User Rank)
        # ============================================
        # البحث في القائمة أولاً
        current_user_in_top = next((item for item in leaderboard if item["isCurrentUser"]), None)
        
        if current_user_in_top:
            user_rank_info = current_user_in_top
        else:
            # إذا لم يكن في الـ 50 الأوائل، نعيد بياناته الشخصية لكن بدون Rank دقيق (للسرعة)
            # أو نعيد Rank = "+50"
            
            # جلب نقاطي
            my_xp = 0
            if period == 'all_time':
                if subject:
                    my_xp = frappe.db.get_value("Player Subject Score", {"player": user, "subject": subject}, "total_xp") or 0
                else:
                    my_xp = frappe.db.get_value("Player Profile", {"user": user}, "total_xp") or 0
            else:
                 # حساب نقاطي الأسبوعية
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