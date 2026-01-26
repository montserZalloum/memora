# Tasks: Progress Tracking and Smart Unlocking Engine (Bitset Edition)

**Input**: Design documents from `/specs/005-progress-engine-bitset/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required per Constitution Principle IV (Logic Verification - TDD for unlock and XP logic)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md (Frappe app module extension):
- **DocTypes**: `memora/memora/doctype/{doctype_name}/`
- **Services**: `memora/services/progress_engine/`
- **API**: `memora/api/`
- **Tests**: `memora/tests/unit/progress_engine/`, `memora/tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and service directory structure

- [X] T001 Create progress_engine service directory structure in memora/services/progress_engine/
- [X] T002 [P] Create __init__.py with module exports in memora/services/progress_engine/__init__.py
- [X] T003 [P] Create test directories in memora/tests/unit/progress_engine/ and memora/tests/integration/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema changes and core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Schema Modifications

- [X] T004 [P] Add `next_bit_index` field to Memora Subject in memora/memora/doctype/memora_subject/memora_subject.json
- [X] T005 [P] Add `bit_index` field to Memora Lesson in memora/memora/doctype/memora_lesson/memora_lesson.json
- [X] T006 [P] Add `is_linear` field to Memora Topic in memora/memora/doctype/memora_topic/memora_topic.json
- [X] T007 [P] Add `passed_lessons_bitset` field to Memora Structure Progress in memora/memora/doctype/memora_structure_progress/memora_structure_progress.json

### Lesson Controller Logic

- [X] T008 Implement before_insert hook for bit_index assignment in memora/memora/doctype/memora_lesson/memora_lesson.py

### Core Bitmap Manager

- [X] T009 [P] Write unit tests for bitmap operations (set_bit, check_bit, get_bitmap) in memora/tests/unit/progress_engine/test_bitmap_manager.py
- [X] T010 Implement bitmap_manager.py with set_bit, check_bit, get_bitmap, mark_dirty functions in memora/services/progress_engine/bitmap_manager.py

### JSON Structure Enhancement

- [X] T011 Update json_generator.py to include `bit_index` and `is_linear` in subject JSON output in memora/services/cdn_export/json_generator.py

### Migration Script

- [X] T012 Create migration script to backfill bit_index for existing lessons in memora/services/progress_engine/migration.py

**Checkpoint**: Foundation ready - Schema changes applied, bitmap manager working, JSON includes progress fields

---

## Phase 3: User Story 1 - Complete a Lesson and Track Progress (Priority: P1) 🎯 MVP

**Goal**: Students can complete lessons and have their progress recorded instantly with XP rewards

**Independent Test**: Complete a lesson via API, verify bitmap updated in Redis, XP added to wallet

### Tests for User Story 1

- [X] T013 [P] [US1] Write unit tests for XP calculation (first completion, hearts bonus) in memora/tests/unit/progress_engine/test_xp_calculator.py
- [X] T014 [P] [US1] Write contract test for complete_lesson endpoint in memora/tests/contract/test_progress_api.py
- [X] T015 [P] [US1] Write integration test for lesson completion flow in memora/tests/integration/test_lesson_completion.py

### Implementation for User Story 1

- [X] T016 [US1] Implement xp_calculator.py with calculate_xp function (base + hearts bonus) in memora/services/progress_engine/xp_calculator.py
- [X] T017 [US1] Implement complete_lesson API endpoint in memora/api/progress.py
- [X] T018 [US1] Add hearts validation (check player has hearts > 0) in complete_lesson endpoint
- [X] T019 [US1] Integrate XP award with Memora Player Wallet in complete_lesson endpoint
- [X] T020 [US1] Add interaction logging for lesson completion events in memora/api/progress.py

**Checkpoint**: Students can complete lessons, receive XP, progress is tracked in Redis

---

## Phase 4: User Story 2 - View Progress with Unlock States (Priority: P1)

**Goal**: Students can view their complete progress with accurate Passed/Unlocked/Locked states for all nodes

**Independent Test**: Request progress API, verify all nodes have correct status based on bitmap and is_linear rules

### Tests for User Story 2

- [X] T021 [P] [US2] Write unit tests for unlock_calculator (linear rules) in memora/tests/unit/progress_engine/test_unlock_calculator.py
- [X] T022 [P] [US2] Write unit tests for unlock_calculator (non-linear rules) in memora/tests/unit/progress_engine/test_unlock_calculator.py
- [X] T023 [P] [US2] Write unit tests for container state computation in memora/tests/unit/progress_engine/test_unlock_calculator.py
- [X] T024 [P] [US2] Write contract test for get_progress endpoint in memora/tests/contract/test_progress_api.py
- [X] T025 [P] [US2] Write integration test for progress retrieval in memora/tests/integration/test_progress_retrieval.py

