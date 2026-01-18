import frappe
import json
from frappe import _
import math
from frappe.utils import now_datetime, add_days, get_datetime, getdate, nowdate, cint
import random
from .ai_engine import get_ai_distractors

@frappe.whitelist()
def get_subjects():
    """
    جلب المواد الخاصة بالطالب بناءً على خطته الدراسية (صفه وتخصصه).
    المنطق:
    1. نحدد صف وتخصص الطالب.
    2. نجلب الخطة الدراسية (Academic Plan) المطابقة.
    3. نعرض المواد المذكورة في الخطة فقط.
    4. نستخدم "اسم العرض" (Display Name) من الخطة إذا وجد (مثلاً: عرض "رياضيات" بدلاً من "رياضيات أدبي").
    """
    try:
        user = frappe.session.user
        
        # 1. جلب بيانات الطالب (Context)
        profile = frappe.db.get_value("Player Profile", {"user": user}, 
            ["current_grade", "current_stream", "academic_year"], as_dict=True)
            
        if not profile or not profile.current_grade:
            # حالة خاصة: لم يقم الطالب بالتسجيل (Onboarding) بعد
            # يمكننا إرجاع "كل المواد" كعرض تجريبي، أو قائمة فارغة لتوجيهه للإعدادات
            # سنرجع فارغ ليقوم الفرونت بتحويله لصفحة Onboarding
            return []

        # 2. البحث عن الخطة الدراسية (The Plan)
        # نبحث عن خطة تطابق الصف + التخصص + السنة
        filters = {
            "grade": profile.current_grade,
            "year": profile.academic_year or "2025" # Fallback year
        }
        
        # التخصص قد يكون فارغاً (للصفوف الأساسية)، لذا نتحقق منه
        if profile.current_stream:
            filters["stream"] = profile.current_stream
            
        plan_name = frappe.db.get_value("Game Academic Plan", filters, "name")
        
        if not plan_name:
            # لم نجد خطة لهذا التخصص! (خطأ في إدخال البيانات من الأدمن)
            return []

        # 3. جلب المواد من داخل الخطة
        # نستخرج المواد من الجدول الفرعي (Game Plan Subject)
        plan_subjects = frappe.get_all("Game Plan Subject", 
            filters={"parent": plan_name}, 
            fields=["subject", "display_name"],
            order_by="idx asc" # الترتيب حسب ما وضعه الأدمن في الخطة
        )
        
        final_list = []
        
        for item in plan_subjects:
            # جلب تفاصيل المادة الأصلية (الأيقونة، اللون، إلخ)
            original_subject = frappe.db.get_value("Game Subject", item.subject, 
                ["name", "title", "icon", "is_paid"], as_dict=True)
            
            if not original_subject: continue

            # المنطق الذكي للتسمية 🧠
            # إذا كان هناك "display_name" في الخطة، نستخدمه (مثلاً: "إنجليزي")
            # وإلا نستخدم الاسم الأصلي (مثلاً: "إنجليزي مستوى ثالث")
            title_to_show = item.display_name if item.display_name else original_subject.title
            
            final_list.append({
                "name": original_subject.name,   # الـ ID الحقيقي
                "title": title_to_show,          # الاسم المخصص للطالب
                "icon": original_subject.icon,
                "is_paid": original_subject.is_paid
                # لا نرسل "locked" هنا، لأننا نريد السماح له بالدخول لرؤية الـ Free Preview
            })

        return final_list

    except Exception as e:
        frappe.log_error("Get Subjects Failed", frappe.get_traceback())
        return []


@frappe.whitelist()
def get_my_subjects():
    """
    Get subjects specific to the current user's Academic Plan.
    Returns subjects with their display names and additional metadata.
    """
    try:
        user = frappe.session.user

        # 1. Fetch Player Profile
        profile = frappe.db.get_value("Player Profile",
            {"user": user},
            ["current_grade", "current_stream", "academic_year"],
            as_dict=True)

        if not profile or not profile.current_grade:
            return []  # No profile set up yet

        current_grade = profile.current_grade
        current_stream = profile.current_stream
        academic_year = profile.academic_year or "2025"

        # 2. Fetch the Game Academic Plan
        plan_filters = {
            "grade": current_grade,
            "year": academic_year
        }

        if current_stream:
            plan_filters["stream"] = current_stream

        plan_name = frappe.db.get_value("Game Academic Plan", plan_filters, "name")

        if not plan_name:
            return []  # No plan configured

        plan = frappe.get_doc("Game Academic Plan", plan_name)

        # 3. Extract unique subjects from the plan
        subject_map = {}

        for row in plan.subjects:
            subject_name = row.subject

            if subject_name not in subject_map:
                # Fetch subject details
                subject_info = frappe.db.get_value("Game Subject",
                    {"name": subject_name, "is_published": 1},
                    ["name", "title", "icon"], as_dict=True)

                if subject_info:
                    subject_map[subject_name] = {
                        "id": subject_info.name,
                        "name": subject_info.title,
                        "icon": subject_info.icon,
                        "display_name": row.display_name or subject_info.title,
                        "is_mandatory": row.is_mandatory
                    }

        # Convert to list
        subjects = list(subject_map.values())

        return subjects

    except Exception as e:
        frappe.log_error(title="get_my_subjects failed", message=frappe.get_traceback())
        return []


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
        

import frappe
from frappe import _
from frappe.utils import nowdate, cint

