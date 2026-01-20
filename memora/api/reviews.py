"""
Review Session Domain Module

This module handles review session generation and submission for SRS.
"""

import frappe
import json
import random
from frappe import _
from frappe.utils import add_days, now_datetime, cint, getdate, nowdate
from ..ai_engine import get_ai_distractors
from .srs import update_srs_after_review
from .leaderboard import update_subject_progression
from .utils import SafeModeManager


def get_active_season():
	"""
	Get the currently active season for SRS

	Returns:
		str: Season name or None if no active season
	"""
	season = frappe.db.get_value(
		"Game Subscription Season",
		{"is_active": 1, "enable_redis": 1},
		"season_name"
	)
	return season


def get_reviews_safe_mode(user: str, season: str, subject: str = None, limit: int = 10):
	"""
	Safe Mode fallback query for retrieving due reviews

	This function provides a lightweight indexed query for degraded mode when Redis is unavailable.
	It limits results to prevent database overload.

	Args:
		user: User email or ID
		season: Season name
		subject: Optional subject filter
		limit: Maximum number of items to return (default 10)

	Returns:
		List[dict]: List of due review items with question_id, next_review_date, stability
	"""
	try:
		# Build query conditions
		conditions = ["player = %s", "next_review_date <= NOW()"]
		params = [user]
		
		# CRITICAL FIX: Add season filter (T029)
		if season:
			conditions.append("season = %s")
			params.append(season)

		if subject:
			conditions.append("subject = %s")
			params.append(subject)

		# Execute Safe Mode query with limit
		query = f"""
			SELECT question_id, next_review_date, stability, subject
			FROM `tabPlayer Memory Tracker`
			WHERE {' AND '.join(conditions)}
			ORDER BY next_review_date ASC
			LIMIT %s
		"""
		params.append(limit)

		results = frappe.db.sql(query, tuple(params), as_dict=True)
		return results

	except Exception as e:
		frappe.log_error(
			f"Safe Mode query failed: {str(e)}",
			"get_reviews_safe_mode"
		)
		return []


def get_mastery_counts(user):
    """
    Helper function to update UI.

    Args:
        user: User ID

    Returns:
        Dictionary with mastery counts by stability level
    """
    data = frappe.db.sql("""
        SELECT stability, COUNT(*) as count
        FROM `tabPlayer Memory Tracker`
        WHERE player = %s GROUP BY stability
    """, (user,), as_dict=True)
    mastery_map = {row.stability: row.count for row in data}
    return {
        "new": mastery_map.get(1, 0),
        "learning": mastery_map.get(2, 0),
        "mature": mastery_map.get(3, 0) + mastery_map.get(4, 0)
    }


