# Data Model: API Module Reorganization

**Feature Branch**: `002-api-reorganization`
**Date**: 2026-01-19
**Status**: Complete

## Overview

This document describes the module organization for the API reorganization. Unlike traditional data models that define database entities, this "data model" defines the code organization structure, function mappings, and module dependencies.

**Note**: This is a code organization feature. No database schema changes are required. All existing DocTypes and database tables remain unchanged.

---

## Module Organization

### Package Structure

```
memora/
├── api/
│   ├── __init__.py              # Re-exports all public functions
│   ├── utils.py                 # Shared utilities
│   ├── subjects.py              # Subjects & Tracks domain
│   ├── map_engine.py            # Map Engine domain
│   ├── sessions.py              # Session & Gameplay domain
│   ├── srs.py                   # SRS/Memory algorithms
│   ├── reviews.py               # Review Session domain
│   ├── profile.py               # Profile domain
│   ├── quests.py                # Daily Quests domain
│   ├── leaderboard.py           # Leaderboard domain
│   ├── onboarding.py            # Onboarding domain
│   └── store.py                 # Store domain
```

---

## Module Definitions

### 1. `api/__init__.py` - Public API Gateway

**Purpose**: Re-export all public `@frappe.whitelist()` functions to maintain backward compatibility.

**Functions Re-exported**:
- From `subjects.py`: `get_subjects`, `get_my_subjects`, `get_game_tracks`
- From `map_engine.py`: `get_map_data`, `get_topic_details`
- From `sessions.py`: `submit_session`, `get_lesson_details`
- From `srs.py`: (none - all functions are internal helpers)
- From `reviews.py`: `get_review_session`, `submit_review_session`
- From `profile.py`: `get_player_profile`, `get_full_profile_stats`
- From `quests.py`: `get_daily_quests`
- From `leaderboard.py`: `get_leaderboard`
- From `onboarding.py`: `get_academic_masters`, `set_academic_profile`
- From `store.py`: `get_store_items`, `request_purchase`

**Dependencies**: All domain modules, `utils.py`

**Approximate Size**: 30-50 lines

---

### 2. `api/utils.py` - Shared Utilities

**Purpose**: Contains helper functions used across multiple domain modules.

**Functions**:
- `get_user_active_subscriptions(user)` - Get user's active subscriptions
- `check_subscription_access(active_subs, subject_id, track_id=None)` - Check if user has access to a subject/track

**Dependencies**: `frappe`, `frappe.db`

**Approximate Size**: 100-150 lines

**Used By**: `map_engine.py`, `sessions.py`, `reviews.py`, `profile.py`, `quests.py`, `leaderboard.py`, `onboarding.py`, `store.py`

---

### 3. `api/subjects.py` - Subjects & Tracks Domain

**Purpose**: Handle subject listing and track retrieval based on academic plan.

**Public Functions** (`@frappe.whitelist()`):
- `get_subjects()` - Get subjects based on user's academic plan (Arabic version)
- `get_my_subjects()` - Get subjects for current user (English version)
- `get_game_tracks(subject)` - Get tracks for a given subject

**Internal Functions**: None

**Dependencies**: `frappe`, `frappe.db`, `frappe.get_doc`, `frappe.get_all`, `frappe.log_error`

**Approximate Size**: 150-200 lines

**Related DocTypes**:
- `Player Profile`
- `Game Academic Plan`
- `Game Plan Subject`
- `Game Subject`
- `Game Learning Track`

---

### 4. `api/map_engine.py` - Map Engine Domain

**Purpose**: Provide smart hybrid map data with lazy loading for topic-based units.

**Public Functions** (`@frappe.whitelist()`):
- `get_map_data(subject=None)` - Get map data with smart hybrid loading
- `get_topic_details(topic_id)` - Get topic/lesson details (lazy load)

**Internal Functions**: None

**Dependencies**: `frappe`, `frappe.db`, `frappe.get_doc`, `frappe.get_all`, `frappe.log_error`, `.utils.get_user_active_subscriptions`, `.utils.check_subscription_access`

**Approximate Size**: 350-400 lines

