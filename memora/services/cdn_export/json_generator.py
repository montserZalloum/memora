import frappe
import json
from datetime import datetime, timedelta
from frappe.utils import now_datetime
from .dependency_resolver import get_affected_plan_ids
from .access_calculator import calculate_access_level, apply_plan_overrides
from .search_indexer import generate_search_index, generate_subject_shard, SHARD_THRESHOLD

def generate_manifest(plan_doc):
    """
    Generate plan manifest JSON according to contract schema.

    Args:
        plan_doc (frappe.doc): Memora Academic Plan document

    Returns:
        dict: Complete manifest data ready for CDN upload
    """
    manifest = {
        "plan_id": plan_doc.name,
        "title": plan_doc.title,
        "version": int(now_datetime().timestamp()),
        "generated_at": now_datetime().isoformat(),
        "subjects": [],
        "search_index_url": f"plans/{plan_doc.name}/search_index.json"
    }

    if plan_doc.season:
        manifest["season"] = plan_doc.season
    if plan_doc.grade:
        manifest["grade"] = plan_doc.grade
    if plan_doc.stream:
        manifest["stream"] = plan_doc.stream

    plan_overrides = apply_plan_overrides(plan_doc.name)

    plan_subjects = frappe.get_all(
        "Memora Plan Subject",
        filters={"parent": plan_doc.name},
        fields=["subject", "sort_order"],
        order_by="sort_order"
    )

    subject_ids = [ps.subject for ps in plan_subjects]
    subjects = frappe.get_all(
        "Memora Subject",
        filters={"name": ["in", subject_ids]},
        fields=["name", "title", "description", "image", "color_code", "is_published", "required_item"]
    )
    subject_dict = {s.name: s for s in subjects}

    for ps in plan_subjects:
        subject = subject_dict.get(ps.subject)
        if not subject:
            continue

        access_level = calculate_access_level(subject, parent_access=None, plan_overrides=plan_overrides)
        if access_level is None:
            continue

        subject_data = {
            "id": subject.name,
            "title": subject.title,
            "sort_order": ps.sort_order,
            "url": f"subjects/{subject.name}.json"
        }

        if subject.description:
            subject_data["description"] = subject.description
        if subject.image:
            subject_data["image"] = subject.image
        if subject.color_code:
            subject_data["color_code"] = subject.color_code

        subject_data["access"] = {
            "is_published": subject.is_published,
            "access_level": access_level
        }

        if subject.required_item:
            subject_data["access"]["required_item"] = subject.required_item
            subject_data["access"]["is_sold_separately"] = False

        manifest["subjects"].append(subject_data)

    return manifest

