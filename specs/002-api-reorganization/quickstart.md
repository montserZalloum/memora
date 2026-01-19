# Quickstart Guide: API Module Reorganization

**Feature Branch**: `002-api-reorganization`
**Date**: 2026-01-19
**Status**: Complete

## Overview

This guide helps developers understand and work with the reorganized API module structure. The monolithic `api.py` file (1897 lines) has been split into a modular package with domain-specific modules.

---

## What Changed?

### Before
```
memora/
└── api.py  # 1897 lines, monolithic
```

### After
```
memora/
├── api/
│   ├── __init__.py              # Public API gateway
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
└── api.py  # DEPRECATED (to be removed)
```

---

## Backward Compatibility

### ✅ No Breaking Changes

All existing imports continue to work exactly as before:

```python
# These imports still work:
from memora.api import get_subjects
from memora.api import get_map_data
from memora.api import submit_session
from memora.api import get_review_session
# ... and all other public functions
```

The `api/__init__.py` file re-exports all public `@frappe.whitelist()` functions, so external code doesn't need to change.

---

## Module Reference

### Public API Functions

All functions decorated with `@frappe.whitelist()` are public and can be called from the frontend:

#### Subjects & Tracks
- `get_subjects()` - Get subjects based on user's academic plan
- `get_my_subjects()` - Get subjects for current user
- `get_game_tracks(subject)` - Get tracks for a subject

#### Map Engine
- `get_map_data(subject=None)` - Get map data with smart hybrid loading
- `get_topic_details(topic_id)` - Get topic/lesson details (lazy load)

#### Sessions
- `submit_session(session_meta, gamification_results, interactions)` - Submit gameplay session
- `get_lesson_details(lesson_id)` - Get lesson content with stages

#### Reviews
- `get_review_session(subject=None, topic_id=None)` - Get review session
- `submit_review_session(session_data)` - Submit review session

#### Profile
- `get_player_profile()` - Get basic player profile
- `get_full_profile_stats(subject=None)` - Get full profile statistics

#### Quests
- `get_daily_quests(subject=None)` - Get daily quests

#### Leaderboard
- `get_leaderboard(subject=None, period='all_time')` - Get leaderboard

#### Onboarding
- `get_academic_masters()` - Get academic master data
- `set_academic_profile(grade, stream=None)` - Set academic profile

#### Store
- `get_store_items()` - Get store items
- `request_purchase(item_id, transaction_id=None)` - Request purchase

### Internal Helper Functions

These functions are NOT decorated with `@frappe.whitelist()` and are internal to the package:

#### SRS Algorithms (`api/srs.py`)
- `process_srs_batch(user, interactions, subject=None, topic=None)`
- `infer_rating(duration_ms, attempts)`
- `calculate_next_review(rating)`
- `update_memory_tracker(user, atom_id, rating, next_date, subject=None, topic=None)`
- `create_memory_tracker(user, atom_id, rating)`
- `update_srs_after_review(user, question_id, is_correct, duration_ms, subject=None, topic=None)`

#### Review Helpers (`api/reviews.py`)
- `get_mastery_counts(user)`

#### Leaderboard Helpers (`api/leaderboard.py`)
- `update_subject_progression(user, subject_name, xp_earned)`

#### Shared Utilities (`api/utils.py`)
- `get_user_active_subscriptions(user)`
- `check_subscription_access(active_subs, subject_id, track_id=None)`

---

## Import Patterns

### Importing Public Functions (Recommended)

```python
# Import specific functions (explicit)
from memora.api import get_subjects, get_map_data, submit_session

# Import entire module (less common)
import memora.api as api
subjects = api.get_subjects()
```

### Importing Internal Functions (For Package Development)

```python
# Import from utils (shared across domain modules)
from .utils import get_user_active_subscriptions, check_subscription_access

# Import from other domain modules (use sparingly)
from .srs import process_srs_batch
from .leaderboard import update_subject_progression

# Import from sibling package (ai_engine)
from ..ai_engine import get_ai_distractors
```

---

## Finding Code

### By Domain

| Domain | Module | Functions |
|---------|---------|-----------|
| Subjects & Tracks | `api/subjects.py` | `get_subjects()`, `get_my_subjects()`, `get_game_tracks()` |
| Map Engine | `api/map_engine.py` | `get_map_data()`, `get_topic_details()` |
| Sessions | `api/sessions.py` | `submit_session()`, `get_lesson_details()` |
| Reviews | `api/reviews.py` | `get_review_session()`, `submit_review_session()` |
| Profile | `api/profile.py` | `get_player_profile()`, `get_full_profile_stats()` |
| Quests | `api/quests.py` | `get_daily_quests()` |
| Leaderboard | `api/leaderboard.py` | `get_leaderboard()` |
| Onboarding | `api/onboarding.py` | `get_academic_masters()`, `set_academic_profile()` |
| Store | `api/store.py` | `get_store_items()`, `request_purchase()` |

