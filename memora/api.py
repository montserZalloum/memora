import frappe
import json
from frappe import _


@frappe.whitelist()
def get_map_data():
    try:
        user = frappe.session.user
        subjects = frappe.get_all("Game Subject", fields=["name", "title", "icon"], filters={"is_published": 1})
        
        completed_lessons = frappe.get_all("Gameplay Session", 
            filters={"player": user}, 
            fields=["lesson"], 
            pluck="lesson"
        )
        
        full_map = []
        for subject in subjects:
            units = frappe.get_all("Game Unit", 
                filters={"subject": subject.name}, 
                fields=["name", "title", "`order`"], 
                order_by="`order` asc"
            )
            
            for unit in units:
                lessons = frappe.get_all("Game Lesson", 
                    filters={"unit": unit.name}, 
                    fields=["name", "title", "xp_reward"]
                )
                
                for lesson in lessons:
                    status = "locked"
                    if lesson.name in completed_lessons:
                        status = "completed"
                    elif not full_map or full_map[-1]["status"] == "completed":
                        status = "available"
                    
                    full_map.append({
                        "id": lesson.name,
                        "title": lesson.title,
                        "unit_title": unit.title,
                        "subject_title": subject.title, # <--- Add this line
                        "subject_icon": subject.icon,
                        "status": status,
                        "xp": lesson.xp_reward
                    })
        return full_map
    except Exception as e:
        frappe.log_error(title="get_map_data failed", message=frappe.get_traceback())
        frappe.throw("Could not load journey map.")


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