import frappe
from frappe import _

@frappe.whitelist()
def get_map_data():
    try:
        user = frappe.session.user
        
        # 1. Fetch hierarchy (with safety check on sorting field)
        subjects = frappe.get_all("Game Subject", 
            fields=["name", "title", "icon"], 
            filters={"is_published": 1}
        )
        
        # 2. Get player progress
        completed_lessons = frappe.get_all("Gameplay Session", 
            filters={"player": user}, 
            fields=["lesson"], 
            pluck="lesson"
        )
        
        full_map = []
        
        for subject in subjects:
            # Use backticks around `order` to avoid SQL syntax errors
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
                        "subject_icon": subject.icon,
                        "status": status,
                        "xp": lesson.xp_reward
                    })
                    
        return full_map

    except Exception as e:
        # This logs the error to the 'Error Log' Doctype in Frappe Desk
        frappe.log_error(title="get_map_data failed", message=frappe.get_traceback())
        # Throws a clean error message to the React frontend
        frappe.throw(_("Could not load journey map. Please try again later."))

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
        # Validate input
        lesson_id = session_meta.get('lesson_id')
        if not lesson_id:
            frappe.throw(_("Invalid session data"))

        # Create the Gameplay Session record
        new_session = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": frappe.session.user,
            "lesson": lesson_id,
            "raw_data": frappe.as_json(interactions) # Save full history as JSON
        })
        new_session.insert(ignore_permissions=True)
        
        # Logic to update Player Profile XP/Gems can go here...
        
        return {"status": "success"}

    except Exception as e:
        frappe.log_error(title="submit_session failed", message=frappe.get_traceback())
        frappe.throw(_("Failed to save progress."))