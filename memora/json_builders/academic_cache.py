import frappe
import json
import os

# --- الإعدادات الأساسية ---
BASE_STATIC_PATH = 'static_api'

def save_static_file(folder, file_name, data):
    """حفظ الملف وتحديث نسخته في Redis"""
    path = frappe.get_site_path('public', BASE_STATIC_PATH, folder)
    if not os.path.exists(path):
        os.makedirs(path)
    
    full_path = os.path.join(path, file_name)
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # تحديث النسخة في Redis للملف المباشر
    version_key = f"version:{folder}:{file_name}"
    timestamp = int(frappe.utils.now_datetime().timestamp())
    frappe.cache().set_value(version_key, timestamp)

# --- 1. بناء ملف الخطة (قائمة المواد) ---
def rebuild_academic_plan_json(plan_name):
    if not frappe.db.exists("Game Academic Plan", plan_name): return
    plan = frappe.get_doc("Game Academic Plan", plan_name)
    
    subjects_list = []
    for item in plan.subjects:
        subject_doc = frappe.db.get_value("Game Subject", item.subject, ["name", "title", "icon", "is_paid"], as_dict=True)
        if not subject_doc: continue
        
        subjects_list.append({
            "id": subject_doc.name,
            "title": item.display_name or subject_doc.title,
            "icon": subject_doc.icon,
            "is_paid": subject_doc.is_paid,
            "has_free_sample": check_if_subject_has_free_content(subject_doc.name)
        })

    data = {
        "metadata": {"grade": plan.grade, "stream": plan.stream, "season": plan.season, "updated_at": str(frappe.utils.now())},
        "subjects": subjects_list
    }
    file_name = f"plan_{plan.grade}_{plan.stream or 'general'}_{plan.season}.json".lower().replace(" ", "_")
    save_static_file("plans", file_name, data)

# --- 2. بناء هيكل المادة (المستوى الأول - بدون دروس) ---
def rebuild_subject_structure_json(subject_id):
    """يحتوي على التراكات والوحدات والتوبيكات مع 'نسخة' كل توبيك"""
    if not frappe.db.exists("Game Subject", subject_id): return
    
    # استخدام Game Learning Track (الاسم الصحيح)
    tracks = frappe.get_all("Game Learning Track", 
        filters={"subject": subject_id," is_published": 1}, 
        fields=["name", "track_name", "is_paid"], order_by="idx asc")
    
    final_tracks = []
    for t in tracks:
        units = frappe.get_all("Game Unit", 
            filters={"learning_track": t.name}, 
            fields=["name", "title", "is_free_preview"], order_by="idx asc")
        
        for u in units:
            # نجلب التوبيكات مع modified timestamp ليكون هو الـ version
            u["topics"] = frappe.get_all("Game Topic", 
                filters={"unit": u.name}, 
                fields=["name", "title", "modified"], order_by="idx asc")
            
            # تحويل الوقت لـ timestamp
            for tp in u["topics"]:
                tp["version"] = int(tp.modified.timestamp())
                del tp["modified"] # لا نحتاجه في الـ JSON

        t["units"] = units
        final_tracks.append(t)

    save_static_file("subjects", f"structure_{subject_id}.json", {
        "subject_id": subject_id,
        "tracks": final_tracks
    })

# --- 3. بناء قائمة دروس التوبيك (المستوى الثاني) ---
def rebuild_topic_content_json(topic_id):
    """يحتوي على قائمة الدروس مع 'نسخة' كل درس"""
    if not frappe.db.exists("Game Topic", topic_id): return

    lessons = frappe.get_all("Game Lesson", 
        filters={"topic": topic_id}, 
        fields=["name", "title", "lesson_type", "modified"], order_by="idx asc")

    for lesson in lessons:
        lesson["version"] = int(lesson.modified.timestamp())
        del lesson["modified"]

    save_static_file("topics", f"content_{topic_id}.json", {
        "topic_id": topic_id, 
        "lessons": lessons
    })

