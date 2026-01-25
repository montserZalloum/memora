import frappe
from frappe.utils import now_datetime
from .access_calculator import apply_plan_overrides, calculate_access_level


SHARD_THRESHOLD = 500


def generate_search_index(plan_id):
    """
    Generate search index for a plan, supporting sharding for large plans.

    Returns a search index with either:
    - Single file with all lessons (< 500 lessons)
    - Sharded index with references to subject shard files (>= 500 lessons)

    Args:
        plan_id (str): Plan document name

    Returns:
        dict: Search index data matching contracts/search_index.schema.json
    """
    try:
        plan_doc = frappe.get_doc("Memora Academic Plan", plan_id)
    except frappe.DoesNotExistError as e:
        frappe.log_error(f"Plan {plan_id} not found: {str(e)}", "Search Index Generation Failed")
        return {"error": f"Plan {plan_id} not found"}
    except Exception as e:
        frappe.log_error(f"Error loading plan {plan_id}: {str(e)}", "Search Index Generation Error")
        return {"error": str(e)}

    try:
        plan_overrides = apply_plan_overrides(plan_id)
    except Exception as e:
        frappe.log_error(f"Error loading plan overrides for {plan_id}: {str(e)}", "Search Index Overrides Error")
        plan_overrides = {}

    all_lessons = []
    subject_lesson_counts = {}

    try:
        plan_subjects = frappe.get_all(
            "Memora Plan Subject",
            filters={"parent": plan_id},
            fields=["subject"],
            order_by="sort_order"
        )
    except Exception as e:
        frappe.log_error(f"Error loading plan subjects for {plan_id}: {str(e)}", "Search Index Plan Subjects Error")
        plan_subjects = []

    subject_ids = [ps.subject for ps in plan_subjects]
    subjects = frappe.get_all(
        "Memora Subject",
        filters={"name": ["in", subject_ids]},
        fields=["name", "title"]
    )
    subjects_dict = {s.name: s for s in subjects}

    tracks = frappe.get_all(
        "Memora Track",
        filters={"parent_subject": ["in", subject_ids]},
        fields=["name", "title", "parent_subject"]
    )

    track_ids = [track.name for track in tracks]
    units = frappe.get_all(
        "Memora Unit",
        filters={"parent_track": ["in", track_ids]},
        fields=["name", "title", "parent_track"]
    )

    unit_ids = [unit.name for unit in units]
    topics = frappe.get_all(
        "Memora Topic",
        filters={"parent_unit": ["in", unit_ids]},
        fields=["name", "title", "parent_unit"]
    )

    topic_ids = [topic.name for topic in topics]
    lessons = frappe.get_all(
        "Memora Lesson",
        filters={"parent_topic": ["in", topic_ids], "is_published": 1},
        fields=["name", "title", "parent_topic"]
    )

    for ps in plan_subjects:
        subject_doc = subjects_dict.get(ps.subject)
        if not subject_doc:
            continue

        try:
            subject_access = calculate_access_level(subject_doc, parent_access=None, plan_overrides=plan_overrides)
        except Exception as e:
            frappe.log_error(f"Error calculating access level for subject {ps.subject}: {str(e)}", "Access Level Calculation Error")
            continue
        
        if subject_access is None:
            continue

        subject_data = {
            "subject_id": subject_doc.name,
            "subject_name": subject_doc.title,
            "lessons": []
        }

        for track in [t for t in tracks if t.parent_subject == subject_doc.name]:
            track_access = calculate_access_level(track, parent_access=subject_access, plan_overrides=plan_overrides)
            
            if track_access is None:
                continue

            for unit in [u for u in units if u.parent_track == track.name]:
                unit_access = calculate_access_level(unit, parent_access=track_access, plan_overrides=plan_overrides)
                
                if unit_access is None:
                    continue

                for topic in [t for t in topics if t.parent_unit == unit.name]:
                    topic_access = calculate_access_level(topic, parent_access=unit_access, plan_overrides=plan_overrides)
                    
                    if topic_access is None:
                        continue

                    for lesson in [l for l in lessons if l.parent_topic == topic.name]:
                        lesson_access = calculate_access_level(lesson, parent_access=topic_access, plan_overrides=plan_overrides)
                        
                        if lesson_access is None:
                            continue

                        lesson_entry = {
                            "lesson_id": lesson.name,
                            "lesson_name": lesson.title,
                            "subject_id": subject_doc.name,
                            "subject_name": subject_doc.title,
                            "unit_id": unit.name,
                            "unit_name": unit.title,
                            "topic_id": topic.name,
                            "topic_name": topic.title
                        }

                        all_lessons.append(lesson_entry)
                        subject_data["lessons"].append(lesson_entry)

        subject_lesson_counts[subject_doc.name] = len(subject_data["lessons"])

    total_lessons = len(all_lessons)

    search_index = {
        "plan_id": plan_id,
        "version": int(now_datetime().timestamp()),
        "generated_at": now_datetime().isoformat(),
        "total_lessons": total_lessons
    }

    if total_lessons >= SHARD_THRESHOLD:
        search_index["is_sharded"] = True
        search_index["shards"] = generate_shard_references(subject_lesson_counts, plan_id)
    else:
        search_index["is_sharded"] = False
        search_index["entries"] = all_lessons

    return search_index