# =========================================================
# 🗺️ MAP ENGINE: The Core Logic
# =========================================================

@frappe.whitelist()
def get_map_data(subject=None):
    """
    محرك الخريطة الذكي (Smart Hybrid Map).
    - إذا كانت الوحدة (Lesson Based): تعيد الدروس فوراً لرسم المسار.
    - إذا كانت الوحدة (Topic Based): تعيد المواضيع فقط (Lazy Load).
    """
    try:
        user = frappe.session.user

        # 1. السياق الأكاديمي
        profile = frappe.db.get_value("Player Profile", {"user": user}, 
            ["current_grade", "current_stream", "academic_year"], as_dict=True)

        if not profile or not profile.current_grade:
            return [] 

        # 2. جلب الخطة
        plan_filters = {
            "grade": profile.current_grade,
            "year": profile.academic_year or "2025"
        }
        if profile.current_stream:
            plan_filters["stream"] = profile.current_stream

        plan_name = frappe.db.get_value("Game Academic Plan", plan_filters, "name")
        if not plan_name: return []

        plan_doc = frappe.get_doc("Game Academic Plan", plan_name)

        # 3. تجميع القواعد
        subject_rules = {}
        for row in plan_doc.subjects:
            if subject and row.subject != subject: continue 

            if row.subject not in subject_rules:
                subject_rules[row.subject] = {
                    'include_all': False,
                    'units': set(),
                    'display_name': row.display_name or None
                }
            
            if row.selection_type == 'All Units':
                subject_rules[row.subject]['include_all'] = True
            elif row.selection_type == 'Specific Unit' and row.specific_unit:
                subject_rules[row.subject]['units'].add(row.specific_unit)

        # 4. البيانات المساعدة
        active_subs = get_user_active_subscriptions(user)
        completed_lessons_set = set(frappe.get_all("Gameplay Session", 
            filters={"player": user}, pluck="lesson"))

        final_map = []

        for sub_id, rule in subject_rules.items():
            subject_doc = frappe.db.get_value("Game Subject", sub_id, 
                ["name", "title", "is_paid"], as_dict=True)
            if not subject_doc: continue

            unit_filters = {"subject": sub_id}
            if not rule['include_all']:
                if not rule['units']: continue 
                unit_filters["name"] = ["in", list(rule['units'])]

            units = frappe.get_all("Game Unit", 
                filters=unit_filters,
                fields=["name", "title", "learning_track", "is_free_preview", "structure_type", "is_linear_topics"],
                order_by="creation asc"
            )

            subject_data = {
                "subject_id": sub_id,
                "title": rule['display_name'] or subject_doc.title,
                "units": []
            }

            previous_unit_completed = True 

            for unit in units:
                track_is_paid = 0
                if unit.learning_track:
                    track_is_paid = frappe.db.get_value("Game Learning Track", unit.learning_track, "is_paid") or 0

                # تحديد نوع الهيكلية للعرض
                # نرسلها للفرونت ليقرر شكل الرسم
                unit_style = "lessons" if unit.structure_type == "Lesson Based" else "topics"

                unit_output = {
                    "id": unit.name,
                    "title": unit.title,
                    "style": unit_style, # 👈 الحقل الجديد للتمييز
                    "topics": []
                }

                # -------------------------------------------------
                # السيناريو 1: Lesson Based (تحميل فوري للدروس)
                # -------------------------------------------------
                if unit_style == "lessons":
                    # نجلب الدروس مباشرة ونضعها في توبيك وهمي
                    direct_lessons = frappe.get_all("Game Lesson", 
                        filters={"unit": unit.name, "topic": ["is", "not set"], "is_published": 1},
                        fields=["name", "title", "xp_reward"],
                        order_by="creation asc"
                    )
                    
                    if not direct_lessons: continue

                    # معالجة حالة الدروس (قفل/فتح)
                    processed_lessons = []
                    previous_lesson_completed = True
                    has_financial_access = False
                    
                    # فحص مالي (وحدة)
                    if unit.is_free_preview or (not subject_doc.is_paid and not track_is_paid) or check_subscription_access(active_subs, sub_id, unit.learning_track):
                        has_financial_access = True

                    for lesson in direct_lessons:
                        is_completed = lesson.name in completed_lessons_set
                        status = "locked"
                        
                        if is_completed:
                            status = "completed"
                        else:
                            if not has_financial_access:
                                status = "locked_premium"
                            elif previous_lesson_completed: # (نفترض دائماً خطي في هذا الوضع)
                                status = "available"
                                previous_lesson_completed = False
                            else:
                                status = "locked"
                        
                        processed_lessons.append({
                            "id": lesson.name,
                            "title": lesson.title,
                            "status": status,
                            "xp": lesson.xp_reward
                        })
                        if is_completed: previous_lesson_completed = True

                    # إضافة التوبيك الوهمي مع الدروس
                    unit_output["topics"].append({
                        "id": f"{unit.name}-default",
                        "title": unit.title,
                        "is_virtual": True,
                        "lessons": processed_lessons # ✅ نرسل الدروس هنا
                    })

                # -------------------------------------------------
                # السيناريو 2: Topic Based (تحميل كسول)
                # -------------------------------------------------
                else:
                    real_topics = frappe.get_all("Game Topic", 
                        filters={"unit": unit.name},
                        fields=["name", "title", "is_free_preview", "is_linear", "description"],
                        order_by="creation asc"
                    )
                    
                    previous_topic_completed = True # للتحكم بتسلسل التوبيكس

                    for topic in real_topics:
                        # فحص مالي (توبيك)
                        has_financial_access = False
                        if unit.is_free_preview or topic.is_free_preview or (not subject_doc.is_paid and not track_is_paid) or check_subscription_access(active_subs, sub_id, unit.learning_track):
                            has_financial_access = True

                        # نحتاج لحساب حالة التوبيك (هل هو مكتمل؟)
                        # هنا نضطر لجلب الدروس فقط للحساب (Count Check) وليس للإرسال
                        topic_lessons = frappe.get_all("Game Lesson", 
                            filters={"topic": topic.name, "is_published": 1},
                            fields=["name"], # ID only
                            order_by="creation asc"
                        )
                        
                        total_lessons = len(topic_lessons)
                        completed_count = len([l for l in topic_lessons if l.name in completed_lessons_set])
                        is_fully_completed = (total_lessons > 0 and total_lessons == completed_count)

                        # تحديد حالة التوبيك
                        topic_status = "locked"
                        if is_fully_completed:
                            topic_status = "completed"
                        elif not has_financial_access:
                            topic_status = "locked_premium"
                        elif unit.is_linear_topics and not previous_topic_completed:
                            topic_status = "locked"
                        else:
                            # إذا كان متاحاً مالياً، ووصله الدور في الترتيب
                            topic_status = "available"

                        if is_fully_completed: previous_topic_completed = True
                        
                        # إضافة التوبيك (بدون دروس)
                        unit_output["topics"].append({
                            "id": topic.name,
                            "title": topic.title,
                            "description": topic.description,
                            "status": topic_status,
                            "stats": { # ميتا داتا للعرض
                                "total": total_lessons,
                                "completed": completed_count
                            }
                            # ❌ lessons removed here
                        })

                subject_data["units"].append(unit_output)
            
            final_map.append(subject_data)

        return final_map

    except Exception as e:
        frappe.log_error("Get Map Failed", frappe.get_traceback())
        return []