### Implementation for User Story 2

- [X] T026 [US2] Implement structure_loader.py with LRU-cached JSON loading in memora/services/progress_engine/structure_loader.py
- [X] T027 [US2] Implement unlock_calculator.py with compute_node_states function in memora/services/progress_engine/unlock_calculator.py
- [X] T028 [US2] Implement linear unlock logic (prev sibling must be passed) in unlock_calculator.py
- [X] T029 [US2] Implement non-linear unlock logic (all children unlock when parent unlocks) in unlock_calculator.py
- [X] T030 [US2] Implement container state computation (Passed only if ALL children Passed) in unlock_calculator.py
- [X] T031 [US2] Implement progress_computer.py orchestrating bitmap + structure + unlock in memora/services/progress_engine/progress_computer.py
- [X] T032 [US2] Implement get_progress API endpoint in memora/api/progress.py
- [X] T033 [US2] Calculate and return completion_percentage in get_progress response

**Checkpoint**: Students can view full progress tree with accurate unlock states

---

## Phase 5: User Story 3 - Continue Learning with Next-Up Suggestion (Priority: P1)

**Goal**: Progress API returns suggested_next_lesson_id for "Continue Learning" button

**Independent Test**: Request progress, verify suggested_next_lesson_id points to first unlocked (not passed) lesson

### Tests for User Story 3

- [X] T034 [P] [US3] Write unit tests for next_lesson_finder in memora/tests/unit/progress_engine/test_next_lesson_finder.py
- [X] T035 [P] [US3] Write integration test for suggested_next_lesson_id in memora/tests/integration/test_next_lesson.py

### Implementation for User Story 3

- [X] T036 [US3] Implement find_next_lesson function (first Unlocked not Passed in tree order) in memora/services/progress_engine/progress_computer.py
- [X] T037 [US3] Add suggested_next_lesson_id to get_progress response in memora/api/progress.py
- [X] T038 [US3] Handle edge cases: all passed (return null), empty subject (return null) in progress_computer.py

**Checkpoint**: Continue Learning feature fully functional

---

## Phase 6: User Story 4 - Replay Lesson for Record-Breaking Bonus (Priority: P2)

**Goal**: Students can replay passed lessons and earn bonus XP if they beat their previous best hearts

**Independent Test**: Replay a passed lesson with more hearts, verify only differential bonus XP awarded

### Tests for User Story 4

- [X] T039 [P] [US4] Write unit tests for record-breaking XP calculation in memora/tests/unit/progress_engine/test_xp_calculator.py
- [X] T040 [P] [US4] Write integration test for replay bonus XP in memora/tests/integration/test_replay_bonus.py

### Implementation for User Story 4

- [X] T041 [US4] Implement best_hearts storage in Redis (best_hearts:{player}:{subject} key) in memora/services/progress_engine/bitmap_manager.py
- [X] T042 [US4] Extend xp_calculator.py with record-breaking bonus logic in memora/services/progress_engine/xp_calculator.py
- [X] T043 [US4] Update complete_lesson to detect replay and calculate bonus XP in memora/api/progress.py
- [X] T044 [US4] Return is_new_record and is_first_completion flags in complete_lesson response

**Checkpoint**: Mastery loop with record-breaking bonuses working

---

## Phase 7: User Story 5, 6, 7 - Content Management Resilience (Priority: P2)

**Goal**: Lesson reordering, deletion, and addition don't break progress tracking

**Independent Test**: Reorder/delete/add lessons, verify existing student progress intact

### Tests for User Stories 5, 6, 7

- [X] T045 [P] [US5] Write integration test for progress after lesson reordering in memora/tests/integration/test_content_changes.py
- [X] T046 [P] [US6] Write integration test for progress after lesson deletion in memora/tests/integration/test_content_changes.py
- [X] T047 [P] [US7] Write integration test for progress after new lesson addition in memora/tests/integration/test_content_changes.py

### Implementation for User Stories 5, 6, 7

- [X] T048 [US5] Verify unlock_calculator uses bit_index (immutable) not sort_order for completion check
- [X] T049 [US6] Ensure deleted lessons (not in JSON) are gracefully skipped in progress_computer.py
- [X] T050 [US7] Verify new lessons get unique bit_index from subject counter in memora_lesson.py before_insert

**Checkpoint**: Content changes don't affect existing student progress

---

## Phase 8: User Story 8 - System Recovery After Failure (Priority: P3)

**Goal**: Progress data recoverable from MariaDB if Redis cache fails

**Independent Test**: Clear Redis, request progress, verify data loaded from MariaDB snapshot

### Tests for User Story 8

