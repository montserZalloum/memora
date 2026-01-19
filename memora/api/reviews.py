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
    1. Focus mode support (Topic Focus) with dynamic size.
    2. Exclude questions solved today (Smart Filtering).
    3. Self-healing for corrupt data (Self-Healing).
    4. Use AI to generate distractors for quiz cards.

    Args:
        subject: Optional subject filter
        topic_id: Optional topic filter for focus mode

    Returns:
        List of quiz cards
    """
    try:
        user = frappe.session.user
        import random

        limit = 15  # Default limit for general review

        # =========================================================
        # 1. Fetch Candidate Items (Fetch Candidates)
        # =========================================================

        # A. Topic-specific review (Focus Mode) 🎯
        if topic_id:
            # Calculate appropriate size
            total_items = frappe.db.count("Player Memory Tracker", {"player": user, "topic": topic_id})
            if total_items == 0: return []

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

        # B. General review (Daily Mix) 📅
        else:
            conditions = "player = %s AND next_review_date <= NOW()"
            params = [user]
            if subject:
                conditions += " AND subject = %s"
                params.append(subject)

            due_items = frappe.db.sql(f"""
                SELECT name, question_id, stability
                FROM `tabPlayer Memory Tracker`
                WHERE {conditions}
                ORDER BY next_review_date ASC
                LIMIT 15
            """, tuple(params), as_dict=True)

        if not due_items: return []

        quiz_cards = []
        corrupt_tracker_ids = []
        lesson_cache = {}  # Cache to avoid fetching same lesson repeatedly

        # =========================================================
        # 2. Process Cards (Processing Cards)
        # =========================================================
        for item in due_items:
            raw_id = item.question_id

            # أ. Parse ID (ID Parsing)
            if ":" in raw_id:
                parts = raw_id.rsplit(":", 1)
                stage_row_name = parts[0]
                try: target_atom_index = int(parts[1])
                except: target_atom_index = None
            else:
                stage_row_name = raw_id
                target_atom_index = None

            # ب. Safe Lookup (Safe Lookup) 🔥
            stage_data = None
            try:
                stage_data = frappe.db.get_value("Game Stage", stage_row_name,
                    ["config", "type", "parent"], as_dict=True)
            except Exception:
                stage_data = None

            if not stage_data:
                corrupt_tracker_ids.append(item.name)
                continue

            # ج. Verify lesson
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
            # د. Convert REVEAL -> QUIZ
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
            # هـ. Convert MATCHING -> QUIZ
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
        return quiz_cards[:limit]

    except Exception as e:
        frappe.log_error("Get Review Session Failed", frappe.get_traceback())
        return []


@frappe.whitelist()
def submit_review_session(session_data):
    """
    Submit review session results.

    Updates SRS memory tracking and awards XP.
    Calculates remaining items for Netflix effect.

    Args:
        session_data: Session data with answers and metadata

    Returns:
        Response with XP earned and remaining items
    """
    try:
        user = frappe.session.user

        if isinstance(session_data, str): data = json.loads(session_data)
        else: data = session_data

        interactions = data.get('answers', [])
        session_meta = data.get('session_meta', {})
        total_combo = data.get('total_combo', 0)
        completion_time_ms = data.get('completion_time_ms', 0)

        current_subject = session_meta.get('subject')
        current_topic = session_meta.get('topic')  # ✅

        # Calculate rewards
        correct_count = sum(1 for item in interactions if item.get('is_correct'))
        max_combo = int(total_combo)
        total_xp = (correct_count * 10) + (max_combo * 2)

        # Update memory
        for item in interactions:
            question_id = item.get('question_id')
            is_correct = item.get('is_correct')
            duration = item.get('time_spent_ms') or item.get('duration_ms') or 3000

            if question_id:
                # ✅ Fix here: we pass topic to corrected function
                update_srs_after_review(user, question_id, is_correct, duration, current_subject, current_topic)

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

        return {
            "status": "success",
            "xp_earned": total_xp,
            "remaining_items": remaining_count,
            "new_stability_counts": get_mastery_counts(user)
        }

    except Exception as e:
        frappe.log_error("Submit Review Failed", frappe.get_traceback())
        return {"status": "error", "message": str(e)}