# =========================================================
# 🛠️ HELPER: Subscription Checker
# =========================================================

def get_user_active_subscriptions(user):
    """
    جلب الاشتراكات الفعالة.
    التصحيح:
    1. يعتمد على تاريخ انتهاء 'الموسم' (Linked Season) وليس الاشتراك نفسه.
    2. يجلب ID البروفايل الصحيح بدلاً من التخمين.
    """
    # 1. جلب معرف البروفايل الآمن (Best Practice)
    # هذا يحميك لو قررت تغير تسمية البروفايل مستقبلاً
    profile_name = frappe.db.get_value("Player Profile", {"user": user}, "name")
    
    if not profile_name:
        return []

    # 2. الاستعلام الذكي (SQL Join)
    # نربط جدول الاشتراكات بجدول المواسم للتحقق من التاريخ
    active_subs = frappe.db.sql("""
        SELECT 
            sub.name, sub.type
        FROM 
            `tabGame Player Subscription` sub
        JOIN 
            `tabGame Subscription Season` season ON sub.linked_season = season.name
        WHERE 
            sub.player = %s 
            AND sub.status = 'Active'
            AND season.end_date >= CURDATE()
    """, (profile_name,), as_dict=True)
    
    # 3. تجميع العناصر (Items Retrieval)
    final_access_list = []
    
    for sub in active_subs:
        if sub.type == 'Global Access':
            final_access_list.append({"type": "Global"})
        else:
            # جلب المواد المحددة من الجدول الفرعي
            items = frappe.get_all("Game Subscription Access", 
                filters={"parent": sub.name}, 
                fields=["type", "subject", "track"]
            )
            final_access_list.extend(items)
            
    return final_access_list

def check_subscription_access(active_subs, subject_id, track_id=None):
    """
    فحص هل تغطي الاشتراكات هذه المادة أو التراك.
    """
    for access in active_subs:
        # 1. اشتراك شامل
        if access.get("type") == "Global":
            return True
            
        # 2. اشتراك مادة
        if access.get("type") == "Subject" and access.get("subject") == subject_id:
            return True
            
        # 3. اشتراك تراك (إذا وجد)
        if track_id and access.get("type") == "Track" and access.get("track") == track_id:
            return True
            
    return False


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
        
        if isinstance(session_meta, str): session_meta = json.loads(session_meta)
        if isinstance(interactions, str): interactions = json.loads(interactions)
        if isinstance(gamification_results, str): gamification_results = json.loads(gamification_results)

        lesson_id = session_meta.get('lesson_id')
        if not lesson_id: frappe.throw("Missing lesson_id")

        xp_earned = gamification_results.get('xp_earned', 0)
        score = gamification_results.get('score', 0)

        # 1. اكتشاف المادة والتوبيك (Subject & Topic Lookup) 🕵️‍♂️
        # نجلب topic من الدرس، و subject من التراك/الوحدة
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

        # 2. أرشفة الجلسة
        doc = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": user,
            "lesson": lesson_id,
            "xp_earned": xp_earned,
            "score": score,
            "raw_data": json.dumps(interactions, ensure_ascii=False)
        })
        doc.insert(ignore_permissions=True)
        
        # 3. تحديث الـ XP العام
        if xp_earned > 0:
            frappe.db.sql("UPDATE `tabPlayer Profile` SET total_xp = total_xp + %s WHERE user = %s", (xp_earned, user))

        # 4. تحديث نقاط المادة (Leaderboard)
        if current_subject and xp_earned > 0:
            update_subject_progression(user, current_subject, xp_earned)

        # 5. تحديث الذاكرة (SRS) - نمرر المادة والتوبيك ✅
        if interactions and isinstance(interactions, list):
            process_srs_batch(user, interactions, current_subject, current_topic)

        frappe.db.commit() 

        return {"status": "success", "message": "Session Saved ✅"}

    except Exception as e:
        frappe.log_error("submit_session failed", frappe.get_traceback())
        frappe.throw(str(e))

