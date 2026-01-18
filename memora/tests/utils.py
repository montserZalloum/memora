"""
Test Utilities for Memora App

This module provides helper functions for creating test data, simulating user actions,
and verifying test results.

Functions are organized into the following categories:
- User & Profile Helpers: Create test users and player profiles
- Academic Structure Helpers: Create grades, streams, subjects, units, lessons
- Subscription Helpers: Create seasons and subscriptions
- Session & SRS Helpers: Submit sessions, create memory trackers
- Verification Helpers: Verify XP, session counts, stability levels
- Cleanup Helpers: Remove test data after tests
"""

import frappe
from frappe.utils import now_datetime, add_days, getdate, nowdate
import random
import json


# ============================================================
# USER & PROFILE HELPERS
# ============================================================

def create_test_user(email=None, first_name="Test", password="test123"):
    """
    Create a test user account.

    Args:
        email: User email (auto-generated if None)
        first_name: User's first name
        password: User password

    Returns:
        str: User email (user ID)
    """
    if not email:
        email = f"test_{random.randint(1000, 9999)}@memora.test"

    if frappe.db.exists("User", email):
        return email

    # Use SQL insert to bypass hooks that cause issues in tests
    frappe.db.sql("""
        INSERT INTO `tabUser`
        (name, email, first_name, enabled, user_type, send_welcome_email, creation, modified, owner, modified_by, docstatus)
        VALUES (%s, %s, %s, 1, 'Website User', 0, NOW(), NOW(), 'Administrator', 'Administrator', 0)
    """, (email, email, first_name))

    frappe.db.commit()

    return email


def create_test_player(email=None, grade=None, stream=None,
                       academic_year="2025", total_xp=0):
    """
    Create a Player Profile for testing.

    Args:
        email: User email (creates user if needed)
        grade: Link to Game Academic Grade
        stream: Link to Game Academic Stream (optional)
        academic_year: Academic year string
        total_xp: Initial XP value

    Returns:
        dict: {user: email, profile_name: profile_doc_name}
    """
    if not email:
        email = create_test_user()
    else:
        # Ensure user exists
        if not frappe.db.exists("User", email):
            create_test_user(email=email)

    # Check if profile already exists
    existing = frappe.db.get_value("Player Profile", {"user": email}, "name")
    if existing:
        return {"user": email, "profile_name": existing}

    profile = frappe.get_doc({
        "doctype": "Player Profile",
        "user": email,
        "current_grade": grade,
        "current_stream": stream,
        "academic_year": academic_year,
        "total_xp": total_xp,
        "gems_balance": 0
    })
    profile.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"user": email, "profile_name": profile.name}


# ============================================================
# ACADEMIC STRUCTURE HELPERS
# ============================================================

def create_test_grade(grade_name=None, valid_streams=None):
    """
    Create a test academic grade.

    Args:
        grade_name: Grade name (e.g., "Grade-10", "Tawjihi")
        valid_streams: List of stream names that are valid for this grade

    Returns:
        str: Grade name (document name)
    """
    if not grade_name:
        grade_name = f"Grade-{random.randint(1, 12)}"

    if frappe.db.exists("Game Academic Grade", grade_name):
        return grade_name

    grade = frappe.get_doc({
        "doctype": "Game Academic Grade",
        "grade_name": grade_name,
        "valid_streams": []
    })

    # Add valid streams if provided
    if valid_streams:
        for stream_name in valid_streams:
            # Ensure stream exists
            if not frappe.db.exists("Game Academic Stream", stream_name):
                create_test_stream(stream_name)

            grade.append("valid_streams", {
                "stream": stream_name
            })

    grade.insert(ignore_permissions=True)
    frappe.db.commit()

    return grade_name


def create_test_stream(stream_name=None):
    """
    Create a test academic stream.

    Args:
        stream_name: Stream name (e.g., "Scientific", "Literary")

    Returns:
        str: Stream name (document name)
    """
    if not stream_name:
        stream_name = f"Stream-{random.randint(100, 999)}"

    if frappe.db.exists("Game Academic Stream", stream_name):
        return stream_name

    stream = frappe.get_doc({
        "doctype": "Game Academic Stream",
        "stream_name": stream_name
    })
    stream.insert(ignore_permissions=True)
    frappe.db.commit()

    return stream_name


