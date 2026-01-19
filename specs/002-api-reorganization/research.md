# Research: API Module Reorganization

**Feature Branch**: `002-api-reorganization`
**Date**: 2026-01-19
**Status**: Complete

## Overview

This document consolidates research findings for reorganizing the monolithic `api.py` file (1897 lines) into a modular package structure while maintaining backward compatibility and preserving all existing functionality.

---

## Domain Groupings

Based on analysis of `api.py`, the following functional domains have been identified:

### 1. **Subjects & Tracks Domain**
- `get_subjects()` - Get subjects based on academic plan
- `get_my_subjects()` - Get subjects for current user
- `get_game_tracks(subject)` - Get tracks for a subject

### 2. **Map Engine Domain**
- `get_map_data(subject=None)` - Smart hybrid map engine
- `get_topic_details(topic_id)` - Get topic/lesson details (lazy loading)

### 3. **Session & Gameplay Domain**
- `submit_session(session_meta, gamification_results, interactions)` - Submit gameplay session
- `get_lesson_details(lesson_id)` - Get lesson content with stages

### 4. **SRS/Memory Domain**
- `process_srs_batch(user, interactions, subject=None, topic=None)` - Process SRS batch
- `infer_rating(duration_ms, attempts)` - Convert time+accuracy to memory score
- `calculate_next_review(rating)` - Calculate next review date
- `update_memory_tracker(user, atom_id, rating, next_date, subject=None, topic=None)` - Update memory tracker
- `create_memory_tracker(user, atom_id, rating)` - Create memory tracker
- `update_srs_after_review(user, question_id, is_correct, duration_ms, subject=None, topic=None)` - Update SRS after review

### 5. **Review Session Domain**
- `get_review_session(subject=None, topic_id=None)` - Get review session
- `submit_review_session(session_data)` - Submit review session
- `get_mastery_counts(user)` - Get mastery counts

### 6. **Profile Domain**
- `get_player_profile()` - Get basic player profile
- `get_full_profile_stats(subject=None)` - Get full profile stats

### 7. **Daily Quests Domain**
- `get_daily_quests(subject=None)` - Get daily quests

### 8. **Leaderboard Domain**
- `get_leaderboard(subject=None, period='all_time')` - Get leaderboard
- `update_subject_progression(user, subject_name, xp_earned)` - Update subject progression

### 9. **Onboarding Domain**
- `get_academic_masters()` - Get academic masters (grades, streams, seasons)
- `set_academic_profile(grade, stream=None)` - Set academic profile

### 10. **Store Domain**
- `get_store_items()` - Get store items
- `request_purchase(item_id, transaction_id=None)` - Request purchase

### 11. **Shared Utilities**
- `get_user_active_subscriptions(user)` - Get user active subscriptions
- `check_subscription_access(active_subs, subject_id, track_id=None)` - Check subscription access

---

## Research Findings

### 1. Python Package Organization Best Practices

**Decision**: Use package structure with `__init__.py` re-exports

**Rationale**:
- Python packages with `__init__.py` are the standard way to organize related modules
- Re-exporting functions from `__init__.py` maintains backward compatibility
- Allows external code to continue importing from the original location
- Follows Python's PEP 8 guidelines for module organization

**Alternatives Considered**:
1. **Separate modules without package** - Rejected because it would break backward compatibility
2. **Namespace packages** - Rejected because Frappe's import system requires explicit package structure
3. **Single file with imports** - Rejected because it doesn't solve the original problem of navigation difficulty

**Best Practices**:
- Each module should be under 400 lines (as per success criteria)
- Use relative imports within the package (`from .utils import get_user_active_subscriptions`)
- Re-export all public `@frappe.whitelist()` functions from `api/__init__.py`
- Keep shared utilities in a dedicated `api/utils.py` module

---

### 2. Import Management in Python Packages

**Decision**: Use explicit imports and re-exports

**Rationale**:
- Explicit imports make dependencies clear
- Re-exports from `__init__.py` maintain backward compatibility
- Avoids circular import issues through proper dependency design