# =========================================================
# 🧠 THE BRAIN: SRS Algorithms
# =========================================================

def process_srs_batch(user, interactions, subject=None, topic=None):
    """
    معالجة مجموعة من التفاعلات لتحديث الذاكرة.
    تستقبل 'subject' لتمريره للدالة النهائية.
    """
    for item in interactions:
        atom_id = item.get("question_id")
        if not atom_id: continue
        duration = item.get("duration_ms", item.get("time_spent_ms", 3000))
        attempts = item.get("attempts_count", 1)
        rating = infer_rating(duration, attempts)
        next_review_date = calculate_next_review(rating)
        
        # ✅ نمرر التوبيك
        update_memory_tracker(user, atom_id, rating, next_review_date, subject, topic)


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


def update_memory_tracker(user, atom_id, rating, next_date, subject=None, topic=None): # ✅
    existing_tracker = frappe.db.get_value("Player Memory Tracker", 
        {"player": user, "question_id": atom_id}, "name")

    values = {
        "stability": rating,
        "last_review_date": now_datetime(),
        "next_review_date": next_date
    }
    if subject: values["subject"] = subject
    if topic: values["topic"] = topic # ✅ حفظ التوبيك عند التحديث

    if existing_tracker:
        frappe.db.set_value("Player Memory Tracker", existing_tracker, values)
    else:
        doc = frappe.get_doc({
            "doctype": "Player Memory Tracker",
            "player": user,
            "question_id": atom_id,
            "subject": subject,
            "topic": topic, # ✅ حفظ التوبيك عند الإنشاء
            "stability": rating,
            "last_review_date": now_datetime(),
            "next_review_date": next_date
        })
        doc.insert(ignore_permissions=True)


