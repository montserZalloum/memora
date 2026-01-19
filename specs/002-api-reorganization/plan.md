# Implementation Plan: API Module Reorganization

**Branch**: `002-api-reorganization` | **Date**: 2026-01-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-api-reorganization/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Reorganize the monolithic `api.py` file (1897 lines) into a modular package structure with domain-specific modules. The approach uses a Python package with `__init__.py` that re-exports all public `@frappe.whitelist()` functions to maintain backward compatibility. Each domain module will contain logically related functions, with shared utilities in a dedicated `utils.py` module. The reorganization aims to improve code navigation and maintainability while preserving all existing functionality with zero breaking changes.

## Technical Context

**Language/Version**: Python 3.11+ (Frappe framework)
**Primary Dependencies**: Frappe Framework, frappe.whitelist() decorator
**Storage**: Frappe Database (MariaDB/MySQL) - No schema changes required
**Testing**: pytest (existing test suite), Frappe test framework
**Target Platform**: Linux server (Frappe backend)
**Project Type**: Single project (Frappe app)
**Performance Goals**: No performance degradation - API responses must remain identical
**Constraints**: Zero breaking changes, maintain backward compatibility, each module < 400 lines
**Scale/Scope**: 11 domain modules, 1 shared utilities module, ~1897 lines of code to reorganize

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Academic-First Architecture (The Brain)
- **Status**: ✅ PASS - No changes to Academic Plan logic
- **Impact**: The reorganization is purely code organization. All academic filtering logic remains in the same functions, just moved to different files. The `get_subjects()`, `get_my_subjects()`, and related academic filtering functions will preserve their exact logic.

### II. Backend Sovereignty (Headless Logic)
- **Status**: ✅ PASS - No changes to backend logic
- **Impact**: All critical business logic (SRS calculation, access control, store filtering) remains in Python backend. The reorganization only changes file locations, not the logic itself. The React app remains a "dumb renderer."

### III. Lock-First Security (The Freemium Model)
- **Status**: ✅ PASS - No changes to access control logic
- **Impact**: The `get_user_active_subscriptions()` and `check_subscription_access()` utility functions maintain their exact implementation. All subscription/access control checks remain on the server side.

### IV. Data Integrity & Stable Identity
- **Status**: ✅ PASS - No changes to data handling
- **Impact**: All SRS tracking, memory updates, and session submissions use the same database operations. No changes to ID injection or self-healing logic.

### V. Performance & Scalability
- **Status**: ✅ PASS - No performance degradation
- **Impact**: The reorganization does not change database queries, lazy loading behavior, or transaction handling. The `get_map_data()` function continues to use the same payload-efficient approach.

### Quality Standards
- **Testing**: ✅ PASS - All existing tests must pass without modification (or with only import path updates)
- **Documentation**: ✅ PASS - All API endpoints maintain their existing documentation

**Overall Gate Status**: ✅ PASS - All constitution principles are upheld. The reorganization is a code organization change only, with no modifications to business logic, data handling, or security controls.

---

## Post-Design Constitution Check

*GATE: Re-evaluated after Phase 1 design.*

### I. Academic-First Architecture (The Brain)
- **Status**: ✅ PASS - No changes to Academic Plan logic
- **Post-Design Verification**: All academic filtering logic remains in the same functions, just moved to `api/subjects.py` and `api/map_engine.py`. The `get_subjects()`, `get_my_subjects()`, and related functions preserve their exact implementation.

### II. Backend Sovereignty (Headless Logic)
- **Status**: ✅ PASS - No changes to backend logic
- **Post-Design Verification**: All critical business logic (SRS calculation, access control, store filtering) remains in Python backend. Functions are now in domain-specific modules (`api/srs.py`, `api/store.py`, etc.) but logic is unchanged. The React app remains a "dumb renderer."

### III. Lock-First Security (The Freemium Model)
- **Status**: ✅ PASS - No changes to access control logic
- **Post-Design Verification**: The `get_user_active_subscriptions()` and `check_subscription_access()` utility functions maintain their exact implementation in `api/utils.py`. All subscription/access control checks remain on the server side in the same functions.

### IV. Data Integrity & Stable Identity
- **Status**: ✅ PASS - No changes to data handling
- **Post-Design Verification**: All SRS tracking, memory updates, and session submissions use the same database operations. No changes to ID injection or self-healing logic. Functions are now in `api/srs.py` and `api/sessions.py` but data handling is identical.

### V. Performance & Scalability
- **Status**: ✅ PASS - No performance degradation
- **Post-Design Verification**: The reorganization does not change database queries, lazy loading behavior, or transaction handling. The `get_map_data()` function in `api/map_engine.py` continues to use the same payload-efficient approach. No performance impact expected from modularization.

### Quality Standards
- **Testing**: ✅ PASS - All existing tests must pass without modification (or with only import path updates)
- **Post-Design Verification**: The reorganization maintains all function signatures and decorators. Tests should pass without changes to test logic, only import paths may need updating if they import internal functions.

- **Documentation**: ✅ PASS - All API endpoints maintain their existing documentation
- **Post-Design Verification**: Function docstrings are preserved in their new modules. API contracts in `contracts/api-openapi.yaml` document all endpoints accurately.

**Overall Post-Design Gate Status**: ✅ PASS - All constitution principles continue to be upheld. The modular design preserves all business logic, data handling, security controls, and performance characteristics while improving code organization.

## Project Structure

### Documentation (this feature)

```text
specs/002-api-reorganization/
├── spec.md               # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
memora/
├── api/                 # NEW: Modular API package
│   ├── __init__.py      # Re-exports all public @frappe.whitelist() functions
│   ├── utils.py         # Shared utilities (get_user_active_subscriptions, check_subscription_access)
│   ├── subjects.py      # Subjects & Tracks domain
│   ├── map_engine.py    # Map Engine domain
│   ├── sessions.py      # Session & Gameplay domain
│   ├── srs.py           # SRS/Memory algorithms
│   ├── reviews.py       # Review Session domain
│   ├── profile.py       # Profile domain
│   ├── quests.py        # Daily Quests domain
│   ├── leaderboard.py   # Leaderboard domain
│   ├── onboarding.py    # Onboarding domain
│   └── store.py        # Store domain
├── api.py              # DEPRECATED: Original monolithic file (to be removed after migration)
├── ai_engine.py        # AI distractor generation (imported by reviews.py)
├── config/             # Configuration files
├── memora/             # DocType definitions
├── migrations/         # Database migrations
├── public/            # Frontend assets
├── templates/         # HTML templates
├── tests/            # Test suite
└── www/              # Web assets
```

**Structure Decision**: The selected structure is a Python package (`memora/api/`) with domain-specific modules. This aligns with Python best practices for organizing related functionality and allows for backward compatibility through re-exports from `__init__.py`. The original `api.py` file will be deprecated and eventually removed after successful migration.

## Complexity Tracking

> **No constitution violations detected. This section is not required.**
