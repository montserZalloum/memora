# Tasks: Atomic JSON Content Generation & CDN Distribution

**Input**: Design documents from `/specs/008-atomic-content-cdn/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Constitution Gate IV requires TDD for access calculator enhancements and file generators. Test tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- Include exact file paths in descriptions

## Path Conventions (Frappe App Structure)

- **DocTypes**: `memora/memora/doctype/{doctype_name}/`
- **Services**: `memora/services/cdn_export/`
- **Tests**: `memora/tests/unit/cdn_export/`
- **Schemas**: `memora/services/cdn_export/schemas/`

---

## Phase 1: Setup

**Purpose**: Copy JSON Schema contracts and prepare test infrastructure

- [x] T001 [P] Copy manifest.schema.json from specs/008-atomic-content-cdn/contracts/ to memora/services/cdn_export/schemas/
- [x] T002 [P] Copy subject_hierarchy.schema.json from specs/008-atomic-content-cdn/contracts/ to memora/services/cdn_export/schemas/
- [x] T003 [P] Copy subject_bitmap.schema.json from specs/008-atomic-content-cdn/contracts/ to memora/services/cdn_export/schemas/
- [x] T004 [P] Copy topic.schema.json from specs/008-atomic-content-cdn/contracts/ to memora/services/cdn_export/schemas/
- [x] T005 [P] Copy lesson.schema.json from specs/008-atomic-content-cdn/contracts/ to memora/services/cdn_export/schemas/
- [x] T006 Create test fixtures directory memora/tests/fixtures/cdn_export/ with sample DocType data

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DocType changes and access calculator enhancements required by ALL user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### DocType Schema Updates

- [x] T007 Add "Set Access Level" and "Set Linear" options to action field in memora/memora/doctype/memora_plan_override/memora_plan_override.json
- [x] T008 Run bench migrate to apply DocType changes

### Access Calculator Enhancements (TDD Required - Constitution Gate IV)

- [x] T009 Write unit tests for "Set Access Level" override action in memora/tests/unit/cdn_export/test_access_calculator.py
- [x] T010 Write unit tests for "Set Linear" override action in memora/tests/unit/cdn_export/test_access_calculator.py
- [x] T011 Implement "Set Access Level" override in calculate_access_level() in memora/services/cdn_export/access_calculator.py
- [x] T012 Implement "Set Linear" override handling (new function calculate_linear_mode()) in memora/services/cdn_export/access_calculator.py
- [x] T013 Verify all access calculator tests pass with pytest memora/tests/unit/cdn_export/test_access_calculator.py

**Checkpoint**: Foundation ready - DocType updated, access calculator enhanced, tests passing

---

## Phase 3: User Story 1 - Student Loads Subject Content (Priority: P1) 🎯 MVP

**Goal**: Generate manifest.json with subject list, access levels, and hierarchy/bitmap URLs

**Independent Test**: Fetch manifest.json for a plan and verify it contains all expected subjects with correct access levels and navigation URLs (hierarchy_url, bitmap_url)

### Tests for User Story 1 (TDD Required)

- [x] T014 [P] [US1] Write unit test for generate_manifest_atomic() validating subjects array structure in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T015 [P] [US1] Write unit test for manifest including hierarchy_url and bitmap_url per subject in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T016 [P] [US1] Write unit test for empty subjects array when plan has no subjects in memora/tests/unit/cdn_export/test_json_generator.py

### Implementation for User Story 1

- [x] T017 [US1] Create generate_manifest_atomic() function in memora/services/cdn_export/json_generator.py (new function, preserve existing generate_manifest for backward compat)
- [x] T018 [US1] Update manifest structure to include hierarchy_url, bitmap_url per subject (data-model.md section 1)
- [x] T019 [US1] Validate generated manifest against manifest.schema.json using jsonschema
- [x] T020 [US1] Verify User Story 1 tests pass with pytest memora/tests/unit/cdn_export/test_json_generator.py -k manifest

**Checkpoint**: Manifest generation working, independently testable

---

## Phase 4: User Story 2 - Student Navigates Subject Hierarchy (Priority: P1)

**Goal**: Generate {subject_id}_h.json with tracks → units → topics structure, NO lessons embedded

**Independent Test**: Fetch subject hierarchy JSON and verify structure matches tracks/units/topics with correct access inheritance, is_linear flags, and topic_url references

### Tests for User Story 2 (TDD Required)

- [x] T021 [P] [US2] Write unit test for generate_subject_hierarchy() excluding lessons from output in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T022 [P] [US2] Write unit test for is_linear flag at every hierarchy level in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T023 [P] [US2] Write unit test for topic_url generation pointing to topic JSON files in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T024 [P] [US2] Write unit test for Hidden nodes excluded from hierarchy in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T025 [P] [US2] Write unit test for access level inheritance (paid subject → paid children) in memora/tests/unit/cdn_export/test_json_generator.py

### Implementation for User Story 2

- [x] T026 [US2] Create generate_subject_hierarchy() function in memora/services/cdn_export/json_generator.py (replaces monolithic generate_subject_json for hierarchy)
- [x] T027 [US2] Implement is_linear extraction from DocTypes and apply "Set Linear" overrides
- [x] T028 [US2] Generate topic_url values pointing to plans/{plan_id}/{topic_id}.json
- [x] T029 [US2] Calculate lesson_count per topic without loading lesson details
- [x] T030 [US2] Add stats block (total_tracks, total_units, total_topics, total_lessons)
- [x] T031 [US2] Validate generated hierarchy against subject_hierarchy.schema.json
- [x] T032 [US2] Verify User Story 2 tests pass with pytest memora/tests/unit/cdn_export/test_json_generator.py -k hierarchy

**Checkpoint**: Hierarchy generation working, lessons excluded, independently testable

---

## Phase 5: User Story 3 - Student Accesses Topic Lessons (Priority: P1)

**Goal**: Generate {topic_id}.json with lesson list, bit_index references, and lesson_url pointers

**Independent Test**: Fetch topic JSON and verify lesson list with correct bit_indices and lesson_url values

### Tests for User Story 3 (TDD Required)

- [x] T033 [P] [US3] Write unit test for generate_topic_json() with lessons array in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T034 [P] [US3] Write unit test for bit_index included per lesson in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T035 [P] [US3] Write unit test for lesson_url pointing to shared lessons/{lesson_id}.json in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T036 [P] [US3] Write unit test for parent breadcrumb (unit_id, track_id, subject_id) in topic JSON in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T037 [P] [US3] Write unit test for hidden lessons excluded from topic in memora/tests/unit/cdn_export/test_json_generator.py

### Implementation for User Story 3

- [x] T038 [US3] Create generate_topic_json() function in memora/services/cdn_export/json_generator.py
- [x] T039 [US3] Include parent breadcrumb (unit, track, subject) in topic JSON
- [x] T040 [US3] Generate lesson_url values pointing to lessons/{lesson_id}.json
- [x] T041 [US3] Include stage_count per lesson without loading full stage data
- [x] T042 [US3] Apply plan overrides for lesson visibility (Hide action)
- [x] T043 [US3] Validate generated topic against topic.schema.json
- [x] T044 [US3] Verify User Story 3 tests pass with pytest memora/tests/unit/cdn_export/test_json_generator.py -k topic

**Checkpoint**: Topic generation working, independently testable

---

## Phase 6: User Story 4 - Student Plays Lesson Content (Priority: P1)

**Goal**: Generate shared {lesson_id}.json with stages, NO access block (access determined by topic)

**Independent Test**: Fetch lesson JSON and verify all stages present with type, weight, target_time, is_skippable, config

### Tests for User Story 4 (TDD Required)

- [x] T045 [P] [US4] Write unit test for generate_lesson_json_shared() with stages array in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T046 [P] [US4] Write unit test verifying NO access block in shared lesson JSON in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T047 [P] [US4] Write unit test verifying NO parent block in shared lesson JSON in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T048 [P] [US4] Write unit test for navigation.is_standalone=true in lesson JSON in memora/tests/unit/cdn_export/test_json_generator.py
- [x] T049 [P] [US4] Write unit test for stage fields (idx, title, type, weight, target_time, is_skippable, config) in memora/tests/unit/cdn_export/test_json_generator.py

### Implementation for User Story 4

- [x] T050 [US4] Create generate_lesson_json_shared() function in memora/services/cdn_export/json_generator.py
- [x] T051 [US4] Remove access block from lesson JSON (plan-agnostic)
- [x] T052 [US4] Remove parent block from lesson JSON (plan-agnostic)
- [x] T053 [US4] Add navigation.is_standalone=true to lesson JSON
- [x] T054 [US4] Ensure stage config is properly serialized (JSON within JSON)
- [x] T055 [US4] Validate generated lesson against lesson.schema.json
- [x] T056 [US4] Verify User Story 4 tests pass with pytest memora/tests/unit/cdn_export/test_json_generator.py -k lesson_shared

**Checkpoint**: Shared lesson generation working, no access/parent blocks, independently testable

---

## Phase 7: User Story 5 - Content Admin Triggers Regeneration (Priority: P2)

**Goal**: Update batch processor to generate atomic files with two-phase commit for consistency

**Independent Test**: Modify a subject and verify affected plans are queued, all atomic files are generated, and atomic consistency is maintained

### Tests for User Story 5 (TDD Required)

- [ ] T057 [P] [US5] Write unit test for generate_bitmap_json() structure (subject_id, mappings) in memora/tests/unit/cdn_export/test_json_generator.py
- [ ] T058 [P] [US5] Write test for atomic consistency - staging then swap in memora/tests/unit/cdn_export/test_atomic_consistency.py
- [ ] T059 [P] [US5] Write test for rollback on generation failure in memora/tests/unit/cdn_export/test_atomic_consistency.py
- [ ] T060 [P] [US5] Write test for get_atomic_content_paths_for_plan() returning correct file paths in memora/tests/unit/cdn_export/test_batch_processor.py

### Implementation for User Story 5

- [ ] T061 [US5] Create generate_bitmap_json() function in memora/services/cdn_export/json_generator.py
- [ ] T062 [US5] Include all lesson bit_index mappings with topic_id reference
- [ ] T063 [US5] Validate generated bitmap against subject_bitmap.schema.json
- [ ] T064 [US5] Create get_atomic_content_paths_for_plan() function in memora/services/cdn_export/json_generator.py
- [ ] T065 [US5] Update _rebuild_plan() in memora/services/cdn_export/batch_processor.py to use atomic generators
- [ ] T066 [US5] Implement two-phase commit: write to staging (.tmp suffix) then atomic rename
- [ ] T067 [US5] Implement rollback: delete staging files on failure
- [ ] T068 [US5] Update file paths: plans/{plan_id}/ for plan-specific, lessons/ for shared
- [ ] T069 [US5] Verify User Story 5 tests pass with pytest memora/tests/unit/cdn_export/test_batch_processor.py -k atomic

**Checkpoint**: Batch processor updated, atomic consistency implemented, independently testable

---

## Phase 8: User Story 6 - System Enforces Access Control (Priority: P2)

**Goal**: Ensure access_level fields differ correctly according to inheritance rules and overrides

**Independent Test**: Compare JSON outputs for different plans and verify access_level fields follow inheritance rules and override precedence

### Tests for User Story 6

- [ ] T070 [P] [US6] Write integration test for paid subject → all children inherit "paid" in memora/tests/unit/cdn_export/test_access_calculator.py
- [ ] T071 [P] [US6] Write integration test for is_free_preview piercing (node + descendants → free_preview) in memora/tests/unit/cdn_export/test_access_calculator.py
- [ ] T072 [P] [US6] Write integration test for is_sold_separately creating independent paid island in memora/tests/unit/cdn_export/test_access_calculator.py
- [ ] T073 [P] [US6] Write integration test for override precedence (override > flag > inheritance) in memora/tests/unit/cdn_export/test_access_calculator.py
- [ ] T074 [P] [US6] Write integration test for required_item propagation to children in memora/tests/unit/cdn_export/test_access_calculator.py

### Implementation for User Story 6

- [ ] T075 [US6] Ensure required_item is included in access block when access_level is "paid" in all generators
- [ ] T076 [US6] Verify is_sold_separately creates independent access scope (track-level)
- [ ] T077 [US6] Verify override precedence: Set Access Level > Set Free > is_free_preview > required_item > inheritance
- [ ] T078 [US6] Verify User Story 6 tests pass with pytest memora/tests/unit/cdn_export/test_access_calculator.py -k integration

**Checkpoint**: Access control inheritance verified, override precedence correct

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, backward compatibility, and documentation

- [ ] T079 [P] Update memora/services/cdn_export/__init__.py exports for new functions
- [ ] T080 [P] Add deprecation warning to old generate_subject_json() pointing to new atomic functions
- [ ] T081 Mark old subjects/ directory for cleanup (create migration script)
- [ ] T082 Update change_tracker.py doc_events to queue plans for atomic regeneration
- [ ] T083 [P] Add logging for atomic file generation steps in batch_processor.py
- [ ] T084 Run full test suite: pytest memora/tests/unit/cdn_export/ -v
- [ ] T085 Verify quickstart.md examples work with new atomic file structure
- [ ] T086 Update CLAUDE.md with 008-atomic-content-cdn feature documentation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phases 3-8)**: All depend on Foundational completion
  - US1-US4 (P1): Can proceed in parallel or sequentially
  - US5-US6 (P2): Can start after Foundational, or after US1-US4
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

| User Story | Depends On | Can Run With |
|------------|------------|--------------|
| US1 (Manifest) | Foundational | US2, US3, US4 |
| US2 (Hierarchy) | Foundational | US1, US3, US4 |
| US3 (Topic) | Foundational | US1, US2, US4 |
| US4 (Lesson) | Foundational | US1, US2, US3 |
| US5 (Regeneration) | US1, US2, US3, US4 | US6 |
| US6 (Access Control) | Foundational | US1-US5 |

### Within Each User Story

1. Write tests FIRST (TDD - Constitution Gate IV)
2. Verify tests FAIL before implementation
3. Implement until tests pass
4. Validate with schema
5. Story complete → checkpoint

### Parallel Opportunities

**Phase 1**: All T001-T006 can run in parallel (different files)

**Phase 2**: T009-T010 tests can run in parallel (different test cases)

**Phase 3-8**: Within each story, all test tasks [P] can run in parallel

**Cross-Story**: US1, US2, US3, US4 can be developed in parallel by different developers

---

## Parallel Example: User Story 2

```bash
# Launch all US2 tests in parallel:
pytest memora/tests/unit/cdn_export/test_json_generator.py::test_generate_subject_hierarchy_excludes_lessons &
pytest memora/tests/unit/cdn_export/test_json_generator.py::test_hierarchy_is_linear_at_every_level &
pytest memora/tests/unit/cdn_export/test_json_generator.py::test_hierarchy_topic_url_generation &
pytest memora/tests/unit/cdn_export/test_json_generator.py::test_hidden_nodes_excluded &
pytest memora/tests/unit/cdn_export/test_json_generator.py::test_access_inheritance &
wait
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (schemas copied)
2. Complete Phase 2: Foundational (DocType + access calculator)
3. Complete Phase 3: User Story 1 (manifest generation)
4. **STOP and VALIDATE**: Generate manifest.json and verify structure
5. Minimal viable product: Plans have manifest with subject list