@frappe.whitelist()
def get_player_profile():
    """
    جلب البيانات الأساسية للاعب عند فتح التطبيق.
    التحديث: إضافة الصف والتخصص للتحقق من الـ Onboarding.
    """
    try:
        user = frappe.session.user
        
        # جلب البيانات من البروفايل بما فيها الحقول الأكاديمية الجديدة
        profile = frappe.db.get_value("Player Profile", {"user": user}, 
            ["total_xp", "gems_balance", "current_grade", "current_stream"], 
            as_dict=True
        )

        if not profile:
            # في حال كان مستخدماً جديداً جداً وليس له بروفايل بعد
            return {
                "xp": 0, 
                "gems": 0, 
                "current_grade": None,
                "current_stream": None
            }

        return {
            "xp": int(profile.total_xp or 0),
            "gems": int(profile.gems_balance or 0),
            # 👇 هذه هي الحقول التي ينتظرها الفرونت-إند
            "current_grade": profile.current_grade,
            "current_stream": profile.current_stream
        }

    except Exception as e:
        frappe.log_error("Get Player Profile Failed", frappe.get_traceback())
        return {}


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
def get_review_session(subject=None, topic_id=None):
    """
    جلب جلسة مراجعة ذكية.
    المميزات:
    1. دعم وضع التركيز (Topic Focus) مع حجم ديناميكي.
    2. استبعاد الأسئلة التي تم حلها اليوم (Smart Filtering).
    3. تنظيف ذاتي للبيانات الفاسدة (Self-Healing).
    4. استخدام AI لتوليد الخيارات الخاطئة (Distractors).
    """
    try:
        user = frappe.session.user
        import random
        
        limit = 15 # الحد الافتراضي للمراجعة العامة

        # =========================================================
        # 1. جلب العناصر المرشحة (Fetch Candidates)
        # =========================================================
        
        # A. مراجعة توبيك محدد (Focus Mode) 🎯
        if topic_id:
            # حساب الحجم المناسب
            total_items = frappe.db.count("Player Memory Tracker", {"player": user, "topic": topic_id})
            if total_items == 0: return []

            calculated_limit = int(total_items * 0.10)
            limit = max(10, min(calculated_limit, 30))

            # الاستعلام الذكي: هات (الخطأ) أو (القديم). استبعد (الجديد الصحيح).
            due_items = frappe.db.sql("""
                SELECT name, question_id, stability 
                FROM `tabPlayer Memory Tracker`
                WHERE player = %s 
                AND topic = %s
                AND (
                    stability = 1 
                    OR 
                    last_review_date < CURDATE()
                )
                ORDER BY stability ASC, last_review_date ASC
                LIMIT %s
            """, (user, topic_id, limit), as_dict=True)

            # خطة الطوارئ (Fallback): إذا القائمة فارغة (ختم التوبيك اليوم)، هات عشوائي
            if not due_items and total_items > 0:
                due_items = frappe.db.sql("""
                    SELECT name, question_id, stability 
                    FROM `tabPlayer Memory Tracker`
                    WHERE player = %s AND topic = %s
                    ORDER BY RAND()
                    LIMIT 10
                """, (user, topic_id), as_dict=True)

        # B. مراجعة عامة (Daily Mix) 📅
        else:
            conditions = "player = %s AND next_review_date <= NOW()"
            params = [user]
            if subject:
                conditions += " AND subject = %s"
                params.append(subject)
                
            due_items = frappe.db.sql(f"""
                SELECT name, question_id, stability 
                FROM `tabPlayer Memory Tracker`
                WHERE {conditions}
                ORDER BY next_review_date ASC
                LIMIT 15
            """, tuple(params), as_dict=True)
        
        if not due_items: return []

        quiz_cards = []
        corrupt_tracker_ids = []
        lesson_cache = {} # Cache لتجنب تكرار جلب نفس الدرس

        # =========================================================
        # 2. معالجة البطاقات (Processing Cards)
        # =========================================================
        for item in due_items:
            raw_id = item.question_id
            
            # أ. تحليل المعرف (ID Parsing)
            if ":" in raw_id:
                parts = raw_id.rsplit(":", 1)
                stage_row_name = parts[0]
                try: target_atom_index = int(parts[1])
                except: target_atom_index = None
            else:
                stage_row_name = raw_id
                target_atom_index = None

            # ب. البحث الآمن (Safe Lookup) 🔥
            stage_data = None
            try:
                stage_data = frappe.db.get_value("Game Stage", stage_row_name, 
                    ["config", "type", "parent"], as_dict=True)
            except Exception:
                stage_data = None

            if not stage_data:
                corrupt_tracker_ids.append(item.name)
                continue
                
            # ج. التحقق من الدرس
            lesson_id = stage_data.parent
            if lesson_id not in lesson_cache:
                lesson_doc = frappe.get_doc("Game Lesson", lesson_id)
                if not lesson_doc.is_published:
                    corrupt_tracker_ids.append(item.name)
                    continue
                lesson_cache[lesson_id] = lesson_doc
            
            lesson_doc = lesson_cache[lesson_id]
            config = frappe.parse_json(stage_data.config)
            
            # =====================================================
            # د. تحويل REVEAL -> QUIZ
            # =====================================================
            if stage_data.type == 'Reveal':
                highlights = config.get('highlights', [])
                
                # 1. تجميع المخزون المحلي (الخيار الاحتياطي)
                local_distractor_pool = []
                for s in lesson_doc.stages:
                    if s.type == 'Reveal':
                        s_conf = frappe.parse_json(s.config) if s.config else {}
                        for h in s_conf.get('highlights', []):
                            local_distractor_pool.append(h['word'])
                
                for idx, highlight in enumerate(highlights):
                    if target_atom_index is not None and target_atom_index != idx:
                        continue
                        
                    correct_word = highlight['word']
                    question_text = config.get('sentence', '').replace(correct_word, "____")
                    
                    # 🤖 محاولة الـ AI
                    selected_distractors = []
                    # تأكد أن دالة get_ai_distractors موجودة في الملف
                    ai_options = get_ai_distractors("reveal", correct_word, config.get('sentence', ''))
                    
                    if ai_options and len(ai_options) >= 3:
                        selected_distractors = ai_options[:3]
                    else:
                        # Fallback: استخدام المخزون المحلي
                        distractors = [w for w in local_distractor_pool if w != correct_word]
                        distractors = list(set(distractors))
                        random.shuffle(distractors)
                        selected_distractors = distractors[:3]
                        while len(selected_distractors) < 3: selected_distractors.append("...") 

                    options = selected_distractors + [correct_word]
                    random.shuffle(options)
                    
                    atom_id = f"{stage_row_name}:{idx}"

                    quiz_cards.append({
                        "id": atom_id,
                        "type": "quiz",
                        "question": question_text,
                        "correct_answer": correct_word,
                        "options": options,
                        "origin_type": "reveal"
                    })

            # =====================================================
            # هـ. تحويل MATCHING -> QUIZ
            # =====================================================
            elif stage_data.type == 'Matching':
                pairs = config.get('pairs', [])
                
                for idx, pair in enumerate(pairs):
                    if target_atom_index is not None and target_atom_index != idx:
                        continue

                    question_text = pair.get('right')
                    correct_answer = pair.get('left')
                    
                    # 🤖 محاولة الـ AI
                    selected_distractors = []
                    ai_options = get_ai_distractors("matching", correct_answer, question_text)
                    
                    if ai_options and len(ai_options) >= 3:
                        selected_distractors = ai_options[:3]
                    else:
                        # Fallback: استخدام باقي الخيارات في نفس السؤال
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

        # =========================================================
        # 3. التنظيف والإرجاع
        # =========================================================
        if corrupt_tracker_ids:
            # حذف البيانات القديمة بصمت
            frappe.db.delete("Player Memory Tracker", {"name": ["in", corrupt_tracker_ids]})

        random.shuffle(quiz_cards)
        return quiz_cards[:limit]

    except Exception as e:
        frappe.log_error("Get Review Session Failed", frappe.get_traceback())
        return []