def create_test_subject(name=None, title=None, is_paid=0):
    """
    Create a test subject.

    Args:
        name: Subject ID
        title: Subject display title
        is_paid: 1 if paid, 0 if free

    Returns:
        str: Subject name
    """
    if not name:
        name = f"SUBJ-{random.randint(1000, 9999)}"

    if frappe.db.exists("Game Subject", name):
        return name

    subject = frappe.get_doc({
        "doctype": "Game Subject",
        "name": name,
        "title": title or name,
        "is_paid": is_paid,
        "icon": "book"
    })
    subject.insert(ignore_permissions=True)
    frappe.db.commit()

    return name


def create_test_academic_plan(grade, stream=None, year="2025",
                               subjects=None):
    """
    Create an academic plan with subjects.

    Args:
        grade: Grade ID
        stream: Stream ID (optional)
        year: Academic year
        subjects: List of dicts [{subject, display_name, selection_type, specific_unit}]

    Returns:
        str: Plan name
    """
    # Ensure grade exists
    if not frappe.db.exists("Game Academic Grade", grade):
        create_test_grade(grade)

    # Check if stream exists
    if stream and not frappe.db.exists("Game Academic Stream", stream):
        create_test_stream(stream)

    # Create unique plan name
    plan_id = f"PLAN-{grade}-{stream or 'NA'}-{year}"

    if frappe.db.exists("Game Academic Plan", plan_id):
        return plan_id

    plan = frappe.get_doc({
        "doctype": "Game Academic Plan",
        "name": plan_id,
        "grade": grade,
        "stream": stream,
        "year": year,
        "subjects": []
    })

    # Add subjects if provided
    if subjects:
        for subj in subjects:
            # Ensure subject exists
            if not frappe.db.exists("Game Subject", subj["subject"]):
                create_test_subject(subj["subject"])

            plan.append("subjects", {
                "subject": subj["subject"],
                "display_name": subj.get("display_name"),
                "selection_type": subj.get("selection_type", "All Units"),
                "specific_unit": subj.get("specific_unit")
            })

    plan.insert(ignore_permissions=True)
    frappe.db.commit()

    return plan_id


def create_test_learning_track(name=None, subject=None, is_paid=0):
    """Create a test learning track."""
    if not name:
        name = f"TRACK-{random.randint(1000, 9999)}"

    if frappe.db.exists("Game Learning Track", name):
        return name

    # Ensure subject exists
    if subject and not frappe.db.exists("Game Subject", subject):
        create_test_subject(subject)

    track = frappe.get_doc({
        "doctype": "Game Learning Track",
        "name": name,
        "subject": subject,
        "is_paid": is_paid,
        "title": f"Track {name}"
    })
    track.insert(ignore_permissions=True)
    frappe.db.commit()

    return name


def create_test_unit(name=None, subject=None, learning_track=None,
                     is_free_preview=0, order=1):
    """
    Create a test unit.

    Args:
        name: Unit ID
        subject: Subject ID
        learning_track: Track ID
        is_free_preview: 1 if free preview, 0 otherwise
        order: Unit order number

    Returns:
        str: Unit name
    """
    if not name:
        name = f"UNIT-{random.randint(1000, 9999)}"

    if frappe.db.exists("Game Unit", name):
        return name

    # Ensure dependencies exist
    if subject and not frappe.db.exists("Game Subject", subject):
        create_test_subject(subject)

    if learning_track and not frappe.db.exists("Game Learning Track", learning_track):
        create_test_learning_track(learning_track, subject)

    unit = frappe.get_doc({
        "doctype": "Game Unit",
        "name": name,
        "title": f"Unit {name}",
        "subject": subject,
        "learning_track": learning_track,
        "is_free_preview": is_free_preview,
        "order": order
    })
    unit.insert(ignore_permissions=True)
    frappe.db.commit()

    return name