**Alternatives Considered**:
1. **Wildcard imports** (`from module import *`) - Rejected because it makes dependencies unclear and can cause namespace pollution
2. **Dynamic imports** - Rejected because it adds complexity and makes debugging harder
3. **Lazy imports** - Rejected because it's unnecessary for this use case and adds complexity

**Best Practices**:
- Use absolute imports for external dependencies (`import frappe`, `import json`)
- Use relative imports for internal package dependencies (`from .utils import get_user_active_subscriptions`)
- Place shared utilities at the bottom of the dependency hierarchy
- Avoid circular dependencies by ensuring modules only depend on modules "below" them

---

### 3. Backward Compatibility Strategy

**Decision**: Re-export all public functions from `api/__init__.py`

**Rationale**:
- External code can continue importing from `memora.api` without changes
- Zero breaking changes to existing integrations
- Allows gradual migration if needed

**Alternatives Considered**:
1. **Create alias file** - Rejected because it adds an extra file to maintain
2. **Deprecation warnings** - Rejected because we want to maintain full compatibility, not deprecate
3. **Breaking changes with migration guide** - Rejected because success criteria require zero breaking changes

**Best Practices**:
- In `api/__init__.py`, import and re-export all `@frappe.whitelist()` functions
- Maintain exact function signatures (parameters, return types)
- Preserve all existing docstrings
- Keep the same decorator patterns (`@frappe.whitelist()`)

---

### 4. Avoiding Circular Imports

**Decision**: Design dependency hierarchy with shared utilities at the bottom

**Rationale**:
- Circular imports are a common pitfall when splitting large files
- A clear dependency hierarchy prevents circular dependencies
- Shared utilities should be imported by domain modules, not vice versa

**Alternatives Considered**:
1. **Lazy imports inside functions** - Rejected because it makes code harder to understand and test
2. **Import modules instead of functions** - Rejected because it's less explicit and harder to trace
3. **Restructure code to remove dependencies** - Rejected because it would require significant refactoring beyond the scope

**Best Practices**:
- Place `api/utils.py` at the bottom of the dependency hierarchy
- Domain modules can import from `utils.py`
- Domain modules should not import from other domain modules
- If cross-domain communication is needed, use utility functions

**Proposed Dependency Hierarchy**:
```
api/
├── __init__.py          (re-exports all functions)
├── utils.py             (shared utilities - bottom of hierarchy)
├── subjects.py          (imports from utils.py)
├── map_engine.py        (imports from utils.py)
├── sessions.py          (imports from utils.py)
├── srs.py               (imports from utils.py)
├── reviews.py           (imports from utils.py)
├── profile.py           (imports from utils.py)
├── quests.py            (imports from utils.py)
├── leaderboard.py       (imports from utils.py)
├── onboarding.py        (imports from utils.py)
└── store.py             (imports from utils.py)
```

---

### 5. Re-exporting Functions in Python

**Decision**: Use explicit re-exports in `__init__.py`

**Rationale**:
- Makes the public API explicit
- Maintains backward compatibility
- Follows Python best practices

**Alternatives Considered**:
1. **Wildcard re-exports** (`from .module import *`) - Rejected because it's unclear what's being exported
2. **Import module and access via module** - Rejected because it breaks backward compatibility
3. **Create wrapper functions** - Rejected because it adds unnecessary indirection

**Best Practices**:
- In `api/__init__.py`, explicitly import and re-export each public function
- Use the pattern: `from .subjects import get_subjects, get_my_subjects, get_game_tracks`
- This maintains the exact import path: `from memora.api import get_subjects`

---

### 6. Frappe-Specific Considerations

**Decision**: Ensure `@frappe.whitelist()` decorator works correctly in submodules

**Rationale**:
- Frappe's `@frappe.whitelist()` decorator registers API endpoints
- The decorator should work regardless of the module location
- No changes to the decorator usage are needed

**Alternatives Considered**:
1. **Move all decorated functions to `__init__.py`** - Rejected because it defeats the purpose of modularization
2. **Use custom decorator** - Rejected because it's unnecessary complexity
3. **Register endpoints manually** - Rejected because it's not how Frappe works