# --- 4. بناء تفاصيل الدرس (المستوى الثالث - الملف الثقيل) ---
def rebuild_lesson_detail_json(lesson_id):
    """يحتوي على الجداول والأجزاء لدرس واحد فقط"""
    if not frappe.db.exists("Game Lesson", lesson_id): return
    
    lesson_doc = frappe.db.get_value("Game Lesson", lesson_id, ["name", "title", "lesson_type"], as_dict=True)
    
    parts = frappe.get_all("Game Lesson Part", 
        filters={"parent": lesson_id}, 
        fields=["title", "content_type", "table_data"], order_by="idx asc")
    
    for part in parts:
        if part.table_data and isinstance(part.table_data, str):
            try: part.table_data = json.loads(part.table_data)
            except: pass

    save_static_file("lessons", f"detail_{lesson_id}.json", {
        "lesson_id": lesson_id,
        "title": lesson_doc.title,
        "parts": parts
    })

# --- أدوات مساعدة ---
def check_if_subject_has_free_content(subject_id):
    # SQL JOIN صحيح باستخدام Game Learning Track
    has_free = frappe.db.sql("""
        SELECT u.name FROM `tabGame Unit` u
        JOIN `tabGame Learning Track` lt ON u.learning_track = lt.name
        WHERE lt.subject = %s AND u.is_free_preview = 1
        LIMIT 1
    """, (subject_id,))
    if has_free: return 1
    
    has_free_topic = frappe.db.sql("""
        SELECT tp.name FROM `tabGame Topic` tp
        JOIN `tabGame Unit` u ON tp.unit = u.name
        JOIN `tabGame Learning Track` lt ON u.learning_track = lt.name
        WHERE lt.subject = %s AND tp.is_free_preview = 1
        LIMIT 1
    """, (subject_id,))
    return 1 if has_free_topic else 0

# --- التريجرز (Triggers) مع مراعاة الأبناء والآباء ---

def trigger_lesson_update(doc, method=None):
    # 1. بناء ملف الدرس الثقيل
    frappe.enqueue(rebuild_lesson_detail_json, lesson_id=doc.name, enqueue_after_commit=True)
    # 2. تحديث قائمة الدروس في التوبيك (لتحديث الـ version)
    if doc.topic:
        frappe.enqueue(rebuild_topic_content_json, topic_id=doc.topic, enqueue_after_commit=True)

def trigger_topic_update(doc, method=None):
    # 1. تحديث قائمة دروس التوبيك
    frappe.enqueue(rebuild_topic_content_json, topic_id=doc.name, enqueue_after_commit=True)
    # 2. تحديث هيكل المادة (لتحديث نسخة التوبيك)
    unit_lt = frappe.db.get_value("Game Unit", doc.unit, "learning_track")
    subject_id = frappe.db.get_value("Game Learning Track", unit_lt, "subject")
    if subject_id:
        frappe.enqueue(rebuild_subject_structure_json, subject_id=subject_id, enqueue_after_commit=True)

def trigger_unit_update(doc, method=None):
    subject_id = frappe.db.get_value("Game Learning Track", doc.learning_track, "subject")
    if subject_id:
        frappe.enqueue(rebuild_subject_structure_json, subject_id=subject_id, enqueue_after_commit=True)

def trigger_track_update(doc, method=None):
    if doc.subject:
        frappe.enqueue(rebuild_subject_structure_json, subject_id=doc.subject, enqueue_after_commit=True)

def trigger_subject_update(doc, method=None):
    frappe.enqueue(rebuild_subject_structure_json, subject_id=doc.name, enqueue_after_commit=True)
    plans = frappe.get_all("Game Plan Subject", filters={"subject": doc.name}, pluck="parent")
    for p in plans:
        frappe.enqueue(rebuild_academic_plan_json, plan_name=p, enqueue_after_commit=True)