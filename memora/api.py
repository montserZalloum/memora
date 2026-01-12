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


@frappe.whitelist()
def get_full_profile_stats():
    """
    API شامل لجلب كل إحصائيات البروفايل دفعة واحدة.
    """
    try:
        user = frappe.session.user
        
        # 1. جلب البيانات الأساسية
        user_doc = frappe.get_doc("User", user)
        profile = frappe.db.get_value("Player Profile", {"user": user}, 
            ["total_xp", "gems_balance"], as_dict=True) or {"total_xp": 0, "gems_balance": 0}
        
        # --- منطق المستوى (RPG Curve) ---
        current_xp = profile.get("total_xp", 0)
        
        if current_xp == 0:
            level = 1
        else:
            level = int(0.07 * math.sqrt(current_xp)) + 1

        # حدود المستوى (للعرض في الواجهة: 150/500 XP)
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


        # 2. حساب الـ Streak 🔥
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


        # 3. النشاط الأسبوعي (مع تعريب الأيام) 📊
        weekly_data_raw = frappe.db.sql("""
            SELECT DATE(creation) as day, SUM(xp_earned) as daily_xp
            FROM `tabGameplay Session`
            WHERE player = %s AND creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(creation)
        """, (user,), as_dict=True)

        xp_map = {getdate(d.day): d.daily_xp for d in weekly_data_raw}
        
        # قاموس لتعريب الأيام
        days_ar = {
            'Sat': 'سبت', 'Sun': 'أحد', 'Mon': 'إثنين', 
            'Tue': 'ثلاثاء', 'Wed': 'أربعاء', 'Thu': 'خميس', 'Fri': 'جمعة'
        }
        
        weekly_activity = []
        for i in range(6, -1, -1):
            date_cursor = add_days(getdate(nowdate()), -i)
            day_en = date_cursor.strftime("%a")
            
            weekly_activity.append({
                "day": days_ar.get(day_en, day_en), # الاسم العربي
                "full_date": date_cursor.strftime("%Y-%m-%d"),
                "xp": xp_map.get(date_cursor, 0),
                "isToday": date_cursor == getdate(nowdate())
            })


        # 4. حالة الذاكرة 🧠
        mastery_raw = frappe.db.sql("""
            SELECT stability, COUNT(*) as count
            FROM `tabPlayer Memory Tracker`
            WHERE player = %s
            GROUP BY stability
        """, (user,), as_dict=True)
        
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
            # أضفنا هذه القيم لكي تتمكن الواجهة من كتابة (150 / 500 XP)
            "xpInLevel": int(xp_progress_in_level), 
            "xpToNextLevel": int(xp_needed),
            "streak": streak,
            "gems": profile.get("gems_balance", 0),
            "totalXP": int(current_xp),
            "totalLearned": total_learned,
            "weeklyActivity": weekly_activity,
            "mastery": stats_mastery
        }

    except Exception as e:
        frappe.log_error("Get Profile Stats Error", frappe.get_traceback())
        return {}

