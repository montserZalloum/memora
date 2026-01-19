---

description: "Task list for API Module Reorganization feature"
---

# Tasks: API Module Reorganization

**Input**: Design documents from `/specs/002-api-reorganization/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `memora/`, `tests/` at repository root
- Paths shown below use the actual project structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create memora/api/ directory structure per implementation plan
- [ ] T002 [P] Create memora/api/__init__.py file with package initialization
- [ ] T003 [P] Review existing test suite in memora/tests/ to understand test patterns

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Extract shared utility functions to memora/api/utils.py (get_user_active_subscriptions, check_subscription_access)
- [ ] T005 [P] Update import statements in extracted utility functions to use proper Frappe imports
- [ ] T006 [P] Add docstrings to utility functions in memora/api/utils.py
- [ ] T007 Verify utility functions work correctly by running existing tests that use them

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Developer Navigates to Relevant Code (Priority: P1) 🎯 MVP

**Goal**: Split the monolithic api.py file into domain-specific modules for improved navigation and maintainability.

**Independent Test**: Can be verified by checking that each API endpoint can be found in a logically named module file within 10 seconds of understanding which domain it belongs to.

### Implementation for User Story 1

- [ ] T008 [P] [US1] Create memora/api/subjects.py with get_subjects(), get_my_subjects(), get_game_tracks() functions
- [ ] T009 [P] [US1] Create memora/api/map_engine.py with get_map_data(), get_topic_details() functions
- [ ] T010 [P] [US1] Create memora/api/sessions.py with submit_session(), get_lesson_details() functions
- [ ] T011 [P] [US1] Create memora/api/srs.py with internal SRS helper functions (process_srs_batch, infer_rating, calculate_next_review, update_memory_tracker, update_srs_after_review, create_memory_tracker)
- [ ] T012 [P] [US1] Create memora/api/reviews.py with get_review_session(), submit_review_session(), get_mastery_counts() functions
- [ ] T013 [P] [US1] Create memora/api/profile.py with get_player_profile(), get_full_profile_stats() functions
- [ ] T014 [P] [US1] Create memora/api/quests.py with get_daily_quests() function
- [ ] T015 [P] [US1] Create memora/api/leaderboard.py with get_leaderboard(), update_subject_progression() functions
- [ ] T016 [P] [US1] Create memora/api/onboarding.py with get_academic_masters(), set_academic_profile() functions
- [ ] T017 [P] [US1] Create memora/api/store.py with get_store_items(), request_purchase() functions
- [ ] T018 [US1] Update memora/api/__init__.py to re-export all public @frappe.whitelist() functions from domain modules
- [ ] T019 [US1] Update relative imports in memora/api/map_engine.py to import from .utils (get_user_active_subscriptions, check_subscription_access)
- [ ] T020 [US1] Update relative imports in memora/api/sessions.py to import from .srs and .leaderboard
- [ ] T021 [US1] Update relative imports in memora/api/reviews.py to import from .srs, .leaderboard, .utils, and ..ai_engine
- [ ] T022 [US1] Update relative imports in memora/api/profile.py to import from .utils
- [ ] T023 [US1] Update relative imports in memora/api/leaderboard.py to import from .utils (if needed)
- [ ] T024 [US1] Update relative imports in memora/api/onboarding.py to import from .utils (if needed)
- [ ] T025 [US1] Update relative imports in memora/api/store.py to import from .utils
- [ ] T026 [US1] Add module-level docstrings to each domain module explaining its purpose
- [ ] T027 [US1] Verify each module file is under 400 lines of code (split if necessary)
- [ ] T028 [US1] Add inline comments explaining complex logic in each module
- [ ] T029 [US1] Create a README.md in memora/api/ directory explaining the module organization

**Checkpoint**: At this point, User Story 1 should be fully functional - the API is now modularized and developers can navigate to relevant code quickly

---

## Phase 4: User Story 2 - All Existing API Endpoints Function Correctly (Priority: P1)

**Goal**: Ensure all existing API functionality continues to work exactly as before with zero breaking changes.

**Independent Test**: Can be verified by running all existing tests and manually testing each API endpoint to confirm identical responses before and after reorganization.

### Tests for User Story 2 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T030 [P] [US2] Contract test for all API endpoints in memora/tests/test_api_contract.py
- [ ] T031 [P] [US2] Integration test for subject retrieval workflow in memora/tests/integration/test_subject_workflow.py
- [ ] T032 [P] [US2] Integration test for session submission workflow in memora/tests/integration/test_session_workflow.py
- [ ] T033 [P] [US2] Integration test for review session workflow in memora/tests/integration/test_review_workflow.py

### Implementation for User Story 2

- [ ] T034 [US2] Run existing test suite to verify no regressions (pytest memora/tests/)
- [ ] T035 [US2] Manually test all 15 API endpoints using Frappe API client or curl
- [ ] T036 [US2] Verify backward compatibility: test that code importing from memora.api still works
- [ ] T037 [US2] Test subscription access control across all modules (map_engine, sessions, reviews, profile, quests, leaderboard, onboarding, store)
- [ ] T038 [US2] Test SRS memory tracking after session submission and review completion
- [ ] T039 [US2] Test XP calculation and subject progression updates
- [ ] T040 [US2] Test leaderboard ranking for both all-time and weekly periods
- [ ] T041 [US2] Test daily quests generation and completion tracking
- [ ] T042 [US2] Test store item filtering (owned items, pending requests, grade/stream filtering)
- [ ] T043 [US2] Test academic profile setup and validation
- [ ] T044 [US2] Test AI distractor generation in review sessions
- [ ] T045 [US2] Test map data lazy loading for topic-based units
- [ ] T046 [US2] Test error handling and logging across all modules
- [ ] T047 [US2] Verify all @frappe.whitelist() decorators are present on public functions
- [ ] T048 [US2] Verify all function signatures (parameters, return types) match original api.py
- [ ] T049 [US2] Test database transaction handling in submit_session and submit_review_session
- [ ] T050 [US2] Test self-healing logic for orphaned memory tracker records
- [ ] T051 [US2] Test focus mode (topic-specific reviews) vs daily mix reviews
- [ ] T052 [US2] Verify no circular import errors exist between modules
- [ ] T053 [US2] Test that all imports resolve correctly (both absolute and relative)
- [ ] T054 [US2] Run quickstart.md validation if available

**Checkpoint**: All user stories should now be independently functional - the API reorganization is complete and all functionality works correctly

---

## Phase 5: User Story 3 - Shared Utilities Are Accessible Across Modules (Priority: P2)

**Goal**: Ensure shared helper functions are properly organized and accessible across all modules without duplication.

**Independent Test**: Can be verified by confirming helper functions are defined once in utils.py and imported where needed, with no duplicate function definitions across modules.

### Implementation for User Story 3

- [ ] T055 [P] [US3] Audit all domain modules to identify any duplicate helper functions
- [ ] T056 [US3] Move any duplicate helpers to memora/api/utils.py
- [ ] T057 [US3] Update all modules to import shared utilities from .utils
- [ ] T058 [US3] Verify no duplicate function definitions exist across module files
- [ ] T059 [US3] Test that updating a utility function in utils.py affects all modules using it
- [ ] T060 [US3] Add comprehensive docstrings to all utility functions explaining their purpose and usage
- [ ] T061 [US3] Create unit tests for utility functions in memora/tests/test_api_utils.py

**Checkpoint**: All user stories should now be independently functional - shared utilities are properly organized and accessible

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T062 [P] Update documentation in docs/ to reflect new API structure
- [ ] T063 [P] Update API contracts in specs/002-api-reorganization/contracts/api-openapi.yaml if needed
- [ ] T064 [P] Add inline comments explaining the module organization strategy
- [ ] T065 Code cleanup and refactoring (remove any unused imports or variables)
- [ ] T066 Performance optimization across all stories (verify no performance degradation)
- [ ] T067 [P] Additional unit tests for complex logic in memora/tests/unit/
- [ ] T068 Security hardening (verify all access control checks remain in place)
- [ ] T069 Run quickstart.md validation
- [ ] T070 Create migration guide for developers transitioning from old api.py to new modular structure
- [ ] T071 Update any external documentation or developer guides that reference api.py
- [ ] T072 Consider deprecating the original memora/api.py file after successful migration

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (Phase 3): Can start after Foundational - No dependencies on other stories
  - User Story 2 (Phase 4): Depends on User Story 1 completion (must have modules created first)
  - User Story 3 (Phase 5): Can start after User Story 1 completion (modules must exist to audit)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on User Story 1 - Must have modules created before testing endpoints
- **User Story 3 (P2)**: Depends on User Story 1 - Must have modules created before auditing for duplicates

### Within Each User Story

- Models before services (not applicable - this is code reorganization, not new models)
- Services before endpoints (not applicable - endpoints are being moved, not created)
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all domain module creation tasks (T008-T017) can run in parallel
- All import update tasks within a module can be done together
- All testing tasks in User Story 2 marked [P] can run in parallel
- All audit tasks in User Story 3 marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all domain module creation tasks together:
Task: "Create memora/api/subjects.py with get_subjects(), get_my_subjects(), get_game_tracks() functions"
Task: "Create memora/api/map_engine.py with get_map_data(), get_topic_details() functions"
Task: "Create memora/api/sessions.py with submit_session(), get_lesson_details() functions"
Task: "Create memora/api/srs.py with internal SRS helper functions"
Task: "Create memora/api/reviews.py with get_review_session(), submit_review_session(), get_mastery_counts() functions"
Task: "Create memora/api/profile.py with get_player_profile(), get_full_profile_stats() functions"
Task: "Create memora/api/quests.py with get_daily_quests() function"
Task: "Create memora/api/leaderboard.py with get_leaderboard(), update_subject_progression() functions"
Task: "Create memora/api/onboarding.py with get_academic_masters(), set_academic_profile() functions"
Task: "Create memora/api/store.py with get_store_items(), request_purchase() functions"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Verify modules are created and organized correctly
5. Review module structure with team

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test module organization → Review code structure
3. Add User Story 2 → Test all endpoints → Verify zero breaking changes
4. Add User Story 3 → Audit and consolidate utilities → Verify no duplicates
5. Complete Polish → Final documentation and cleanup

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: Create subjects.py, map_engine.py, sessions.py
   - Developer B: Create srs.py, reviews.py, profile.py
   - Developer C: Create quests.py, leaderboard.py, onboarding.py, store.py
3. Team reviews and consolidates imports
4. Team tests all endpoints together (User Story 2)
5. Team audits for duplicate utilities (User Story 3)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (if tests are included)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- **Critical**: All function signatures and @frappe.whitelist() decorators must be preserved exactly
- **Critical**: All imports must be updated to use relative imports for internal package dependencies
- **Critical**: The ai_engine import must use `from ..ai_engine import get_ai_distractors` (sibling package)
- **Critical**: Each module file should not exceed 400 lines of code
- **Critical**: Zero breaking changes - all existing functionality must work identically

---

## Module Size Targets

Based on the data-model.md analysis:

- `api/__init__.py`: 30-50 lines (re-exports only)
- `api/utils.py`: 100-150 lines (shared utilities)
- `api/subjects.py`: 150-200 lines (3 public functions)
- `api/map_engine.py`: 350-400 lines (2 public functions with complex logic)
- `api/sessions.py`: 100-150 lines (2 public functions)
- `api/srs.py`: 200-250 lines (7 internal helper functions)
- `api/reviews.py`: 350-400 lines (2 public functions + 1 helper with AI integration)
- `api/profile.py`: 200-250 lines (2 public functions with stats calculations)
- `api/quests.py`: 120-150 lines (1 public function)
- `api/leaderboard.py`: 150-200 lines (1 public function + 1 helper)
- `api/onboarding.py`: 100-150 lines (2 public functions)
- `api/store.py`: 150-200 lines (2 public functions)

**Total estimated lines**: ~1,900-2,200 lines (similar to original api.py but better organized)

---

## Risk Mitigation

### Risk 1: Breaking existing functionality
- **Mitigation**: Comprehensive testing in User Story 2, manual verification of all endpoints
- **Fallback**: Keep original api.py as backup until migration is verified

### Risk 2: Circular import errors
- **Mitigation**: Follow dependency graph strictly, use utils.py for shared functions, avoid cross-module imports
- **Detection**: Run Python import checker after each module creation

### Risk 3: Missing function signatures or decorators
- **Mitigation**: Careful review during module creation, automated comparison with original api.py
- **Verification**: Contract tests in User Story 2

### Risk 4: Performance degradation
- **Mitigation**: No logic changes, only file reorganization, performance testing in User Story 2
- **Monitoring**: Compare response times before and after reorganization

---

## Success Criteria Verification

After completing all tasks, verify the following success criteria from spec.md:

- [ ] **SC-001**: Developers can locate any API endpoint's source code within 30 seconds by navigating to the appropriate domain module
- [ ] **SC-002**: 100% of existing API endpoints return identical responses before and after reorganization
- [ ] **SC-003**: No duplicate function definitions exist across the reorganized module files
- [ ] **SC-004**: Each module file contains no more than 400 lines of code
- [ ] **SC-005**: All existing automated tests pass without modification (or with only import path updates)
- [ ] **SC-006**: New developers can understand the API organization from file/folder names alone without reading documentation