**Related DocTypes**:
- `Player Profile`
- `Game Academic Plan`
- `Game Subject`
- `Game Unit`
- `Game Topic`
- `Game Lesson`
- `Gameplay Session`
- `Game Learning Track`

**Key Logic**:
- Academic plan filtering (Grade/Stream)
- Subscription access control
- Linear vs. non-linear progression
- Lesson-based vs. topic-based unit structures

---

### 5. `api/sessions.py` - Session & Gameplay Domain

**Purpose**: Handle gameplay session submission and lesson content retrieval.

**Public Functions** (`@frappe.whitelist()`):
- `submit_session(session_meta, gamification_results, interactions)` - Submit gameplay session
- `get_lesson_details(lesson_id)` - Get lesson content with stages

**Internal Functions**: None

**Dependencies**: `frappe`, `json`, `frappe.db`, `frappe.get_doc`, `frappe.log_error`, `.srs.process_srs_batch`, `.leaderboard.update_subject_progression`

**Approximate Size**: 100-150 lines

**Related DocTypes**:
- `Gameplay Session`
- `Player Profile`
- `Game Lesson`
- `Game Stage`
- `Player Memory Tracker`
- `Player Subject Score`

**Key Logic**:
- Session archiving
- XP calculation and updates
- Subject progression tracking
- SRS batch processing

---

### 6. `api/srs.py` - SRS/Memory Algorithms

**Purpose**: Implement Spaced Repetition System algorithms for memory tracking.

**Public Functions**: None (all functions are internal helpers)

**Internal Functions**:
- `process_srs_batch(user, interactions, subject=None, topic=None)` - Process batch of SRS updates
- `infer_rating(duration_ms, attempts)` - Convert time+accuracy to memory score (1-4)
- `calculate_next_review(rating)` - Calculate next review date based on rating
- `update_memory_tracker(user, atom_id, rating, next_date, subject=None, topic=None)` - Update/create memory tracker record
- `create_memory_tracker(user, atom_id, rating)` - Create new memory tracker record
- `update_srs_after_review(user, question_id, is_correct, duration_ms, subject=None, topic=None)` - Update SRS after review session

**Dependencies**: `frappe`, `frappe.db`, `frappe.get_doc`, `frappe.get_value`, `frappe.set_value`, `frappe.utils.add_days`, `frappe.utils.now_datetime`, `frappe.utils.cint`

**Approximate Size**: 200-250 lines

**Related DocTypes**:
- `Player Memory Tracker`
- `Gameplay Session`

**Key Logic**:
- Rating inference (1=AGAIN, 2=HARD, 3=GOOD, 4=EASY)
- Review interval calculation (0, 2, 4, 7, 14 days)
- Memory tracker upsert logic
- Self-healing for orphaned data

---

### 7. `api/reviews.py` - Review Session Domain

**Purpose**: Handle review session generation and submission for SRS.

**Public Functions** (`@frappe.whitelist()`):
- `get_review_session(subject=None, topic_id=None)` - Get review session with quiz cards
- `submit_review_session(session_data)` - Submit review session results

**Internal Functions**:
- `get_mastery_counts(user)` - Get mastery statistics for user

**Dependencies**: `frappe`, `json`, `random`, `frappe.db`, `frappe.get_doc`, `frappe.get_all`, `frappe.get_value`, `frappe.log_error`, `frappe.parse_json`, `frappe.delete`, `frappe.utils.add_days`, `frappe.utils.now_datetime`, `frappe.utils.cint`, `frappe.utils.getdate`, `frappe.utils.nowdate`, `..ai_engine.get_ai_distractors`, `.srs.update_srs_after_review`, `.utils.get_user_active_subscriptions`, `.leaderboard.update_subject_progression`

**Approximate Size**: 350-400 lines

**Related DocTypes**:
- `Player Memory Tracker`
- `Gameplay Session`
- `Game Stage`
- `Game Lesson`
- `Game Topic`

