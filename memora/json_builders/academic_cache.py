import frappe
import json
import os
from slugify import slugify

# --- الإعدادات الأساسية ---
BASE_STATIC_PATH = 'static_api'

def save_static_file(folder, file_name, data):
    """حفظ الملف في مجلد الـ public الخاص بالموقع لخدمته عبر Nginx"""
    path = frappe.get_site_path('public', BASE_STATIC_PATH, folder)
    if not os.path.exists(path):
        os.makedirs(path)
    
    full_path = os.path.join(path, file_name)
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    version_key = f"version:{file_name}"
    timestamp = int(frappe.utils.now_datetime().timestamp())
    frappe.cache().set_value(version_key, timestamp)

@frappe.whitelist()
def get_plan_version(grade, season, stream=None):
    """
    API سريع جداً يرجع فقط رقم نسخة ملف الخطة المطلوبة.
    يستخدمه الفرونت إند ليعرف هل يقرأ من الكاش (sessionStorage) أم يطلب الملف الجديد.
    """
    # 1. بناء اسم الملف المتوقع
    file_name = f"plan_{grade}_{stream or 'general'}_{season}.json".lower().replace(" ", "_")
    version_key = f"version:{file_name}"

    # 2. جلب النسخة من Redis
    version = frappe.cache().get_value(version_key)

    # 3. إذا لم تكن موجودة (أول مرة)، نجلبها من وقت تعديل الدوكتيب
    if not version:
        modified = frappe.db.get_value("Game Academic Plan", 
            {"grade": grade, "season": season, "stream": stream}, "modified")
        version = int(modified.timestamp()) if modified else 1
        # تخزينها في Redis لسرعة الطلبات القادمة
        frappe.cache().set_value(version_key, version)

    return {"version": version}

# --- 1. بناء ملف الخطة (قائمة المواد) ---
def rebuild_academic_plan_json(plan_name):
    if not frappe.db.exists("Game Academic Plan", plan_name): return
    
    plan = frappe.get_doc("Game Academic Plan", plan_name)
    subjects_list = []
    
    for item in plan.subjects:
        subject_doc = frappe.get_doc("Game Subject", item.subject)
        subjects_list.append({
            "id": subject_doc.name,
            "title": item.display_name or subject_doc.title,
            "icon": subject_doc.icon,
            "is_paid": subject_doc.is_paid,
            "has_free_sample": check_if_subject_has_free_content(item.subject)
        })

    data = {
        "metadata": {
            "grade": plan.grade,
            "stream": plan.stream,
            "season": plan.season,
            "updated_at": frappe.utils.now()
        },
        "subjects": subjects_list
    }

    file_name = f"plan_{plan.grade}_{plan.stream or 'general'}_{plan.season}.json".lower().replace(" ", "_")
    save_static_file("plans", file_name, data)

# --- 2. بناء ملف هيكل المادة (Tracks -> Units -> Topics) ---
def rebuild_subject_structure_json(subject_id):
    if not frappe.db.exists("Game Subject", subject_id): return
    
    subject = frappe.get_doc("Game Subject", subject_id)
    
    # جلب التراكات
    tracks = frappe.get_all("Game Track", 
        filters={"subject": subject_id}, 
        fields=["name", "title", "is_paid"], order_by="idx asc")
    
    final_tracks = []
    for t in tracks:
        # جلب الوحدات لكل تراك
        units = frappe.get_all("Game Unit", 
            filters={"track": t.name}, 
            fields=["name", "title", "is_free_preview"], order_by="idx asc")
        
        for u in units:
            # جلب التوبيكات لكل وحدة
            u["topics"] = frappe.get_all("Game Topic", 
                filters={"unit": u.name}, 
                fields=["name", "title", "is_free_preview"], order_by="idx asc")
        
        t["units"] = units
        final_tracks.append(t)

    data = {
        "subject_id": subject.name,
        "title": subject.title,
        "tracks": final_tracks
    }
    
    save_static_file("subjects", f"structure_{subject_id}.json", data)