@frappe.whitelist()
def get_daily_quests():
    """
    يقوم بحساب المهام اليومية (Quests) وإرجاع حالتها.
    (نسخة خالية من الجواهر - Gems Free)
    """
    try:
        user = frappe.session.user
        quests = []

        # =================================================
        # 1. الحسابات (Calculations) - ⚠️ هذا ما كان ناقصاً
        # =================================================
        
        # أ. حساب عدد المراجعات المستحقة
        due_reviews_count = frappe.db.sql("""
            SELECT COUNT(*) 
            FROM `tabPlayer Memory Tracker`
            WHERE player = %s AND next_review_date <= NOW()
        """, (user,))[0][0]

        # ب. حساب هل لعب اليوم؟
        played_today = frappe.db.sql("""
            SELECT COUNT(*) 
            FROM `tabGameplay Session`
            WHERE player = %s AND DATE(creation) = CURDATE()
        """, (user,))[0][0]

        # ج. حساب مجموع XP اليوم
        today_xp = frappe.db.sql("""
            SELECT SUM(xp_earned) 
            FROM `tabGameplay Session`
            WHERE player = %s AND DATE(creation) = CURDATE()
        """, (user,))[0][0] or 0

        # =================================================
        # 2. بناء المهام (Quest Building)
        # =================================================

        # --- المهمة الأولى: إنعاش الذاكرة (SRS) ---
        # تظهر فقط إذا كان هناك مراجعات، أو إذا أنجزها (لتظهر كمكتملة)
        # لكن للتبسيط سنظهرها فقط إذا كانت > 0 لتنبيه المستخدم
        if due_reviews_count > 0:
            quests.append({
                "id": "quest_review",
                "type": "review",
                "title": "أنعش ذاكرتك",
                "description": f"لديك {due_reviews_count} معلومة تحتاج للمراجعة!",
                "icon": "brain",
                "progress": 0,
                "target": due_reviews_count,
                "reward": {"type": "xp", "amount": due_reviews_count * 10}, 
                "status": "active",
                "isUrgent": True # 🔴 يشعل الضوء الأحمر
            })

        # --- المهمة الثانية: شعلة النشاط (Streak) ---
        quests.append({
            "id": "quest_streak",
            "type": "streak",
            "title": "شعلة النشاط",
            "description": "أكمل درساً واحداً اليوم.",
            "icon": "flame",
            "progress": 1 if played_today > 0 else 0,
            "target": 1,
            "reward": {"type": "xp", "amount": 100}, # مكافأة XP بدلاً من الجواهر
            "status": "completed" if played_today > 0 else "active",
            "isUrgent": False
        })

        # --- المهمة الثالثة: تحدي النقاط (Daily XP) ---
        target_xp = 200
        quests.append({
            "id": "quest_xp",
            "type": "xp_goal",
            "title": "تحدي النقاط اليومي",
            "description": f"اجمع {target_xp} نقطة خبرة اليوم.",
            "icon": "trophy",
            "progress": int(today_xp),
            "target": target_xp,
            "reward": {"type": "xp", "amount": 150}, # مكافأة XP بدلاً من الجواهر
            "status": "completed" if today_xp >= target_xp else "active",
            "isUrgent": False
        })

        return quests

    except Exception as e:
        frappe.log_error("Get Daily Quests Failed", frappe.get_traceback())
        return []



import frappe
import json
import random

