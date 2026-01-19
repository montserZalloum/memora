# Feature Specification: API Module Reorganization

**Feature Branch**: `002-api-reorganization`
**Created**: 2026-01-19
**Status**: Draft
**Input**: User description: "i want to devide the api.py file to multiple files because it's too big now, i wanna reorganize the file to multiple files"

## Clarifications

### Session 2026-01-19

- Q: What module organization structure should be used? → A: Package structure - Create `api/` folder with `__init__.py` and domain modules (e.g., `api/subjects.py`, `api/srs.py`). Re-export all public functions from `api/__init__.py`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Navigates to Relevant Code (Priority: P1)

As a developer, when I need to modify or debug API functionality, I can quickly locate the relevant code by navigating to a domain-specific module file instead of scrolling through a 1900+ line monolithic file.

**Why this priority**: This directly addresses the core problem - a large, hard-to-navigate codebase. Improved navigation reduces development time and cognitive load.

**Independent Test**: Can be verified by checking that each API endpoint can be found in a logically named module file within 10 seconds of understanding which domain it belongs to.

**Acceptance Scenarios**:

1. **Given** a developer needs to modify subject-related functionality, **When** they look for subject APIs, **Then** they find them in a dedicated subjects module file.
2. **Given** a developer needs to debug SRS (Spaced Repetition System) logic, **When** they search for memory/review functions, **Then** they find them in a dedicated SRS/memory module file.
3. **Given** a new developer joins the project, **When** they explore the API structure, **Then** they can understand the organization through clear module naming conventions.

---

### User Story 2 - All Existing API Endpoints Function Correctly (Priority: P1)

As an application user, when I interact with the Memora learning platform, all existing functionality continues to work exactly as before - subjects load, lessons play, progress saves, reviews work, and purchases process.

**Why this priority**: Preserving existing functionality is critical - the reorganization must be transparent to end users with zero breaking changes.

**Independent Test**: Can be verified by running all existing tests and manually testing each API endpoint to confirm identical responses before and after reorganization.

**Acceptance Scenarios**:

1. **Given** the API has been reorganized, **When** the frontend calls any existing endpoint, **Then** the response format and data are identical to before.
2. **Given** the API has been reorganized, **When** session submissions occur, **Then** XP, memory tracking, and progress are recorded correctly.
3. **Given** the API has been reorganized, **When** review sessions are requested, **Then** quiz cards are generated with the same logic and AI distractor integration.

---

### User Story 3 - Shared Utilities Are Accessible Across Modules (Priority: P2)

As a developer, when I work on any API module, I can access shared helper functions (like subscription checking, user context retrieval) without code duplication.

**Why this priority**: Proper code organization with shared utilities prevents duplication and ensures consistent behavior across modules.

**Independent Test**: Can be verified by confirming helper functions are defined once and imported where needed, with no duplicate function definitions across modules.

**Acceptance Scenarios**:

1. **Given** subscription checking is needed in multiple modules, **When** I look for the function, **Then** it exists in one shared location and is imported elsewhere.
2. **Given** a common helper function is updated, **When** the change is made, **Then** all modules using it automatically get the updated behavior.

---

### Edge Cases

- What happens when circular imports occur between modules? (Must be avoided through proper dependency design)
- How does the system handle existing imports from external code that imports from `api.py` directly?
- What happens if a helper function is moved but an old reference remains?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST split the current `api.py` file into domain-specific module files based on functional groupings.
- **FR-002**: System MUST maintain all existing `@frappe.whitelist()` decorated functions as callable API endpoints.
- **FR-003**: System MUST preserve all function signatures (parameters, return types) exactly as they currently exist.
- **FR-004**: System MUST ensure all internal function calls between modules work correctly through proper imports.
- **FR-005**: System MUST organize shared/helper functions into a common utilities module to avoid code duplication.
- **FR-006**: System MUST maintain backward compatibility - any code importing from the original api.py location should continue to work or have clear migration path.
- **FR-007**: Each module file MUST contain logically related functions that share a common domain (e.g., subjects, map, SRS, profile, store).

### Key Entities

- **API Module**: A Python file containing related API endpoint functions and their supporting helpers, organized by functional domain.
- **Shared Utilities Module**: A Python file containing helper functions used across multiple API modules (e.g., `get_user_active_subscriptions`, `check_subscription_access`).
- **Domain Groupings**: Logical categories for organizing endpoints:
  - Subjects & Tracks (subject listing, track fetching)
  - Map Engine (map data, lesson details, topic details)
  - SRS/Memory (review sessions, memory tracking, SRS algorithms)
  - Player Profile (profile stats, daily quests, onboarding)
  - Leaderboard (ranking, scoring)
  - Store (items listing, purchase requests)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can locate any API endpoint's source code within 30 seconds by navigating to the appropriate domain module.
- **SC-002**: 100% of existing API endpoints return identical responses before and after reorganization.
- **SC-003**: No duplicate function definitions exist across the reorganized module files.
- **SC-004**: Each module file contains no more than 400 lines of code (promoting maintainability).
- **SC-005**: All existing automated tests pass without modification (or with only import path updates).
- **SC-006**: New developers can understand the API organization from file/folder names alone without reading documentation.

## Assumptions

- The reorganization will use a **package structure**: an `api/` directory with `__init__.py` containing domain-specific modules (e.g., `api/subjects.py`, `api/srs.py`, `api/profile.py`).
- The `api/__init__.py` file will re-export all public `@frappe.whitelist()` functions to maintain backward compatibility for existing imports.
- The Frappe framework's `@frappe.whitelist()` decorator will continue to work correctly when functions are in submodules.
- No changes to the database schema or DocTypes are needed - this is purely a code organization change.
- The AI distractor import (`from .ai_engine import get_ai_distractors`) will continue to work with updated relative import paths.
