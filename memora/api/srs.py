"""
SRS/Memory Algorithms Module

This module implements Spaced Repetition System algorithms for memory tracking.
All functions in this module are internal helpers (not public API).
"""

import frappe
from frappe.utils import add_days, now_datetime, cint


def process_srs_batch(user, interactions, subject=None, topic=None):
    """
    Process a batch of interactions to update memory.

    Receives 'subject' to pass to the final function.

    Args:
        user: User ID
        interactions: List of interaction objects
        subject: Optional subject ID
        topic: Optional topic ID
    """
    for item in interactions:
        atom_id = item.get("question_id")
        if not atom_id: continue
        duration = item.get("duration_ms", item.get("time_spent_ms", 3000))
        attempts = item.get("attempts_count", 1)
        rating = infer_rating(duration, attempts)
        next_review_date = calculate_next_review(rating)

        # ✅ Pass topic
        update_memory_tracker(user, atom_id, rating, next_review_date, subject, topic)


def infer_rating(duration_ms, attempts):
    """
    Logic: Converts Time + Accuracy into a Memory Score.

    Ratings:
    1 = AGAIN (Fail) - Wrong answer, needs immediate drill.
    2 = HARD         - Correct but slow (> 5s).
    3 = GOOD         - Correct and steady (2s - 5s).
    4 = EASY         - Correct and instant (< 2s).
    """
    # If the user made a mistake (attempts > 1), it's a FAIL regardless of time.
    if attempts > 1:
        return 1

    # If correct on first try, judge by speed:
    if duration_ms < 2000:  # Less than 2 seconds
        return 4  # EASY

    if duration_ms < 5000:  # Less than 5 seconds
        return 3  # GOOD

    # More than 5 seconds
    return 2  # HARD


def calculate_next_review(rating):
    """
    Logic: Determines how many days to wait before the next review.

    Current Protocol (Fixed Intervals):
    1 (Fail) -> 0 Days (Review Tomorrow/ASAP)
    2 (Hard) -> 2 Days
    3 (Good) -> 4 Days
    4 (Easy) -> 7 Days
    """
    interval_map = {
        1: 0,  # Fail: Reset
        2: 2,  # Hard
        3: 4,  # Good
        4: 7   # Easy
    }

    days_to_add = interval_map.get(rating, 1)  # Default to 1 day if error

    # Return the actual DateTime object
    return add_days(now_datetime(), days_to_add)


def update_memory_tracker(user, atom_id, rating, next_date, subject=None, topic=None):
    """
    Update or create memory tracker record for a question.

    Args:
        user: User ID
        atom_id: Question ID
        rating: Memory score (1-4)
        next_date: Next review datetime
        subject: Optional subject ID
        topic: Optional topic ID
    """
    existing_tracker = frappe.db.get_value("Player Memory Tracker",
        {"player": user, "question_id": atom_id}, "name")

    values = {
        "stability": rating,
        "last_review_date": now_datetime(),
        "next_review_date": next_date
    }
    if subject: values["subject"] = subject
    if topic: values["topic"] = topic  # ✅ Save topic on update

    if existing_tracker:
        frappe.db.set_value("Player Memory Tracker", existing_tracker, values)
    else:
        doc = frappe.get_doc({
            "doctype": "Player Memory Tracker",
            "player": user,
            "question_id": atom_id,
            "subject": subject,
            "topic": topic,  # ✅ Save topic on creation
            "stability": rating,
            "last_review_date": now_datetime(),
            "next_review_date": next_date
        })
        doc.insert(ignore_permissions=True)


def create_memory_tracker(user, atom_id, rating):
    """
    Create a new memory tracker record for a question.

    Called when student sees the question for the first time,
    or when discovering a new ID.

    Args:
        user: User ID
        atom_id: Question ID
        rating: Initial memory score (1-4)

    Returns:
        Name of created tracker record
    """
    # Determine next review date based on initial rating
    # 1: tomorrow, 2: 3 days, 3: week, 4: 2 weeks
    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days = interval_map.get(rating, 1)  # Default to one day

    doc = frappe.get_doc({
        "doctype": "Player Memory Tracker",
        "player": user,
        "question_id": atom_id,  # Ensure this matches the DocType field name
        "stability": rating,
        "last_review_date": now_datetime(),
        "next_review_date": add_days(now_datetime(), days)
    })

    doc.insert(ignore_permissions=True)
    return doc.name


def update_srs_after_review(user, question_id, is_correct, duration_ms, subject=None, topic=None):
    """
    Update memory tracker status after review session.

    Fixed variable count (added topic) and removed duplicate logic.

    Args:
        user: User ID
        question_id: Question ID
        is_correct: Whether answer was correct
        duration_ms: Time taken to answer
        subject: Optional subject ID
        topic: Optional topic ID
    """
    # 1. Fetch current record
    tracker_name = frappe.db.get_value("Player Memory Tracker",
        {"player": user, "question_id": question_id}, "name")

    current_stability = 0
    if tracker_name:
        current_stability = cint(frappe.db.get_value("Player Memory Tracker", tracker_name, "stability"))

    # 2. Rating algorithm (Speed Bonus)
    new_stability = current_stability

    if is_correct:
        if duration_ms < 2000:
            new_stability = min(current_stability + 2, 4)  # Very fast
        elif duration_ms > 6000:
            new_stability = max(current_stability, 1)  # Slow
        else:
            new_stability = min(current_stability + 1, 4)  # Normal

        if new_stability < 1: new_stability = 1
    else:
        new_stability = 1  # Error

    # 3. Calculate next date
    interval_map = {1: 1, 2: 3, 3: 7, 4: 14}
    days_to_add = interval_map.get(new_stability, 1)
    new_date = add_days(now_datetime(), days_to_add)

    # 4. Storage (once and correctly)
    # Pass topic to helper function
    update_memory_tracker(user, question_id, new_stability, new_date, subject, topic)

    # 5. Cleanup parent records
    if ":" in question_id:
        parent_id = question_id.rsplit(":", 1)[0]
        parent_tracker = frappe.db.get_value("Player Memory Tracker",
            {"player": user, "question_id": parent_id}, "name")

        if parent_tracker:
            frappe.db.set_value("Player Memory Tracker", parent_tracker,
                "next_review_date", new_date)
