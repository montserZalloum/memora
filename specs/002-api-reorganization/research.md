# Research: API Module Reorganization

**Date**: 2026-01-19
**Feature**: 002-api-reorganization

## Research Topics

### 1. Python Package Structure Best Practices

**Decision**: Use standard Python package with `__init__.py` re-exports

**Rationale**:
- Python's import system caches modules, so splitting into multiple files has negligible performance impact
- Using `__init__.py` to re-export public functions maintains backward compatibility
- Follows PEP 8 and standard Python conventions for package organization

**Alternatives Considered**:
- Single file with regions/comments: Rejected - doesn't solve navigation or maintainability issues
- Multiple separate modules without package: Rejected - harder to manage imports and organize

### 2. Frappe @whitelist Decorator in Submodules

**Decision**: Decorators work correctly in submodules when properly imported

**Rationale**:
- Frappe's `@frappe.whitelist()` decorator registers functions at import time
- Functions in submodules are discovered when the package is imported
- The decorator doesn't depend on the file location, only that the function is importable

**Verification Required**:
- After implementation, verify that all API endpoints are callable via Frappe's API mechanism
- Test with: `bench execute memora.api.subjects.get_subjects`

### 3. Circular Import Prevention Strategy

**Decision**: Use `_utils.py` prefix (underscore) for internal shared utilities

**Rationale**:
- The underscore prefix signals "internal module" per Python convention
- Place shared helper functions (no `@whitelist`) in `_utils.py`
- Domain modules import from `_utils.py` but not from each other
- This creates a clear dependency hierarchy: `_utils.py` → domain modules → `__init__.py`

**Dependency Graph**:
```
_utils.py (no dependencies on other api modules)
    ↑
subjects.py, map.py, srs.py, profile.py, leaderboard.py, store.py, onboarding.py
    ↑
__init__.py (re-exports all public functions)
    ↑
api.py (backward compat shim)
```

### 4. Backward Compatibility Approach

**Decision**: Keep original `api.py` as thin import shim

**Rationale**:
- Existing code may import directly: `from memora.api import get_subjects`
- Frappe may have references to `memora.api.function_name` in hooks or elsewhere
- A shim file that does `from memora.api import *` ensures zero breaking changes

**Implementation**:
```python
# memora/api.py (after refactoring)
"""
Backward compatibility shim.
All API functions have been moved to memora/api/ package.
This file re-exports them for backward compatibility.
"""
from memora.api import *
```

### 5. Module Assignment Analysis

Based on analysis of the current `api.py` (1897 lines), functions are assigned as follows:

| Module | Functions | Est. Lines |
|--------|-----------|------------|
| `_utils.py` | `get_user_active_subscriptions`, `check_subscription_access` | ~70 |
| `subjects.py` | `get_subjects`, `get_my_subjects`, `get_game_tracks` | ~120 |
| `map.py` | `get_map_data`, `get_lesson_details`, `get_topic_details` | ~450 |
| `srs.py` | `process_srs_batch`, `infer_rating`, `calculate_next_review`, `update_memory_tracker`, `get_review_session`, `submit_review_session`, `update_srs_after_review`, `get_mastery_counts`, `create_memory_tracker` | ~400 |
| `profile.py` | `get_player_profile`, `get_full_profile_stats`, `get_daily_quests` | ~250 |
| `leaderboard.py` | `get_leaderboard`, `update_subject_progression` | ~170 |
| `store.py` | `get_store_items`, `request_purchase` | ~130 |
| `onboarding.py` | `get_academic_masters`, `set_academic_profile` | ~100 |
| `__init__.py` | Re-exports only | ~50 |

**Total**: ~1740 lines (excludes duplicate imports that will be consolidated)

### 6. Import Consolidation

**Decision**: Each module has its own imports, consolidated at module level

**Current Issue**: The original `api.py` has duplicate import blocks (e.g., `import frappe` appears twice)

**Resolution**: Each new module will have a clean import section with only the imports it needs. Common imports:
- `frappe`, `frappe._` - All modules
- `frappe.utils` functions - Most modules
- `json` - Modules handling JSON data (srs.py, profile.py, store.py)
- `math` - profile.py, leaderboard.py (for level calculations)
- `random` - srs.py (for quiz card shuffling)

### 7. AI Engine Import Path

**Decision**: Update relative import path in srs.py

**Current** (in api.py):
```python
from .ai_engine import get_ai_distractors
```

**After** (in api/srs.py):
```python
from ..ai_engine import get_ai_distractors
```

**Rationale**: The `ai_engine.py` file remains at `memora/ai_engine.py`, so modules inside `memora/api/` need to use `..` to go up one level.

## Conclusion

All research topics resolved. No external dependencies or unknowns remain. Ready to proceed to Phase 1.
