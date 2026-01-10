import frappe
import json
from frappe import _

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
        # 1. Handle potential stringified JSON (sometimes Axios/Frappe interaction does this)
        if isinstance(session_meta, str):
            session_meta = json.loads(session_meta)
        if isinstance(interactions, str):
            interactions = json.loads(interactions)

        lesson_id = session_meta.get('lesson_id')
        
        if not lesson_id:
            frappe.throw("Missing lesson_id in session_meta")

        # 2. Create the document
        # Ensure 'player', 'lesson', and 'raw_data' are the exact field names in your Doctype
        doc = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": frappe.session.user,
            "lesson": lesson_id,
            "raw_data": json.dumps(interactions, ensure_ascii=False)
        })
        
        doc.insert(ignore_permissions=True)
        # Ensure the database saves the change
        frappe.db.commit() 

        return {"status": "success", "name": doc.name}

    except Exception as e:
        frappe.log_error(title="submit_session failed", message=frappe.get_traceback())
        # Provide the real error message for debugging (remove in production)
        frappe.throw(f"Failed to save progress: {str(e)}")