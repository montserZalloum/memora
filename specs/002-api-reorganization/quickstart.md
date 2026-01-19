# Quickstart: API Module Reorganization

**Date**: 2026-01-19
**Feature**: 002-api-reorganization

## Overview

This guide explains how to work with the reorganized API module structure.

## Directory Structure

```
memora/
├── api/                    # NEW: API package
│   ├── __init__.py         # Re-exports all public functions
│   ├── _utils.py           # Shared utilities (internal)
│   ├── subjects.py         # Subject/track APIs
│   ├── map.py              # Map engine APIs
│   ├── srs.py              # SRS/memory APIs
│   ├── profile.py          # Player profile APIs
│   ├── leaderboard.py      # Ranking APIs
│   ├── store.py            # Store/purchase APIs
│   └── onboarding.py       # Academic setup APIs
├── api.py                  # Backward compat shim
└── ai_engine.py            # AI utilities (unchanged)
```

## Importing Functions

### For New Code (Recommended)
Import directly from the specific module:

```python
from memora.api.subjects import get_subjects, get_my_subjects
from memora.api.srs import get_review_session, submit_review_session
from memora.api.profile import get_player_profile
```

### For Backward Compatibility
The original import path still works:

```python
from memora.api import get_subjects  # Still works!
```

## Module Responsibilities

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `_utils.py` | Shared helpers (no @whitelist) | `get_user_active_subscriptions`, `check_subscription_access` |
| `subjects.py` | Subject & track listing | `get_subjects`, `get_my_subjects`, `get_game_tracks` |
| `map.py` | Learning map structure | `get_map_data`, `get_lesson_details`, `get_topic_details` |
| `srs.py` | Spaced repetition system | `get_review_session`, `submit_review_session`, `submit_session` |
| `profile.py` | Player stats & quests | `get_player_profile`, `get_full_profile_stats`, `get_daily_quests` |
| `leaderboard.py` | Rankings & scoring | `get_leaderboard`, `update_subject_progression` |
| `store.py` | Store & purchases | `get_store_items`, `request_purchase` |
| `onboarding.py` | Academic setup | `get_academic_masters`, `set_academic_profile` |

## Adding New Endpoints

1. **Identify the correct module** based on domain responsibility
2. **Add imports** at the top of the module file
3. **Implement the function** with `@frappe.whitelist()` decorator
4. **Export in `__init__.py`** if it should be publicly accessible

Example:
```python
# In api/profile.py
@frappe.whitelist()
def get_achievements():
    """New endpoint for player achievements."""
    # Implementation...
    pass

# In api/__init__.py
from .profile import (
    get_player_profile,
    get_full_profile_stats,
    get_daily_quests,
    get_achievements,  # Add new export
)
```

## Using Shared Utilities

The `_utils.py` module contains helpers used across multiple domains:

```python
# In any api module
from ._utils import get_user_active_subscriptions, check_subscription_access

def my_endpoint():
    user = frappe.session.user
    active_subs = get_user_active_subscriptions(user)
    if check_subscription_access(active_subs, subject_id):
        # User has access
        pass
```

## Testing

Run existing tests to verify no regressions:

```bash
cd /path/to/frappe-bench
bench run-tests --app memora
```

Test individual endpoints:

```bash
bench execute memora.api.subjects.get_subjects
bench execute memora.api.profile.get_player_profile
```

## Troubleshooting

### ImportError: cannot import name 'X' from 'memora.api'

**Cause**: Function not exported in `api/__init__.py`

**Fix**: Add the function to the exports in `api/__init__.py`

### Circular Import Error

**Cause**: Module A imports from Module B, and Module B imports from Module A

**Fix**: Move shared code to `_utils.py` and have both modules import from there

### @whitelist function not found

**Cause**: The module wasn't imported when Frappe initialized

**Fix**: Ensure the function is exported in `api/__init__.py` and the package imports correctly