# --- 3. بناء ملف التوبيك (الدروس -> الأجزاء -> الجداول) ---
def rebuild_topic_content_json(topic_id):
    """هذا الملف هو الأثقل، يحتوي على الدروس بكل تفاصيلها"""
    if not frappe.db.exists("Game Topic", topic_id): return

    lessons = frappe.get_all("Game Lesson", 
        filters={"topic": topic_id}, 
        fields=["name", "title", "lesson_type"], order_by="idx asc")

    for lesson in lessons:
        # جلب أجزاء الدرس (Parts) والجداول (Tables)
        # ملاحظة: سنفترض وجود جداول فرعية داخل الدرس للأجزاء
        lesson["parts"] = frappe.get_all("Game Lesson Part", 
            filters={"parent": lesson.name}, 
            fields=["title", "content_type", "table_data"], order_by="idx asc")
        
        # تحويل نصوص الجداول (JSON Strings) إلى Objects حقيقية إذا كانت مخزنة كنصوص
        for part in lesson["parts"]:
            if part.table_data and isinstance(part.table_data, str):
                try: part.table_data = json.loads(part.table_data)
                except: pass

    save_static_file("topics", f"content_{topic_id}.json", {"topic_id": topic_id, "lessons": lessons})

# --- أدوات مساعدة ---
def check_if_subject_has_free_content(subject_id):
    """
    يفحص إذا كانت المادة تحتوي على أي عينة مجانية.
    الأسماء المصححة:
    - tabGame Learning Track
    - tabGame Unit (يرتبط بـ learning_track)
    - tabGame Topic (يرتبط بـ unit)
    """
    # 1. فحص الوحدات المجانية
    # نربط الوحدة بالـ Learning Track ومن ثم بالمادة (Subject)
    has_free_unit = frappe.db.sql("""
        SELECT u.name FROM `tabGame Unit` u
        JOIN `tabGame Learning Track` lt ON u.learning_track = lt.name
        WHERE lt.subject = %s AND u.is_free_preview = 1
        LIMIT 1
    """, (subject_id,))

    if has_free_unit:
        return 1

    # 2. فحص التوبيكات المجانية
    # نربط التوبيك بالوحدة بالـ Learning Track بالمادة
    has_free_topic = frappe.db.sql("""
        SELECT tp.name FROM `tabGame Topic` tp
        JOIN `tabGame Unit` u ON tp.unit = u.name
        JOIN `tabGame Learning Track` lt ON u.learning_track = lt.name
        WHERE lt.subject = %s AND tp.is_free_preview = 1
        LIMIT 1
    """, (subject_id,))

    return 1 if has_free_topic else 0

# --- 4. التريجرز (Triggers) ---

def trigger_plan_update(doc, method=None):
    frappe.enqueue(rebuild_academic_plan_json, plan_name=doc.name, enqueue_after_commit=True)

def trigger_subject_update(doc, method=None):
    frappe.enqueue(rebuild_subject_structure_json, subject_id=doc.name, enqueue_after_commit=True)
    # تحديث الخطط المرتبطة
    plans = frappe.get_all("Game Plan Subject", filters={"subject": doc.name}, pluck="parent")
    for p in plans: frappe.enqueue(rebuild_academic_plan_json, plan_name=p, enqueue_after_commit=True)

def trigger_unit_update(doc, method=None):
    subject_id = doc.subject
    if subject_id:
        frappe.enqueue(rebuild_subject_structure_json, subject_id=subject_id, enqueue_after_commit=True)
        trigger_subject_update(frappe.get_doc("Game Subject", subject_id))

def trigger_topic_update(doc, method=None):
    # تحديث محتوى التوبيك نفسه
    frappe.enqueue(rebuild_topic_content_json, topic_id=doc.name, enqueue_after_commit=True)
    # تحديث هيكل المادة (لأن اسم التوبيك قد يتغير في القائمة)
    unit_doc = frappe.get_doc("Game Unit", doc.unit)
    trigger_unit_update(unit_doc)

def trigger_lesson_update(doc, method=None):
    # تحديث ملف التوبيك التابع له الدرس
    frappe.enqueue(rebuild_topic_content_json, topic_id=doc.topic, enqueue_after_commit=True)