@frappe.whitelist()
def get_review_session(subject=None, topic_id=None):
    """
    Get smart review session with quiz cards.

    Features:
    1. Redis cache for <100ms response time (T028)
    2. Safe Mode fallback with rate limiting (T029)
    3. Focus mode support (Topic Focus) with dynamic size.
    4. Exclude questions solved today (Smart Filtering).
    5. Self-healing for corrupt data (Self-Healing).
    6. Use AI to generate distractors for quiz cards.

    Args:
        subject: Optional subject filter
        topic_id: Optional topic filter for focus mode

    Returns:
        Dict with quiz cards and degradation status
        {
            "questions": [...],
            "is_degraded": bool,
            "season": str
        }
    """
    try:
        user = frappe.session.user

        # =========================================================
        # Redis Integration & Safe Mode (T028, T029, T030)
        # =========================================================

        # Initialize Safe Mode Manager
        safe_mode = SafeModeManager()
        is_degraded = False
        season = get_active_season()

        # Only use Redis for general review (not topic-specific)
        if not topic_id and season:
            # Check if Safe Mode is active
            if safe_mode.is_safe_mode_active():
                # Safe Mode: Check rate limit first
                if not safe_mode.check_rate_limit(user):
                    frappe.throw(
                        _("Too many requests. Please wait 30 seconds before trying again."),
                        exc=frappe.ValidationError,
                        title=_("Rate Limit Exceeded")
                    )

                # Use Safe Mode fallback query
                safe_mode_items = get_reviews_safe_mode(user, season, subject, limit=15)

                if safe_mode_items:
                    # Convert Safe Mode items to due_items format
                    due_items = safe_mode_items
                    is_degraded = True
                else:
                    due_items = []
            else:
                # Normal Mode: Use Redis cache
                try:
                    from memora.services.srs_redis_manager import SRSRedisManager
                    redis_manager = SRSRedisManager()

                    # Get due items from Redis with rehydration
                    redis_items, was_rehydrated = redis_manager.get_due_items_with_rehydration(
                        user, season, limit=15
                    )

                    if redis_items:
                        # Redis hit - fetch full records from DB for filtering
                        # Use frappe.get_all for clean parameterized queries
                        filters = {
                            "player": user,
                            "question_id": ["in", redis_items],
                            "season": season
                        }

                        if subject:
                            # Add subject filter for better performance
                            filters["subject"] = subject

                        due_items = frappe.get_all(
                            "Player Memory Tracker",
                            filters=filters,
                            fields=["name", "question_id", "stability"],
                            order_by="next_review_date asc",
                            limit=15
                        )
                    else:
                        # No items in cache/DB
                        due_items = []
                except Exception as e:
                    frappe.log_error(
                        f"Redis retrieval failed, falling back to DB: {str(e)}",
                        "get_review_session"
                    )
                    # Fallback to DB query
                    due_items = []
                    is_degraded = True
        else:
            # Topic-specific or no season - use original DB logic
            due_items = None
            is_degraded = False

        limit = 15  # Default limit for general review

        # =========================================================
        # 1. Fetch Candidate Items (Fetch Candidates)
        # =========================================================

        # A. Topic-specific review (Focus Mode) 🎯
        if topic_id:
            # Calculate appropriate size
            total_items = frappe.db.count("Player Memory Tracker", {"player": user, "topic": topic_id})
            if total_items == 0:
                return {"questions": [], "is_degraded": False, "season": season or ""}

            calculated_limit = int(total_items * 0.10)
            limit = max(10, min(calculated_limit, 30))

            # Smart query: fetch (wrong) or (old). Exclude (new correct).
            due_items = frappe.db.sql("""
                SELECT name, question_id, stability
                FROM `tabPlayer Memory Tracker`
                WHERE player = %s
                AND topic = %s
                AND (
                    stability = 1
                    OR
                    last_review_date < CURDATE()
                )
                ORDER BY stability ASC, last_review_date ASC
                LIMIT %s
            """, (user, topic_id, limit), as_dict=True)

            # Fallback plan: If list is empty (finished topic today), fetch random
            if not due_items and total_items > 0:
                due_items = frappe.db.sql("""
                    SELECT name, question_id, stability
                    FROM `tabPlayer Memory Tracker`
                    WHERE player = %s AND topic = %s
                    ORDER BY RAND()
                    LIMIT 10
                """, (user, topic_id), as_dict=True)

        # B. General review (Daily Mix) 📅 - only if not already fetched from Redis
        elif due_items is None:
            conditions = ["player = %s", "next_review_date <= NOW()"]
            params = [user]
            
            if subject:
                conditions.append("subject = %s")
                params.append(subject)
            
            # Apply Season Filter for DB query too
            if season:
                conditions.append("season = %s")
                params.append(season)

            due_items = frappe.db.sql(f"""
                SELECT name, question_id, stability
                FROM `tabPlayer Memory Tracker`
                WHERE {' AND '.join(conditions)}
                ORDER BY next_review_date ASC
                LIMIT 15
            """, tuple(params), as_dict=True)

        if not due_items:
            return {"questions": [], "is_degraded": is_degraded, "season": season or ""}

        quiz_cards = []
        corrupt_tracker_ids = []
        lesson_cache = {}  # Cache to avoid fetching same lesson repeatedly

        # =========================================================
        # 2. Process Cards (Processing Cards)
        # =========================================================
        for item in due_items:
            raw_id = item.question_id

            # A. Parse ID (ID Parsing)
            if ":" in raw_id:
                parts = raw_id.rsplit(":", 1)
                stage_row_name = parts[0]
                try: target_atom_index = int(parts[1])
                except: target_atom_index = None
            else:
                stage_row_name = raw_id
                target_atom_index = None

            # B. Safe Lookup (Safe Lookup) 🔥
            stage_data = None
            try:
                stage_data = frappe.db.get_value("Game Stage", stage_row_name,
                    ["config", "type", "parent"], as_dict=True)
            except Exception:
                stage_data = None

            if not stage_data:
                corrupt_tracker_ids.append(item.name)
                continue

            # C. Verify lesson
            lesson_id = stage_data.parent
            if lesson_id not in lesson_cache:
                lesson_doc = frappe.get_doc("Game Lesson", lesson_id)
                if not lesson_doc.is_published:
                    corrupt_tracker_ids.append(item.name)
                    continue
                lesson_cache[lesson_id] = lesson_doc

            lesson_doc = lesson_cache[lesson_id]
            config = frappe.parse_json(stage_data.config)

            # =====================================================
            # D. Convert REVEAL -> QUIZ
            # =====================================================
            if stage_data.type == 'Reveal':
                highlights = config.get('highlights', [])

                # 1. Gather local inventory (backup option)
                local_distractor_pool = []
                for s in lesson_doc.stages:
                    if s.type == 'Reveal':
                        s_conf = frappe.parse_json(s.config) if s.config else {}
                        for h in s_conf.get('highlights', []):
                            local_distractor_pool.append(h['word'])

                for idx, highlight in enumerate(highlights):
                    if target_atom_index is not None and target_atom_index != idx:
                        continue

                    correct_word = highlight['word']
                    question_text = config.get('sentence', '').replace(correct_word, "____")

                    # 🤖 AI attempt
                    selected_distractors = []
                    # Ensure get_ai_distractors function exists in file
                    ai_options = get_ai_distractors("reveal", correct_word, config.get('sentence', ''))

                    if ai_options and len(ai_options) >= 3:
                        selected_distractors = ai_options[:3]
                    else:
                        # Fallback: Use local inventory
                        distractors = [w for w in local_distractor_pool if w != correct_word]
                        distractors = list(set(distractors))
                        random.shuffle(distractors)
                        selected_distractors = distractors[:3]
                        while len(selected_distractors) < 3: selected_distractors.append("...")

                    options = selected_distractors + [correct_word]
                    random.shuffle(options)

                    atom_id = f"{stage_row_name}:{idx}"

                    quiz_cards.append({
                        "id": atom_id,
                        "type": "quiz",
                        "question": question_text,
                        "correct_answer": correct_word,
                        "options": options,
                        "origin_type": "reveal"
                    })

            # =====================================================
            # E. Convert MATCHING -> QUIZ
            # =====================================================
            elif stage_data.type == 'Matching':
                pairs = config.get('pairs', [])

                for idx, pair in enumerate(pairs):
                    if target_atom_index is not None and target_atom_index != idx:
                        continue

                    question_text = pair.get('right')
                    correct_answer = pair.get('left')

                    # 🤖 AI attempt
                    selected_distractors = []
                    ai_options = get_ai_distractors("matching", correct_answer, question_text)

                    if ai_options and len(ai_options) >= 3:
                        selected_distractors = ai_options[:3]
                    else:
                        # Fallback: Use other options in same question
                        distractors = [p.get('left') for p in pairs if p.get('left') != correct_answer]
                        random.shuffle(distractors)
                        selected_distractors = distractors[:3]
                        while len(selected_distractors) < 3: selected_distractors.append("...")

                    options = selected_distractors + [correct_answer]
                    random.shuffle(options)

                    atom_id = f"{stage_row_name}:{idx}"

                    quiz_cards.append({
                        "id": atom_id,
                        "type": "quiz",
                        "question": f"ما هو المرادف لـ: {question_text}؟",
                        "correct_answer": correct_answer,
                        "options": options,
                        "origin_type": "matching"
                    })

        # =========================================================
        # 3. Cleanup and Return
        # =========================================================
        if corrupt_tracker_ids:
            # Delete old data silently
            frappe.db.delete("Player Memory Tracker", {"name": ["in", corrupt_tracker_ids]})

        random.shuffle(quiz_cards)
        return {
            "questions": quiz_cards[:limit],
            "is_degraded": is_degraded,
            "season": season or ""
        }

    except Exception as e:
        frappe.log_error("Get Review Session Failed", frappe.get_traceback())
        return {
            "questions": [],
            "is_degraded": False,
            "season": ""
        }