def create_test_lesson(name=None, unit=None, xp_reward=50,
                       is_published=1, stages=None):
    """
    Create a test lesson with stages.

    Args:
        name: Lesson ID
        unit: Unit ID
        xp_reward: XP awarded for completion
        is_published: Publication status
        stages: List of stage dicts [{title, type, config}]

    Returns:
        str: Lesson name
    """
    if not name:
        name = f"LESSON-{random.randint(1000, 9999)}"

    if frappe.db.exists("Game Lesson", name):
        return name

    # Ensure unit exists
    if unit and not frappe.db.exists("Game Unit", unit):
        create_test_unit(unit)

    lesson = frappe.get_doc({
        "doctype": "Game Lesson",
        "name": name,
        "title": f"Lesson {name}",
        "unit": unit,
        "xp_reward": xp_reward,
        "is_published": is_published,
        "stages": []
    })

    # Add stages if provided
    if stages:
        for stage in stages:
            lesson.append("stages", {
                "title": stage.get("title", "Stage"),
                "type": stage.get("type", "Reveal"),
                "config": json.dumps(stage.get("config", {}))
            })

    lesson.insert(ignore_permissions=True)
    frappe.db.commit()

    return name


# ============================================================
# SUBSCRIPTION HELPERS
# ============================================================

def create_test_season(name=None, start_date=None, end_date=None):
    """
    Create a test subscription season.

    Args:
        name: Season ID
        start_date: Season start datetime
        end_date: Season end datetime

    Returns:
        str: Season name
    """
    if not name:
        name = f"SEASON-{random.randint(1000, 9999)}"

    if frappe.db.exists("Game Subscription Season", name):
        return name

    if not start_date:
        start_date = now_datetime()
    if not end_date:
        end_date = add_days(now_datetime(), 30)

    season = frappe.get_doc({
        "doctype": "Game Subscription Season",
        "name": name,
        "title": f"Season {name}",
        "start_date": start_date,
        "end_date": end_date
    })
    season.insert(ignore_permissions=True)
    frappe.db.commit()

    return name


def create_test_subscription(user, season=None, subscription_type="Global",
                             access_items=None):
    """
    Create a test subscription for a user.

    Args:
        user: User email
        season: Season ID (creates active season if None)
        subscription_type: "Global", "Subject", or "Track"
        access_items: List of dicts [{type, subject, track}] for access items

    Returns:
        str: Subscription name
    """
    # Ensure user profile exists
    if not frappe.db.exists("Player Profile", {"user": user}):
        create_test_player(user)

    # Create or use season
    if not season:
        season = create_test_season(
            start_date=add_days(now_datetime(), -5),
            end_date=add_days(now_datetime(), 25)
        )

    subscription = frappe.get_doc({
        "doctype": "Game Player Subscription",
        "player": user,
        "linked_season": season,
        "subscription_type": subscription_type,
        "access_items": []
    })

    # Add access items if provided
    if access_items:
        for item in access_items:
            subscription.append("access_items", {
                "access_type": item.get("type", "Subject"),
                "subject": item.get("subject"),
                "track": item.get("track")
            })

    subscription.insert(ignore_permissions=True)
    frappe.db.commit()

    return subscription.name


# ============================================================
# SESSION & SRS HELPERS
# ============================================================

def submit_test_session(user, lesson_id, xp_earned=50, score=100,
                       interactions=None):
    """
    Submit a gameplay session for a user.

    Args:
        user: User email
        lesson_id: Lesson ID
        xp_earned: XP earned in session
        score: Score achieved
        interactions: List of interaction dicts (for SRS processing)

    Returns:
        str: Session document name
    """
    if interactions is None:
        interactions = []

    session = frappe.get_doc({
        "doctype": "Gameplay Session",
        "player": user,
        "lesson": lesson_id,
        "xp_earned": xp_earned,
        "score": score,
        "raw_data": json.dumps(interactions, ensure_ascii=False)
    })
    session.insert(ignore_permissions=True)

    # Update player XP
    frappe.db.sql("""
        UPDATE `tabPlayer Profile`
        SET total_xp = total_xp + %s
        WHERE user = %s
    """, (xp_earned, user))

    frappe.db.commit()

    return session.name