def generate_shard_references(subject_lesson_counts, plan_id):
    """
    Generate shard references for large plans.

    Args:
        subject_lesson_counts (dict): {subject_id: lesson_count}
        plan_id (str): Plan document name

    Returns:
        list: List of shard references with subject_id, subject_name, url, lesson_count
    """
    shards = []

    subject_ids = [subject_id for subject_id, lesson_count in subject_lesson_counts.items() if lesson_count > 0]
    subjects = frappe.get_all(
        "Memora Subject",
        filters={"name": ["in", subject_ids]},
        fields=["name", "title"]
    )
    subjects_dict = {s.name: s for s in subjects}

    for subject_id, lesson_count in subject_lesson_counts.items():
        if lesson_count == 0:
            continue

        subject = subjects_dict.get(subject_id)
        if not subject:
            continue

        shard_ref = {
            "subject_id": subject_id,
            "subject_name": subject.title,
            "url": f"plans/{plan_id}/search/{subject_id}.json",
            "lesson_count": lesson_count
        }

        shards.append(shard_ref)

    return shards


def generate_subject_shard(plan_id, subject_id):
    """
    Generate a search index shard for a specific subject.

    Used when total lessons >= SHARD_THRESHOLD.

    Args:
        plan_id (str): Plan document name
        subject_id (str): Subject document name

    Returns:
        dict: Subject-specific search index with lessons for that subject
    """
    plan_overrides = apply_plan_overrides(plan_id)
    subject_doc = frappe.get_doc("Memora Subject", subject_id)
    subject_access = calculate_access_level(subject_doc, parent_access=None, plan_overrides=plan_overrides)
    
    if subject_access is None:
        return {
            "plan_id": plan_id,
            "subject_id": subject_id,
            "subject_name": subject_doc.title,
            "generated_at": now_datetime().isoformat(),
            "lessons": []
        }

    entries = []

    tracks = frappe.get_all(
        "Memora Track",
        filters={"parent_subject": subject_doc.name},
        fields=["name", "title", "parent_subject"]
    )

    track_ids = [track.name for track in tracks]
    units = frappe.get_all(
        "Memora Unit",
        filters={"parent_track": ["in", track_ids]},
        fields=["name", "title", "parent_track"]
    )

    unit_ids = [unit.name for unit in units]
    topics = frappe.get_all(
        "Memora Topic",
        filters={"parent_unit": ["in", unit_ids]},
        fields=["name", "title", "parent_unit"]
    )

    topic_ids = [topic.name for topic in topics]
    lessons = frappe.get_all(
        "Memora Lesson",
        filters={"parent_topic": ["in", topic_ids], "is_published": 1},
        fields=["name", "title", "parent_topic"]
    )

    for track in tracks:
        track_access = calculate_access_level(track, parent_access=subject_access, plan_overrides=plan_overrides)
        
        if track_access is None:
            continue

        for unit in [u for u in units if u.parent_track == track.name]:
            unit_access = calculate_access_level(unit, parent_access=track_access, plan_overrides=plan_overrides)
            
            if unit_access is None:
                continue

            for topic in [t for t in topics if t.parent_unit == unit.name]:
                topic_access = calculate_access_level(topic, parent_access=unit_access, plan_overrides=plan_overrides)
                
                if topic_access is None:
                    continue

                for lesson in [l for l in lessons if l.parent_topic == topic.name]:
                    lesson_access = calculate_access_level(lesson, parent_access=topic_access, plan_overrides=plan_overrides)
                    
                    if lesson_access is None:
                        continue

                    entry = {
                        "lesson_id": lesson.name,
                        "lesson_name": lesson.title,
                        "subject_id": subject_doc.name,
                        "subject_name": subject_doc.title,
                        "unit_id": unit.name,
                        "unit_name": unit.title,
                        "topic_id": topic.name,
                        "topic_name": topic.title
                    }

                    entries.append(entry)

    return {
        "plan_id": plan_id,
        "subject_id": subject_id,
        "subject_name": subject_doc.title,
        "generated_at": now_datetime().isoformat(),
        "lessons": entries
    }