def generate_subject_json(subject_doc, plan_id=None):
    """
    Generate subject JSON with complete content hierarchy.

    Args:
        subject_doc (frappe.doc): Memora Subject document
        plan_id (str, optional): Plan ID for override lookup

    Returns:
        dict or None: Complete subject data with tracks, units, topics, lessons, or None if hidden
    """
    plan_overrides = apply_plan_overrides(plan_id) if plan_id else {}
    
    subject_access = calculate_access_level(subject_doc, parent_access=None, plan_overrides=plan_overrides)
    if subject_access is None:
        return None

    subject_data = {
        "id": subject_doc.name,
        "title": subject_doc.title,
        "description": subject_doc.description or "",
        "sort_order": subject_doc.sort_order,
        "tracks": [],
        "access": {
            "is_published": subject_doc.is_published,
            "access_level": subject_access
        }
    }

    if subject_doc.image:
        subject_data["image"] = subject_doc.image
    if subject_doc.color_code:
        subject_data["color_code"] = subject_doc.color_code

    if subject_doc.required_item:
        subject_data["access"]["required_item"] = subject_doc.required_item
        subject_data["access"]["is_sold_separately"] = False

    tracks = frappe.get_all(
        "Memora Track",
        filters={"parent_subject": subject_doc.name},
        fields=["name", "title", "description", "sort_order", "is_sold_separately", "parent_item_required", "required_item"],
        order_by="sort_order"
    )

    track_ids = [track.name for track in tracks]
    all_units = frappe.get_all(
        "Memora Unit",
        filters={"parent_track": ["in", track_ids]},
        fields=["name", "title", "description", "sort_order", "parent_track"]
    )
    units_by_track = {}
    for unit in all_units:
        if unit.parent_track not in units_by_track:
            units_by_track[unit.parent_track] = []
        units_by_track[unit.parent_track].append(unit)

    all_topics = frappe.get_all(
        "Memora Topic",
        filters={"parent_unit": ["in", [u.name for u in all_units]]},
        fields=["name", "title", "description", "sort_order", "parent_unit"]
    )
    topics_by_unit = {}
    for topic in all_topics:
        if topic.parent_unit not in topics_by_unit:
            topics_by_unit[topic.parent_unit] = []
        topics_by_unit[topic.parent_unit].append(topic)

    all_lessons = frappe.get_all(
        "Memora Lesson",
        filters={"parent_topic": ["in", [t.name for t in all_topics]]},
        fields=["name", "title", "description", "sort_order", "is_free_preview", "is_published", "required_item", "parent_topic"]
    )
    lessons_by_topic = {}
    for lesson in all_lessons:
        if lesson.parent_topic not in lessons_by_topic:
            lessons_by_topic[lesson.parent_topic] = []
        lessons_by_topic[lesson.parent_topic].append(lesson)

    for track in tracks:
        track_access = calculate_access_level(track, parent_access=subject_access, plan_overrides=plan_overrides)
        
        if track_access is None:
            continue

        track_data = {
            "id": track.name,
            "title": track.title,
            "description": track.description or "",
            "sort_order": track.sort_order,
            "units": [],
            "access": {
                "is_published": True,
                "access_level": track_access
            }
        }

        if track.required_item:
            track_data["access"]["required_item"] = track.required_item
            track_data["access"]["is_sold_separately"] = track.is_sold_separately
            track_data["access"]["parent_item_required"] = track.parent_item_required

        for unit in units_by_track.get(track.name, []):
            unit_access = calculate_access_level(unit, parent_access=track_access, plan_overrides=plan_overrides)
            
            if unit_access is None:
                continue

            unit_data = {
                "id": unit.name,
                "title": unit.title,
                "description": unit.description or "",
                "sort_order": unit.sort_order,
                "topics": [],
                "access": {
                    "is_published": True,
                    "access_level": unit_access
                }
            }

            if track.required_item:
                unit_data["access"]["required_item"] = track.required_item
                unit_data["access"]["is_sold_separately"] = track.is_sold_separately
                unit_data["access"]["parent_item_required"] = track.parent_item_required

            for topic in topics_by_unit.get(unit.name, []):
                topic_access = calculate_access_level(topic, parent_access=unit_access, plan_overrides=plan_overrides)
                
                if topic_access is None:
                    continue

                topic_data = {
                    "id": topic.name,
                    "title": topic.title,
                    "description": topic.description or "",
                    "sort_order": topic.sort_order,
                    "lessons": [],
                    "access": {
                        "is_published": True,
                        "access_level": topic_access
                    }
                }

                if track.required_item:
                    topic_data["access"]["required_item"] = track.required_item
                    topic_data["access"]["is_sold_separately"] = track.is_sold_separately
                    topic_data["access"]["parent_item_required"] = track.parent_item_required

                for lesson in lessons_by_topic.get(topic.name, []):
                    lesson_access = calculate_access_level(lesson, parent_access=topic_access, plan_overrides=plan_overrides)
                    
                    if lesson_access is None:
                        continue

                    lesson_data = {
                        "id": lesson.name,
                        "title": lesson.title,
                        "description": lesson.description or "",
                        "sort_order": lesson.sort_order,
                        "stages": [],
                        "access": {
                            "is_published": lesson.is_published,
                            "access_level": lesson_access
                        }
                    }

                    if lesson.required_item:
                        lesson_data["access"]["required_item"] = lesson.required_item

                    stages = frappe.get_all(
                        "Memora Lesson Stage",
                        filters={"parent": lesson.name},
                        fields=["name", "title", "stage_config", "sort_order"],
                        order_by="sort_order"
                    )

                    for stage in stages:
                        stage_data = {
                            "id": stage.name,
                            "title": stage.title,
                            "stage_config": json.loads(stage.stage_config) if stage.stage_config else {},
                            "sort_order": stage.sort_order
                        }
                        lesson_data["stages"].append(stage_data)

                    topic_data["lessons"].append(lesson_data)

                unit_data["topics"].append(topic_data)

            track_data["units"].append(unit_data)

        subject_data["tracks"].append(track_data)

    return subject_data

