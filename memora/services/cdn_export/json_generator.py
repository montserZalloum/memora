import frappe
import json
import os
from datetime import datetime, timedelta
from frappe.utils import now_datetime
from .dependency_resolver import get_affected_plan_ids
from .access_calculator import calculate_access_level, apply_plan_overrides
from .search_indexer import generate_search_index, generate_subject_shard, SHARD_THRESHOLD
from .url_resolver import get_content_url

# Schema directory for JSON validation
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), 'schemas')

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
        "search_index_url": get_content_url(f"plans/{plan_doc.name}/search_index.json")
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
        # fields=["subject", "sort_order"],
        fields=["subject"],  # "sort_order" commented out
        # order_by="sort_order"
        order_by="subject"  # sort_by commented out, using name as fallback
    )

    subject_ids = [ps.subject for ps in plan_subjects]
    subjects = frappe.get_all(
        "Memora Subject",
        filters={"name": ["in", subject_ids]},
        # fields=["name", "title", "description", "image", "color_code", "is_published", "required_item"]
        fields=["name", "title", "description", "image", "color_code", "is_published", "is_linear"]  # "required_item" commented out
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
		"is_linear": subject.is_linear if hasattr(subject, "is_linear") else True,
            # "sort_order": ps.sort_order,
            "url": get_content_url(f"subjects/{subject.name}.json")
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

        # if subject.required_item:
        #     subject_data["access"]["required_item"] = subject.required_item
        #     subject_data["access"]["is_sold_separately"] = False

        manifest["subjects"].append(subject_data)

    return manifest

def generate_manifest_atomic(plan_doc):
    """
    Generate plan manifest JSON for atomic CDN distribution (Phase 3: User Story 1).
    
    Atomic structure includes hierarchy_url and bitmap_url for each subject,
    enabling granular cache invalidation and shared lesson content.

    Args:
        plan_doc (frappe.doc): Memora Academic Plan document

    Returns:
        dict: Manifest data conforming to manifest.schema.json
    """
    manifest = {
        "plan_id": plan_doc.name,
        "title": plan_doc.title,
        "version": int(now_datetime().timestamp()),
        "generated_at": now_datetime().isoformat(),
        "subjects": [],
        "search_index_url": get_content_url(f"plans/{plan_doc.name}/search_index.json")
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
        fields=["subject"],
        order_by="subject"
    )

    subject_ids = [ps.subject for ps in plan_subjects]
    subjects = frappe.get_all(
        "Memora Subject",
        filters={"name": ["in", subject_ids]},
        fields=["name", "title", "description", "image", "color_code", "is_published", "is_linear"]
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
            "is_linear": subject.is_linear if hasattr(subject, "is_linear") else True,
            "hierarchy_url": get_content_url(f"plans/{plan_doc.name}/{subject.name}_h.json"),
            "bitmap_url": get_content_url(f"plans/{plan_doc.name}/{subject.name}_b.json"),
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

        # Include required_item if access level is paid
        if access_level == "paid" and hasattr(subject, "required_item") and subject.required_item:
            subject_data["access"]["required_item"] = subject.required_item

        manifest["subjects"].append(subject_data)

    return manifest

def validate_manifest_against_schema(manifest):
    """
    Validate generated manifest against manifest.schema.json.
    
    Args:
        manifest (dict): Manifest data to validate
        
    Returns:
        tuple: (is_valid: bool, errors: list of error messages)
    """
    import jsonschema
    import os
    
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "schemas",
        "manifest.schema.json"
    )
    
    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
    except Exception as e:
        return False, [f"Failed to load manifest schema: {str(e)}"]
    
    try:
        jsonschema.validate(instance=manifest, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Schema validation error: {str(e)}"]

def generate_subject_hierarchy(subject_doc, plan_id=None):
    """
    Generate subject hierarchy JSON (Phase 4: User Story 2).
    
    Generates {subject_id}_h.json with tracks → units → topics structure,
    NO lessons embedded. Each topic includes topic_url pointing to separate topic JSON
    and lesson_count for UI display without loading lesson details.

    Args:
        subject_doc (frappe.doc): Memora Subject document
        plan_id (str, optional): Plan ID for override lookup

    Returns:
        dict or None: Subject hierarchy data conforming to subject_hierarchy.schema.json,
                      or None if subject is hidden by override
    """
    plan_overrides = apply_plan_overrides(plan_id) if plan_id else {}
    
    subject_access = calculate_access_level(subject_doc, parent_access=None, plan_overrides=plan_overrides)
    if subject_access is None:
        frappe.log_error(
            f"[WARN] Subject {subject_doc.name} skipped - access level is None (likely hidden by plan override)",
            "CDN JSON Generation"
        )
        return None

    hierarchy = {
        "id": subject_doc.name,
        "title": subject_doc.title,
        "is_linear": subject_doc.is_linear if hasattr(subject_doc, "is_linear") else True,
        "version": int(now_datetime().timestamp()),
        "generated_at": now_datetime().isoformat(),
        "access": {
            "is_published": subject_doc.is_published,
            "access_level": subject_access
        },
        "tracks": []
    }

    if subject_doc.description:
        hierarchy["description"] = subject_doc.description
    if subject_doc.image:
        hierarchy["image"] = subject_doc.image
    if subject_doc.color_code:
        hierarchy["color_code"] = subject_doc.color_code

    # Include required_item if access level is paid
    if subject_access == "paid" and hasattr(subject_doc, "required_item") and subject_doc.required_item:
        hierarchy["access"]["required_item"] = subject_doc.required_item

    # Fetch all tracks for this subject
    tracks = frappe.get_all(
        "Memora Track",
        filters={"parent_subject": subject_doc.name},
        fields=["name", "title", "description", "is_linear"],
        order_by="name"
    )

    # Fetch all units and organize by track
    track_ids = [track.name for track in tracks]
    all_units = frappe.get_all(
        "Memora Unit",
        filters={"parent_track": ["in", track_ids]},
        fields=["name", "title", "description", "parent_track", "is_linear"],
    )
    units_by_track = {}
    for unit in all_units:
        if unit.parent_track not in units_by_track:
            units_by_track[unit.parent_track] = []
        units_by_track[unit.parent_track].append(unit)

    # Fetch all topics and organize by unit
    unit_ids = [unit.name for unit in all_units]
    all_topics = frappe.get_all(
        "Memora Topic",
        filters={"parent_unit": ["in", unit_ids]},
        fields=["name", "title", "description", "parent_unit", "is_linear"],
    )
    topics_by_unit = {}
    for topic in all_topics:
        if topic.parent_unit not in topics_by_unit:
            topics_by_unit[topic.parent_unit] = []
        topics_by_unit[topic.parent_unit].append(topic)

    # Count lessons per topic (without loading lesson details)
    topic_ids = [topic.name for topic in all_topics]
    all_lessons = frappe.get_all(
        "Memora Lesson",
        filters={"parent_topic": ["in", topic_ids]},
        fields=["parent_topic"],
    )
    lesson_count_by_topic = {}
    for lesson in all_lessons:
        if lesson.parent_topic not in lesson_count_by_topic:
            lesson_count_by_topic[lesson.parent_topic] = 0
        lesson_count_by_topic[lesson.parent_topic] += 1

    # Track statistics
    stats = {
        "total_tracks": 0,
        "total_units": 0,
        "total_topics": 0,
        "total_lessons": len(all_lessons)
    }

    # Build hierarchy: tracks → units → topics (NO lessons)
    for track in tracks:
        track_access = calculate_access_level(track, parent_access=subject_access, plan_overrides=plan_overrides)
        
        if track_access is None:
            continue  # Skip hidden tracks

        track_data = {
            "id": track.name,
            "title": track.title,
            "is_linear": track.is_linear if hasattr(track, "is_linear") else True,
            "access": {
                "is_published": True,
                "access_level": track_access
            },
            "units": []
        }

        if track.description:
            track_data["description"] = track.description
        if hasattr(track, "image") and track.image:
            track_data["image"] = track.image

        if track_access == "paid" and hasattr(track, "required_item") and track.required_item:
            track_data["access"]["required_item"] = track.required_item

        for unit in units_by_track.get(track.name, []):
            unit_access = calculate_access_level(unit, parent_access=track_access, plan_overrides=plan_overrides)
            
            if unit_access is None:
                continue  # Skip hidden units

            unit_data = {
                "id": unit.name,
                "title": unit.title,
                "is_linear": unit.is_linear if hasattr(unit, "is_linear") else True,
                "access": {
                    "is_published": True,
                    "access_level": unit_access
                },
                "topics": []
            }

            if unit.description:
                unit_data["description"] = unit.description
            if hasattr(unit, "image") and unit.image:
                unit_data["image"] = unit.image
            if hasattr(unit, "badge_image") and unit.badge_image:
                unit_data["badge_image"] = unit.badge_image

            if unit_access == "paid" and hasattr(unit, "required_item") and unit.required_item:
                unit_data["access"]["required_item"] = unit.required_item

            for topic in topics_by_unit.get(unit.name, []):
                topic_access = calculate_access_level(topic, parent_access=unit_access, plan_overrides=plan_overrides)
                
                if topic_access is None:
                    continue  # Skip hidden topics

                # Calculate lesson count for this topic
                topic_lesson_count = lesson_count_by_topic.get(topic.name, 0)

                topic_data = {
                    "id": topic.name,
                    "title": topic.title,
                    "is_linear": topic.is_linear if hasattr(topic, "is_linear") else True,
                    "topic_url": get_content_url(f"plans/{plan_id}/{topic.name}.json") if plan_id else f"plans/shared/{topic.name}.json",
                    "access": {
                        "is_published": True,
                        "access_level": topic_access
                    },
                    "lesson_count": topic_lesson_count
                }

                if topic.description:
                    topic_data["description"] = topic.description
                if hasattr(topic, "image") and topic.image:
                    topic_data["image"] = topic.image

                if topic_access == "paid" and hasattr(topic, "required_item") and topic.required_item:
                    topic_data["access"]["required_item"] = topic.required_item

                unit_data["topics"].append(topic_data)
                stats["total_topics"] += 1

            if unit_data["topics"]:  # Only add unit if it has visible topics
                track_data["units"].append(unit_data)
                stats["total_units"] += 1

        if track_data["units"]:  # Only add track if it has visible units
            hierarchy["tracks"].append(track_data)
            stats["total_tracks"] += 1

    # Add stats to hierarchy
    hierarchy["stats"] = stats

    frappe.log_error(
        f"[INFO] Generated subject hierarchy for {subject_doc.name} with {stats['total_tracks']} tracks, "
        f"{stats['total_units']} units, {stats['total_topics']} topics",
        "CDN JSON Generation"
    )
    return hierarchy

def validate_subject_hierarchy_against_schema(hierarchy):
    """
    Validate generated subject hierarchy against subject_hierarchy.schema.json.
    
    Args:
        hierarchy (dict): Hierarchy data to validate
        
    Returns:
        tuple: (is_valid: bool, errors: list of error messages)
    """
    import jsonschema
    import os
    
    schema_path = os.path.join(
        os.path.dirname(__file__),
        "schemas",
        "subject_hierarchy.schema.json"
    )
    
    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
    except Exception as e:
        return False, [f"Failed to load subject_hierarchy schema: {str(e)}"]
    
    try:
        jsonschema.validate(instance=hierarchy, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Schema validation error: {str(e)}"]

def generate_subject_json(subject_doc, plan_id=None):
	"""
	Generate subject JSON with complete content hierarchy.

	Args:
		subject_doc (frappe.doc): Memora Subject document
		plan_id (str, optional): Plan ID for override lookup

	Returns:
		dict or None: Complete subject data with tracks, units, topics, lessons, or None if hidden
	"""
	import frappe
	
	plan_overrides = apply_plan_overrides(plan_id) if plan_id else {}
	
	subject_access = calculate_access_level(subject_doc, parent_access=None, plan_overrides=plan_overrides)
	if subject_access is None:
		frappe.log_error(
			f"[WARN] Subject {subject_doc.name} skipped - access level is None (likely hidden by plan override)",
			"CDN JSON Generation"
		)
		return None

	subject_data = {
		"id": subject_doc.name,
		"title": subject_doc.title,
		"description": subject_doc.description or "",
		# "sort_order": subject_doc.sort_order,
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

	# if subject_doc.required_item:
	# 	subject_data["access"]["required_item"] = subject_doc.required_item
	# 	subject_data["access"]["is_sold_separately"] = False

	tracks = frappe.get_all(
		"Memora Track",
		filters={"parent_subject": subject_doc.name},
		# fields=["name", "title", "description", "sort_order", "is_sold_separately", "parent_item_required", "required_item"],
		fields=["name", "title", "description", "is_sold_separately", "parent_item_required", "is_linear"],  # "sort_order" and "required_item" commented out
		# order_by="sort_order"
		order_by="name"  # sort_by commented out, using name as fallback
	)

	track_ids = [track.name for track in tracks]
	all_units = frappe.get_all(
		"Memora Unit",
		filters={"parent_track": ["in", track_ids]},
		# fields=["name", "title", "description", "sort_order", "parent_track"]
		fields=["name", "title", "description", "parent_track"]  # "sort_order" commented out
	)
	units_by_track = {}
	for unit in all_units:
		if unit.parent_track not in units_by_track:
			units_by_track[unit.parent_track] = []
		units_by_track[unit.parent_track].append(unit)

	all_topics = frappe.get_all(
		"Memora Topic",
		filters={"parent_unit": ["in", [u.name for u in all_units]]},
		# fields=["name", "title", "description", "sort_order", "parent_unit"]
		fields=["name", "title", "description", "parent_unit"]  # "sort_order" commented out
	)
	topics_by_unit = {}
	for topic in all_topics:
		if topic.parent_unit not in topics_by_unit:
			topics_by_unit[topic.parent_unit] = []
		topics_by_unit[topic.parent_unit].append(topic)

	all_lessons = frappe.get_all(
		"Memora Lesson",
		filters={"parent_topic": ["in", [t.name for t in all_topics]]},
		# fields=["name", "title", "description", "sort_order", "is_free_preview", "is_published", "required_item", "parent_topic"]
		fields=["name", "title", "description", "is_free_preview", "is_published", "parent_topic"]  # "sort_order" and "required_item" commented out
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
			"is_linear": track.is_linear if hasattr(track, "is_linear") else True,
			# "sort_order": track.sort_order,
			"units": [],
			"access": {
				"is_published": True,
				"access_level": track_access
			}
		}

		# if track.required_item:
		# 	track_data["access"]["required_item"] = track.required_item
		# 	track_data["access"]["is_sold_separately"] = track.is_sold_separately
		# 	track_data["access"]["parent_item_required"] = track.parent_item_required

		for unit in units_by_track.get(track.name, []):
			unit_access = calculate_access_level(unit, parent_access=track_access, plan_overrides=plan_overrides)
			
			if unit_access is None:
				continue

			unit_data = {
				"id": unit.name,
				"title": unit.title,
				"description": unit.description or "",
				"is_linear": unit.is_linear if hasattr(unit, "is_linear") else True,
				# "sort_order": unit.sort_order,
				"topics": [],
				"access": {
					"is_published": True,
					"access_level": unit_access
				}
			}

			# if track.required_item:
			# 	unit_data["access"]["required_item"] = track.required_item
			# 	unit_data["access"]["is_sold_separately"] = track.is_sold_separately
			# 	unit_data["access"]["parent_item_required"] = track.parent_item_required

			for topic in topics_by_unit.get(unit.name, []):
				topic_access = calculate_access_level(topic, parent_access=unit_access, plan_overrides=plan_overrides)
				
				if topic_access is None:
					continue

				topic_data = {
			"id": topic.name,
			"title": topic.title,
			"description": topic.description or "",
			"is_linear": topic.is_linear if hasattr(topic, "is_linear") else True,
					"is_linear": topic.is_linear if hasattr(topic, "is_linear") else True,
					# "sort_order": topic.sort_order,
					"lessons": [],
					"access": {
						"is_published": True,
						"access_level": topic_access
					}
				}

				# if track.required_item:
				# 	topic_data["access"]["required_item"] = track.required_item
				# 	topic_data["access"]["is_sold_separately"] = track.is_sold_separately
				# 	topic_data["access"]["parent_item_required"] = track.parent_item_required

				for lesson in lessons_by_topic.get(topic.name, []):
					lesson_access = calculate_access_level(lesson, parent_access=topic_access, plan_overrides=plan_overrides)
					
					if lesson_access is None:
						continue

					lesson_data = {
				"id": lesson.name,
				"title": lesson.title,
				"description": lesson.description or "",
				"bit_index": lesson.bit_index if hasattr(lesson, "bit_index") else -1,
						"bit_index": lesson.bit_index if hasattr(lesson, "bit_index") else -1,
						# "sort_order": lesson.sort_order,
						"stages": [],
						"access": {
							"is_published": lesson.is_published,
							"access_level": lesson_access
						}
					}

					# if lesson.required_item:
					# 	lesson_data["access"]["required_item"] = lesson.required_item

					stages = frappe.get_all(
						"Memora Lesson Stage",
						filters={"parent": lesson.name},
						# fields=["name", "title", "config", "sort_order"],
						fields=["name", "title", "config"],  # "sort_order" commented out
						# order_by="sort_order"
						order_by="name"  # sort_by commented out, using name as fallback
					)

					for stage in stages:
						stage_data = {
							"id": stage.name,
							"title": stage.title,
							"config": json.loads(stage.config) if stage.config else {}
							# "sort_order": stage.sort_order
						}
						lesson_data["stages"].append(stage_data)

					topic_data["lessons"].append(lesson_data)

				unit_data["topics"].append(topic_data)

			track_data["units"].append(unit_data)

		subject_data["tracks"].append(track_data)

	frappe.log_error(
		f"[INFO] Generated subject JSON for {subject_doc.name} with {len(subject_data['tracks'])} tracks",
		"CDN JSON Generation"
	)
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
        # fields=["name", "required_item", "is_sold_separately", "parent_item_required"]
        fields=["name", "is_sold_separately", "parent_item_required"]  # "required_item" commented out
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
        # "sort_order": unit_doc.sort_order,
        "topics": [],
        "access": {
            "is_published": True,
            "access_level": unit_access
        }
    }

    # if track_doc.required_item:
    #     unit_data["access"]["required_item"] = track_doc.required_item
    #     unit_data["access"]["is_sold_separately"] = track_doc.is_sold_separately
    #     unit_data["access"]["parent_item_required"] = track_doc.parent_item_required

    topics = frappe.get_all(
        "Memora Topic",
        filters={"parent_unit": unit_doc.name},
        # fields=["name", "title", "description", "sort_order"],
        fields=["name", "title", "description"],  # "sort_order" commented out
        # order_by="sort_order"
        order_by="name"  # sort_by commented out, using name as fallback
    )

    topic_ids = [topic.name for topic in topics]
    all_lessons = frappe.get_all(
        "Memora Lesson",
        filters={"parent_topic": ["in", topic_ids]},
        # fields=["name", "title", "description", "sort_order", "is_free_preview", "is_published", "required_item", "parent_topic"]
        fields=["name", "title", "description", "is_free_preview", "is_published", "parent_topic"]  # "sort_order" and "required_item" commented out
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
			"is_linear": topic.is_linear if hasattr(topic, "is_linear") else True,
					"is_linear": topic.is_linear if hasattr(topic, "is_linear") else True,
            # "sort_order": topic.sort_order,
            "lessons": [],
            "access": {
                "is_published": True,
                "access_level": topic_access
            }
        }

        # if track_doc.required_item:
        #     topic_data["access"]["required_item"] = track_doc.required_item
        #     topic_data["access"]["is_sold_separately"] = track_doc.is_sold_separately
        #     topic_data["access"]["parent_item_required"] = track_doc.parent_item_required

        for lesson in lessons_by_topic.get(topic.name, []):
            lesson_access = calculate_access_level(lesson, parent_access=topic_access, plan_overrides=plan_overrides)
            
            if lesson_access is None:
                continue

            lesson_data = {
				"id": lesson.name,
				"title": lesson.title,
				"description": lesson.description or "",
				"bit_index": lesson.bit_index if hasattr(lesson, "bit_index") else -1,
						"bit_index": lesson.bit_index if hasattr(lesson, "bit_index") else -1,
                # "sort_order": lesson.sort_order,
                "stages": [],
                "access": {
                    "is_published": lesson.is_published,
                    "access_level": lesson_access
                }
            }

            # if lesson.required_item:
            #     lesson_data["access"]["required_item"] = lesson.required_item

            stages = frappe.get_all(
                "Memora Lesson Stage",
                filters={"parent": lesson.name},
                # fields=["name", "title", "config", "sort_order"],
                fields=["name", "title", "config"],  # "sort_order" commented out
                # order_by="sort_order"
                order_by="name"  # sort_by commented out, using name as fallback
            )

            for stage in stages:
                stage_data = {
                    "id": stage.name,
                    "title": stage.title,
                    "config": json.loads(stage.config) if stage.config else {}
                    # "sort_order": stage.sort_order
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
		"bit_index": lesson_doc.bit_index if hasattr(lesson_doc, "bit_index") else -1,
        # "sort_order": lesson_doc.sort_order,
        "version": int(now_datetime().timestamp()),
        "generated_at": now_datetime().isoformat(),
        "stages": [],
        "access": {
            "is_published": lesson_doc.is_published,
            "access_level": lesson_access
        }
    }

    # if lesson_doc.required_item:
    #     lesson_data["access"]["required_item"] = lesson_doc.required_item

    stages = frappe.get_all(
        "Memora Lesson Stage",
        filters={"parent": lesson_doc.name},
        # fields=["name", "title", "config", "sort_order"],
        fields=["name", "title", "config"],  # "sort_order" commented out
        # order_by="sort_order"
        order_by="name"  # sort_by commented out, using name as fallback
    )

    settings = frappe.get_single("CDN Settings")
    signed_url_expiry_hours = getattr(settings, 'signed_url_expiry_hours', 4)
    expiry_time = now_datetime() + timedelta(hours=signed_url_expiry_hours)
    lesson_data["signed_url_expiry"] = expiry_time.isoformat()

    for stage in stages:
        config = json.loads(stage.config) if stage.config else {}

        stage_data = {
            # "idx": stage.sort_order,
            "idx": stages.index(stage) + 1,  # using index as fallback
            "title": stage.title,
            "type": config.get("type", "Text"),
            "config": config
        }

        if stage_data["type"] == "Video" and "video_url" in config:
            from .cdn_uploader import generate_signed_url, get_cdn_client
            try:
                client = get_cdn_client(settings)
                video_key = config["video_url"].split(f"{settings.bucket_name}/")[-1]
                signed_url = generate_signed_url(
                    client,
                    settings.bucket_name,
                    video_key,
                    expiry_seconds=signed_url_expiry_hours * 3600
                )
                stage_data["config"]["video_url"] = signed_url
            except Exception as e:
                frappe.log_error(f"Failed to generate signed URL for video {config.get('video_url')}: {str(e)}", "Signed URL Generation Failed")

        lesson_data["stages"].append(stage_data)

    return lesson_data

def generate_topic_json(topic_doc, plan_id=None, subject_id=None):
	"""
	Generate topic JSON with lesson list (Phase 5: User Story 3).
	
	Generates {topic_id}.json with lesson list, bit_index references, and lesson_url pointers.
	Includes parent breadcrumb (unit_id, track_id, subject_id) and access control.
	Lessons are shared across plans, so lesson_url points to lessons/{lesson_id}.json

	Args:
		topic_doc (frappe.doc): Memora Topic document
		plan_id (str, optional): Plan ID for override lookup
		subject_id (str, optional): Subject ID for bitmap generation

	Returns:
		dict or None: Topic data conforming to topic.schema.json,
					  or None if topic is hidden by override
	"""
	plan_overrides = apply_plan_overrides(plan_id) if plan_id else {}
	
	# Get parent documents for breadcrumb
	unit_doc = frappe.get_doc("Memora Unit", topic_doc.parent_unit)
	track_doc = frappe.get_doc("Memora Track", unit_doc.parent_track)
	subject_doc = frappe.get_doc("Memora Subject", track_doc.parent_subject)
	
	# Calculate access levels with inheritance
	subject_access = calculate_access_level(subject_doc, parent_access=None, plan_overrides=plan_overrides)
	track_access = calculate_access_level(track_doc, parent_access=subject_access, plan_overrides=plan_overrides)
	unit_access = calculate_access_level(unit_doc, parent_access=track_access, plan_overrides=plan_overrides)
	topic_access = calculate_access_level(topic_doc, parent_access=unit_access, plan_overrides=plan_overrides)
	
	if topic_access is None:
		frappe.log_error(
			f"[WARN] Topic {topic_doc.name} skipped - access level is None (likely hidden by plan override)",
			"CDN JSON Generation"
		)
		return None
	
	# Build topic data
	topic_data = {
		"id": topic_doc.name,
		"title": topic_doc.title,
		"is_linear": topic_doc.is_linear if hasattr(topic_doc, "is_linear") else True,
		"version": int(now_datetime().timestamp()),
		"generated_at": now_datetime().isoformat(),
		"parent": {
			"unit_id": unit_doc.name,
			"unit_title": unit_doc.title,
			"track_id": track_doc.name,
			"track_title": track_doc.title,
			"subject_id": subject_doc.name,
			"subject_title": subject_doc.title
		},
		"access": {
			"is_published": topic_doc.is_published,
			"access_level": topic_access
		},
		"lessons": []
	}
	
	# Add optional fields
	if topic_doc.description:
		topic_data["description"] = topic_doc.description
	if hasattr(topic_doc, "image") and topic_doc.image:
		topic_data["image"] = topic_doc.image
	
	# Include required_item if access level is paid
	if topic_access == "paid" and hasattr(topic_doc, "required_item") and topic_doc.required_item:
		topic_data["access"]["required_item"] = topic_doc.required_item
	
	# Fetch all lessons for this topic
	lessons = frappe.get_all(
		"Memora Lesson",
		filters={"parent_topic": topic_doc.name},
		fields=["name", "title", "description", "is_published", "bit_index"],
		order_by="name"
	)
	
	# Fetch stage counts
	lesson_ids = [lesson.name for lesson in lessons]
	if lesson_ids:
		all_stages = frappe.get_all(
			"Memora Lesson Stage",
			filters={"parent": ["in", lesson_ids]},
			fields=["parent"]
		)
		stage_count_by_lesson = {}
		for stage in all_stages:
			if stage.parent not in stage_count_by_lesson:
				stage_count_by_lesson[stage.parent] = 0
			stage_count_by_lesson[stage.parent] += 1
	else:
		stage_count_by_lesson = {}
	
	# Process each lesson
	for lesson in lessons:
		lesson_access = calculate_access_level(lesson, parent_access=topic_access, plan_overrides=plan_overrides)
		
		if lesson_access is None:
			continue  # Skip hidden lessons
		
		lesson_data = {
			"id": lesson.name,
			"title": lesson.title,
			"bit_index": lesson.bit_index if hasattr(lesson, "bit_index") else -1,
			"lesson_url": get_content_url(f"lessons/{lesson.name}.json"),
			"access": {
				"is_published": lesson.is_published,
				"access_level": lesson_access
			},
			"stage_count": stage_count_by_lesson.get(lesson.name, 0)
		}
		
		# Add optional fields
		if lesson.description:
			lesson_data["description"] = lesson.description
		
		topic_data["lessons"].append(lesson_data)
	
	# Validate against schema
	is_valid, errors = validate_topic_json_against_schema(topic_data)
	if not is_valid:
		frappe.log_error(
			f"Generated topic JSON for {topic_doc.name} failed schema validation: {errors}",
			"CDN JSON Generation"
		)
	
	frappe.log_error(
		f"[INFO] Generated topic JSON for {topic_doc.name} with {len(topic_data['lessons'])} lessons",
		"CDN JSON Generation"
	)
	
	return topic_data

def validate_topic_json_against_schema(topic):
	"""
	Validate generated topic against topic.schema.json.
	
	Args:
		topic (dict): Topic data to validate
		
	Returns:
		tuple: (is_valid: bool, errors: list of error messages)
	"""
	import jsonschema
	import os
	
	schema_path = os.path.join(
		os.path.dirname(__file__),
		"schemas",
		"topic.schema.json"
	)
	
	try:
		with open(schema_path, "r") as f:
			schema = json.load(f)
	except Exception as e:
		return False, [f"Failed to load topic schema: {str(e)}"]
	
	try:
		jsonschema.validate(instance=topic, schema=schema)
		return True, []
	except jsonschema.ValidationError as e:
		return False, [str(e)]
	except Exception as e:
		return False, [f"Schema validation error: {str(e)}"]

def generate_lesson_json_shared(lesson_doc):
	"""
	Generate shared lesson JSON with stages, NO access/parent blocks (Phase 6: User Story 4).
	
	This function generates a plan-agnostic shared lesson JSON file that can be referenced 
	by multiple topics across different plans. The lesson contains only content (stages) and 
	navigation information, with no plan-specific access control or parent information.
	
	Access control is determined at the topic level, and parent context varies by plan.
	This allows lessons to be shared and cached across plans.
	
	Args:
		lesson_doc (frappe.doc): Memora Lesson document
	
	Returns:
		dict: Lesson data conforming to lesson.schema.json with stages but NO access/parent blocks
	"""
	# Build lesson data - NO access or parent blocks for shared lessons
	lesson_data = {
		"id": lesson_doc.name,
		"title": lesson_doc.title,
		"version": int(now_datetime().timestamp()),
		"generated_at": now_datetime().isoformat(),
		"stages": [],
		"navigation": {
			"is_standalone": True  # Always true for shared lessons
		}
	}
	
	# Add optional description
	if hasattr(lesson_doc, "description") and lesson_doc.description:
		lesson_data["description"] = lesson_doc.description
	
	# Add optional image
	if hasattr(lesson_doc, "image") and lesson_doc.image:
		lesson_data["image"] = lesson_doc.image
	
	# Fetch all stages for this lesson
	stages = frappe.get_all(
		"Memora Lesson Stage",
		filters={"parent": lesson_doc.name},
		fields=["idx", "title", "type", "weight", "target_time", "is_skippable", "config"],
		order_by="idx"
	)
	
	# Process each stage
	for stage in stages:
		# Parse config JSON
		config = {}
		if stage.config:
			try:
				config = json.loads(stage.config)
			except (json.JSONDecodeError, TypeError):
				config = {}
		
		# Build stage data with all fields
		stage_data = {
			"idx": stage.idx,
			"title": stage.title,
			"type": stage.type,
			"config": config
		}
		
		# Add optional fields if present
		if hasattr(stage, "weight") and stage.weight is not None:
			stage_data["weight"] = stage.weight
		if hasattr(stage, "target_time") and stage.target_time is not None:
			stage_data["target_time"] = stage.target_time
		if hasattr(stage, "is_skippable") and stage.is_skippable is not None:
			stage_data["is_skippable"] = stage.is_skippable
		
		lesson_data["stages"].append(stage_data)
	
	# Validate against schema
	is_valid, errors = validate_lesson_json_against_schema(lesson_data)
	if not is_valid:
		frappe.log_error(
			f"Generated shared lesson JSON for {lesson_doc.name} failed schema validation: {errors}",
			"CDN JSON Generation"
		)
	
	frappe.log_error(
		f"[INFO] Generated shared lesson JSON for {lesson_doc.name} with {len(lesson_data['stages'])} stages",
		"CDN JSON Generation"
	)
	
	return lesson_data


def validate_lesson_json_against_schema(lesson):
	"""
	Validate generated lesson against lesson.schema.json.
	
	Args:
		lesson (dict): Lesson data to validate
		
	Returns:
		tuple: (is_valid: bool, errors: list of error messages)
	"""
	import jsonschema
	import os
	
	schema_path = os.path.join(
		os.path.dirname(__file__),
		"schemas",
		"lesson.schema.json"
	)
	
	try:
		with open(schema_path, "r") as f:
			schema = json.load(f)
	except Exception as e:
		return False, [f"Failed to load lesson schema: {str(e)}"]
	
	try:
		jsonschema.validate(instance=lesson, schema=schema)
		return True, []
	except jsonschema.ValidationError as e:
		return False, [str(e)]
	except Exception as e:
		return False, [f"Schema validation error: {str(e)}"]

def get_content_paths_for_plan(plan_name):
	"""
	Generate all file paths that need to be generated for a plan.

	Args:
		plan_name (str): Plan document name

	Returns:
		dict: Dictionary of {path: data} for all CDN files
	"""
	import frappe
	
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
		# order_by="sort_order"
		order_by="subject"  # sort_by commented out, using name as fallback
	)

	subject_ids = [ps.subject for ps in plan_subjects]
	subjects = frappe.get_all(
		"Memora Subject",
		filters={"name": ["in", subject_ids]},
		# fields=["name", "title", "description", "is_published", "sort_order"]
		fields=["name", "title", "description", "is_published"]  # "sort_order" commented out
	)
	subjects_dict = {s.name: s for s in subjects}

	frappe.log_error(
		f"[INFO] Plan {plan_name}: Found {len(subjects)} subjects",
		"CDN JSON Generation"
	)

	tracks = frappe.get_all(
		"Memora Track",
		filters={"parent_subject": ["in", subject_ids]},
		# fields=["name", "title", "description", "sort_order", "is_sold_separately", "parent_item_required", "parent_subject"]
		fields=["name", "title", "description", "is_sold_separately", "parent_item_required", "parent_subject"]  # "sort_order" commented out
	)

	track_ids = [track.name for track in tracks]
	units = frappe.get_all(
		"Memora Unit",
		filters={"parent_track": ["in", track_ids]},
		# fields=["name", "title", "description", "sort_order", "parent_track"]
		fields=["name", "title", "description", "parent_track"]  # "sort_order" commented out
	)

	unit_ids = [unit.name for unit in units]
	topics = frappe.get_all(
		"Memora Topic",
		filters={"parent_unit": ["in", unit_ids]},
		# fields=["name", "title", "description", "sort_order", "parent_unit"]
		fields=["name", "title", "description", "parent_unit"]  # "sort_order" commented out
	)

	topic_ids = [topic.name for topic in topics]
	lessons = frappe.get_all(
		"Memora Lesson",
		filters={"parent_topic": ["in", topic_ids]},
		# fields=["name", "title", "description", "sort_order", "is_free_preview", "is_published",  "parent_topic"]
		fields=["name", "title", "description", "is_free_preview", "is_published", "parent_topic"]  # "sort_order" commented out
	)

	skipped_subjects = 0
	for ps in plan_subjects:
		subject = subjects_dict.get(ps.subject)
		if not subject:
			continue

		subject_data = generate_subject_json(subject, plan_id=plan_name)
		if subject_data is None:
			skipped_subjects += 1
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

	frappe.log_error(
		f"[INFO] Plan {plan_name}: Generated {len(all_files)} files (skipped {skipped_subjects} subjects due to access level)",
		"CDN JSON Generation"
	)

	for path, data in all_files.items():
		from .local_storage import write_content_file
		success, error = write_content_file(path, data)
		if not success:
			frappe.log_error(f"Failed to write local file {path}: {error}", "CDN JSON Generation")

	return all_files


def generate_bitmap_json(subject_doc):
	"""
	Generate subject bitmap JSON with lesson → bit_index mappings (Phase 7: User Story 5).
	
	The bitmap file maps each lesson in a subject to its bit_index in the progress engine,
	enabling efficient progress tracking via bitmaps. This file is shared across plans.
	
	Args:
		subject_doc (frappe.doc): Memora Subject document
	
	Returns:
		dict: Bitmap data conforming to subject_bitmap.schema.json
	"""
	import frappe
	
	# Get all tracks for this subject
	tracks = frappe.get_all(
		"Memora Track",
		filters={"parent_subject": subject_doc.name},
		fields=["name"]
	)
	
	track_ids = [t.name for t in tracks]
	
	# Get all units for these tracks
	units = frappe.get_all(
		"Memora Unit",
		filters={"parent_track": ["in", track_ids]},
		fields=["name"]
	)
	
	unit_ids = [u.name for u in units]
	
	# Get all topics for these units
	topics = frappe.get_all(
		"Memora Topic",
		filters={"parent_unit": ["in", unit_ids]},
		fields=["name"]
	)
	
	topic_ids = [t.name for t in topics]
	
	# Get all lessons for these topics (ordered by creation/index)
	lessons = frappe.get_all(
		"Memora Lesson",
		filters={"parent_topic": ["in", topic_ids], "docstatus": 1},  # Only submitted lessons
		fields=["name", "parent_topic"],
		order_by="creation"
	)
	
	# Build bitmap with bit_index for each lesson
	bitmap_data = {
		"subject_id": subject_doc.name,
		"version": int(now_datetime().timestamp()),
		"generated_at": now_datetime().isoformat(),
		"total_lessons": len(lessons),
		"mappings": {}
	}
	
	for idx, lesson in enumerate(lessons):
		bitmap_data["mappings"][lesson.name] = {
			"bit_index": idx,
			"topic_id": lesson.parent_topic
		}
	
	# Validate against schema
	is_valid, errors = validate_subject_bitmap_against_schema(bitmap_data)
	if not is_valid:
		frappe.log_error(
			f"Generated bitmap JSON for {subject_doc.name} failed schema validation: {errors}",
			"CDN JSON Generation"
		)
	
	frappe.log_error(
		f"[INFO] Generated bitmap JSON for {subject_doc.name} with {len(lessons)} lessons",
		"CDN JSON Generation"
	)
	
	return bitmap_data


def validate_subject_bitmap_against_schema(bitmap_data):
	"""
	Validate bitmap JSON against subject_bitmap.schema.json.
	
	Args:
		bitmap_data (dict): Bitmap JSON to validate
	
	Returns:
		tuple: (is_valid, errors) where errors is list of validation errors
	"""
	try:
		import jsonschema
		
		schema_path = os.path.join(SCHEMA_DIR, "subject_bitmap.schema.json")
		with open(schema_path, "r") as f:
			schema = json.load(f)
		
		jsonschema.validate(bitmap_data, schema)
		return True, []
	except Exception as e:
		return False, [str(e)]


def get_atomic_content_paths_for_plan(plan_name):
	"""
	Get all atomic file paths that need to be generated for a plan (Phase 7: User Story 5).
	
	Returns structured path information for all atomic files: manifest, hierarchies,
	bitmaps, topics, and shared lessons.
	
	Args:
		plan_name (str): Plan document name
	
	Returns:
		dict: Structure with paths for {manifest, hierarchies, bitmaps, topics, lessons}
	"""
	import frappe
	
	# Get all plan subjects
	plan_subjects = frappe.get_all(
		"Memora Academic Plan Subject",
		filters={"parent": plan_name},
		fields=["subject"]
	)
	
	subject_ids = [ps.subject for ps in plan_subjects]
	
	# Get all topics for these subjects (via tracks → units)
	tracks = frappe.get_all(
		"Memora Track",
		filters={"parent_subject": ["in", subject_ids]},
		fields=["name"]
	)
	
	track_ids = [t.name for t in tracks]
	
	units = frappe.get_all(
		"Memora Unit",
		filters={"parent_track": ["in", track_ids]},
		fields=["name"]
	)
	
	unit_ids = [u.name for u in units]
	
	topics = frappe.get_all(
		"Memora Topic",
		filters={"parent_unit": ["in", unit_ids]},
		fields=["name"]
	)
	
	topic_ids = [t.name for t in topics]
	
	# Get all lessons
	lessons = frappe.get_all(
		"Memora Lesson",
		filters={"parent_topic": ["in", topic_ids], "docstatus": 1},
		fields=["name"]
	)
	
	lesson_ids = [l.name for l in lessons]
	
	# Build paths dictionary
	paths = {
		"manifest": f"plans/{plan_name}/manifest.json",
		"hierarchies": [f"plans/{plan_name}/{subj}_h.json" for subj in subject_ids],
		"bitmaps": [f"plans/{plan_name}/{subj}_b.json" for subj in subject_ids],
		"topics": [f"plans/{plan_name}/{t}.json" for t in topic_ids],
		"lessons": [f"lessons/{l}.json" for l in lesson_ids]
	}
	
	return paths