**Best Practices**:
- Keep `@frappe.whitelist()` decorator on functions in their respective modules
- Re-export decorated functions from `api/__init__.py`
- The decorator will work correctly as long as the package is imported

---

### 7. Module Size Guidelines

**Decision**: Target maximum 400 lines per module

**Rationale**:
- Aligns with success criteria (SC-004)
- Promotes maintainability
- Reduces cognitive load for developers

**Alternatives Considered**:
1. **No line limit** - Rejected because it doesn't address the original problem
2. **Smaller limit (200 lines)** - Rejected because it would create too many small files
3. **Larger limit (600 lines)** - Rejected because it doesn't provide enough benefit

**Best Practices**:
- If a module exceeds 400 lines, consider further splitting
- Group related functions together
- Use descriptive module names
- Keep helper functions in the same module as the functions they support

---

### 8. Testing Strategy

**Decision**: Run all existing tests to verify functionality

**Rationale**:
- Success criteria (SC-005) requires all existing tests to pass
- Ensures no regressions during reorganization
- Validates that the reorganization is transparent to end users

**Alternatives Considered**:
1. **Write new tests** - Rejected because existing tests should be sufficient
2. **Skip testing** - Rejected because it violates success criteria
3. **Manual testing only** - Rejected because automated tests are more reliable

**Best Practices**:
- Run all existing tests before starting the reorganization
- Run tests after each module is created
- Fix any test failures immediately
- Verify that all API endpoints return identical responses

---

## Proposed Module Structure

```
memora/
├── api/
│   ├── __init__.py              # Re-exports all public functions
│   ├── utils.py                 # Shared utilities (get_user_active_subscriptions, check_subscription_access)
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

## Migration Path

### Phase 1: Create Package Structure
1. Create `memora/api/` directory
2. Create `memora/api/__init__.py` with re-exports
3. Create `memora/api/utils.py` with shared utilities

### Phase 2: Migrate Domain Modules
1. Create each domain module with appropriate functions
2. Update imports to use relative imports
3. Test each module independently

### Phase 3: Verify and Clean Up
1. Run all existing tests
2. Verify all API endpoints work correctly
3. Remove or deprecate the old `api.py` file

### Phase 4: Documentation
1. Update any internal documentation
2. Add comments explaining the new structure
3. Create migration guide for developers

---

## Risks and Mitigations

### Risk 1: Circular Imports
**Mitigation**: Design clear dependency hierarchy with utils at the bottom

### Risk 2: Breaking Changes
**Mitigation**: Re-export all functions from `api/__init__.py` to maintain backward compatibility

### Risk 3: Test Failures
**Mitigation**: Run tests after each module is created, fix issues immediately

### Risk 4: Function Signature Changes
**Mitigation**: Preserve exact function signatures, only change import statements

### Risk 5: Frappe Decorator Issues
**Mitigation**: Test that `@frappe.whitelist()` works correctly in submodules

---

## Success Criteria Alignment

- **SC-001**: Developers can locate any API endpoint's source code within 30 seconds - ✅ Achieved through domain-specific modules
- **SC-002**: 100% of existing API endpoints return identical responses - ✅ Achieved through re-exports and preserved signatures
- **SC-003**: No duplicate function definitions exist - ✅ Achieved through clear module separation
- **SC-004**: Each module file contains no more than 400 lines - ✅ Achieved through domain-based splitting
- **SC-005**: All existing automated tests pass - ✅ Achieved through testing strategy
- **SC-006**: New developers can understand the API organization from file/folder names - ✅ Achieved through descriptive naming

---

## Conclusion

The research confirms that a package structure with re-exports from `__init__.py` is the optimal approach for reorganizing the `api.py` file. This approach:

1. Maintains backward compatibility
2. Improves code navigation and maintainability
3. Follows Python best practices
4. Aligns with Frappe's architecture
5. Meets all success criteria

The proposed module structure and dependency hierarchy provide a clear path forward for implementation.