def generate_unit_json(unit_doc, plan_id=None):
    """
    Generate unit JSON with content hierarchy (unit → topics → lessons).

    Args:
        unit_doc (frappe.doc): Memora Unit document
        plan_id (str, optional): Plan ID for override lookup

    Returns:
        dict or None: Complete unit data with topics and lessons, or None if hidden
    """
    plan_overrides = apply_plan_overrides(plan_id) if plan_id else {}
    
    track_doc = frappe.get_all(
        "Memora Track",
        filters={"name": unit_doc.parent_track},
        fields=["name", "required_item", "is_sold_separately", "parent_item_required"]
    )
    if not track_doc:
        return None
    track_doc = track_doc[0]
    track_access = calculate_access_level(track_doc, parent_access=None, plan_overrides=plan_overrides)
    
    unit_access = calculate_access_level(unit_doc, parent_access=track_access, plan_overrides=plan_overrides)
    if unit_access is None:
        return None

    unit_data = {
        "id": unit_doc.name,
        "title": unit_doc.title,
        "description": unit_doc.description or "",
        "sort_order": unit_doc.sort_order,
        "topics": [],
        "access": {
            "is_published": True,
            "access_level": unit_access
        }
    }

    if track_doc.required_item:
        unit_data["access"]["required_item"] = track_doc.required_item
        unit_data["access"]["is_sold_separately"] = track_doc.is_sold_separately
        unit_data["access"]["parent_item_required"] = track_doc.parent_item_required

    topics = frappe.get_all(
        "Memora Topic",
        filters={"parent_unit": unit_doc.name},
        fields=["name", "title", "description", "sort_order"],
        order_by="sort_order"
    )

    topic_ids = [topic.name for topic in topics]
    all_lessons = frappe.get_all(
        "Memora Lesson",
        filters={"parent_topic": ["in", topic_ids]},
        fields=["name", "title", "description", "sort_order", "is_free_preview", "is_published", "required_item", "parent_topic"]
    )
    lessons_by_topic = {}
    for lesson in all_lessons:
        if lesson.parent_topic not in lessons_by_topic:
            lessons_by_topic[lesson.parent_topic] = []
        lessons_by_topic[lesson.parent_topic].append(lesson)

    for topic in topics:
        topic_access = calculate_access_level(topic, parent_access=unit_access, plan_overrides=plan_overrides)
        
        if topic_access is None:
            continue

        topic_data = {
            "id": topic.name,
            "title": topic.title,
            "description": topic.description or "",
            "sort_order": topic.sort_order,
            "lessons": [],
            "access": {
                "is_published": True,
                "access_level": topic_access
            }
        }

        if track_doc.required_item:
            topic_data["access"]["required_item"] = track_doc.required_item
            topic_data["access"]["is_sold_separately"] = track_doc.is_sold_separately
            topic_data["access"]["parent_item_required"] = track_doc.parent_item_required

        for lesson in lessons_by_topic.get(topic.name, []):
            lesson_access = calculate_access_level(lesson, parent_access=topic_access, plan_overrides=plan_overrides)
            
            if lesson_access is None:
                continue

            lesson_data = {
                "id": lesson.name,
                "title": lesson.title,
                "description": lesson.description or "",
                "sort_order": lesson.sort_order,
                "stages": [],
                "access": {
                    "is_published": lesson.is_published,
                    "access_level": lesson_access
                }
            }

            if lesson.required_item:
                lesson_data["access"]["required_item"] = lesson.required_item

            stages = frappe.get_all(
                "Memora Lesson Stage",
                filters={"parent": lesson.name},
                fields=["name", "title", "stage_config", "sort_order"],
                order_by="sort_order"
            )

            for stage in stages:
                stage_data = {
                    "id": stage.name,
                    "title": stage.title,
                    "stage_config": json.loads(stage.stage_config) if stage.stage_config else {},
                    "sort_order": stage.sort_order
                }
                lesson_data["stages"].append(stage_data)

            topic_data["lessons"].append(lesson_data)

        unit_data["topics"].append(topic_data)

    return unit_data

def generate_lesson_json(lesson_doc, plan_id=None):
    """
    Generate lesson JSON with stages and signed URLs for video content.

    Args:
        lesson_doc (frappe.doc): Memora Lesson document
        plan_id (str, optional): Plan ID for override lookup

    Returns:
        dict or None: Complete lesson data with stages, or None if hidden
    """
    plan_overrides = apply_plan_overrides(plan_id) if plan_id else {}

    topic_doc = frappe.get_doc("Memora Topic", lesson_doc.parent_topic)
    unit_doc = frappe.get_doc("Memora Unit", topic_doc.parent_unit)
    track_doc = frappe.get_doc("Memora Track", unit_doc.parent_track)

    track_access = calculate_access_level(track_doc, parent_access=None, plan_overrides=plan_overrides)
    topic_access = calculate_access_level(topic_doc, parent_access=track_access, plan_overrides=plan_overrides)
    lesson_access = calculate_access_level(lesson_doc, parent_access=topic_access, plan_overrides=plan_overrides)

    if lesson_access is None:
        return None

    lesson_data = {
        "id": lesson_doc.name,
        "title": lesson_doc.title,
        "description": lesson_doc.description or "",
        "sort_order": lesson_doc.sort_order,
        "version": int(now_datetime().timestamp()),
        "generated_at": now_datetime().isoformat(),
        "stages": [],
        "access": {
            "is_published": lesson_doc.is_published,
            "access_level": lesson_access
        }
    }

    if lesson_doc.required_item:
        lesson_data["access"]["required_item"] = lesson_doc.required_item

    stages = frappe.get_all(
        "Memora Lesson Stage",
        filters={"parent": lesson_doc.name},
        fields=["name", "title", "stage_config", "sort_order"],
        order_by="sort_order"
    )

    settings = frappe.get_single("CDN Settings")
    signed_url_expiry_hours = getattr(settings, 'signed_url_expiry_hours', 4)
    expiry_time = now_datetime() + timedelta(hours=signed_url_expiry_hours)
    lesson_data["signed_url_expiry"] = expiry_time.isoformat()

    for stage in stages:
        stage_config = json.loads(stage.stage_config) if stage.stage_config else {}

        stage_data = {
            "idx": stage.sort_order,
            "title": stage.title,
            "type": stage_config.get("type", "Text"),
            "config": stage_config
        }

        if stage_data["type"] == "Video" and "video_url" in stage_config:
            from .cdn_uploader import generate_signed_url, get_cdn_client
            try:
                client = get_cdn_client(settings)
                video_key = stage_config["video_url"].split(f"{settings.bucket_name}/")[-1]
                signed_url = generate_signed_url(
                    client,
                    settings.bucket_name,
                    video_key,
                    expiry_seconds=signed_url_expiry_hours * 3600
                )
                stage_data["config"]["video_url"] = signed_url
            except Exception as e:
                frappe.log_error(f"Failed to generate signed URL for video {stage_config.get('video_url')}: {str(e)}", "Signed URL Generation Failed")

        lesson_data["stages"].append(stage_data)

    return lesson_data