@frappe.whitelist()
def submit_review_session(session_data):
    try:
        user = frappe.session.user
        
        if isinstance(session_data, str): data = json.loads(session_data)
        else: data = session_data
            
        interactions = data.get('answers', []) 
        session_meta = data.get('session_meta', {})
        total_combo = data.get('total_combo', 0)
        completion_time_ms = data.get('completion_time_ms', 0)
        
        current_subject = session_meta.get('subject')
        current_topic = session_meta.get('topic') # ✅ استلام التوبيك

        # حساب الجوائز
        correct_count = sum(1 for item in interactions if item.get('is_correct'))
        max_combo = int(total_combo)
        total_xp = (correct_count * 10) + (max_combo * 2)
        
        # تحديث الذاكرة
        for item in interactions:
            question_id = item.get('question_id')
            is_correct = item.get('is_correct')
            duration = item.get('time_spent_ms') or item.get('duration_ms') or 3000
            
            if question_id:
                # ✅ نمرر التوبيك هنا
                update_srs_after_review(user, question_id, is_correct, duration, current_subject, current_topic)

        # تسجيل الجلسة
        full_log_data = {
            "meta": session_meta,
            "interactions": interactions,
            "stats": {"correct": correct_count, "combo": max_combo, "time_ms": completion_time_ms}
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

        # التحديثات
        if total_xp > 0:
            frappe.db.sql("UPDATE `tabPlayer Profile` SET total_xp = total_xp + %s WHERE user = %s", (total_xp, user))
            if current_subject:
                update_subject_progression(user, current_subject, total_xp)

        frappe.db.commit()

        # =========================================================
        # 🆕 حساب المتبقي (Netflix Effect)
        # =========================================================
        remaining_count = 0
        if current_topic:
            # كم سؤال بقي في "المنطقة الحمراء أو البيضاء" لهذا التوبيك؟
            remaining_count = frappe.db.sql("""
                SELECT COUNT(*) FROM `tabPlayer Memory Tracker`
                WHERE player = %s 
                AND topic = %s
                AND (stability = 1 OR last_review_date < CURDATE())
            """, (user, current_topic))[0][0]

        return {
            "status": "success",
            "xp_earned": total_xp,
            "remaining_items": remaining_count, # ✅ يرسل للفرونت ليظهر زر "أكمل"
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

    attempts = 1 if is_correct else 2
    rating = infer_rating(duration_ms, attempts) # أو منطقك المخصص
    # (استخدم منطقك المفضل للسرعة هنا، المهم التمرير للدالة التالية)
    
    # حساب الموعد القادم (منطقك)
    new_stability = min(4, rating) if is_correct else 1 # تبسيط للدمج، استخدم كودك الأصلي هنا
    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days_to_add = interval_map.get(new_stability, 1)
    new_date = add_days(nowdate(), days_to_add)

    # ✅ التخزين النهائي
    update_memory_tracker(user, question_id, new_stability, new_date, subject, topic)
    
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


# =========================================================
# 🎓 STUDENT ONBOARDING APIS
# =========================================================

@frappe.whitelist()
def get_academic_masters():
    """
    جلب البيانات الرئيسية للتسجيل.
    التحديث: يربط التخصصات بالصفوف (Nested Streams).
    يرجع JSON يحتوي على الصفوف، وكل صف يحتوي على قائمة IDs للتخصصات المسموحة له.
    """
    try:
        # 1. جلب التخصصات (كمرجع كامل - Master Data)
        # نحتاج هذا لكي يعرف الفرونت اسم التخصص ورقمه
        all_streams = frappe.get_all("Game Academic Stream", 
            fields=["name", "stream_name"], 
            order_by="creation asc"
        )
        
        # 2. جلب الصفوف مع تخصصاتها المسموحة
        # نستخدم get_all للجلب السريع، ثم loop بسيط
        grades_list = frappe.get_all("Game Academic Grade", 
            fields=["name", "grade_name"],
            order_by="creation asc"
        )
        
        enriched_grades = []
        for g in grades_list:
            # نحتاج للدخول للجدول الفرعي، لذا نستخدم get_doc أو استعلام مخصص
            # هنا نستخدم استعلام مباشر للأداء الأفضل (بدل تحميل كامل الدوكيومنت)
            allowed_streams = frappe.get_all("Game Grade Valid Stream", 
                filters={"parent": g.name}, 
                pluck="stream" # يرجع قائمة IDs مباشرة ['Scientific', 'Literary']
            )
            
            enriched_grades.append({
                "id": g.name,
                "name": g.grade_name,
                "allowed_streams": allowed_streams # 👈 القائمة المفلترة
            })

        # 3. الموسم الحالي
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
    حفظ خيارات الطالب.
    التحديث: يقوم بإنشاء البروفايل إذا لم يكن موجوداً (للمستخدمين الجدد).
    """
    try:
        user = frappe.session.user
        
        # 1. التحقق من صحة البيانات (Validation)
        if not frappe.db.exists("Game Academic Grade", grade):
            frappe.throw("Invalid Grade Selected")

        if stream:
            # التأكد من أن التخصص متاح لهذا الصف
            is_allowed = frappe.db.exists("Game Grade Valid Stream", {
                "parent": grade,
                "stream": stream
            })
            if not is_allowed:
                frappe.throw(f"Stream '{stream}' is not valid for Grade '{grade}'")
            
        # 2. جلب الموسم الفعال
        season = frappe.db.get_value("Game Subscription Season", {"is_active": 1}, "name")

        # 3. البحث عن البروفايل (Upsert Logic)
        profile_name = frappe.db.get_value("Player Profile", {"user": user}, "name")

        if profile_name:
            # ✅ حالة التحديث: البروفايل موجود
            frappe.db.set_value("Player Profile", profile_name, {
                "current_grade": grade,
                "current_stream": stream if stream else None,
                "academic_year": season
            })
        else:
            # 🆕 حالة الإنشاء: مستخدم جديد لا يملك بروفايل
            new_profile = frappe.get_doc({
                "doctype": "Player Profile",
                "user": user,
                "current_grade": grade,
                "current_stream": stream if stream else None,
                "academic_year": season,
                "total_xp": 0,
                "hearts": 5 # القيمة الافتراضية للقلوب
            })
            new_profile.insert(ignore_permissions=True)

        return {"status": "success", "message": "Academic profile saved successfully"}

    except Exception as e:
        frappe.log_error("Set Profile Failed", frappe.get_traceback())
        return {"status": "error", "message": str(e)}


# =========================================================
# 🛒 STORE APIs
# =========================================================

@frappe.whitelist()
def get_store_items():
    """
    جلب المنتجات مع إخفاء ما تم شراؤه (بناءً على الموسم الفعال).
    """
    try:
        user = frappe.session.user
        
        # 1. جلب سياق الطالب
        profile = frappe.db.get_value("Player Profile", {"user": user}, 
            ["current_grade", "current_stream"], as_dict=True)
        
        user_grade = profile.get("current_grade") if profile else None
        user_stream = profile.get("current_stream") if profile else None

        # 2. ما هي المواد التي يمتلكها الطالب حالياً؟ (Active Season Subs)
        # نستخدم الدالة المساعدة التي تعتمد على تاريخ الموسم
        active_access = get_user_active_subscriptions(user)
        
        # تحويل القائمة إلى Sets للبحث السريع
        owned_subjects = {x['subject'] for x in active_access if x['type'] == 'Subject'}
        owned_tracks = {x['track'] for x in active_access if x['type'] == 'Track'}
        has_global = any(x['type'] == 'Global' for x in active_access)

        if has_global:
            return [] # لديه اشتراك شامل، لا داعي لشراء شيء

        # 3. الطلبات المعلقة (Pending)
        pending_items = frappe.get_all("Game Purchase Request", 
            filters={"user": user, "docstatus": 0}, pluck="sales_item")

        # 4. جلب المنتجات
        items = frappe.get_all("Game Sales Item", 
            fields=["name", "item_name", "description", "price", "discounted_price", "image", "sku", "target_grade"],
            order_by="price asc"
        )

        # 5. تحليل محتويات الباقات (لنعرف ماذا نخفي)
        item_names = [i.name for i in items]
        bundle_contents = frappe.get_all("Game Bundle Content", 
            filters={"parent": ["in", item_names]}, 
            fields=["parent", "type", "target_subject", "target_track"]
        )
        
        # Map: Item -> Contents
        content_map = {}
        for c in bundle_contents:
            if c.parent not in content_map: content_map[c.parent] = []
            content_map[c.parent].append(c)

        # 6. جلب قواعد التخصصات (Streams)
        stream_rules = {}
        targets = frappe.get_all("Game Item Target Stream", filters={"parent": ["in", item_names]}, fields=["parent", "stream"])
        for t in targets:
            if t.parent not in stream_rules: stream_rules[t.parent] = []
            stream_rules[t.parent].append(t.stream)

        # 7. الفلترة النهائية
        filtered_items = []
        for item in items:
            # أ. هل تم طلبها سابقاً؟
            if item.name in pending_items: continue

            # ب. هل يمتلك محتواها؟
            # القاعدة: إذا كانت الباقة تحتوي على مادة يملكها الطالب، نخفي الباقة
            contents = content_map.get(item.name, [])
            is_owned = False
            for c in contents:
                if c.type == 'Subject' and c.target_subject in owned_subjects:
                    is_owned = True; break
                if c.type == 'Track' and c.target_track in owned_tracks:
                    is_owned = True; break
            
            if is_owned: continue # إخفاء ما تم شراؤه

            # ج. فلترة الصف والتخصص
            if item.target_grade and item.target_grade != user_grade: continue
            
            allowed_streams = stream_rules.get(item.name, [])
            if allowed_streams and (not user_stream or user_stream not in allowed_streams):
                continue

            filtered_items.append(item)

        return filtered_items

    except Exception as e:
        frappe.log_error("Get Store Items Failed", frappe.get_traceback())
        return []


@frappe.whitelist()
def request_purchase(item_id, transaction_id=None):
    """
    يقوم الطالب بإرسال طلب شراء.
    الحالة الافتراضية: Pending.
    لن يفتح المحتوى إلا بعد موافقة الآدمن.
    """
    try:
        user = frappe.session.user
        
        # التأكد من عدم وجود طلب معلق لنفس الباقة (منع التكرار)
        existing = frappe.db.exists("Game Purchase Request", {
            "user": user,
            "sales_item": item_id,
            "docstatus": 0 # 0 means Draft/Pending
        })
        
        if existing:
            return {"status": "pending", "message": "لديك طلب قيد المراجعة لهذه الباقة بالفعل."}

        # جلب السعر للحفظ
        item_price = frappe.db.get_value("Game Sales Item", item_id, "discounted_price") or \
                     frappe.db.get_value("Game Sales Item", item_id, "price")

        # إنشاء الطلب
        doc = frappe.get_doc({
            "doctype": "Game Purchase Request",
            "user": user,          # تأكد من تطابق اسم الحقل مع الـ DocType
            "sales_item": item_id, # تأكد من تطابق اسم الحقل
            "status": "Pending",
            "price": item_price,
            "transaction_id": transaction_id # لو أرسله من الفرونت
        })
        doc.insert(ignore_permissions=True)
        
        return {
            "status": "success", 
            "message": "تم إرسال طلبك! سيتم تفعيل الاشتراك بعد مراجعة الإدارة."
        }

    except Exception as e:
        frappe.log_error("Purchase Request Failed", frappe.get_traceback())
        return {"status": "error", "message": "حدث خطأ أثناء الطلب."}


@frappe.whitelist()
def get_topic_details(topic_id):
    """
    جلب تفاصيل الدروس لتوبيك معين (عند الضغط عليه في الخريطة).
    يدعم التوبيك الحقيقي والتوبيك الوهمي (للوحدات المباشرة).
    """
    try:
        user = frappe.session.user
        
        lessons_data = []
        is_linear_progression = 1 # الافتراضي
        has_financial_access = False
        topic_title = ""
        topic_desc = ""

        # ---------------------------------------------------------
        # 1. تحديد نوع التوبيك وجلب بياناته وبيانات الأب (Unit/Subject)
        # ---------------------------------------------------------
        
        # الحالة أ: توبيك وهمي (درس مباشر تابع للوحدة)
        if topic_id.endswith("-default"):
            unit_id = topic_id.replace("-default", "")
            unit_doc = frappe.db.get_value("Game Unit", unit_id, 
                ["name", "title", "subject", "learning_track", "is_free_preview"], as_dict=True)
            
            if not unit_doc: frappe.throw("Unit not found")
            
            topic_title = unit_doc.title
            topic_desc = "دروس الوحدة"
            is_linear_progression = 1 # نفترض الوحدات المباشرة خطية
            
            # جلب الدروس
            raw_lessons = frappe.get_all("Game Lesson",
                filters={"unit": unit_id, "topic": ["is", "not set"], "is_published": 1},
                fields=["name", "title", "xp_reward"],
                order_by="creation asc"
            )
            
            # التحقق المالي (يعتمد على الوحدة)
            check_doc = unit_doc # سنفحص على مستوى الوحدة

        # الحالة ب: توبيك حقيقي
        else:
            topic_doc = frappe.db.get_value("Game Topic", topic_id,
                ["name", "title", "description", "unit", "is_free_preview", "is_linear"], as_dict=True)
            
            if not topic_doc: frappe.throw("Topic not found")
            
            topic_title = topic_doc.title
            topic_desc = topic_doc.description
            is_linear_progression = topic_doc.is_linear
            
            # جلب بيانات الأب (للفحص المالي)
            unit_doc = frappe.db.get_value("Game Unit", topic_doc.unit, 
                ["subject", "learning_track", "is_free_preview"], as_dict=True)
                
            # جلب الدروس
            raw_lessons = frappe.get_all("Game Lesson",
                filters={"topic": topic_id, "is_published": 1},
                fields=["name", "title", "xp_reward"],
                order_by="creation asc"
            )
            
            check_doc = topic_doc # سنفحص على مستوى التوبيك + الوحدة

        # ---------------------------------------------------------
        # 2. التحقق المالي (Financial Check) 💰
        # ---------------------------------------------------------
        # نحتاج بيانات المادة والتراك
        subject_doc = frappe.db.get_value("Game Subject", unit_doc.subject, ["name", "is_paid"], as_dict=True)
        track_is_paid = 0
        if unit_doc.learning_track:
            track_is_paid = frappe.db.get_value("Game Learning Track", unit_doc.learning_track, "is_paid") or 0

        active_subs = get_user_active_subscriptions(user)

        # منطق الفتح (OR Logic)
        if unit_doc.is_free_preview: # الوحدة مجانية
            has_financial_access = True
        elif check_doc.get("is_free_preview"): # التوبيك مجاني
            has_financial_access = True
        elif (not subject_doc.is_paid) and (not track_is_paid): # المادة والتراك مجانيان
            has_financial_access = True
        elif check_subscription_access(active_subs, unit_doc.subject, unit_doc.learning_track): # اشتراك
            has_financial_access = True

        # ---------------------------------------------------------
        # 3. معالجة حالة الدروس (Progress Logic) ⛓️
        # ---------------------------------------------------------
        # جلب ما تم إنجازه
        if raw_lessons:
            lesson_ids = [l.name for l in raw_lessons]
            completed_set = set(frappe.get_all("Gameplay Session", 
                filters={"player": user, "lesson": ["in", lesson_ids]}, 
                pluck="lesson"))
        else:
            completed_set = set()

        previous_lesson_completed = True

        for lesson in raw_lessons:
            is_completed = lesson.name in completed_set
            status = "locked"

            if is_completed:
                status = "completed"
                # إذا اكتمل، الذي بعده مسموح له أن يفتح
                previous_lesson_completed = True 
            else:
                if not has_financial_access:
                    status = "locked_premium" # قفل مالي (اذهب للمتجر)
                elif is_linear_progression and not previous_lesson_completed:
                    status = "locked" # قفل تسلسلي (أكمل السابق)
                else:
                    status = "available" # متاح للعب
                    # بما أن هذا متاح ولم يكتمل، نغلق الذي بعده
                    previous_lesson_completed = False 

            lessons_data.append({
                "id": lesson.name,
                "title": lesson.title,
                "status": status,
                "xp": lesson.xp_reward
            })

        return {
            "topic_id": topic_id,
            "title": topic_title,
            "description": topic_desc,
            "is_locked_premium": not has_financial_access, # حالة عامة للتوبيك
            "lessons": lessons_data
        }

    except Exception as e:
        frappe.log_error("Get Topic Details Failed", frappe.get_traceback())
        return {"error": str(e)}