### By Function Name

If you know the function name, use your IDE's search (Ctrl+Shift+F / Cmd+Shift+F) to search across the `api/` directory.

---

## Common Tasks

### Adding a New API Endpoint

1. **Choose the appropriate module** based on the domain (see table above)
2. **Add the function** to the module file
3. **Decorate with `@frappe.whitelist()`** if it's a public endpoint
4. **Re-export from `__init__.py`** if it's a public function

Example:
```python
# In api/subjects.py

@frappe.whitelist()
def get_subject_details(subject_id):
    """Get detailed information about a subject."""
    # Implementation here
    return result
```

```python
# In api/__init__.py

from .subjects import get_subjects, get_my_subjects, get_game_tracks, get_subject_details  # Add new function
```

### Modifying an Existing Function

1. **Find the function** in the appropriate module (see "Finding Code" section)
2. **Make your changes**
3. **Test the changes** (see "Testing" section)

### Adding a Shared Utility

1. **Add the function** to `api/utils.py`
2. **Import it** in the modules that need it

Example:
```python
# In api/utils.py

def get_user_context(user):
    """Get user's academic context (grade, stream, year)."""
    profile = frappe.db.get_value("Player Profile", {"user": user},
        ["current_grade", "current_stream", "academic_year"], as_dict=True)
    return profile
```

```python
# In api/subjects.py

from .utils import get_user_context

@frappe.whitelist()
def get_subjects():
    user = frappe.session.user
    context = get_user_context(user)
    # Use context...
```

---

## Testing

### Running Tests

```bash
# Run all tests
bench run-tests

# Run specific test file
bench run-tests memora.tests.test_onboarding_profile

# Run with verbose output
bench run-tests --verbose
```

### Testing API Endpoints

```bash
# Using Frappe's test client
bench --site your-site run-tests --module memora

# Manual testing via curl
curl -X POST http://your-site/api/method/memora.api.get_subjects \
  -H "Authorization: token <your-token>"
```

### Verifying Functionality

After reorganization, verify:

1. ✅ All existing tests pass
2. ✅ All API endpoints return identical responses
3. ✅ No duplicate function definitions
4. ✅ All modules are under 400 lines
5. ✅ Frontend can still call all endpoints

---

## Migration Guide for Developers

### If You're Importing from api.py

**No changes needed!** Your imports continue to work:

```python
# This still works:
from memora.api import get_subjects
```

### If You're Importing Internal Functions

**You need to update your imports:**

**Before:**
```python
from memora.api import get_user_active_subscriptions
```

**After:**
```python
from memora.api.utils import get_user_active_subscriptions
```

### If You're Reading the Source Code

**Navigate to the new module structure:**

**Before:**
```
Open: memora/api.py (1897 lines)
Scroll to find the function you need
```

**After:**
```
Open: memora/api/subjects.py (150-200 lines)
Open: memora/api/map_engine.py (350-400 lines)
Open: memora/api/sessions.py (100-150 lines)
# ... etc.
```

---

## Troubleshooting

### Import Error: "No module named 'memora.api'"

**Cause**: The `api/` directory doesn't have an `__init__.py` file.

**Solution**: Ensure `memora/api/__init__.py` exists and contains the re-exports.

### Import Error: "cannot import name 'X' from 'memora.api'"

**Cause**: The function is not re-exported from `api/__init__.py`.

**Solution**: Add the function to the re-exports in `api/__init__.py`:

```python
from .subjects import get_subjects, get_my_subjects, get_game_tracks, get_subject_details
# Add missing function here
```

### Circular Import Error

**Cause**: Two modules are importing each other.

**Solution**: Move shared code to `api/utils.py` or restructure to avoid circular dependencies.

### Function Not Found

**Cause**: The function was moved to a different module.

**Solution**: Check the "Finding Code" section to locate the new module.

---

## Best Practices

1. **Keep modules under 400 lines** - If a module grows too large, consider further splitting
2. **Use relative imports** within the package (`from .utils import ...`)
3. **Re-export public functions** from `__init__.py` for backward compatibility
4. **Document public functions** with clear docstrings
5. **Test after each change** to catch issues early
6. **Avoid circular dependencies** - Use `utils.py` for shared code
7. **Follow domain boundaries** - Don't mix unrelated functionality in one module

---

## Support

If you encounter issues:

1. Check the [data-model.md](./data-model.md) for module organization details
2. Check the [research.md](./research.md) for design decisions
3. Check the [API contracts](./contracts/api-openapi.yaml) for endpoint specifications
4. Ask in the team chat or create an issue

---

## Summary

The reorganized API structure provides:

- ✅ **Better code navigation** - Find functions in domain-specific modules
- ✅ **Maintainability** - Smaller, focused modules are easier to understand and modify
- ✅ **Backward compatibility** - All existing imports continue to work
- ✅ **Clear organization** - Domain-based structure makes the codebase easier to learn

Happy coding! 🚀