- [X] T051 [P] [US8] Write unit tests for cache_warmer in memora/tests/unit/progress_engine/test_cache_warmer.py
- [X] T052 [P] [US8] Write unit tests for snapshot_syncer in memora/tests/unit/progress_engine/test_snapshot_syncer.py
- [X] T053 [P] [US8] Write integration test for cache miss recovery in memora/tests/integration/test_cache_recovery.py

### Implementation for User Story 8

- [X] T054 [US8] Implement cache_warmer.py with warm_from_mariadb function in memora/services/progress_engine/cache_warmer.py
- [X] T055 [US8] Implement snapshot_syncer.py with sync_pending_bitmaps function in memora/services/progress_engine/snapshot_syncer.py
- [X] T056 [US8] Add scheduler hook for 30-second sync job in memora/hooks.py
- [X] T057 [US8] Integrate cache warming into bitmap_manager.get_bitmap (fallback on cache miss)
- [X] T058 [US8] Update best_hearts to also sync to MariaDB snapshot in snapshot_syncer.py

**Checkpoint**: Full durability - Redis can fail and recover without data loss

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T059 [P] Add API endpoint docstrings and type hints in memora/api/progress.py
- [X] T060 [P] Add logging throughout progress_engine services
- [X] T061 Run performance benchmark (target: <20ms for 1000 lessons)
- [X] T062 [P] Update quickstart.md with actual measured benchmarks in specs/005-progress-engine-bitset/quickstart.md
- [X] T063 Security review: validate all API inputs, check player enrollment
- [X] T064 Run full test suite and fix any failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
- **Polish (Phase 9)**: Depends on at least US1-US3 being complete

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 (Complete Lesson) | Foundational | - |
| US2 (View Progress) | Foundational | US1 |
| US3 (Next-Up) | US2 (needs unlock logic) | - |
| US4 (Replay Bonus) | US1 (needs complete_lesson) | US2, US3 |
| US5/6/7 (Content Resilience) | Foundational | US1, US2, US3, US4 |
| US8 (Recovery) | US1 (needs bitmap writes) | US2, US3, US4 |

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Core logic before API integration
3. Happy path before edge cases
4. Story complete before moving to next priority

### Parallel Opportunities

```
Phase 2 (Foundational):
  T004 || T005 || T006 || T007  (all schema changes in parallel)
  T009 || T011                   (tests and JSON update in parallel)

Phase 3 (US1):
  T013 || T014 || T015          (all US1 tests in parallel)

Phase 4 (US2):
  T021 || T022 || T023 || T024 || T025  (all US2 tests in parallel)

Phase 5 (US3):
  T034 || T035                  (US3 tests in parallel)

Phase 6 (US4):
  T039 || T040                  (US4 tests in parallel)

Phase 7 (US5/6/7):
  T045 || T046 || T047          (content change tests in parallel)

Phase 8 (US8):
  T051 || T052 || T053          (recovery tests in parallel)
```

---

## Parallel Example: User Story 2 (Unlock Logic)

```bash
# Launch all US2 tests together:
Task: "Write unit tests for unlock_calculator (linear rules)" [T021]
Task: "Write unit tests for unlock_calculator (non-linear rules)" [T022]
Task: "Write unit tests for container state computation" [T023]
Task: "Write contract test for get_progress endpoint" [T024]
Task: "Write integration test for progress retrieval" [T025]

# Then implement sequentially:
T026 → T027 → T028 → T029 → T030 → T031 → T032 → T033
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US1 - Complete Lesson
4. Complete Phase 4: US2 - View Progress
5. Complete Phase 5: US3 - Next-Up Suggestion
6. **STOP and VALIDATE**: Full progress read/write flow working
7. Deploy/demo MVP

### Incremental Delivery

| Increment | Stories | Value Delivered |
|-----------|---------|-----------------|
| MVP | US1 + US2 + US3 | Core progress tracking and viewing |
| V1.1 | + US4 | Mastery loop with replay bonuses |
| V1.2 | + US5/6/7 | Content management resilience |
| V1.3 | + US8 | Full durability and recovery |

### Suggested MVP Scope

**User Stories 1, 2, 3** deliver:
- Lesson completion with XP
- Full progress tree with unlock states
- Continue Learning functionality

This is a complete, testable, deployable increment.

---

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | 64 |
| Setup Tasks | 3 |
| Foundational Tasks | 9 |
| US1 Tasks | 8 |
| US2 Tasks | 13 |
| US3 Tasks | 5 |
| US4 Tasks | 6 |
| US5/6/7 Tasks | 6 |
| US8 Tasks | 8 |
| Polish Tasks | 6 |
| Parallel Opportunities | 28 tasks marked [P] |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to user story for traceability
- Each user story independently testable after completion
- Constitution Principle IV requires TDD for unlock_calculator and xp_calculator
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