@frappe.whitelist()
def get_review_session():
    """
    يولد جلسة مراجعة ذكية (Lightning Round).
    الميزات:
    1. يحول الـ Reveal/Matching إلى أسئلة خيارات متعددة (Quiz).
    2. يستخدم Atomic IDs (مثل :0, :1) لتتبع كل معلومة بدقة.
    3. يولد خيارات خاطئة (Distractors) من نفس الدرس.
    """
    try:
        user = frappe.session.user
        
        # 1. جلب العناصر المستحقة للمراجعة
        # نطلب 15 بدلاً من 10 لأن بعض العناصر القديمة قد تتفكك لأكثر من سؤال
        due_items = frappe.db.sql("""
            SELECT question_id, stability 
            FROM `tabPlayer Memory Tracker`
            WHERE player = %s AND next_review_date <= NOW()
            ORDER BY next_review_date ASC
            LIMIT 15
        """, (user,), as_dict=True)
        
        if not due_items:
            return []

        quiz_cards = []
        lesson_map = {} # Cache لتقليل استعلامات الداتابيز
        
        for item in due_items:
            # 2. تحليل الـ ID
            # قد يكون ID قديم: "LESSON-1-STAGE-3"
            # أو ID ذري جديد: "LESSON-1-STAGE-3:1"
            raw_id = item.question_id
            target_atom_index = None
            
            if ":" in raw_id:
                parts = raw_id.rsplit(":", 1)
                
                # نتأكد أن الجزء الأخير هو رقم فعلاً
                if len(parts) == 2 and parts[1].isdigit():
                    base_id = parts[0]
                    target_atom_index = int(parts[1])
                else:
                    # في هذه الحالة، النقطة هي جزء من الاسم وليست الفاصل
                    base_id = raw_id
                    target_atom_index = None
            else:
                base_id = raw_id
                
            # تفكيك الـ Base ID لمعرفة الدرس والمرحلة
            # المتوقع: {LESSON_ID}-STAGE-{INDEX}
            if "-STAGE-" not in base_id: continue
            
            parts = base_id.split('-STAGE-')
            lesson_id = parts[0]
            try:
                stage_index = int(parts[1])
            except: continue
            
            # 3. جلب محتوى الدرس (مع الكاش)
            if lesson_id not in lesson_map:
                if frappe.db.exists("Game Lesson", lesson_id):
                    lesson_map[lesson_id] = frappe.get_doc("Game Lesson", lesson_id)
                else:
                    continue
            
            lesson_doc = lesson_map[lesson_id]
            
            if stage_index >= len(lesson_doc.stages): continue
            
            stage = lesson_doc.stages[stage_index]
            config = frappe.parse_json(stage.config)
            
            # =========================================================
            # 🅰️ التحويل: REVEAL -> QUIZ
            # =========================================================
            if stage.type == 'Reveal':
                highlights = config.get('highlights', [])
                
                # تجهيز "بنك المموهات" من نفس الدرس
                lesson_distractor_pool = []
                for s in lesson_doc.stages:
                    if s.type == 'Reveal':
                        s_conf = frappe.parse_json(s.config)
                        for h in s_conf.get('highlights', []):
                            lesson_distractor_pool.append(h['word'])
                
                # الدوران على كل كلمة في المرحلة
                for idx, highlight in enumerate(highlights):
                    # 🔴 الفلتر الذري:
                    # إذا كان الـ Tracker يطلب الكلمة رقم 1 تحديداً، نتجاهل الباقي
                    if target_atom_index is not None and target_atom_index != idx:
                        continue
                        
                    correct_word = highlight['word']
                    
                    # إنشاء السؤال (استبدال الكلمة بفراغ)
                    question_text = config.get('sentence', '').replace(correct_word, "____")
                    
                    # اختيار 3 خيارات خاطئة
                    distractors = [w for w in lesson_distractor_pool if w != correct_word]
                    # إزالة التكرار
                    distractors = list(set(distractors))
                    random.shuffle(distractors)
                    selected_distractors = distractors[:3]
                    
                    # تعبئة النقص إذا لم نجد كلمات كافية
                    while len(selected_distractors) < 3:
                        selected_distractors.append("...") 

                    options = selected_distractors + [correct_word]
                    random.shuffle(options)
                    
                    # تحديد الـ ID الجديد (دائماً نستخدم الـ Suffix الآن)
                    atom_id = f"{base_id}:{idx}"

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
            elif stage.type == 'Matching':
                pairs = config.get('pairs', [])
                
                for idx, pair in enumerate(pairs):
                    # 🔴 الفلتر الذري
                    if target_atom_index is not None and target_atom_index != idx:
                        continue

                    question_text = pair.get('right') # السؤال
                    correct_answer = pair.get('left') # الجواب
                    
                    # المموهات: الإجابات الأخرى في نفس السؤال
                    distractors = [p.get('left') for p in pairs if p.get('left') != correct_answer]
                    
                    random.shuffle(distractors)
                    selected_distractors = distractors[:3]
                    
                    while len(selected_distractors) < 3:
                         selected_distractors.append("...")

                    options = selected_distractors + [correct_answer]
                    random.shuffle(options)
                    
                    atom_id = f"{base_id}:{idx}"
                    
                    quiz_cards.append({
                        "id": atom_id,
                        "type": "quiz",
                        "question": f"ما هو المرادف لـ: {question_text}؟",
                        "correct_answer": correct_answer,
                        "options": options,
                        "origin_type": "matching"
                    })

    
        # خلط الأسئلة النهائية
        random.shuffle(quiz_cards)
        
        # إرجاع 10 فقط للجلسة السريعة
        return quiz_cards[:10]

    except Exception as e:
        frappe.log_error("Get Review Session Failed", frappe.get_traceback())
        return []


@frappe.whitelist()
def submit_review_session(session_data):
    """
    API خاص لاستلام نتائج المراجعة السريعة.
    تم تحديثه ليدعم تحليل الوقت المستغرق (Duration).
    """
    try:
        ensure_review_system_exists() 

        user = frappe.session.user
        if isinstance(session_data, str):
            session_data = json.loads(session_data)

        # 1. استخراج البيانات
        results = session_data.get('results', {})
        # لاحظ: في الفرونت أسميناها interactions، تأكد أن الاسم متطابق
        interactions = session_data.get('interactions', []) 
        
        # 2. حساب الجوائز (Gamification)
        correct_count = results.get('correct_count', 0)
        max_combo = results.get('max_combo', 0)
        
        base_xp = correct_count * 10
        combo_bonus = max_combo * 2
        total_xp = base_xp + combo_bonus
        
        # 3. تحديث الذاكرة (SRS with Time Logic) 🧠
        for item in interactions:
            question_id = item.get('question_id')
            is_correct = item.get('is_correct')
            # 👇 الجديد: قراءة الوقت (الافتراضي 3000ms إذا لم يرسل)
            duration = item.get('duration_ms', 3000) 
            
            update_srs_after_review(user, question_id, is_correct, duration)

        # 4. تسجيل الجلسة
        doc = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": user,
            "lesson": "REVIEW-SESSION",
            "xp_earned": total_xp,
            "score": total_xp,
            "raw_data": json.dumps(session_data, ensure_ascii=False)
        })
        doc.insert(ignore_permissions=True)

        # 5. تحديث الرصيد
        if total_xp > 0:
            frappe.db.sql("""
                UPDATE `tabPlayer Profile`
                SET total_xp = total_xp + %s
                WHERE user = %s
            """, (total_xp, user))

        frappe.db.commit()

        return {
            "status": "success",
            "xp_earned": total_xp,
            "new_stability_counts": get_mastery_counts(user)
        }

    except Exception as e:
        frappe.log_error("Submit Review Failed", frappe.get_traceback())
        return {"status": "error", "message": str(e)}