**Key Logic**:
- Smart filtering (due items, exclude today's reviews)
- Focus mode (topic-specific reviews)
- Self-healing (cleanup corrupt trackers)
- AI distractor generation for quiz cards
- Stage type conversion (Reveal/Matching → Quiz)

---

### 8. `api/profile.py` - Profile Domain

**Purpose**: Handle player profile data and statistics.

**Public Functions** (`@frappe.whitelist()`):
- `get_player_profile()` - Get basic player profile (XP, gems, grade, stream)
- `get_full_profile_stats(subject=None)` - Get full profile stats with mastery data

**Internal Functions**: None

**Dependencies**: `frappe`, `math`, `frappe.db`, `frappe.get_doc`, `frappe.get_all`, `frappe.get_value`, `frappe.log_error`, `frappe.utils.getdate`, `frappe.utils.add_days`, `frappe.utils.nowdate`, `.utils.get_user_active_subscriptions`

**Approximate Size**: 200-250 lines

**Related DocTypes**:
- `Player Profile`
- `User`
- `Gameplay Session`
- `Player Memory Tracker`

**Key Logic**:
- Level calculation (RPG curve: level = int(0.07 * sqrt(xp)) + 1)
- Streak calculation (consecutive days)
- Weekly activity tracking
- Mastery statistics (new, learning, mature)

---

### 9. `api/quests.py` - Daily Quests Domain

**Purpose**: Generate daily quests based on user's review needs and activity.

**Public Functions** (`@frappe.whitelist()`):
- `get_daily_quests(subject=None)` - Get daily quests (review, streak, XP goals)

**Internal Functions**: None

**Dependencies**: `frappe`, `frappe.db`, `frappe.get_value`, `frappe.log_error`, `frappe.utils.getdate`, `frappe.utils.nowdate`

**Approximate Size**: 120-150 lines

**Related DocTypes**:
- `Player Memory Tracker`
- `Gameplay Session`

**Key Logic**:
- Review quest generation (grouped by subject)
- Streak quest (play any lesson today)
- XP goal quest (daily XP target)
- Quest status tracking (active, completed)

---

### 10. `api/leaderboard.py` - Leaderboard Domain

**Purpose**: Handle leaderboard retrieval and user ranking.

**Public Functions** (`@frappe.whitelist()`):
- `get_leaderboard(subject=None, period='all_time')` - Get leaderboard (all-time or weekly)

**Internal Functions**:
- `update_subject_progression(user, subject_name, xp_earned)` - Update subject XP and level

**Dependencies**: `frappe`, `math`, `frappe.db`, `frappe.get_doc`, `frappe.get_all`, `frappe.get_value`, `frappe.log_error`

**Approximate Size**: 150-200 lines

**Related DocTypes**:
- `Player Subject Score`
- `Player Profile`
- `User`
- `Gameplay Session`

**Key Logic**:
- All-time vs. weekly ranking
- Subject-specific vs. global leaderboard
- Level calculation (same formula as profile)
- User rank detection (in top 50 or 50+)

---

### 11. `api/onboarding.py` - Onboarding Domain

**Purpose**: Handle student onboarding and academic profile setup.

**Public Functions** (`@frappe.whitelist()`):
- `get_academic_masters()` - Get academic master data (grades, streams, seasons)
- `set_academic_profile(grade, stream=None)` - Set user's academic profile

**Internal Functions**: None

**Dependencies**: `frappe`, `frappe.db`, `frappe.get_doc`, `frappe.get_all`, `frappe.get_value`, `frappe.exists`, `frappe.log_error`, `frappe.set_value`

**Approximate Size**: 100-150 lines

**Related DocTypes**:
- `Game Academic Grade`
- `Game Academic Stream`
- `Game Grade Valid Stream`
- `Game Subscription Season`
- `Player Profile`

**Key Logic**:
- Nested streams (grades with allowed streams)
- Profile upsert (create if not exists)
- Stream validation (check if stream is valid for grade)
- Season detection (active season)

---

### 12. `api/store.py` - Store Domain

**Purpose**: Handle store item listing and purchase requests.

**Public Functions** (`@frappe.whitelist()`):
- `get_store_items()` - Get store items (filter out owned/pending items)
- `request_purchase(item_id, transaction_id=None)` - Submit purchase request

**Internal Functions**: None

**Dependencies**: `frappe`, `frappe.db`, `frappe.get_doc`, `frappe.get_all`, `frappe.get_value`, `frappe.exists`, `frappe.log_error`, `.utils.get_user_active_subscriptions`

**Approximate Size**: 150-200 lines

**Related DocTypes**:
- `Game Sales Item`
- `Game Purchase Request`
- `Game Bundle Content`
- `Game Item Target Stream`
- `Player Profile`
- `Game Subject`
- `Game Learning Track`

**Key Logic**:
- Filter out owned items (based on subscriptions)
- Filter out pending items
- Bundle content analysis
- Grade/stream filtering
- Purchase request deduplication

---

## Dependency Graph

```
                    ┌─────────────┐
                    │  __init__  │
                    └──────┬──────┘
                           │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
   │ subjects │        │map_engine│        │sessions │
   └────┬────┘        └────┬────┘        └────┬────┘
        │                  │                  │
        │                  │                  │
        │                  │                  │
        │              ┌───▼────┐      ┌───▼────┐
        │              │ reviews │      │  srs   │
        │              └───┬────┘      └───┬────┘
        │                  │                  │
        │                  │                  │
        │                  │              ┌───▼────┐
        │                  │              │profile │
        │                  │              └───┬────┘
        │                  │                  │
        │                  │              ┌───▼────┐
        │                  │              │ quests │
        │                  │              └───┬────┘
        │                  │                  │
        │                  │              ┌───▼────┐
        │                  │              │leaderbd│
        │                  │              └───┬────┘
        │                  │                  │
        │                  │              ┌───▼────┐
        │                  │              │onboard│
        │                  │              └───┬────┘
        │                  │                  │
        │                  │              ┌───▼────┐
        └──────────────────┴──────────────┤ store  │
                                   └───┬────┘
                                       │
                                   ┌───▼────┐
                                   │ utils  │
                                   └────────┘
```

**Legend**:
- `__init__`: Public API gateway (re-exports all functions)
- Domain modules (subjects, map_engine, etc.): Contain business logic
- `utils`: Shared utilities (bottom of dependency hierarchy)
- Arrows indicate import direction (module → utils)

**Key Rules**:
1. All domain modules can import from `utils.py`
2. Domain modules should NOT import from other domain modules
3. `__init__.py` imports from all domain modules
4. `sessions.py` can import from `srs.py` and `leaderboard.py`
5. `reviews.py` can import from `srs.py` and `leaderboard.py`

---

## Import Patterns

### Absolute Imports (External Dependencies)
```python
import frappe
import json
import math
import random
from frappe import _
from frappe.utils import now_datetime, add_days, get_datetime, getdate, nowdate, cint
```

### Relative Imports (Internal Package Dependencies)
```python
# From domain modules to utils
from .utils import get_user_active_subscriptions, check_subscription_access

# From sessions.py to srs.py
from .srs import process_srs_batch

# From sessions.py to leaderboard.py
from .leaderboard import update_subject_progression

# From reviews.py to srs.py
from .srs import update_srs_after_review

# From reviews.py to ai_engine (sibling package)
from ..ai_engine import get_ai_distractors
```

### Re-exports (in __init__.py)
```python
# Re-export all public functions
from .subjects import get_subjects, get_my_subjects, get_game_tracks
from .map_engine import get_map_data, get_topic_details
from .sessions import submit_session, get_lesson_details
from .reviews import get_review_session, submit_review_session
from .profile import get_player_profile, get_full_profile_stats
from .quests import get_daily_quests
from .leaderboard import get_leaderboard
from .onboarding import get_academic_masters, set_academic_profile
from .store import get_store_items, request_purchase
```

---

## Function Mapping

### Original api.py → New Module Mapping

| Function | Original Line(s) | New Module | Public? |
|----------|------------------|------------|---------|
| `get_subjects()` | 10-83 | `subjects.py` | ✅ Yes |
| `get_my_subjects()` | 86-152 | `subjects.py` | ✅ Yes |
| `get_game_tracks()` | 155-170 | `subjects.py` | ✅ Yes |
| `get_map_data()` | 181-393 | `map_engine.py` | ✅ Yes |
| `get_user_active_subscriptions()` | 399-442 | `utils.py` | ❌ No |
| `check_subscription_access()` | 444-461 | `utils.py` | ❌ No |
| `get_lesson_details()` | 464-495 | `sessions.py` | ✅ Yes |
| `submit_session()` | 498-559 | `sessions.py` | ✅ Yes |
| `process_srs_batch()` | 565-579 | `srs.py` | ❌ No |
| `infer_rating()` | 582-604 | `srs.py` | ❌ No |
| `calculate_next_review()` | 607-627 | `srs.py` | ❌ No |
| `update_memory_tracker()` | 630-655 | `srs.py` | ❌ No |
| `get_player_profile()` | 658-692 | `profile.py` | ✅ Yes |
| `get_full_profile_stats()` | 695-840 | `profile.py` | ✅ Yes |
| `get_daily_quests()` | 844-963 | `quests.py` | ✅ Yes |
| `get_review_session()` | 967-1185 | `reviews.py` | ✅ Yes |
| `submit_review_session()` | 1188-1263 | `reviews.py` | ✅ Yes |
| `update_srs_after_review()` | 1266-1311 | `srs.py` | ❌ No |
| `get_mastery_counts()` | 1314-1326 | `reviews.py` | ❌ No |
| `create_memory_tracker()` | 1329-1349 | `srs.py` | ❌ No |
| `update_subject_progression()` | 1352-1371 | `leaderboard.py` | ❌ No |
| `get_leaderboard()` | 1374-1508 | `leaderboard.py` | ✅ Yes |
| `get_academic_masters()` | 1515-1564 | `onboarding.py` | ✅ Yes |
| `set_academic_profile()` | 1567-1619 | `onboarding.py` | ✅ Yes |
| `get_store_items()` | 1626-1714 | `store.py` | ✅ Yes |
| `request_purchase()` | 1717-1759 | `store.py` | ✅ Yes |
| `get_topic_details()` | 1762-1897 | `map_engine.py` | ✅ Yes |

**Total**: 27 functions
- **Public API functions**: 16 (decorated with `@frappe.whitelist()`)
- **Internal helper functions**: 11

---

## Module Size Estimates

| Module | Estimated Lines | Functions | Status |
|--------|----------------|-----------|--------|
| `__init__.py` | 30-50 | 16 re-exports | ✅ Under 400 |
| `utils.py` | 100-150 | 2 | ✅ Under 400 |
| `subjects.py` | 150-200 | 3 | ✅ Under 400 |
| `map_engine.py` | 350-400 | 2 | ✅ Under 400 |
| `sessions.py` | 100-150 | 2 | ✅ Under 400 |
| `srs.py` | 200-250 | 6 | ✅ Under 400 |
| `reviews.py` | 350-400 | 3 | ✅ Under 400 |
| `profile.py` | 200-250 | 2 | ✅ Under 400 |
| `quests.py` | 120-150 | 1 | ✅ Under 400 |
| `leaderboard.py` | 150-200 | 2 | ✅ Under 400 |
| `onboarding.py` | 100-150 | 2 | ✅ Under 400 |
| `store.py` | 150-200 | 2 | ✅ Under 400 |

**Total**: ~1,850-2,150 lines (original: 1,897 lines)

**Note**: The increase in total lines is due to:
1. Import statements in each module
2. Module docstrings
3. Re-export statements in `__init__.py`

---

## Validation Rules

### No Circular Imports
- ✅ All domain modules only import from `utils.py`
- ✅ `sessions.py` can import from `srs.py` and `leaderboard.py` (one-way dependency)
- ✅ `reviews.py` can import from `srs.py` and `leaderboard.py` (one-way dependency)
- ✅ No two-way dependencies between domain modules

### Backward Compatibility
- ✅ All public functions re-exported from `api/__init__.py`
- ✅ External code can continue using `from memora.api import get_subjects`
- ✅ Function signatures unchanged
- ✅ Decorators preserved

### Module Size
- ✅ All modules under 400 lines (success criteria SC-004)
- ✅ Each module has a single, clear responsibility

---

## Conclusion

This data model defines a clean, modular organization of the API code that:
1. Improves code navigation and maintainability
2. Maintains backward compatibility
3. Follows Python best practices
4. Aligns with Frappe's architecture
5. Meets all success criteria

The module organization is ready for implementation.
