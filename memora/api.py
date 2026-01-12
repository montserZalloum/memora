import frappe
import json
from frappe import _
from frappe.utils import now_datetime, add_days, get_datetime

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
        for subject in subjects:
            # حساب عدد الدروس الكلي في هذا الموضوع
            # نقوم بالبحث عن الوحدات التابعة للموضوع، ثم الدروس التابعة لتلك الوحدات
            units = frappe.get_all("Game Unit", filters={"subject": subject.name}, pluck="name")
            
            if units:
                lesson_count = frappe.db.count("Game Lesson", filters={"unit": ["in", units]})
            else:
                lesson_count = 0
                
            subject["total_lessons"] = lesson_count
            
        return subjects

    except Exception as e:
        frappe.log_error(title="get_subjects failed", message=frappe.get_traceback())
        frappe.throw("تعذر تحميل المواضيع حالياً.")

@frappe.whitelist()
def get_map_data(subject):
    try:
        if not subject:
            frappe.throw("الرجاء تحديد الموضوع (Subject)")

        user = frappe.session.user
        
        # 1. التأكد من وجود الموضوع وأنه منشور
        subject_info = frappe.db.get_value("Game Subject", 
            {"name": subject, "is_published": 1}, 
            ["name", "title", "icon"], as_dict=True)
            
        if not subject_info:
            frappe.throw("الموضوع غير موجود أو غير منشور")

        # 2. جلب الدروس المكتملة للمستخدم (نحتاجها لتحديد حالة القفل)
        completed_lessons = frappe.get_all("Gameplay Session", 
            filters={"player": user}, 
            fields=["lesson"], 
            pluck="lesson",
        )
        
        # جلب جميع الوحدات التابعة لهذا الموضوع فقط مرتبة حسب حقل order
        units = frappe.get_all("Game Unit", 
            filters={"subject": subject}, 
            fields=["name", "title", "`order`"], 
            order_by="`order` asc, creation asc"
        )
        
        full_map = []
        
        # متغير لتتبع إذا كان الدرس السابق مكتمل (لفتح الدرس الحالي)
        # ملاحظة: إذا كان هذا أول درس في الموضوع، سنحتاج لمنطق إضافي إذا أردت ربطه بالمواضيع السابقة
        # لكن حالياً سنعتمد أن أول درس في الموضوع المختار متاح دائماً ما لم يكن مكتملاً
        
        for unit in units:
            # جلب دروس الوحدة مرتبة حسب تاريخ الإنشاء
            lessons = frappe.get_all("Game Lesson", 
                filters={"unit": unit.name}, 
                fields=["name", "title", "xp_reward"],
                order_by="creation asc" 
            )
            
            for lesson in lessons:
                status = "locked"
                
                if lesson.name in completed_lessons:
                    status = "completed"
                # إذا كان أول درس في القائمة أو الدرس السابق كان مكتملاً
                elif not full_map or full_map[-1]["status"] == "completed":
                    status = "available"
                
                full_map.append({
                    "id": lesson.name,
                    "title": lesson.title,
                    "unit_title": unit.title,
                    "subject_title": subject_info.title,
                    "subject_icon": subject_info.icon,
                    "status": status,
                    "xp": lesson.xp_reward
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
            
        if not frappe.db.exists("Game Lesson", lesson_id):
            return None

        doc = frappe.get_doc("Game Lesson", lesson_id)
        
        return {
            "name": doc.name,
            "title": doc.title,
            "xp_reward": doc.xp_reward,
            "stages": [
                {
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
        
        # 1. تحويل JSON إلى Python
        if isinstance(session_meta, str): session_meta = json.loads(session_meta)
        if isinstance(interactions, str): interactions = json.loads(interactions)
        if isinstance(gamification_results, str): gamification_results = json.loads(gamification_results)

        lesson_id = session_meta.get('lesson_id')
        if not lesson_id: frappe.throw("Missing lesson_id")

        # استخراج الجوائز
        xp_earned = gamification_results.get('xp_earned', 0)
        score = gamification_results.get('score', 0)
        gems_collected = gamification_results.get('gems_collected', 0)

        # 2. أرشفة الجلسة (Log)
        doc = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": user,
            "lesson": lesson_id,
            "xp_earned": xp_earned, # حفظنا الـ XP في السجل
            "score": score,
            "raw_data": json.dumps(interactions, ensure_ascii=False)
        })
        doc.insert(ignore_permissions=True)
        
        # =========================================================
        # 🆕 3. تحديث المحفظة (Player Profile) - هذا هو الجديد
        # =========================================================
        # نقوم بتحديث رصيد اللاعب مباشرة باستخدام SQL لضمان الدقة والسرعة
        if xp_earned > 0 or gems_collected > 0:
            frappe.db.sql("""
                UPDATE `tabPlayer Profile`
                SET 
                    total_xp = total_xp + %s,
                    gems_balance = gems_balance + %s
                WHERE user = %s
            """, (xp_earned, gems_collected, user))

        # =========================================================

        # 4. تحديث الذاكرة (SRS)
        if interactions and isinstance(interactions, list):
            process_srs_batch(user, interactions)

        # 5. تثبيت الحفظ
        frappe.db.commit() 

        return {
            "status": "success", 
            "message": "تم حفظ الجلسة وتحديث النقاط والذاكرة ✅"
        }

    except Exception as e:
        frappe.log_error(title="submit_session failed", message=frappe.get_traceback())
        frappe.throw(f"Error: {str(e)}")

# =========================================================
# 🧠 THE BRAIN: SRS Algorithms
# =========================================================

def process_srs_batch(user, interactions):
    """
    Orchestrator: Takes raw interactions, calculates ratings, 
    and updates the database for each atom.
    """
    for item in interactions:
        atom_id = item.get("question_id")
        
        # Skip if no ID provided
        if not atom_id: 
            continue
            
        duration = item.get("duration_ms", 0)
        attempts = item.get("attempts_count", 1)

        # 1. INFERENCE: Convert behavior to a Score (1-4)
        rating = infer_rating(duration, attempts)

        # 2. SCHEDULING: Calculate the next review date
        # We fetch the previous state to see if we should extend the interval
        # (For MVP, we use static intervals, but this setup allows for growth)
        next_review_date = calculate_next_review(rating)

        # 3. STORAGE: Save to Database
        update_memory_tracker(user, atom_id, rating, next_review_date)


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


def update_memory_tracker(user, atom_id, rating, next_date):
    """
    Database Operator: Inserts or Updates the record in Frappe.
    """
    # 1. التأكد من اسم الحقل الصحيح (question_id بدلاً من question_atom)
    existing_tracker = frappe.db.get_value(
        "Player Memory Tracker", 
        {"player": user, "question_id": atom_id},  # <--- تم التعديل هنا
        "name"
    )

    if existing_tracker:
        # Update existing record
        frappe.db.set_value("Player Memory Tracker", existing_tracker, {
            "stability": rating,
            "last_review_date": now_datetime(),
            "next_review_date": next_date
        })
    else:
        # Create new record
        doc = frappe.get_doc({
            "doctype": "Player Memory Tracker",
            "player": user,
            "question_id": atom_id,  # <--- تم التعديل هنا أيضاً
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


from frappe.utils import add_days, getdate, nowdate, cint

@frappe.whitelist()
def get_full_profile_stats():
    """
    API شامل لجلب كل إحصائيات البروفايل دفعة واحدة.
    يستخدم لتحليل أداء الطالب وعرضه في صفحة البروفايل.
    """
    try:
        user = frappe.session.user
        
        # 1. جلب البيانات الأساسية (Basic Info)
        # ---------------------------------------------------
        user_doc = frappe.get_doc("User", user)
        profile = frappe.db.get_value("Player Profile", {"user": user}, 
            ["total_xp", "gems_balance"], as_dict=True) or {"total_xp": 0, "gems_balance": 0}
        
        # حساب المستوى (كل 1000 نقطة = مستوى)
        current_xp = profile.get("total_xp", 0)
        level = int(current_xp / 1000) + 1 # نبدأ من المستوى 1
        xp_in_level = current_xp % 1000
        next_level_progress = (xp_in_level / 1000) * 100

        # تحديد اللقب بناءً على المستوى (Gamification)
        titles = ["مستكشف مبتدئ", "مغامر تاريخي", "حارس الذاكرة", "أستاذ الزمان", "أسطورة الأردن"]
        title_index = min(level - 1, len(titles) - 1)
        level_title = titles[title_index]


        # 2. حساب الـ Streak (الأيام المتتالية) 🔥
        # ---------------------------------------------------
        # نجلب كل الأيام التي لعب فيها الطالب (بدون تكرار)، مرتبة من الأحدث للأقدم
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
            
            # تحويل النتائج إلى تواريخ Python للمقارنة
            dates = [getdate(d[0]) for d in activity_dates]
            
            # هل لعب اليوم أو الأمس؟ (إذا لم يلعب الأمس أو اليوم، فالستريك انقطع)
            if dates[0] == today or dates[0] == yesterday:
                streak = 1
                # نبدأ العد العكسي من ثاني تاريخ
                for i in range(1, len(dates)):
                    expected_date = add_days(dates[i-1], -1) # التاريخ المتوقع (أمس بالنسبة للي قبله)
                    if dates[i] == expected_date:
                        streak += 1
                    else:
                        break # انقطع التسلسل
            else:
                streak = 0


        # 3. النشاط الأسبوعي (للرسم البياني) 📊
        # ---------------------------------------------------
        # نجلب مجموع XP لكل يوم في آخر 7 أيام
        weekly_data_raw = frappe.db.sql("""
            SELECT DATE(creation) as day, SUM(xp_earned) as daily_xp
            FROM `tabGameplay Session`
            WHERE player = %s AND creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(creation)
        """, (user,), as_dict=True)

        # تحويل البيانات إلى قاموس للسرعة (Date -> XP)
        xp_map = {getdate(d.day): d.daily_xp for d in weekly_data_raw}
        
        weekly_activity = []
        # ننشئ مصفوفة لآخر 7 أيام حتى لو كانت القيم صفراً
        for i in range(6, -1, -1):
            date_cursor = add_days(getdate(nowdate()), -i)
            weekly_activity.append({
                "day": date_cursor.strftime("%a"), # اسم اليوم (Mon, Tue...)
                "full_date": date_cursor.strftime("%Y-%m-%d"),
                "xp": xp_map.get(date_cursor, 0),
                "isToday": date_cursor == getdate(nowdate())
            })


        # 4. حالة الذاكرة (Mastery Ring) 🧠
        # ---------------------------------------------------
        # نعد العناصر حسب قوتها (Stability)
        # Stability: 1=Fail, 2=Hard, 3=Good, 4=Easy
        mastery_raw = frappe.db.sql("""
            SELECT stability, COUNT(*) as count
            FROM `tabPlayer Memory Tracker`
            WHERE player = %s
            GROUP BY stability
        """, (user,), as_dict=True)
        
        mastery_map = {row.stability: row.count for row in mastery_raw}
        
        # تصنيف النتائج للألوان
        # New/Weak: < 2 | Learning: 2 | Mature: > 2
        total_learned = sum(mastery_map.values())
        stats_mastery = {
            "new": mastery_map.get(1, 0),       # أحمر/رمادي
            "learning": mastery_map.get(2, 0),  # برتقالي
            "mature": mastery_map.get(3, 0) + mastery_map.get(4, 0) # أخضر
        }


        # 5. تجميع الـ JSON النهائي
        # ---------------------------------------------------
        return {
            "fullName": user_doc.full_name or user_doc.username,
            "avatarUrl": user_doc.user_image, # صورة المستخدم من Frappe
            "level": level,
            "levelTitle": level_title,
            "nextLevelProgress": int(next_level_progress),
            "streak": streak,
            "gems": profile.get("gems_balance", 0),
            "totalXP": current_xp,
            "totalLearned": total_learned,
            "weeklyActivity": weekly_activity,
            "mastery": stats_mastery
        }

    except Exception as e:
        frappe.log_error("Get Profile Stats Error", frappe.get_traceback())
        return {} # Return empty object on error