def update_srs_after_review(user, question_id, is_correct, duration_ms):
    """
    تحديث حالة الذاكرة بناءً على الدقة والسرعة.
    """
    # البحث عن السجل (الآن يدعم Atomic IDs مثل ...:1 تلقائياً لأنه مجرد نص)
    tracker_name = frappe.db.get_value("Player Memory Tracker", 
        {"player": user, "question_id": question_id}, "name")
    
    if not tracker_name: 
        # حالة نادرة: إذا كان الـ ID جديداً (لم ينشأ من قبل)، ننشئه الآن
        # هذا يحمي النظام في حال تغيرت طريقة توليد الـ IDs
        create_memory_tracker(user, question_id, 1) # نبدأ بـ 1
        return

    current_data = frappe.db.get_value("Player Memory Tracker", tracker_name, 
        ["stability"], as_dict=True)
    
    current_stability = cint(current_data.stability)
    new_stability = current_stability
    
    if is_correct:
        # ✅ الإجابة صحيحة: نحلل السرعة
        
        if duration_ms < 2000: 
            # 🚀 سريع جداً (Easy) -> قفزة مزدوجة (بونص)
            new_stability = min(current_stability + 2, 4)
            
        elif duration_ms > 6000:
            # 🐢 بطيء (Hard) -> يبقى في مكانه (تثبيت)
            # لا نزيد الـ stability لكن نحدث تاريخ المراجعة ليصبح أبعد قليلاً من "الآن"
            new_stability = current_stability # لا تغيير في المستوى
            
        else:
            # 👌 متوسط (Good) -> خطوة واحدة للأمام
            new_stability = min(current_stability + 1, 4)
            
    else:
        # ❌ خطأ (Fail) -> تصفير الذاكرة
        new_stability = 1 
    
    # حساب الموعد القادم
    # 1: غداً، 2: 3 أيام، 3: أسبوع، 4: أسبوعين
    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days_to_add = interval_map.get(new_stability, 1)
    
    new_date = add_days(nowdate(), days_to_add)
    
    # تنفيذ التحديث
    frappe.db.set_value("Player Memory Tracker", tracker_name, {
        "stability": new_stability,
        "last_review_date": now_datetime(),
        "next_review_date": new_date
    })

def get_mastery_counts(user):
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


def ensure_review_system_exists():
    """
    تتأكد من وجود مادة ووحدة ودرس خاص بالنظام (System)
    لربط جلسات المراجعة بها ومنع أخطاء الروابط.
    """
    try:
        # 1. إنشاء مادة للنظام (إذا لم توجد)
        if not frappe.db.exists("Game Subject", "System"):
            frappe.get_doc({
                "doctype": "Game Subject",
                "title": "System",
                "name": "System", # ID يدوي
                "is_published": 0 # مخفية عن الطلاب
            }).insert(ignore_permissions=True)

        # 2. إنشاء وحدة للمراجعات
        if not frappe.db.exists("Game Unit", "System-Reviews"):
            frappe.get_doc({
                "doctype": "Game Unit",
                "title": "System Reviews",
                "name": "System-Reviews",
                "subject": "System",
                "order": 9999
            }).insert(ignore_permissions=True)

        # 3. إنشاء درس المراجعة (الذي نبحث عنه)
        if not frappe.db.exists("Game Lesson", "REVIEW-SESSION"):
            frappe.get_doc({
                "doctype": "Game Lesson",
                "title": "مراجعة الذاكرة",
                "name": "REVIEW-SESSION", # 👈 هذا هو الـ ID المهم
                "unit": "System-Reviews",
                "xp_reward": 0
            }).insert(ignore_permissions=True)
            
    except Exception as e:
        # في حال كان هناك Naming Series يمنع الأسماء اليدوية،
        # قد نحتاج لحل آخر، لكن هذا سيعمل في 99% من الحالات
        frappe.log_error("Setup Review System Failed", str(e))