import frappe
import json
import os
import re

# --- الإعدادات الثوابت ---
BASE_STATIC_PATH = 'static_api'

def slugify(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', '_', text.lower())

def save_static_file(folder, file_name, data):
    try:
        path = frappe.get_site_path('public', BASE_STATIC_PATH, folder)
        if not os.path.exists(path):
            os.makedirs(path)
        
        full_path = os.path.join(path, file_name)
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        version_key = f"version:{folder}:{file_name}"
        timestamp = int(frappe.utils.now_datetime().timestamp())
        frappe.cache().set_value(version_key, timestamp)
    except Exception as e:
        frappe.log_error(f"Static Gen Error: Save {file_name}", frappe.get_traceback())

def delete_static_file(folder, file_name):
    try:
        path = frappe.get_site_path('public', BASE_STATIC_PATH, folder, file_name)
        if os.path.exists(path):
            os.remove(path)
        version_key = f"version:{folder}:{file_name}"
        frappe.cache().delete_value(version_key)
    except Exception as e:
        frappe.log_error(f"Static Gen Error: Delete {file_name}", frappe.get_traceback())

# ==============================================================================
# 2. منطق المحتوى المجاني (Single SQL Query Optimization)
# ==============================================================================

def update_subject_free_status(subject_id):
    """
    فحص المجاني مع التأكد من 'سلسلة النشر' كاملة:
    المادة -> التراك (Published) -> الوحدة (Published) -> [التوبيك (Published)]
    """
    if not subject_id: return

    exists_free = frappe.db.sql("""
        SELECT EXISTS (
            -- 1. البحث عن وحدة مجانية ومنشورة داخل تراك منشور
            SELECT 1 FROM `tabGame Unit` u
            JOIN `tabGame Learning Track` lt ON u.learning_track = lt.name
            WHERE lt.subject = %s 
            AND u.is_free_preview = 1 
            AND u.is_published = 1
            AND lt.is_published = 1  -- ✅ تأكدنا أن التراك منشور
        ) OR EXISTS (
            -- 2. البحث عن توبيك مجاني ومنشور داخل وحدة منشورة وتراك منشور
            SELECT 1 FROM `tabGame Topic` t
            JOIN `tabGame Unit` u ON t.unit = u.name
            JOIN `tabGame Learning Track` lt ON u.learning_track = lt.name
            WHERE lt.subject = %s 
            AND t.is_free_preview = 1 
            AND t.is_published = 1
            AND u.is_published = 1   -- ✅ تأكدنا أن الوحدة منشورة
            AND lt.is_published = 1  -- ✅ تأكدنا أن التراك منشور
        )
    """, (subject_id, subject_id))[0][0]

    set_subject_free_status(subject_id, 1 if exists_free else 0)

def set_subject_free_status(subject_id, new_status):
    current_status = frappe.db.get_value("Game Subject", subject_id, "has_free_content")
    if int(current_status or 0) != int(new_status):
        frappe.db.set_value("Game Subject", subject_id, "has_free_content", new_status)
        plans = frappe.get_all("Game Plan Subject", filters={"subject": subject_id}, pluck="parent")
        for p in plans:
            # استخدام job_id لمنع تكرار المهمة في الطابور لنفس الملف
            frappe.enqueue(rebuild_academic_plan_json, plan_name=p, 
                           enqueue_after_commit=True, job_id=f"rebuild_plan_{p}")

# ==============================================================================
# 3. المولدات (Builders)
# ==============================================================================

def rebuild_academic_plan_json(plan_name):
    if not frappe.db.exists("Game Academic Plan", plan_name): return
    plan = frappe.get_doc("Game Academic Plan", plan_name)

    now = frappe.utils.now()
    
    subject_names = [s.subject for s in plan.subjects]
    subjects_map = {}
    if subject_names:
        all_subjects = frappe.get_all("Game Subject", 
            filters={"name": ["in", subject_names],"is_published": 1},
            fields=["name", "title", "icon", "is_paid", "has_free_content"]
        )
        subjects_map = {s.name: s for s in all_subjects}
    
    subjects_list = []
    for item in plan.subjects:
        s_data = subjects_map.get(item.subject)
        if not s_data: continue
        subjects_list.append({
            "id": s_data.name,
            "title": item.display_name or s_data.title,
            "icon": s_data.icon,
            "is_paid": s_data.is_paid,
            "has_free_sample": s_data.has_free_content
        })

    data = {
        "metadata": {
            "grade": plan.grade, "stream": plan.stream, "season": plan.season, 
            "updated_at": str(now)
        },
        "subjects": subjects_list
    }
    # استخدام slugify لضمان اسم ملف متوافق
    file_name = f"plan_{slugify(plan.grade)}_{slugify(plan.stream or 'general')}_{slugify(plan.season)}.json"
    save_static_file("plans", file_name, data)
    frappe.db.set_value("Game Academic Plan", plan_name, "modified", now, update_modified=False)


def rebuild_subject_structure_json(subject_id):
    if not frappe.db.exists("Game Subject", subject_id): return
    
    # 1. جلب التراكات
    tracks = frappe.get_all("Game Learning Track", 
        filters={"subject": subject_id, "is_published": 1}, 
        fields=["name", "track_name", "is_paid"], order_by="idx asc")
    
    if not tracks:
        save_static_file("subjects", f"structure_{subject_id}.json", {"tracks": []})
        return

    track_names = [t.name for t in tracks]

    # 2. جلب الوحدات (Bulk Query)
    all_units = frappe.get_all("Game Unit", 
        filters={"learning_track": ["in", track_names], "is_published": 1}, 
        fields=["name", "title", "is_free_preview", "structure_type", "modified", "learning_track"], 
        order_by="idx asc")

    if not all_units:
        save_static_file("subjects", f"structure_{subject_id}.json", {"subject_id": subject_id, "tracks": tracks})
        return

    # =================================================================================
    # 🔥 التعديل الجوهري: فحص التوبيكات المجانية دفعة واحدة
    # =================================================================================
    # نستخرج قائمة بأسماء الوحدات التي بداخلها "توبيك مجاني واحد على الأقل"
    unit_names = [u.name for u in all_units]
    
    # نستخدم set للسرعة القصوى في البحث
    units_containing_free_topics = set(frappe.db.sql("""
        SELECT unit FROM `tabGame Topic`
        WHERE unit IN %s 
        AND is_free_preview = 1 
        AND is_published = 1
    """, (unit_names,), pluck=True))
    # =================================================================================

    units_by_track = {}
    for u in all_units:
        # المنطق الجديد: الوحدة تعتبر مجانية للعرض إذا كانت هي مجانية OR تحتوي توبيك مجاني
        if u.is_free_preview == 1 or u.name in units_containing_free_topics:
            u["is_free_preview"] = 1
        else:
            u["is_free_preview"] = 0

        # تحويل التاريخ وحذفه
        u["version"] = int(u.modified.timestamp())
        del u["modified"]

        # التجميع
        if u.learning_track not in units_by_track:
            units_by_track[u.learning_track] = []
        units_by_track[u.learning_track].append(u)

    # 4. دمج البيانات النهائية
    for t in tracks:
        t["units"] = units_by_track.get(t.name, [])

    save_static_file("subjects", f"structure_{subject_id}.json", {
        "subject_id": subject_id,
        "tracks": tracks
    })

def rebuild_container_content_json(container_type, container_id):
    folder = "topics" if container_type == "Topic" else "units"
    doctype = f"Game {container_type}"
    # تأكد أن الحاوية نفسها (توبيك أو وحدة) منشورة قبل بناء ملفها
    if not frappe.db.exists(doctype, {"name": container_id, "is_published": 1}):
        # إذا لم تكن منشورة، نحذف الملف القديم إذا وجد لضمان الأمان
        delete_static_file(folder, f"content_{container_id}.json")
        return

    filter_key = "topic" if container_type == "Topic" else "unit"
    lessons = frappe.get_all("Game Lesson", filters={filter_key: container_id,"is_published": 1}, 
        fields=["name", "title", "modified"], order_by="idx asc")

    if lessons:
        # 2. جلب جميع الـ stages لكل هذه الدروس في استعلام واحد
        lesson_names = [d.name for d in lessons]
        
        # نأتي باسم الـ DocType الخاص بالـ Child Table برمجياً
        child_doctype = frappe.get_meta("Game Lesson").get_field("stages").options
        
        all_stages = frappe.get_all(child_doctype,
            filters={
                "parent": ["in", lesson_names],
                "parenttype": "Game Lesson",
                "parentfield": "stages"
            },
            fields=["*"], # يمكنك تحديد حقول معينة بدلاً من * لتقليل حجم الملف
            order_by="idx asc"
        )

        # 3. تنظيم الـ stages في قاموس (Dictionary) ليسهل ربطها
        from collections import defaultdict
        stages_by_lesson = defaultdict(list)
        for stage in all_stages:
            stages_by_lesson[stage.parent].append(stage)


        for lesson in lessons:
            lesson["version"] = int(lesson.modified.timestamp())
            del lesson["modified"]

    save_static_file(folder, f"content_{container_id}.json", {
        "id": container_id,
        "lessons": lessons
    })

def rebuild_lesson_detail_json(lesson_id):
    # لا تبنِ ملف التفاصيل إلا إذا كان الدرس منشوراً
    if not frappe.db.exists("Game Lesson", {"name": lesson_id, "is_published": 1}):
        delete_static_file("lessons", f"detail_{lesson_id}.json")
        return
    
    # تصحيح الخطأ: جلب البيانات كـ dict
    lesson_data = frappe.db.get_value("Game Lesson", lesson_id, ["name", "title"], as_dict=True)
    
    parts = frappe.get_all("Game Stage", 
        filters={"parent": lesson_id}, 
        fields=["title", "type", "config"], order_by="idx asc")
    
    for part in parts:
        if part.config and isinstance(part.config, str):
            try: part.config = json.loads(part.config)
            except: pass

    save_static_file("lessons", f"detail_{lesson_id}.json", {
        "lesson_id": lesson_id,
        "title": lesson_data["title"], # ✅ تصحيح الوصول للحقل
        "parts": parts
    })

# ==============================================================================
# 4. التريجرز (Events Logic)
# ==============================================================================

def trigger_lesson_update(doc, method=None):
    lesson_id = doc.name
    if method == "on_trash" or not doc.is_published:
        delete_static_file("lessons", f"detail_{lesson_id}.json")
    else:
        frappe.enqueue(rebuild_lesson_detail_json, lesson_id=lesson_id, 
                       enqueue_after_commit=True, job_id=f"lesson_detail_{lesson_id}")

    # 2. التحديث الشلالي للأب المباشر (الحاوية)
    # إذا كان الدرس يتبع لتوبيك
    if doc.topic:
        frappe.enqueue(rebuild_container_content_json, container_type="Topic", container_id=doc.topic, 
                       enqueue_after_commit=True, job_id=f"topic_content_{doc.topic}")
    # إذا كان الدرس يتبع لوحدة مباشرة (Lesson Based)
    elif doc.unit:
        frappe.enqueue(rebuild_container_content_json, container_type="Unit", container_id=doc.unit, 
                       enqueue_after_commit=True, job_id=f"unit_content_{doc.unit}")

def trigger_topic_update(doc, method=None):
    topic_id = doc.name
    
    # 1. تحديث أو حذف ملف التوبيك نفسه (Level 3)
    if method == "on_trash" or not doc.is_published:
        delete_static_file("topics", f"content_{topic_id}.json")
    else:
        frappe.enqueue(rebuild_container_content_json, container_type="Topic", container_id=topic_id, 
                       enqueue_after_commit=True, job_id=f"topic_content_{topic_id}")
    
    # 2. الحصول على subject_id
    res = frappe.db.sql("""
        SELECT lt.subject 
        FROM `tabGame Unit` u
        JOIN `tabGame Learning Track` lt ON u.learning_track = lt.name
        WHERE u.name = %s
    """, (doc.unit,), as_dict=True)
    
    if res:
        s_id = res[0].subject
        
        # 🔥 الإضافة السحرية: تحديث وقت تعديل الوحدة الأم يدوياً
        # هذا سيجعل الـ version يتغير في ملف الهيكل الجديد
        frappe.db.sql("UPDATE `tabGame Unit` SET modified = NOW() WHERE name = %s", (doc.unit,))
        
        # 3. الآن نهز الهيكل، وسيأخذ الوقت الجديد
        frappe.enqueue(rebuild_subject_structure_json, subject_id=s_id, 
                       enqueue_after_commit=True, job_id=f"struct_{s_id}")
        
        # 4. فحص المجاني للمادة
        frappe.enqueue(update_subject_free_status, subject_id=s_id, 
                       enqueue_after_commit=True, job_id=f"free_status_{s_id}")

def trigger_unit_update(doc, method=None):
    if method == "on_trash":
        delete_static_file("units", f"content_{doc.name}.json")
    else:
        frappe.enqueue(rebuild_container_content_json, container_type="Unit", container_id=doc.name, 
                       enqueue_after_commit=True, job_id=f"unit_content_{doc.name}")

    subject_id = frappe.db.get_value("Game Learning Track", doc.learning_track, "subject")
    if subject_id:
        frappe.enqueue(rebuild_subject_structure_json, subject_id=subject_id, 
                       enqueue_after_commit=True, job_id=f"struct_{subject_id}")
        frappe.enqueue(update_subject_free_status, subject_id=subject_id, 
                       enqueue_after_commit=True, job_id=f"free_status_{subject_id}")

def trigger_plan_update(doc, method=None):
    if method == "on_trash":
        file_name = f"plan_{slugify(doc.grade)}_{slugify(doc.stream or 'general')}_{slugify(doc.season)}.json"
        delete_static_file("plans", file_name)
    else:
        frappe.enqueue(rebuild_academic_plan_json, plan_name=doc.name, 
                       enqueue_after_commit=True, job_id=f"rebuild_plan_{doc.name}")

@frappe.whitelist(allow_guest=True)
def get_plan_version(grade, season, stream=None):
    file_name = f"plan_{slugify(grade)}_{slugify(stream or 'general')}_{slugify(season)}.json"
    version_key = f"version:plans:{file_name}"
    version = frappe.cache().get_value(version_key)
    if not version:
        modified = frappe.db.get_value("Game Academic Plan", {"grade": grade, "season": season, "stream": stream}, "modified")
        version = int(modified.timestamp()) if modified else 1
        frappe.cache().set_value(version_key, version)
    return {"version": version}


def trigger_track_update(doc, method=None):
    """عند تعديل أو حذف تراك، نهز هيكل المادة ونتأكد من حالة المجاني"""
    if doc.subject:
        # 1. تحديث ملف هيكل المادة (Level 2)
        frappe.enqueue(rebuild_subject_structure_json, 
                       subject_id=doc.subject, 
                       enqueue_after_commit=True, 
                       job_id=f"struct_{doc.subject}")
        
        # 2. ضروري: إعادة فحص حالة المجاني للمادة
        # (لأن حذف التراك قد يعني اختفاء المحتوى المجاني الوحيد)
        frappe.enqueue(update_subject_free_status, 
                       subject_id=doc.subject, 
                       enqueue_after_commit=True, 
                       job_id=f"free_status_{doc.subject}")

def trigger_subject_deletion(doc, method=None):
    """تُستدعى عند حذف مادة لتنظيف الملفات وتحديث الخطط"""
    subject_id = doc.name
    
    # 1. حذف ملف الهيكل الخاص بالمادة
    delete_static_file("subjects", f"structure_{subject_id}.json")
    
    # 2. تحديث الخطط الدراسية (لإزالة المادة من القائمة)
    # ملاحظة: هذا يعتمد على أن الرابط في Child Table لم يحذف بعد
    plans = frappe.get_all("Game Plan Subject", filters={"subject": subject_id}, pluck="parent")
    for p in plans:
        frappe.enqueue(rebuild_academic_plan_json, 
                       plan_name=p, 
                       enqueue_after_commit=True, 
                       job_id=f"rebuild_plan_{p}")


def trigger_subject_update(doc, method=None):
    """
    يتم استدعاؤها عند تعديل بيانات المادة.
    المسؤولية: تحديث المستوى 2 (Structure) وتحديث المستوى 1 (Plans).
    """
    subject_id = doc.name
    
    # 1. معالجة الحذف
    if method == "on_trash":
        trigger_subject_deletion(doc)
        return

    # 2. تحديث المستوى 2 (هيكل المادة)
    # ملاحظة: rebuild_subject_structure_json بداخلها منطق يحذف الملف إذا كان is_published=0
    frappe.enqueue(
        rebuild_subject_structure_json, 
        subject_id=subject_id, 
        enqueue_after_commit=True, 
        job_id=f"struct_{subject_id}"
    )

    # 3. تحديث حالة "المحتوى المجاني" (Denormalization)
    # نضمن أن يافطة 'جرب مجاناً' ستتحدث إذا قام الأدمن بتغيير شيء في المادة
    frappe.enqueue(
        update_subject_free_status, 
        subject_id=subject_id, 
        enqueue_after_commit=True, 
        job_id=f"free_status_{subject_id}"
    )

    # 4. تحديث المستوى 1 (الخطط الدراسية المرتبطة)
    # نجلب الخطط قبل الدوران لضمان الأداء
    plans = frappe.get_all(
        "Game Plan Subject", 
        filters={"subject": subject_id}, 
        pluck="parent"
    )
    
    for plan_name in list(set(plans)):
        frappe.enqueue(
            rebuild_academic_plan_json, 
            plan_name=plan_name, 
            enqueue_after_commit=True, 
            job_id=f"rebuild_plan_{plan_name}"
        )