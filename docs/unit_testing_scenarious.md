# Unit Testing Plan for Memora App

## Overview
This plan outlines a comprehensive unit testing strategy for the Memora gamified learning platform. The app has 26 API methods and 24 doctypes that need thorough test coverage.

## Existing Test Scenarios (from documentation)

The following scenarios are already defined in the test scenarios document:

### 1. Onboarding & User Profile (TS-01 to TS-04)
- Happy path for grades without streams
- Happy path for grades with streams (Tawjihi)
- Invalid stream combination validation
- Access security without onboarding

### 2. Academic Plan & Content Visibility (TS-05 to TS-06)
- Partial content filtering (Shari'a Math case)
- Subject list aggregation with purchased content

### 3. Freemium Access Model (TS-07 to TS-10)
- Free preview access
- Fully free subject access
- Linear progression educational constraint
- Linear progression override after completion

### 4. Economy & Store (TS-11 to TS-15)
- Grade/stream filtering in store
- Smart hiding of owned items
- Smart hiding of pending requests
- Full purchase flow cycle
- Season expiry validation

### 5. Gamification & SRS Engine (TS-16 to TS-19)
- SRS bonus jump for fast answers
- SRS slow answer behavior
- SRS reset on wrong answers
- Parent cleanup logic for multi-part questions

### 6. Leaderboards (TS-20 to TS-21)
- Subject-specific leaderboard accuracy
- Weekly leaderboard reset logic

---

## Additional Test Cases Recommended

### 7. Session Submission & Gameplay Validation 🎮

**TS-22: Complete Session Flow - XP Calculation**
- *Setup:* Lesson with 3 stages, total possible XP = 100
- *Action:* Submit session with all correct answers
- *Expected:* Player Profile total_xp increases by 100, Player Subject Score updates, Gameplay Session record created

**TS-23: Session Validation - Invalid Lesson ID**
- *Action:* Submit session with non-existent lesson_id
- *Expected:* `404 Not Found` or validation error

**TS-24: Session Validation - Tampered XP**
- *Setup:* Lesson max XP is 100
- *Action:* Submit session with gamification_results.total_xp = 500
- *Expected:* Server recalculates XP based on interactions, ignores client value

**TS-25: Session Validation - Missing Required Fields**
- *Action:* Submit session without session_meta or interactions
- *Expected:* `400 Bad Request` with clear error message

**TS-26: Duplicate Session Prevention**
- *Action:* Submit the same session data twice rapidly
- *Expected:* System should handle idempotently or reject duplicate

**TS-27: Session with Empty Interactions**
- *Action:* Submit session with empty interactions array
- *Expected:* Session saved but no SRS records created, minimal XP awarded

---

### 8. SRS Algorithm Edge Cases 🧮

**TS-28: SRS - Negative Duration Protection**
- *Action:* Submit interaction with duration_ms = -100
- *Expected:* System treats as 0 or minimum threshold, doesn't crash

**TS-29: SRS - Extreme Duration Values**
- *Action:* Submit interaction with duration_ms = 999999999 (16+ minutes)
- *Expected:* System caps at maximum threshold or treats as "very slow"

**TS-30: SRS - Zero Attempts**
- *Action:* Submit interaction with attempts = 0
- *Expected:* System handles gracefully, doesn't divide by zero

**TS-31: SRS - Memory Tracker Orphan Cleanup**
- *Setup:* Memory tracker with question_id that no longer exists in stages
- *Action:* Run review session or cleanup job
- *Expected:* Orphaned records identified and cleaned up

**TS-32: SRS - Stability Overflow**
- *Setup:* Memory tracker with stability = 4 (max level)
- *Action:* Submit another perfect fast answer
- *Expected:* Stability stays at 4 or next_review extends significantly

**TS-33: SRS - First Time Question**
- *Action:* Submit interaction for a question never seen before
- *Expected:* New Memory Tracker created with stability = 1, next_review = today + 2 days

**TS-34: SRS - Review Session Size Limits**
- *Setup:* Player has 100+ items due for review
- *Action:* Call get_review_session()
- *Expected:* Returns exactly 10-15 items (as per code), not all 100

**TS-35: SRS - Parent Question Tracker Date Extension**
- *Setup:* Parent question with 3 variants (A, B, C)
- *Action:* Review variant A today (stability increases)
- *Expected:* Parent tracker next_review_date pushed to future to avoid showing other variants immediately

---

### 9. XP & Level System 📊

**TS-36: Level Calculation Accuracy**
- *Test Cases:*
  - XP = 0 → Level = 1
  - XP = 204 → Level = 2 (0.07 * sqrt(204) + 1 ≈ 2)
  - XP = 10000 → Level = 8
- *Expected:* Formula `level = floor(0.07 * sqrt(xp)) + 1` applies correctly

**TS-37: Subject XP vs Global XP Sync**
- *Action:* Earn 50 XP in Math, 30 XP in Physics
- *Expected:*
  - Global total_xp = 80
  - Math Subject Score total_xp = 50
  - Physics Subject Score total_xp = 30

**TS-38: XP Overflow Protection**
- *Action:* Submit session with extremely large XP value (2^31)
- *Expected:* System validates against lesson max_xp or rejects

**TS-39: Negative XP Protection**
- *Action:* Attempt to submit session with negative XP
- *Expected:* Validation error or ignored

---

### 10. Content Visibility & Locking Logic 🔐

**TS-40: Lock Status - No Profile**
- *Action:* Call get_map_data without a player profile
- *Expected:* All content locked or error message

**TS-41: Lock Status - Partial Unit Completion**
- *Setup:* Unit has 5 lessons. User completed lessons 1-3.
- *Action:* Call get_map_data
- *Expected:*
  - Lessons 1-3: status = "completed"
  - Lesson 4: status = "available" (next in linear progression)
  - Lesson 5: status = "locked" (waiting for lesson 4)

**TS-42: Lock Status - Unit Prerequisites**
- *Setup:* Unit 2 requires Unit 1 completion
- *Action:* User tries to access Unit 2 without completing Unit 1
- *Expected:* All lessons in Unit 2 locked

**TS-43: Track-Specific Content Filtering**
- *Setup:* Subject has 2 tracks (Beginner, Advanced). Lesson A only in Beginner track.
- *Action:* Call get_map_data with track="Advanced"
- *Expected:* Lesson A should not appear in response

**TS-44: Mixed Access Levels**
- *Setup:* Subject has some free lessons, some premium. User has no subscription.
- *Action:* Call get_map_data
- *Expected:* Free lessons show "available", premium show "locked_premium"

---

### 11. Academic Plan & Content Filtering 🎓

**TS-45: Missing Academic Plan**
- *Setup:* Player has grade=10, stream="Scientific", but no academic plan exists for 2026
- *Action:* Call get_my_subjects()
- *Expected:* Empty list or error message explaining missing plan

**TS-46: Plan with Empty Subjects**
- *Setup:* Academic plan exists but has no Plan Subject child rows
- *Action:* Call get_my_subjects()
- *Expected:* Returns empty list (valid scenario for new plans)

**TS-47: Plan Subject vs Track Filtering**
- *Setup:* Plan includes "Math" subject but only tracks 1 and 2, not track 3
- *Action:* Call get_game_tracks("Math")
- *Expected:* Returns only tracks 1 and 2

**TS-48: Cross-Grade Content Leakage**
- *Setup:* User in Grade 10 tries to access Grade 11 content directly (by guessing IDs)
- *Action:* Call get_lesson_details(grade_11_lesson_id)
- *Expected:* Access denied or filtered out

---

### 12. Subscription & Payment System 💳

**TS-49: Multiple Overlapping Subscriptions**
- *Setup:* User has Global subscription + Subject-specific (Math) subscription
- *Action:* Check access for Math content
- *Expected:* Global subscription takes precedence, no conflicts

**TS-50: Subscription Without Season**
- *Setup:* Player Subscription created but linked_season is empty
- *Action:* Check access
- *Expected:* Subscription invalid (season is mandatory for date validation)

**TS-51: Future-Dated Season**
- *Setup:* Subscription linked to season starting tomorrow
- *Action:* Try to access content today
- *Expected:* Content locked (season not started)

**TS-52: Purchase Request State Transitions**
- *Test Flow:*
  - Create request (status=Pending) → Cannot purchase same item again
  - Admin rejects (status=Rejected) → Item reappears in store
  - Admin approves (status=Approved) → Subscription created, item disappears

**TS-53: Bundle Content Validation**
- *Setup:* Bundle claims to contain "Math + Physics" but only Math is in Bundle Content rows
- *Action:* Purchase approved
- *Expected:* Subscription only grants access to Math (what's in child table)

**TS-54: Stream-Specific Bundle Filtering**
- *Setup:* Bundle is for "Scientific Stream" only
- *Action:* Literary Stream student views store
- *Expected:* Bundle hidden from store list

---

### 13. Leaderboard Accuracy & Edge Cases 🏆

**TS-55: Leaderboard with Ties**
- *Setup:* 3 users with exactly 100 XP each
- *Action:* Call get_leaderboard
- *Expected:* All 3 shown, rank handling (tied at #1 or ordered by timestamp)

**TS-56: Leaderboard Pagination**
- *Setup:* 200 active players
- *Action:* Call get_leaderboard
- *Expected:* Returns top 50 only (as per API logic)

**TS-57: Weekly Leaderboard Date Boundary**
- *Setup:* Today is Sunday. Session completed last Sunday (7 days ago).
- *Action:* Call get_leaderboard(period="weekly")
- *Expected:* Last Sunday's session excluded (>7 days)

**TS-58: Subject Leaderboard Isolation**
- *Setup:* User has 500 XP in Math, 0 in Physics
- *Action:* Call get_leaderboard(subject="Physics")
- *Expected:* User not shown in Physics leaderboard

**TS-59: Leaderboard with Deleted Users**
- *Setup:* A top user account is disabled/deleted
- *Action:* Call get_leaderboard
- *Expected:* Deleted user filtered out or shown as [Deleted]

---

### 14. Daily Quests & Streaks 🎯

**TS-60: Daily Quest Generation**
- *Action:* Call get_daily_quests for a subject
- *Expected:* Returns review count, streak info, XP goals

**TS-61: Streak Calculation Accuracy**
- *Setup:* User played 5 consecutive days, skipped 1 day, played today
- *Expected:* Streak = 1 (resets after skip)

**TS-62: Streak Continuation Logic**
- *Setup:* User played yesterday at 11:59 PM, today at 12:01 AM
- *Expected:* Streak increments by 1

**TS-63: Quest Progress Not Reset Mid-Day**
- *Setup:* User completes quest at 10 AM
- *Action:* Check quest status at 11 AM same day
- *Expected:* Quest still marked complete for today

---

### 15. Data Integrity & Error Handling ⚠️

**TS-64: API Call Without Authentication**
- *Action:* Call any API endpoint without logged-in user
- *Expected:* `401 Unauthorized`

**TS-65: API Call Without Player Profile**
- *Setup:* User logged in but never completed onboarding
- *Action:* Call get_my_subjects()
- *Expected:* Graceful error or empty state with onboarding prompt

**TS-66: Invalid Grade/Stream Combination**
- *Action:* Call set_academic_profile(grade="Grade 10", stream="Scientific")
- *Expected:* Validation error (Grade 10 doesn't have streams)

**TS-67: Missing Required Doctype Links**
- *Setup:* Lesson created without a parent Unit
- *Action:* Try to load lesson in map
- *Expected:* Error or skip lesson

**TS-68: Malformed Stage Config JSON**
- *Setup:* Game Stage has invalid JSON in config field
- *Action:* Call get_lesson_details
- *Expected:* Skip stage or return error, don't crash

**TS-69: Concurrent Session Submissions**
- *Setup:* User submits 2 sessions simultaneously
- *Expected:* Both processed correctly, XP summed, no race condition

**TS-70: Large Batch Processing**
- *Setup:* Session with 100+ interactions (very long lesson)
- *Action:* Submit session
- *Expected:* All interactions processed, no timeout

---

### 16. Multi-Device & Edge Cases 📱

**TS-71: Device Registration**
- *Action:* User logs in from new device
- *Expected:* Game Player Device record created

**TS-72: Progress Sync Across Devices**
- *Action:* Complete lesson on Device A, check progress on Device B
- *Expected:* Progress shows on Device B (server-side sync)

**TS-73: Offline Session Submission**
- *Setup:* User plays offline, then reconnects
- *Action:* Submit cached session
- *Expected:* Session accepted if still valid

---

### 17. Performance & Scalability Tests 🚀

**TS-74: Memory Tracker Query Performance**
- *Setup:* User has 1000+ memory tracker records
- *Action:* Call get_review_session()
- *Expected:* Returns within 2 seconds, uses proper indexes

**TS-75: Leaderboard Query Performance**
- *Setup:* Database has 10,000 players
- *Action:* Call get_leaderboard
- *Expected:* Returns top 50 within 1 second

**TS-76: Batch SRS Processing Performance**
- *Setup:* Session with 50 interactions
- *Action:* Submit session
- *Expected:* Processes within 5 seconds

---

## Testing Strategy

### Test Organization

```
/home/corex/aurevia-bench/apps/memora/memora/tests/
├── __init__.py                          # Test module initialization
├── utils.py                             # Shared test helpers (CRITICAL - create first)
├── test_onboarding_profile.py          # TS-01 to TS-04 (4 tests)
├── test_academic_plan_filtering.py     # TS-05, TS-06, TS-45 to TS-48 (6 tests)
├── test_freemium_access.py             # TS-07 to TS-10 (4 tests)
├── test_store_economy.py               # TS-11 to TS-15 (5 tests)
├── test_gamification_srs.py            # TS-16 to TS-19 (4 tests)
├── test_leaderboards.py                # TS-20, TS-21, TS-55 to TS-59 (7 tests)
├── test_session_submission.py          # TS-22 to TS-27 (6 tests)
├── test_srs_edge_cases.py              # TS-28 to TS-35 (8 tests)
├── test_xp_level_system.py             # TS-36 to TS-39 (4 tests)
├── test_content_locking.py             # TS-40 to TS-44 (5 tests)
├── test_subscription_edge_cases.py     # TS-49 to TS-54 (6 tests)
├── test_daily_quests.py                # TS-60 to TS-63 (4 tests)
└── test_error_handling.py              # TS-64 to TS-68 (5 tests)
```

### Test Framework & Approach
- **Framework:** Frappe's `FrappeTestCase`
- **Data Setup:** Programmatic (helper functions in `utils.py`, NOT JSON fixtures)
- **Database:** Frappe test framework handles transaction rollback automatically
- **Total Tests:** 73 test scenarios (excluding performance tests per user request)

### Critical Helper Functions (memora/tests/utils.py)

Must implement these helpers first:

```python
# User & Profile Creation
create_test_user(email=None, first_name="Test", password="test123")
create_test_player(email=None, grade=None, stream=None, academic_year="2025", total_xp=0)

# Academic Structure
create_test_grade(name=None, title=None)
create_test_stream(name=None, title=None)
create_test_subject(name=None, title=None, is_paid=0)
create_test_academic_plan(grade, stream=None, year="2025", subjects=[])
create_test_learning_track(name=None, subject=None, is_paid=0)
create_test_unit(name=None, subject=None, learning_track=None, is_free_preview=0, order=1)
create_test_lesson(name=None, unit=None, xp_reward=50, is_published=1, stages=[])

# Subscription & Payment
create_test_season(name=None, start_date=None, end_date=None)
create_test_subscription(user, season=None, subscription_type="Premium", status="Active")

# Session & SRS
submit_test_session(user, lesson_id, xp_earned=50, score=100, interactions=None)
create_memory_tracker(user, question_id, subject=None, stability=1, next_review_days=1)
create_overdue_review(user, question_id, subject=None, days_overdue=1, stability=2)

# Verification
verify_xp_earned(user, expected_xp)
verify_session_count(user, expected_count)
verify_memory_tracker_stability(user, question_id, expected_stability)
get_user_level(total_xp)

# Cleanup
cleanup_test_data(user_emails=[])
```

### Test Execution Commands

```bash
# Run all tests
bench --site [site-name] run-tests --app memora

# Run specific test module
bench --site [site-name] run-tests --module memora.tests.test_gamification_srs

# Run specific test method
bench --site [site-name] run-tests --module memora.tests.test_gamification_srs --test TestGamificationSRS.test_srs_bonus_jump

# Run with verbose output
bench --site [site-name] run-tests --app memora -v

# Run tests in parallel (faster)
bench --site [site-name] run-parallel-tests --app memora
```

### Key Testing Patterns

**1. Test Class Structure:**
```python
from frappe.tests.utils import FrappeTestCase
import frappe
from memora.tests.utils import create_test_user, create_test_player, cleanup_test_data

class TestOnboardingProfile(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self.test_user = create_test_user()

    def tearDown(self):
        cleanup_test_data([self.test_user])
        super().tearDown()

    def test_scenario(self):
        # Arrange: Set up test data
        create_test_player(self.test_user, grade="Grade-10")

        # Act: Call API as test user
        frappe.set_user(self.test_user)
        result = frappe.call("memora.api.get_subjects")

        # Assert: Verify results
        self.assertIsInstance(result, list)
```

**2. Calling API Methods:**
```python
# Method 1: Direct import (fastest)
from memora.api import get_subjects
frappe.set_user("test@test.com")
subjects = get_subjects()

# Method 2: Using frappe.call() (simulates API)
frappe.set_user("test@test.com")
subjects = frappe.call("memora.api.get_subjects")
```

**3. Verifying Database Changes:**
```python
# Check single value
total_xp = frappe.db.get_value("Player Profile", {"user": "test@test.com"}, "total_xp")
self.assertEqual(total_xp, 100)

# Check record exists
exists = frappe.db.exists("Gameplay Session", {"player": "test@test.com", "lesson": "LESSON-001"})
self.assertTrue(exists)

# Count records
count = frappe.db.count("Player Memory Tracker", {"player": "test@test.com"})
self.assertEqual(count, 5)
```

### Critical Business Logic to Remember

**SRS Rating Logic:**
- Rating 1 (FAIL): `attempts > 1` OR wrong answer
- Rating 2 (HARD): Correct first try, duration > 5000ms
- Rating 3 (GOOD): Correct first try, 2000ms < duration ≤ 5000ms
- Rating 4 (EASY): Correct first try, duration < 2000ms

**SRS Stability Progression:**
- Fast correct (<2s): +2 stability (bonus jump)
- Medium correct: +1 stability
- Slow correct (>6s): No change (min 1)
- Wrong answer: Reset to 1

**Review Intervals:**
- Stability 1: 1 day
- Stability 2: 3 days
- Stability 3: 7 days
- Stability 4: 14 days

**Access Control:**
- First lesson in unit: Always unlocked
- Subsequent lessons: Locked until previous completed
- Free preview (`is_free_preview=1`): Always unlocked
- Paid content: Requires active subscription OR free preview

**Subscription Validation:**
- Active = `season.end_date > NOW()`
- Types: "Premium" (all content) or "Subject" (specific subject)
- Check uses JOIN between subscription and season tables

---

## Implementation Sequence

### Phase 1: Foundation (Priority 1)
**Goal:** Set up test infrastructure and verify it works

1. Create `/home/corex/aurevia-bench/apps/memora/memora/tests/__init__.py`
2. Create `/home/corex/aurevia-bench/apps/memora/memora/tests/utils.py` with all helper functions
3. Implement `test_onboarding_profile.py` (4 tests: TS-01 to TS-04)
4. Run tests to verify infrastructure works

**Deliverable:** Working test framework with helpers, 4 passing tests

### Phase 2: Core Business Logic (Priority 2)
**Goal:** Test critical SRS and session submission logic

5. Implement `test_session_submission.py` (6 tests: TS-22 to TS-27)
6. Implement `test_gamification_srs.py` (4 tests: TS-16 to TS-19)
7. Implement `test_srs_edge_cases.py` (8 tests: TS-28 to TS-35)

**Deliverable:** 18 tests covering session flow and SRS algorithm

### Phase 3: Access Control & Content (Priority 3)
**Goal:** Verify security and content visibility logic

8. Implement `test_academic_plan_filtering.py` (6 tests: TS-05, TS-06, TS-45 to TS-48)
9. Implement `test_freemium_access.py` (4 tests: TS-07 to TS-10)
10. Implement `test_content_locking.py` (5 tests: TS-40 to TS-44)
11. Implement `test_subscription_edge_cases.py` (6 tests: TS-49 to TS-54)

**Deliverable:** 21 tests covering access control and filtering

### Phase 4: Store & Subscriptions (Priority 4)
**Goal:** Test purchase flow and subscription management

12. Implement `test_store_economy.py` (5 tests: TS-11 to TS-15)

**Deliverable:** 5 tests for store and purchase logic

### Phase 5: Gamification Features (Priority 5)
**Goal:** Complete feature coverage for XP, levels, leaderboards

13. Implement `test_xp_level_system.py` (4 tests: TS-36 to TS-39)
14. Implement `test_leaderboards.py` (7 tests: TS-20, TS-21, TS-55 to TS-59)
15. Implement `test_daily_quests.py` (4 tests: TS-60 to TS-63)

**Deliverable:** 15 tests for gamification systems

### Phase 6: Robustness (Priority 6)
**Goal:** Ensure error handling and edge cases covered

16. Implement `test_error_handling.py` (5 tests: TS-64 to TS-68)
17. Run full test suite and verify all 73 tests pass
18. Review coverage report

**Deliverable:** Complete test suite with 73 passing tests

---

## Success Criteria

✅ **Coverage Goals:**
- 90%+ coverage of `/home/corex/aurevia-bench/apps/memora/memora/api.py` (26 API methods)
- 100% coverage of SRS algorithm functions
- 95%+ coverage of subscription/access control logic
- All 73 test scenarios implemented and passing

✅ **Quality Standards:**
- All tests pass consistently (no flaky tests)
- Tests run in under 2 minutes total
- Clear, descriptive test names following `test_<scenario_description>` pattern
- Each test has docstring explaining Given/When/Then
- Proper test isolation (setUp/tearDown with cleanup)

✅ **Deliverables:**
1. **`tests/utils.py`** - 20+ helper functions with docstrings
2. **14 test modules** - 73 total test methods across 14 files
3. **All tests passing** - Verified with `bench run-tests --app memora`
4. **Documentation** - This plan serves as implementation guide

---

## Final Test Count

- **Onboarding & Profile:** 4 tests (TS-01 to TS-04)
- **Academic Plan Filtering:** 6 tests (TS-05, TS-06, TS-45 to TS-48)
- **Freemium Access:** 4 tests (TS-07 to TS-10)
- **Store & Economy:** 5 tests (TS-11 to TS-15)
- **SRS Engine:** 4 tests (TS-16 to TS-19)
- **Leaderboards:** 7 tests (TS-20, TS-21, TS-55 to TS-59)
- **Session Submission:** 6 tests (TS-22 to TS-27)
- **SRS Edge Cases:** 8 tests (TS-28 to TS-35)
- **XP & Levels:** 4 tests (TS-36 to TS-39)
- **Content Locking:** 5 tests (TS-40 to TS-44)
- **Subscription Edge Cases:** 6 tests (TS-49 to TS-54)
- **Daily Quests:** 4 tests (TS-60 to TS-63)
- **Error Handling:** 5 tests (TS-64 to TS-68)

**Total:** 73 comprehensive test scenarios

**Excluded (per user request):**
- TS-74 to TS-76: Performance tests (3 tests)
- Business decision tests: Concurrency, stream changes, offline mode (not yet specified)

---

## Critical Files Reference

**Main API to test:**
- `/home/corex/aurevia-bench/apps/memora/memora/api.py` - All 26 API methods

**Test files to create:**
- `/home/corex/aurevia-bench/apps/memora/memora/tests/utils.py` - Helper functions (CREATE FIRST)
- `/home/corex/aurevia-bench/apps/memora/memora/tests/test_*.py` - 14 test modules

**Doctypes to understand:**
- `Player Profile` - User profile with XP, grade, stream
- `Gameplay Session` - Session logs with XP earned
- `Player Memory Tracker` - SRS state (stability, review dates)
- `Game Player Subscription` - Active subscriptions
- `Game Subscription Season` - Season with start/end dates
- `Game Lesson`, `Game Unit`, `Game Subject` - Content hierarchy

---

This plan provides comprehensive test coverage for the Memora app with 73 test scenarios organized into 14 test modules, using programmatic test data creation and Frappe's testing framework.
