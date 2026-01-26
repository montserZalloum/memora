"""Unit tests for unlock_calculator.py"""

import pytest
from memora.services.progress_engine.unlock_calculator import (
    compute_node_states,
    compute_container_status,
    _is_linear_unlock_locked,
    _compute_unlock_state,
)


@pytest.fixture
def sample_linear_subject():
    """Sample subject structure with linear unlock rules."""
    return {
        "id": "SUBJ-001",
        "type": "subject",
        "is_linear": True,
        "tracks": [
            {
                "id": "TRACK-001",
                "type": "track",
                "is_linear": True,
                "units": [
                    {
                        "id": "UNIT-001",
                        "type": "unit",
                        "is_linear": True,
                        "topics": [
                            {
                                "id": "TOPIC-001",
                                "type": "topic",
                                "is_linear": True,
                                "lessons": [
                                    {"id": "LESSON-001", "type": "lesson", "bit_index": 0},
                                    {"id": "LESSON-002", "type": "lesson", "bit_index": 1},
                                    {"id": "LESSON-003", "type": "lesson", "bit_index": 2},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_nonlinear_subject():
    """Sample subject structure with non-linear unlock rules."""
    return {
        "id": "SUBJ-002",
        "type": "subject",
        "is_linear": False,
        "tracks": [
            {
                "id": "TRACK-002",
                "type": "track",
                "is_linear": False,
                "units": [
                    {
                        "id": "UNIT-002",
                        "type": "unit",
                        "is_linear": False,
                        "topics": [
                            {
                                "id": "TOPIC-002",
                                "type": "topic",
                                "is_linear": False,
                                "lessons": [
                                    {"id": "LESSON-004", "type": "lesson", "bit_index": 3},
                                    {"id": "LESSON-005", "type": "lesson", "bit_index": 4},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_mixed_subject():
    """Sample subject with mixed linear/non-linear rules."""
    return {
        "id": "SUBJ-003",
        "type": "subject",
        "is_linear": True,
        "tracks": [
            {
                "id": "TRACK-003",
                "type": "track",
                "is_linear": True,
                "units": [
                    {
                        "id": "UNIT-003A",
                        "type": "unit",
                        "is_linear": True,
                        "topics": [
                            {
                                "id": "TOPIC-003A",
                                "type": "topic",
                                "is_linear": True,
                                "lessons": [
                                    {"id": "LESSON-006", "type": "lesson", "bit_index": 5},
                                    {"id": "LESSON-007", "type": "lesson", "bit_index": 6},
                                ]
                            }
                        ]
                    },
                    {
                        "id": "UNIT-003B",
                        "type": "unit",
                        "is_linear": False,
                        "topics": [
                            {
                                "id": "TOPIC-003B",
                                "type": "topic",
                                "is_linear": False,
                                "lessons": [
                                    {"id": "LESSON-008", "type": "lesson", "bit_index": 7},
                                    {"id": "LESSON-009", "type": "lesson", "bit_index": 8},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }


def test_linear_unlock_first_lesson_unlocked(sample_linear_subject):
    """First lesson in linear topic should be unlocked."""
    bitmap = b'\x00'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    lesson_001 = result["tracks"][0]["units"][0]["topics"][0]["lessons"][0]
    assert lesson_001["status"] == "unlocked"


def test_linear_unlock_second_lesson_locked_until_first_passed(sample_linear_subject):
    """Second lesson should be locked until first lesson is passed."""
    bitmap = b'\x01'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    lessons = result["tracks"][0]["units"][0]["topics"][0]["lessons"]
    assert lessons[0]["status"] == "passed"
    assert lessons[1]["status"] == "locked"


def test_linear_unlock_second_lesson_unlocked_after_first_passed(sample_linear_subject):
    """Second lesson should be unlocked after first lesson is passed."""
    bitmap = b'\x03'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    lessons = result["tracks"][0]["units"][0]["topics"][0]["lessons"]
    assert lessons[0]["status"] == "passed"
    assert lessons[1]["status"] == "unlocked"


def test_linear_unlock_all_lessons_passed(sample_linear_subject):
    """All lessons should be passed when bitmap has all bits set."""
    bitmap = b'\x07'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    lessons = result["tracks"][0]["units"][0]["topics"][0]["lessons"]
    for lesson in lessons:
        assert lesson["status"] == "passed"


def test_linear_unlock_intermediate_lesson_locked(sample_linear_subject):
    """Lesson should be locked if previous sibling not passed."""
    bitmap = b'\x01'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    lessons = result["tracks"][0]["units"][0]["topics"][0]["lessons"]
    assert lessons[0]["status"] == "passed"
    assert lessons[1]["status"] == "locked"
    assert lessons[2]["status"] == "locked"


def test_nonlinear_unlock_all_children_unlocked(sample_nonlinear_subject):
    """In non-linear topic, all children should unlock when parent unlocks."""
    bitmap = b'\x00'
    
    result = compute_node_states(sample_nonlinear_subject, bitmap)
    
    lessons = result["tracks"][0]["units"][0]["topics"][0]["lessons"]
    for lesson in lessons:
        assert lesson["status"] == "unlocked"


def test_nonlinear_unlock_parent_locked_when_locked(sample_nonlinear_subject):
    """Non-linear children should be locked if parent is locked."""
    subject = sample_nonlinear_subject
    subject["is_linear"] = True
    bitmap = b'\x00'
    
    result = compute_node_states(subject, bitmap)
    
    assert result["status"] == "unlocked"


def test_nonlinear_unlock_no_siblings_block(sample_nonlinear_subject):
    """In non-linear topic, one lesson passed doesn't block others."""
    bitmap = b'\x08'
    
    result = compute_node_states(sample_nonlinear_subject, bitmap)
    
    lessons = result["tracks"][0]["units"][0]["topics"][0]["lessons"]
    assert lessons[0]["status"] == "passed"
    assert lessons[1]["status"] == "unlocked"


def test_nonlinear_unlock_independent_completion(sample_nonlinear_subject):
    """In non-linear, lessons can be completed in any order."""
    bitmap = b'\x10'
    
    result = compute_node_states(sample_nonlinear_subject, bitmap)
    
    lessons = result["tracks"][0]["units"][0]["topics"][0]["lessons"]
    assert lessons[0]["status"] == "unlocked"
    assert lessons[1]["status"] == "passed"


def test_nonlinear_unlock_all_passed_when_all_completed(sample_nonlinear_subject):
    """Non-linear all lessons passed when bitmap has all bits set."""
    bitmap = b'\x18'
    
    result = compute_node_states(sample_nonlinear_subject, bitmap)
    
    lessons = result["tracks"][0]["units"][0]["topics"][0]["lessons"]
    for lesson in lessons:
        assert lesson["status"] == "passed"


def test_container_status_all_children_passed(sample_linear_subject):
    """Container status is passed when all children are passed."""
    bitmap = b'\x07'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    topic = result["tracks"][0]["units"][0]["topics"][0]
    assert topic["status"] == "passed"
    
    unit = result["tracks"][0]["units"][0]
    assert unit["status"] == "passed"
    
    track = result["tracks"][0]
    assert track["status"] == "passed"


def test_container_status_some_children_unpassed(sample_linear_subject):
    """Container status is unlocked when some children are unpassed."""
    bitmap = b'\x01'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    topic = result["tracks"][0]["units"][0]["topics"][0]
    assert topic["status"] == "unlocked"
    
    unit = result["tracks"][0]["units"][0]
    assert unit["status"] == "unlocked"
    
    track = result["tracks"][0]
    assert track["status"] == "unlocked"


def test_container_status_no_children_passed(sample_linear_subject):
    """Container status is unlocked when no children are passed."""
    bitmap = b'\x00'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    topic = result["tracks"][0]["units"][0]["topics"][0]
    assert topic["status"] == "unlocked"
    
    unit = result["tracks"][0]["units"][0]
    assert unit["status"] == "unlocked"


def test_container_status_nested_containers(sample_linear_subject):
    """Nested containers compute status correctly."""
    bitmap = b'\x07'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    assert result["status"] == "passed"
    assert result["tracks"][0]["status"] == "passed"
    assert result["tracks"][0]["units"][0]["status"] == "passed"
    assert result["tracks"][0]["units"][0]["topics"][0]["status"] == "passed"


def test_container_status_empty_children():
    """Container with no children should be unlocked."""
    subject = {
        "id": "SUBJ-EMPTY",
        "type": "subject",
        "is_linear": True,
        "tracks": []
    }
    bitmap = b'\x00'
    
    result = compute_node_states(subject, bitmap)
    
    assert result["status"] == "unlocked"


def test_mixed_linear_nonlinear_rules(sample_mixed_subject):
    """Mixed linear/non-linear rules work correctly."""
    bitmap = b'\x20'
    
    result = compute_node_states(sample_mixed_subject, bitmap)
    
    unit_3a = result["tracks"][0]["units"][0]
    topic_3a = unit_3a["topics"][0]
    
    assert topic_3a["is_linear"] == True
    assert topic_3a["lessons"][0]["status"] == "passed"
    assert topic_3a["lessons"][1]["status"] == "unlocked"
    
    unit_3b = result["tracks"][0]["units"][1]
    topic_3b = unit_3b["topics"][0]
    
    assert topic_3b["is_linear"] == False
    assert topic_3b["lessons"][0]["status"] == "unlocked"
    assert topic_3b["lessons"][1]["status"] == "unlocked"


def test_is_linear_unlock_locked_first_lesson():
    """First lesson in linear unlock is never locked."""
    assert not _is_linear_unlock_locked(is_first_child=True, prev_sibling_passed=None)


def test_is_linear_unlock_locked_prev_not_passed():
    """Lesson locked when previous sibling not passed."""
    assert _is_linear_unlock_locked(is_first_child=False, prev_sibling_passed=False)


def test_is_linear_unlock_locked_prev_passed():
    """Lesson unlocked when previous sibling passed."""
    assert not _is_linear_unlock_locked(is_first_child=False, prev_sibling_passed=True)


def test_compute_unlock_state_linear_locked():
    """Linear unlock returns locked when condition met."""
    status = _compute_unlock_state(
        node_status="not_passed",
        parent_is_linear=True,
        is_first_child=False,
        prev_sibling_passed=False,
        parent_unlock_status="unlocked"
    )
    assert status == "locked"


def test_compute_unlock_state_linear_unlocked():
    """Linear unlock returns unlocked when condition met."""
    status = _compute_unlock_state(
        node_status="not_passed",
        parent_is_linear=True,
        is_first_child=False,
        prev_sibling_passed=True,
        parent_unlock_status="unlocked"
    )
    assert status == "unlocked"


def test_compute_unlock_state_nonlinear_parent_unlocked():
    """Non-linear children unlocked when parent unlocked."""
    status = _compute_unlock_state(
        node_status="not_passed",
        parent_is_linear=False,
        is_first_child=True,
        prev_sibling_passed=None,
        parent_unlock_status="unlocked"
    )
    assert status == "unlocked"


def test_compute_unlock_state_nonlinear_parent_locked():
    """Non-linear children locked when parent locked."""
    status = _compute_unlock_state(
        node_status="not_passed",
        parent_is_linear=False,
        is_first_child=True,
        prev_sibling_passed=None,
        parent_unlock_status="locked"
    )
    assert status == "locked"


def test_compute_unlock_state_passed_always_passed():
    """Passed nodes always have passed status."""
    status = _compute_unlock_state(
        node_status="passed",
        parent_is_linear=True,
        is_first_child=False,
        prev_sibling_passed=False,
        parent_unlock_status="locked"
    )
    assert status == "passed"


def test_compute_node_states_preserves_structure(sample_linear_subject):
    """compute_node_states preserves the original structure."""
    bitmap = b'\x01'
    
    result = compute_node_states(sample_linear_subject, bitmap)
    
    assert result["id"] == "SUBJ-001"
    assert result["type"] == "subject"
    assert len(result["tracks"]) == 1
    assert len(result["tracks"][0]["units"]) == 1
    assert len(result["tracks"][0]["units"][0]["topics"]) == 1
    assert len(result["tracks"][0]["units"][0]["topics"][0]["lessons"]) == 3


def test_compute_node_states_all_lessons_no_progress():
    """All lessons should be unlocked when no progress."""
    subject = {
        "id": "SUBJ-NO-PROG",
        "type": "subject",
        "is_linear": True,
        "tracks": [
            {
                "id": "TRACK-NO-PROG",
                "type": "track",
                "is_linear": True,
                "units": [
                    {
                        "id": "UNIT-NO-PROG",
                        "type": "unit",
                        "is_linear": True,
                        "topics": [
                            {
                                "id": "TOPIC-NO-PROG",
                                "type": "topic",
                                "is_linear": True,
                                "lessons": [
                                    {"id": "LESSON-A", "type": "lesson", "bit_index": 10},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    bitmap = b'\x00'
    
    result = compute_node_states(subject, bitmap)
    
    lesson = result["tracks"][0]["units"][0]["topics"][0]["lessons"][0]
    assert lesson["status"] == "unlocked"


def test_compute_container_status_empty_lessons():
    """Container with empty lessons list is unlocked."""
    container = {
        "id": "TOPIC-EMPTY",
        "type": "topic",
        "is_linear": True,
        "lessons": []
    }
    
    status = compute_container_status(container, [], [])
    
    assert status == "unlocked"
