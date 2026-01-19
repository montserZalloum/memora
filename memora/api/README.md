# Memora API Package

This package reorganizes the monolithic `api.py` file (1897 lines) into a modular package structure with domain-specific modules.

## Purpose

The reorganization improves code navigation and maintainability while preserving all existing functionality with zero breaking changes.

## Module Organization

### Core Files

- **`__init__.py`** - Public API gateway that re-exports all `@frappe.whitelist()` functions to maintain backward compatibility
- **`utils.py`** - Shared utility functions used across multiple domain modules

### Domain Modules

Each domain module contains logically related API functions:

| Module | Purpose | Public Functions |
|---------|-----------|-----------------|
| `subjects.py` | Subjects & Tracks domain | `get_subjects()`, `get_my_subjects()`, `get_game_tracks()` |
| `map_engine.py` | Map Engine domain | `get_map_data()`, `get_topic_details()` | `get_track_details`|
| `sessions.py` | Session & Gameplay domain | `submit_session()`, `get_lesson_details()` |
| `srs.py` | SRS/Memory algorithms | Internal helper functions only |
| `reviews.py` | Review Session domain | `get_review_session()`, `submit_review_session()` |
| `profile.py` | Profile domain | `get_player_profile()`, `get_full_profile_stats()` |
| `quests.py` | Daily Quests domain | `get_daily_quests()` |
| `leaderboard.py` | Leaderboard domain | `get_leaderboard()` |
| `onboarding.py` | Onboarding domain | `get_academic_masters()`, `set_academic_profile()` |
| `store.py` | Store domain | `get_store_items()`, `request_purchase()` |

## Import Patterns

### Public API Usage (Backward Compatible)

```python
# Old way (still works)
from memora.api import get_subjects, get_map_data

# New way (also works)
from memora.api import get_subjects, get_map_data
```

### Internal Module Imports

```python
# Import from utils (shared utilities)
from .utils import get_user_active_subscriptions, check_subscription_access

# Import from other domain modules (allowed dependencies)
from .srs import process_srs_batch
from .leaderboard import update_subject_progression

# Import from sibling packages
from ..ai_engine import get_ai_distractors
```

## Dependency Graph

```
                    ┌─────────────┐
                    │  __init__   │
                    └──────┬──────┘
                           │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │ subjects │        │map_engine│        │sessions │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                     │                     │
         │                     │                  ┌───▼────┐
         │                     │                  │  srs    │
         │                     │                  └───┬────┘
         │                     │                      │
         │                  ┌───▼────┐      ┌───▼────┐
         │                  │ reviews │      │profile  │
         │                  └───┬────┘      └───┬────┘
         │                      │                  │
         │                      │              ┌───▼────┐
         │                      │              │ quests  │
         │                      │              └───┬────┘
         │                      │                  │
         │                  ┌───▼────┐      ┌───▼────┐
         │                  │leaderbd│      │onboard│
         │                  └───┬────┘      └───┬────┘
         │                      │                  │
         └──────────────────────┴──────────────────┴───▼────┐
                                                        │ store  │
                                                        └────────┘
```

## Key Rules

1. **All domain modules can import from `utils.py`**
2. **Domain modules should NOT import from other domain modules** (except for allowed dependencies)
3. **`__init__.py` imports from all domain modules** and re-exports public functions
4. **Allowed cross-module imports:**
   - `sessions.py` can import from `srs.py` and `leaderboard.py`
   - `reviews.py` can import from `srs.py` and `leaderboard.py`

## Module Size Guidelines

Each module file should not exceed 400 lines of code to maintain readability.

## Migration Notes

- The original `memora/api.py` file (1897 lines) can be deprecated after successful migration
- All existing tests should pass without modification (or with only import path updates)
- All API endpoints maintain their existing documentation in `specs/002-api-reorganization/contracts/api-openapi.yaml`

## Testing

To verify the reorganization works correctly:

1. Run existing test suite: `pytest memora/tests/`
2. Manually test all 15 API endpoints
3. Verify backward compatibility: test that code importing from `memora.api` still works
4. Test subscription access control across all modules
5. Test SRS memory tracking after session submission and review completion

## Success Criteria

- ✅ Developers can locate any API endpoint's source code within 30 seconds by navigating to the appropriate domain module
- ✅ 100% of existing API endpoints return identical responses before and after reorganization
- ✅ No duplicate function definitions exist across the reorganized module files
- ✅ Each module file contains no more than 400 lines of code
- ✅ All existing automated tests pass without modification (or with only import path updates)
- ✅ New developers can understand the API organization from file/folder names alone without reading documentation