def get_content_paths_for_plan(plan_name):
    """
    Generate all file paths that need to be generated for a plan.

    Args:
        plan_name (str): Plan document name

    Returns:
        dict: Dictionary of {path: data} for all CDN files
    """
    all_files = {}

    plan_doc = frappe.get_doc("Memora Academic Plan", plan_name)
    all_files[f"plans/{plan_name}/manifest.json"] = generate_manifest(plan_doc)

    search_index = generate_search_index(plan_name)
    all_files[f"plans/{plan_name}/search_index.json"] = search_index

    if search_index.get("is_sharded"):
        for shard in search_index["shards"]:
            subject_id = shard["subject_id"]
            subject_shard = generate_subject_shard(plan_name, subject_id)
            all_files[f"plans/{plan_name}/search/{subject_id}.json"] = subject_shard

    plan_subjects = frappe.get_all(
        "Memora Plan Subject",
        filters={"parent": plan_name},
        fields=["subject"],
        order_by="sort_order"
    )

    subject_ids = [ps.subject for ps in plan_subjects]
    subjects = frappe.get_all(
        "Memora Subject",
        filters={"name": ["in", subject_ids]},
        fields=["name", "title", "description", "is_published", "required_item", "sort_order"]
    )
    subjects_dict = {s.name: s for s in subjects}

    tracks = frappe.get_all(
        "Memora Track",
        filters={"parent_subject": ["in", subject_ids]},
        fields=["name", "title", "description", "sort_order", "is_sold_separately", "parent_item_required", "required_item", "parent_subject"]
    )

    track_ids = [track.name for track in tracks]
    units = frappe.get_all(
        "Memora Unit",
        filters={"parent_track": ["in", track_ids]},
        fields=["name", "title", "description", "sort_order", "parent_track"]
    )

    unit_ids = [unit.name for unit in units]
    topics = frappe.get_all(
        "Memora Topic",
        filters={"parent_unit": ["in", unit_ids]},
        fields=["name", "title", "description", "sort_order", "parent_unit"]
    )

    topic_ids = [topic.name for topic in topics]
    lessons = frappe.get_all(
        "Memora Lesson",
        filters={"parent_topic": ["in", topic_ids]},
        fields=["name", "title", "description", "sort_order", "is_free_preview", "is_published", "required_item", "parent_topic"]
    )

    for ps in plan_subjects:
        subject = subjects_dict.get(ps.subject)
        if not subject:
            continue

        subject_data = generate_subject_json(subject, plan_id=plan_name)
        if subject_data is None:
            continue
        
        all_files[f"subjects/{subject.name}.json"] = subject_data

        for track in [t for t in tracks if t.parent_subject == subject.name]:
            for unit in [u for u in units if u.parent_track == track.name]:
                unit_data = generate_unit_json(unit, plan_id=plan_name)
                if unit_data is None:
                    continue
                
                all_files[f"units/{unit.name}.json"] = unit_data

                for topic in [t for t in topics if t.parent_unit == unit.name]:
                    for lesson in [l for l in lessons if l.parent_topic == topic.name]:
                        lesson_data = generate_lesson_json(lesson, plan_id=plan_name)
                        if lesson_data is None:
                            continue
                        
                        all_files[f"lessons/{lesson.name}.json"] = lesson_data

    return all_files