def create_memory_tracker(user, question_id, subject=None,
                          stability=1, next_review_days=1):
    """
    Create a memory tracker record for SRS testing.

    Args:
        user: User email
        question_id: Question/atom ID
        subject: Subject ID (optional)
        stability: SRS stability level (1-4)
        next_review_days: Days until next review

    Returns:
        str: Tracker document name
    """
    tracker = frappe.get_doc({
        "doctype": "Player Memory Tracker",
        "player": user,
        "question_id": question_id,
        "subject": subject,
        "stability": stability,
        "last_review_date": now_datetime(),
        "next_review_date": add_days(now_datetime(), next_review_days)
    })
    tracker.insert(ignore_permissions=True)
    frappe.db.commit()

    return tracker.name


def create_overdue_review(user, question_id, subject=None,
                          days_overdue=1, stability=2):
    """
    Create an overdue review for testing review session logic.

    Args:
        user: User email
        question_id: Question ID
        subject: Subject ID
        days_overdue: How many days overdue
        stability: Current stability level

    Returns:
        str: Tracker name
    """
    return create_memory_tracker(
        user=user,
        question_id=question_id,
        subject=subject,
        stability=stability,
        next_review_days=-days_overdue  # Negative = past date
    )


# ============================================================
# VERIFICATION HELPERS
# ============================================================

def verify_xp_earned(user, expected_xp):
    """Verify a user has earned expected XP."""
    actual_xp = frappe.db.get_value("Player Profile", {"user": user}, "total_xp")
    return actual_xp == expected_xp


def verify_session_count(user, expected_count):
    """Verify number of sessions for a user."""
    count = frappe.db.count("Gameplay Session", {"player": user})
    return count == expected_count


def verify_memory_tracker_stability(user, question_id, expected_stability):
    """Verify SRS stability level for a question."""
    stability = frappe.db.get_value(
        "Player Memory Tracker",
        {"player": user, "question_id": question_id},
        "stability"
    )
    return stability == expected_stability


def get_user_level(total_xp):
    """
    Calculate level from total XP using the same formula as api.py.

    Formula: level = floor(0.07 * sqrt(xp)) + 1

    Examples:
    - XP = 0 → Level = 1
    - XP = 204 → Level = 2
    - XP = 10000 → Level = 8

    Args:
        total_xp: Total XP amount

    Returns:
        int: Calculated level
    """
    import math
    return int(0.07 * math.sqrt(total_xp)) + 1


# ============================================================
# CLEANUP HELPERS
# ============================================================

def cleanup_test_data(user_emails=None):
    """
    Clean up test data after test execution.

    Args:
        user_emails: List of test user emails to clean up
    """
    if user_emails:
        for email in user_emails:
            # Delete in dependency order
            frappe.db.delete("Gameplay Session", {"player": email})
            frappe.db.delete("Player Memory Tracker", {"player": email})
            frappe.db.delete("Player Subject Score", {"player": email})
            frappe.db.delete("Game Player Subscription", {"player": email})
            frappe.db.delete("Player Profile", {"user": email})
            frappe.db.delete("User", {"email": email})

    frappe.db.commit()


# ============================================================
# ASSERTION HELPERS
# ============================================================

def assert_api_response(response, expected_keys=None):
    """
    Verify API response structure.

    Args:
        response: API response (dict or list)
        expected_keys: List of expected keys (for dict responses)

    Returns:
        bool: True if validation passes
    """
    if expected_keys and isinstance(response, dict):
        for key in expected_keys:
            assert key in response, f"Expected key '{key}' not found in response"

    return True


def assert_lesson_locked(lesson_data, should_be_locked=True):
    """Verify lesson lock status."""
    is_locked = lesson_data.get("locked", False)
    assert is_locked == should_be_locked, \
        f"Lesson lock status mismatch: expected {should_be_locked}, got {is_locked}"


def assert_subject_visible(subjects_list, subject_id, should_be_visible=True):
    """Verify if subject appears in subject list."""
    subject_ids = [s["name"] for s in subjects_list]
    is_visible = subject_id in subject_ids
    assert is_visible == should_be_visible, \
        f"Subject visibility mismatch: {subject_id} expected visible={should_be_visible}"