@frappe.whitelist()
def submit_review_session(session_data):
    """
    Submit review session results.
    """
    try:
        user = frappe.session.user
        season = get_active_season()

        if isinstance(session_data, str): data = json.loads(session_data)
        else: data = session_data

        interactions = data.get('answers', [])
        session_meta = data.get('session_meta', {})
        total_combo = data.get('total_combo', 0)
        completion_time_ms = data.get('completion_time_ms', 0)

        current_subject = session_meta.get('subject')
        current_topic = session_meta.get('topic')

        # Calculate rewards
        correct_count = sum(1 for item in interactions if item.get('is_correct'))
        max_combo = int(total_combo)
        total_xp = (correct_count * 10) + (max_combo * 2)

        # =========================================================
        # Phase 4: Redis Integration & Async Persistence (T038, T039, T040)
        # =========================================================

        # Prepare responses for background persistence
        persistence_responses = []
        redis_manager = None

        # Initialize Redis manager if season is active
        if season:
            try:
                from memora.services.srs_redis_manager import SRSRedisManager
                redis_manager = SRSRedisManager()
            except Exception as e:
                frappe.log_error(
                    f"Failed to initialize Redis manager: {str(e)}",
                    "submit_review_session"
                )
                redis_manager = None

        # Update memory for each interaction
        for item in interactions:
            question_id = item.get('question_id')
            is_correct = item.get('is_correct')
            duration = item.get('time_spent_ms') or item.get('duration_ms') or 3000

            if question_id:
                # Calculate new SRS schedule
                new_stability, new_next_review_date = _calculate_new_srs_schedule(
                    user, question_id, is_correct, duration, season
                )

                # T038: Update Redis synchronously (for instant confirmation)
                if redis_manager and redis_manager.is_available():
                    try:
                        redis_manager.add_item(
                            user,
                            season,
                            question_id,
                            new_next_review_date.timestamp()
                        )
                    except Exception as e:
                        frappe.log_error(
                            f"Failed to update Redis for {question_id}: {str(e)}",
                            "submit_review_session.redis_update"
                        )

                # Prepare for async DB persistence
                persistence_responses.append({
                    "question_id": question_id,
                    "quality": 4 if is_correct and duration < 2000 else (3 if is_correct else 1),
                    "response_time_ms": duration,
                    "new_stability": new_stability,
                    "new_next_review_date": new_next_review_date,
                    "subject": current_subject,
                    "topic": current_topic
                })

        # T039: Queue background job for async DB persistence
        persistence_job_id = None
        if persistence_responses and season:
            try:
                job = frappe.enqueue(
                    "memora.services.srs_persistence.persist_review_batch",
                    queue="srs_write",  # CRITICAL: Use the dedicated queue
                    job_name=f"srs_persist_{user}_{now_datetime().strftime('%Y%m%d_%H%M%S')}",
                    responses=persistence_responses,
                    user=user,
                    season=season,
                    is_async=True,
                    timeout=300
                )
                persistence_job_id = job.id if job else None
            except Exception as e:
                frappe.log_error(
                    f"Failed to enqueue persistence job: {str(e)}",
                    "submit_review_session.enqueue"
                )

        # Log session
        full_log_data = {
            "meta": session_meta,
            "interactions": interactions,
            "stats": {"correct": correct_count, "combo": max_combo, "time_ms": completion_time_ms}
        }

        doc = frappe.get_doc({
            "doctype": "Gameplay Session",
            "player": user,
            "lesson": "مراجعة الذاكرة",
            "xp_earned": total_xp,
            "score": total_xp,
            "raw_data": json.dumps(full_log_data, ensure_ascii=False)
        })
        doc.insert(ignore_permissions=True)

        # Updates
        if total_xp > 0:
            frappe.db.sql("UPDATE `tabPlayer Profile` SET total_xp = total_xp + %s WHERE user = %s", (total_xp, user))
            if current_subject:
                update_subject_progression(user, current_subject, total_xp)

        frappe.db.commit()

        # Calculate remaining (Netflix Effect)
        remaining_count = 0
        if current_topic:
            remaining_count = frappe.db.sql("""
                SELECT COUNT(*) FROM `tabPlayer Memory Tracker`
                WHERE player = %s
                AND topic = %s
                AND (stability = 1 OR last_review_date < CURDATE())
            """, (user, current_topic))[0][0]

        # T040: Return persistence_job_id in response
        response_data = {
            "status": "success",
            "processed": len(interactions),
            "xp_earned": total_xp,
            "remaining_items": remaining_count,
            "new_stability_counts": get_mastery_counts(user)
        }

        if persistence_job_id:
            response_data["persistence_job_id"] = persistence_job_id

        return response_data

    except Exception as e:
        frappe.log_error("Submit Review Failed", frappe.get_traceback())
        return {"status": "error", "message": str(e)}


def _calculate_new_srs_schedule(user, question_id, is_correct, duration_ms, season=None):
    """
    Calculate new SRS schedule for a question without updating DB
    """
    filters = {"player": user, "question_id": question_id}
    if season:
        filters["season"] = season

    stability_value = frappe.db.get_value("Player Memory Tracker", filters, "stability")
    current_stability = cint(stability_value) if stability_value else 0

    new_stability = current_stability
    if is_correct:
        if duration_ms < 2000:
            new_stability = min(current_stability + 2, 4)
        elif duration_ms > 6000:
            new_stability = max(current_stability, 1)
        else:
            new_stability = min(current_stability + 1, 4)
        if new_stability < 1:
            new_stability = 1
    else:
        new_stability = 1

    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days_to_add = interval_map.get(new_stability, 1)
    new_next_review_date = add_days(now_datetime(), days_to_add)

    return new_stability, new_next_review_date