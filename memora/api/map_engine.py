"""
Map Engine Domain Module

This module provides smart hybrid map data with lazy loading for topic-based units.
"""

import frappe
from frappe import _
from .utils import get_user_active_subscriptions, check_subscription_access


@frappe.whitelist()
def get_map_data(subject=None):
    """
    Smart hybrid map engine.

    - If unit is Lesson Based: returns lessons immediately for path drawing.
    - If unit is Topic Based: returns topics only (Lazy Load).
    """
    try:
        user = frappe.session.user

        # 1. Academic context
        profile = frappe.db.get_value("Player Profile", {"user": user},
            ["current_grade", "current_stream", "academic_year"], as_dict=True)

        if not profile or not profile.current_grade:
            return []

        # 2. Fetch plan
        plan_filters = {
            "grade": profile.current_grade,
            "year": profile.academic_year or "2025"
        }
        if profile.current_stream:
            plan_filters["stream"] = profile.current_stream

        plan_name = frappe.db.get_value("Game Academic Plan", plan_filters, "name")
        if not plan_name: return []

        plan_doc = frappe.get_doc("Game Academic Plan", plan_name)

        # 3. Aggregate rules
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

        # 4. Helper data
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

                # Determine structure type for display
                # We send this to frontend to decide drawing style
                unit_style = "lessons" if unit.structure_type == "Lesson Based" else "topics"

                unit_output = {
                    "id": unit.name,
                    "title": unit.title,
                    "style": unit_style,  # 👈 New field for distinction
                    "topics": []
                }

                # -------------------------------------------------
                # Scenario 1: Lesson Based (immediate lesson loading)
                # -------------------------------------------------
                if unit_style == "lessons":
                    # We fetch lessons directly and put them in virtual topic
                    direct_lessons = frappe.get_all("Game Lesson",
                        filters={"unit": unit.name, "topic": ["is", "not set"], "is_published": 1},
                        fields=["name", "title", "xp_reward"],
                        order_by="creation asc"
                    )

                    if not direct_lessons: continue

                    # Process lesson status
                    processed_lessons = []
                    previous_lesson_completed = True
                    has_financial_access = False

                    # Financial check (unit)
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
                            elif previous_lesson_completed:  # (We assume always linear in this mode)
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

                    # Add virtual topic with lessons
                    unit_output["topics"].append({
                        "id": f"{unit.name}-default",
                        "title": unit.title,
                        "is_virtual": True,
                        "lessons": processed_lessons  # ✅ We send lessons here
                    })

                # -------------------------------------------------
                # Scenario 2: Topic Based (lazy loading)
                # -------------------------------------------------
                else:
                    real_topics = frappe.get_all("Game Topic",
                        filters={"unit": unit.name},
                        fields=["name", "title", "is_free_preview", "is_linear", "description"],
                        order_by="creation asc"
                    )

                    previous_topic_completed = True  # To control topic sequence

                    for topic in real_topics:
                        # Financial check (topic)
                        has_financial_access = False
                        if unit.is_free_preview or topic.is_free_preview or (not subject_doc.is_paid and not track_is_paid) or check_subscription_access(active_subs, sub_id, unit.learning_track):
                            has_financial_access = True

                        # We need to calculate topic status (is it completed?)
                        # Here we're forced to fetch lessons just for calculation (Count Check), not for sending
                        topic_lessons = frappe.get_all("Game Lesson",
                            filters={"topic": topic.name, "is_published": 1},
                            fields=["name"],  # ID only
                            order_by="creation asc"
                        )

                        total_lessons = len(topic_lessons)
                        completed_count = len([l for l in topic_lessons if l.name in completed_lessons_set])
                        is_fully_completed = (total_lessons > 0 and total_lessons == completed_count)

                        # Determine topic status
                        topic_status = "locked"
                        if is_fully_completed:
                            topic_status = "completed"
                        elif not has_financial_access:
                            topic_status = "locked_premium"
                        elif unit.is_linear_topics and not previous_topic_completed:
                            topic_status = "locked"
                        else:
                            # If available financially and it's their turn in order
                            topic_status = "available"

                        if is_fully_completed: previous_topic_completed = True

                        # Add topic (without lessons)
                        unit_output["topics"].append({
                            "id": topic.name,
                            "title": topic.title,
                            "description": topic.description,
                            "status": topic_status,
                            "stats": {  # Meta data for display
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


@frappe.whitelist()
def get_topic_details(topic_id):
    """
    Get topic/lesson details (lazy load).

    Supports both real topics and virtual topics (for direct lesson units).
    """
    try:
        user = frappe.session.user

        lessons_data = []
        is_linear_progression = 1  # Default
        has_financial_access = False
        topic_title = ""
        topic_desc = ""

        # ---------------------------------------------------------
        # 1. Determine topic type and fetch its data and parent data (Unit/Subject)
        # ---------------------------------------------------------

        # Case A: Virtual topic (direct lesson belonging to unit)
        if topic_id.endswith("-default"):
            unit_id = topic_id.replace("-default", "")
            unit_doc = frappe.db.get_value("Game Unit", unit_id,
                ["name", "title", "subject", "learning_track", "is_free_preview"], as_dict=True)

            if not unit_doc: frappe.throw("Unit not found")

            topic_title = unit_doc.title
            topic_desc = "دروس الوحدة"
            is_linear_progression = 1  # We assume direct units are linear

            # Fetch lessons
            raw_lessons = frappe.get_all("Game Lesson",
                filters={"unit": unit_id, "topic": ["is", "not set"], "is_published": 1},
                fields=["name", "title", "xp_reward"],
                order_by="creation asc"
            )

            # Financial check (depends on unit)
            check_doc = unit_doc  # We'll check at unit level

        # Case B: Real topic
        else:
            topic_doc = frappe.db.get_value("Game Topic", topic_id,
                ["name", "title", "description", "unit", "is_free_preview", "is_linear"], as_dict=True)

            if not topic_doc: frappe.throw("Topic not found")

            topic_title = topic_doc.title
            topic_desc = topic_doc.description
            is_linear_progression = topic_doc.is_linear

            # Fetch parent data (for financial check)
            unit_doc = frappe.db.get_value("Game Unit", topic_doc.unit,
                ["subject", "learning_track", "is_free_preview"], as_dict=True)

            # Fetch lessons
            raw_lessons = frappe.get_all("Game Lesson",
                filters={"topic": topic_id, "is_published": 1},
                fields=["name", "title", "xp_reward"],
                order_by="creation asc"
            )

            check_doc = topic_doc  # We'll check at topic + unit level

        # ---------------------------------------------------------
        # 2. Financial Check (Financial Check) 💰
        # ---------------------------------------------------------
        # We need subject and track data
        subject_doc = frappe.db.get_value("Game Subject", unit_doc.subject, ["name", "is_paid"], as_dict=True)
        track_is_paid = 0
        if unit_doc.learning_track:
            track_is_paid = frappe.db.get_value("Game Learning Track", unit_doc.learning_track, "is_paid") or 0

        active_subs = get_user_active_subscriptions(user)

        # Access logic (OR Logic)
        if unit_doc.is_free_preview:  # Unit is free
            has_financial_access = True
        elif check_doc.get("is_free_preview"):  # Topic is free
            has_financial_access = True
        elif (not subject_doc.is_paid) and (not track_is_paid):  # Subject and track are free
            has_financial_access = True
        elif check_subscription_access(active_subs, unit_doc.subject, unit_doc.learning_track):  # Subscription
            has_financial_access = True

        # ---------------------------------------------------------
        # 3. Process lesson status (Progress Logic) ⛓️
        # ---------------------------------------------------------
        # Fetch completed
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
                # If completed, next one is allowed to open
                previous_lesson_completed = True
            else:
                if not has_financial_access:
                    status = "locked_premium"  # Financial lock (go to store)
                elif is_linear_progression and not previous_lesson_completed:
                    status = "locked"  # Sequential lock (complete previous)
                else:
                    status = "available"  # Available to play
                    # Since this is available and not completed, we close the next one
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
            "is_locked_premium": not has_financial_access,  # General status for topic
            "lessons": lessons_data
        }

    except Exception as e:
        frappe.log_error("Get Topic Details Failed", frappe.get_traceback())
        return {"error": str(e)}


@frappe.whitelist()
def get_track_details(subject, track=None, is_track_linear=0):
    """
    Get specific track info and its units (No topics/lessons recursion).
    
    Params:
        subject (str): Subject Name (ID)
        track (str): Track Name (ID) - Optional
        is_track_linear (bool/int): If 1, enforces Unit 1 -> Unit 2 progression.
    """
    try:
        user = frappe.session.user
        is_track_linear = frappe.parse_json(is_track_linear) # Ensure boolean

        # 1. Fetch Track Metadata (if track provided)
        track_info = {}
        track_is_paid = 0
        
        if track:
            track_doc = frappe.db.get_value("Game Learning Track", track, 
                ["name", "track_name", "is_paid", "is_sold_separately", "unlock_level"], as_dict=True)
            if track_doc:
                track_info = track_doc
                track_is_paid = track_doc.is_paid

        # 2. Fetch Subject Metadata (Master Lock)
        subject_doc = frappe.db.get_value("Game Subject", subject, ["name", "title", "is_paid"], as_dict=True)
        if not subject_doc:
            return {"error": "Subject not found"}

        # 3. Get User Subscriptions & Progress
        active_subs = get_user_active_subscriptions(user) # Helper function defined in your system
        
        # Get all completed lessons for this user to calculate unit progress
        user_completed_lessons = frappe.get_all("Gameplay Session", 
            filters={"player": user}, pluck="lesson")
        
        user_completed_set = set(user_completed_lessons)

        # 4. Fetch Units for this Track
        # Filter: Match Subject AND (Match Track OR Track is Empty)
        filters = {"subject": subject}
        if track:
            filters["learning_track"] = track
        else:
            filters["learning_track"] = ["is", "not set"]

        units = frappe.get_all("Game Unit",
            filters=filters,
            fields=["name", "title","is_linear_topics", "is_free_preview", "structure_type"],
            order_by="creation asc" # Important for linear check
        )

        units_list = []
        previous_unit_completed = True # Start true for the first unit

        for unit in units:
            # --- A. Check Financial Access ---
            # Access logic: Unit Free OR (Subject Free & Track Free) OR Has Subscription
            is_financially_unlocked = False
            
            if unit.is_free_preview:
                is_financially_unlocked = True
            elif (not subject_doc.is_paid and not track_is_paid):
                is_financially_unlocked = True
            elif check_subscription_access(active_subs, subject, track): # Helper function
                is_financially_unlocked = True

            # --- B. Calculate Progress (Heavy Lifting Optimized) ---
            # We need to know if this unit is completed to unlock the next one (if linear)
            unit_lessons = frappe.get_all("Game Lesson", 
                filters={"unit": unit.name, "is_published": 1}, pluck="name")
            
            total_lessons = len(unit_lessons)
            completed_count = 0
            if total_lessons > 0:
                # Intersection of unit lessons and user completed lessons
                completed_count = len(set(unit_lessons).intersection(user_completed_set))
            
            progress_percent = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0
            is_unit_completed = (progress_percent == 100)

            # --- C. Determine Final Status ---
            status = "locked"
            
            if is_unit_completed:
                status = "completed"
            elif not is_financially_unlocked:
                status = "locked_premium" # Needs payment
            elif is_track_linear and not previous_unit_completed:
                status = "locked_progression" # Needs previous unit
            else:
                status = "available"

            # Append to result
            units_list.append({
                "id": unit.name,
                "title": unit.title,
                "structure_type": unit.structure_type, # 'Topic Based' or 'Lesson Based'
                "status": status,
                "progress": progress_percent,
                "is_free": unit.is_free_preview
            })

            # Update flag for next iteration
            if is_track_linear:
                previous_unit_completed = is_unit_completed

        return {
            "subject": {
                "id": subject_doc.name,
                "title": subject_doc.title
            },
            "track": track_info,
            "units": units_list
        }

    except Exception as e:
        frappe.log_error(f"Get Track Details Error: {str(e)}")
        return {"error": "Failed to fetch track details"}


@frappe.whitelist()
def get_unit_topics(subject, unit, track=None):
    """
    Get topics list for a specific unit with precise status (Locked/Available/Completed).
    """
    try:
        user = frappe.session.user

        # 1. Fetch Context Metadata
        # -------------------------
        subject_doc = frappe.db.get_value("Game Subject", subject, ["is_paid"], as_dict=True)
        unit_doc = frappe.db.get_value("Game Unit", unit, 
            ["name", "title", "is_free_preview", "is_linear_topics", "learning_track"], as_dict=True)
        
        if not unit_doc:
            return {"error": "Unit not found"}

        # Resolve Track (If passed explicitly or derived from unit)
        track_id = track or unit_doc.learning_track
        track_is_paid = 0
        if track_id:
            track_is_paid = frappe.db.get_value("Game Learning Track", track_id, "is_paid") or 0

        # 2. Get User Progress & Subscriptions
        # ------------------------------------
        active_subs = get_user_active_subscriptions(user)
        user_completed_lessons_set = set(frappe.get_all("Gameplay Session", 
            filters={"player": user}, pluck="lesson"))

        # 3. Optimization: Fetch ALL lessons for this unit at once
        # ------------------------------------------------------
        # Instead of querying DB inside the loop, we query once and map in Python
        all_unit_lessons = frappe.get_all("Game Lesson",
            filters={"unit": unit, "is_published": 1},
            fields=["name", "topic"]
        )
        
        # Create a map: { topic_id: [list_of_lesson_ids] }
        topic_lessons_map = {}
        for l in all_unit_lessons:
            if l.topic:
                if l.topic not in topic_lessons_map: topic_lessons_map[l.topic] = []
                topic_lessons_map[l.topic].append(l.name)

        # 4. Fetch Topics
        # ---------------
        topics = frappe.get_all("Game Topic",
            filters={"unit": unit},
            fields=["name", "title", "description", "is_free_preview"],
            order_by="creation asc" # Assuming creation order dictates linearity
        )

        final_topics = []
        previous_topic_completed = True # Flag for linearity check

        for topic in topics:
            # A. Calculate Stats
            # ------------------
            # Get lessons from our memory map (Default to empty list if none)
            topic_lesson_ids = topic_lessons_map.get(topic.name, [])
            total_lessons = len(topic_lesson_ids)
            
            # Count intersection with user completed set
            completed_count = len([l_id for l_id in topic_lesson_ids if l_id in user_completed_lessons_set])
            
            is_fully_completed = (total_lessons > 0 and total_lessons == completed_count)
            progress_percent = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0

            # B. Check Financial Access
            # -------------------------
            # Hierarchy: Unit Free > Topic Free > (Subject & Track Free) > Subscription
            has_financial_access = False
            
            if unit_doc.is_free_preview:
                has_financial_access = True
            elif topic.is_free_preview:
                has_financial_access = True
            elif (not subject_doc.is_paid and not track_is_paid):
                has_financial_access = True
            elif check_subscription_access(active_subs, subject, track_id):
                has_financial_access = True

            # C. Determine Status
            # -------------------
            status = "locked"

            if is_fully_completed:
                status = "completed"
            elif not has_financial_access:
                status = "locked_premium" # 🔒 Needs Payment
            elif unit_doc.is_linear_topics and not previous_topic_completed:
                status = "locked_progression" # ⛓️ Needs Previous Topic
            else:
                status = "available" # 🟢 Ready to play

            # Add to list
            final_topics.append({
                "id": topic.name,
                "title": topic.title,
                "description": topic.description,
                "status": status,
                "progress": progress_percent,
                "stats": {
                    "total_lessons": total_lessons,
                    "completed_lessons": completed_count
                },
                "is_free": topic.is_free_preview
            })

            # Update flag for next iteration
            if unit_doc.is_linear_topics:
                previous_topic_completed = is_fully_completed

        return {
            "unit_title": unit_doc.title,
            "topics": final_topics
        }

    except Exception as e:
        frappe.log_error(f"Get Unit Topics Error: {str(e)}")
        return {"error": "Failed to fetch topics"}