### Incremental Delivery

1. **Setup + Foundational** → Foundation ready
2. **Add US1** → Test manifest generation → MVP!
3. **Add US2** → Test hierarchy generation → Navigation working
4. **Add US3** → Test topic generation → Lesson lists working
5. **Add US4** → Test lesson generation → Full content flow
6. **Add US5** → Test batch processor → Admin regeneration working
7. **Add US6** → Verify access control → Security complete
8. **Polish** → Cleanup and documentation

### Parallel Team Strategy

With 4 developers after Foundational complete:

- Developer A: User Story 1 (Manifest)
- Developer B: User Story 2 (Hierarchy)
- Developer C: User Story 3 (Topic)
- Developer D: User Story 4 (Lesson)

Then:
- All join for US5 (Batch Processor) + US6 (Access Control)
- Finally: Polish phase

---

## Summary

| Phase | Tasks | Test Tasks | Parallel Tasks |
|-------|-------|------------|----------------|
| Setup | 6 | 0 | 5 |
| Foundational | 7 | 2 | 0 |
| US1 (P1) | 7 | 3 | 3 |
| US2 (P1) | 12 | 5 | 5 |
| US3 (P1) | 12 | 5 | 5 |
| US4 (P1) | 12 | 5 | 5 |
| US5 (P2) | 13 | 4 | 4 |
| US6 (P2) | 9 | 5 | 5 |
| Polish | 8 | 0 | 3 |
| **Total** | **86** | **29** | **35** |

**MVP Scope**: Phases 1-3 (US1 only) = 20 tasks
**Full Feature**: All 86 tasks

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [USx] label maps task to specific user story
- TDD required (Constitution Gate IV) - tests before implementation
- Each story independently testable at its checkpoint
- Commit after each task or logical group
- Schema validation required for all generated JSON
