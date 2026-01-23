import frappe
import json
import re

def slugify(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', '_', text.lower())

# مفتاح الريديس لكل طالب
def get_cache_key(user):
    return f"user_access_keys:{user}"

@frappe.whitelist()
def get_user_access_keys():
    """الـ API الذي سيطلبه الويبسايت للحصول على صلاحيات الطالب"""
    user = frappe.session.user
    if user == "Guest":
        return {"subjects": [], "tracks": [], "is_global": 0, "plan_version": 1}

    # 1. القراءة من الريديس (سرعة البرق)
    cache_key = get_cache_key(user)
    cached_data = frappe.cache().get_value(cache_key)
    
    if cached_data:
        return json.loads(cached_data)

    # 2. بناء البيانات إذا لم تكن موجودة (استعلام SQL واحد ذكي)
    user_keys = build_user_access_bundle(user)
    
    # 3. تخزين النتيجة في الريديس لمدة 24 ساعة
    frappe.cache().set_value(cache_key, json.dumps(user_keys), expires_in_sec=86400)
    
    return user_keys

def build_user_access_bundle(user):
    # جلب اسم البروفايل
    profile_name = frappe.db.get_value("Player Profile", {"user": user}, "name")
    if not profile_name:
        return {"subjects": [], "tracks": [], "is_global": 0, "plan_version": 1}

    # استعلام SQL يجمع الصلاحيات من الأب (Subscription) والابن (Access)
    # parent هنا هو الحقل الآلي الذي يربط الجدول الفرعي بالأصلي
    access_data = frappe.db.sql("""
        SELECT 
            sub.type as sub_type,
            acc.type as item_type,
            acc.subject,
            acc.track
        FROM 
            `tabGame Player Subscription` sub
        LEFT JOIN 
            `tabGame Subscription Access` acc ON acc.parent = sub.name
        JOIN 
            `tabGame Subscription Season` season ON sub.linked_season = season.name
        WHERE 
            sub.player = %s 
            AND sub.status = 'Active' 
            AND season.end_date >= CURDATE()
    """, (profile_name,), as_dict=True)

    subjects = set()
    tracks = set()
    is_global = 0

    for row in access_data:
        if row.sub_type == 'Global Access':
            is_global = 1
            break # الوصول الشامل يغطي كل شيء، لا داعي لتكملة الفحص
        
        if row.item_type == 'Subject' and row.subject:
            subjects.add(row.subject)
        elif row.item_type == 'Track' and row.track:
            tracks.add(row.track)

    return {
        "subjects": list(subjects),
        "tracks": list(tracks),
        "is_global": is_global,
        "plan_version": get_student_plan_version(user)
    }

@frappe.whitelist(allow_guest=True)
def get_student_plan_version(user):
    """جلب نسخة الخطة - يجب أن تطابق منطق البناء 100%"""
    
    # 1. جلب بيانات الطالب
    if frappe.session.user != "Guest":
        # للطالب المسجل
        profile = frappe.db.get_value("Player Profile", {"user": user}, 
            ["current_grade", "season", "current_stream"], as_dict=True)
    else:
        # للزائر (Guest) - يمكننا تمرير المعطيات كـ arguments للدالة بدلاً من Profile
        # سأفترض هنا أنك تمررها في الـ args، لكن لنركز على منطق الاسم الآن
        return 1

    if not profile: return 1
    
    # 2. بناء اسم الملف بنفس طريقة دالة البناء بالضبط (Slugify)
    grade_slug = slugify(profile.current_grade)
    stream_slug = slugify(profile.current_stream or 'general')
    season_slug = slugify(profile.season)
    
    # ✅ الاسم يجب أن يكون مطابقاً لما تم حفظه: شرطات (-) وامتداد (.json)
    file_name = f"plan_{grade_slug}_{stream_slug}_{season_slug}.json"
    frappe.log_error(
        title="Academic Cache Debug",
        message=f"DEBUG WRITER: {file_name}"
    )
    
    # 3. مفتاح Redis
    version_key = f"version:plans:{file_name}"
    
    # 4. جلب النسخة
    version = frappe.cache().get_value(version_key)
    
    # 5. في حال عدم وجود كاش (Fallback)
    if not version:
        modified = frappe.db.get_value("Game Academic Plan", 
            {"grade": profile.current_grade, "season": profile.season, "stream": profile.current_stream}, 
            "modified")
            
        version = int(modified.timestamp()) if modified else 1
        
        # تخزين القيمة في Redis للمستقبل
        frappe.cache().set_value(version_key, version)

    frappe.log_error(
        title="Academic Cache Debug",
        message=f"DEBUG WRITER: {file_name}"
    )
        
    return version

# --- دالة مسح الكاش (للاستخدام في الـ Hooks) ---
def handle_purchase_approval(doc, method=None):
    if doc.status == "Approved":
        frappe.cache().delete_value(get_cache_key(doc.user))

def handle_subscription_change(doc, method=None):
    # جلب اليوزر المرتبط بالبروفايل لمسح الكاش الخاص به
    user = frappe.db.get_value("Player Profile", doc.player, "user")
    if user:
        frappe.cache().delete_value(get_cache_key(user))


def handle_season_date_change(doc, method):
    """
    يعمل عند تغيير تاريخ انتهاء الموسم.
    يقوم بمسح كاش الصلاحيات لكل الطلاب المرتبطين بهذا الموسم.
    """
    # نتحقق إذا كان تاريخ الانتهاء هو الذي تغير فعلاً
    if doc.has_value_changed("end_date"):
        # نرسل المهمة للـ Background Worker لكي لا يعلق الموقع عند الأدمن 
        # (لأنه قد يكون هناك آلاف الطلاب في هذا الموسم)
        frappe.enqueue(
            'memora.api.user_access.clear_season_users_cache', 
            season_name=doc.name, 
            enqueue_after_commit=True
        )

def clear_season_users_cache(season_name):
    # 1. جلب كل البروفايلات المرتبطة باشتراكات في هذا الموسم
    profiles = frappe.get_all("Game Player Subscription", 
        filters={"linked_season": season_name, "status": "Active"}, 
        pluck="player")

    if not profiles: return

    # 2. جلب الـ user_id الحقيقي لكل بروفايل
    users = frappe.get_all("Player Profile", 
        filters={"name": ["in", profiles]}, 
        pluck="user")

    # 3. مسح الكاش الخاص بكل يوزر
    for user in users:
        cache_key = f"user_access_keys:{user}"
        frappe.cache().delete_value(cache_key)
        
    frappe.logger().info(f"Cleared access cache for {len(users)} users due to Season {season_name} date change.")


def get_subject_version(subject_id):
    """دالة مساعدة لجلب نسخة هيكل المادة"""
    version_key = f"version:subjects:structure_{subject_id}.json"
    version = frappe.cache().get_value(version_key)
    
    if not version:
        modified = frappe.db.get_value("Game Subject", subject_id, "modified")
        version = int(modified.timestamp()) if modified else 1
        frappe.cache().set_value(version_key, version)
    
    return version