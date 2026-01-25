# Tasks: CDN Content Export System

**Input**: Design documents from `/specs/002-cdn-content-export/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Constitution requires TDD for access inheritance algorithm and override merging (Principle IV). Unit tests included for those critical components.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md, this is a Frappe app with structure:
- **DocTypes**: `memora/memora/doctype/`
- **Services**: `memora/services/cdn_export/`
- **API**: `memora/api/`
- **Hooks**: `memora/hooks.py`
- **Tests**: `memora/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Add boto3 dependency to pyproject.toml
- [X] T002 [P] Create services directory structure at memora/services/cdn_export/__init__.py
- [X] T003 [P] Create test directory structure at memora/tests/unit/cdn_export/__init__.py
- [X] T004 [P] Create integration test directory at memora/tests/integration/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### DocTypes

- [X] T005 Create CDN Settings Single DocType at memora/memora/doctype/cdn_settings/cdn_settings.json with fields per data-model.md
- [X] T006 [P] Create CDN Settings controller at memora/memora/doctype/cdn_settings/cdn_settings.py with validation logic
- [X] T007 [P] Create CDN Sync Log DocType at memora/memora/doctype/cdn_sync_log/cdn_sync_log.json with indexed fields per data-model.md
- [X] T008 [P] Create CDN Sync Log controller at memora/memora/doctype/cdn_sync_log/cdn_sync_log.py

### Schema Updates

- [x] T009 Add is_public field (Check) to Memora Subject DocType at memora/memora/doctype/memora_subject/memora_subject.json
- [x] T010 [P] Add required_item field (Link to Item) to Memora Subject DocType
- [x] T011 [P] Add required_item field (Link to Item) to Memora Track DocType at memora/memora/doctype/memora_track/memora_track.json
- [x] T012 [P] Add parent_item_required field (Check) to Memora Track DocType

### Core Services

- [X] T013 Implement CDN client factory in memora/services/cdn_export/cdn_uploader.py with get_cdn_client() and test_connection()
- [X] T014 [P] Implement Redis queue management in memora/services/cdn_export/change_tracker.py with add_plan_to_queue(), get_pending_plans(), MariaDB fallback
- [X] T015 [P] Implement Redis locking in memora/services/cdn_export/change_tracker.py with acquire_lock(), release_lock(), move_to_dead_letter()

### Unit Tests (TDD Required)

- [X] T016 [P] Write unit tests for access calculator (FAIL first) in memora/tests/unit/cdn_export/test_access_calculator.py covering all access level scenarios
- [X] T017 [P] Write unit tests for dependency resolver (FAIL first) in memora/tests/unit/cdn_export/test_dependency_resolver.py covering hierarchy traversal

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Automatic Content Sync on Changes (Priority: P1) 🎯 MVP

**Goal**: When content is created/updated in Frappe, CDN JSON files are automatically regenerated within 5-minute batch window

**Independent Test**: Create/modify a lesson in Frappe, verify JSON appears on CDN with correct content within batch cycle

### Implementation for User Story 1

- [X] T018 [US1] Implement dependency resolver in memora/services/cdn_export/dependency_resolver.py with get_affected_plan_ids() per research.md
- [X] T019 [US1] Implement JSON generator base in memora/services/cdn_export/json_generator.py with generate_manifest(), generate_subject_json(), generate_unit_json(), generate_lesson_json()
- [X] T020 [US1] Implement upload functions in memora/services/cdn_export/cdn_uploader.py with upload_json(), delete_json(), delete_folder()
- [X] T021 [US1] Implement batch processor in memora/services/cdn_export/batch_processor.py with process_pending_plans(), rebuild_plan() orchestration
- [X] T022 [US1] Add doc_events to memora/hooks.py for content DocTypes (Subject, Track, Unit, Topic, Lesson, Lesson Stage) calling change_tracker handlers
- [X] T023 [US1] Add scheduler_events to memora/hooks.py with cron "*/5 * * * *" calling batch_processor.process_pending_plans
- [X] T024 [US1] Add threshold trigger check in change_tracker.py to enqueue immediate processing when 50 plans reached

**Checkpoint**: User Story 1 complete - content changes trigger CDN sync within 5 minutes

---

## Phase 4: User Story 2 - Plan-Specific Content Generation (Priority: P1)

**Goal**: Exported content respects plan-specific overrides and hides content per plan configuration

**Independent Test**: Create two plans sharing a subject with different overrides, verify each plan's JSON only includes visible content

### Implementation for User Story 2

- [X] T025 [US2] Implement access calculator in memora/services/cdn_export/access_calculator.py with calculate_access_level() per research.md (must pass T016 tests)
- [X] T026 [US2] Implement override processor in memora/services/cdn_export/access_calculator.py with apply_plan_overrides() handling Hide, Set Free, Set Sold Separately actions
- [X] T027 [US2] Update json_generator.py to call access_calculator for each node and exclude hidden content
- [X] T028 [US2] Update json_generator.py to inject access control fields (is_published, access_level, required_item, is_sold_separately, parent_item_required) per contracts/
- [X] T029 [US2] Add doc_events for Memora Plan Override to hooks.py triggering plan rebuild on override changes

**Checkpoint**: User Stories 1 AND 2 complete - plan-specific content with correct access levels

---

## Phase 5: User Story 3 - Content Deletion Handling (Priority: P2)

**Goal**: Trashed/deleted content is removed from CDN and parent references are updated

**Independent Test**: Trash a lesson, verify parent unit JSON no longer references it and lesson JSON is removed from CDN

### Implementation for User Story 3

- [X] T030 [US3] Implement on_content_delete handler in memora/services/cdn_export/change_tracker.py handling on_trash and after_delete events
- [X] T031 [US3] Implement on_restore handler in change_tracker.py treating restore as new insert
- [X] T032 [US3] Implement delete_plan_folder() in cdn_uploader.py for complete plan deletion
- [X] T033 [US3] Add on_trash, after_delete, on_restore events to hooks.py doc_events for all content DocTypes
- [X] T034 [US3] Add plan deletion handling to hooks.py for Memora Academic Plan on_trash and after_delete

**Checkpoint**: User Story 3 complete - deletions properly clean up CDN

---

## Phase 6: User Story 4 - Access Control Metadata in JSON (Priority: P2)

**Goal**: JSON files contain all access control fields for frontend rendering

**Independent Test**: Generate JSON for paid content, verify all access metadata fields present with correct values

### Implementation for User Story 4

- [X] T035 [US4] Implement signed URL generation in memora/services/cdn_export/cdn_uploader.py with generate_signed_url() for video content (4-hour expiry)
- [X] T036 [US4] Update json_generator.py generate_lesson_json() to replace video URLs in stage config with signed URLs
- [X] T037 [US4] Validate generated JSON against contracts/manifest.schema.json, subject.schema.json, unit.schema.json, lesson.schema.json in batch_processor.py
- [X] T038 [P] [US4] Write contract tests in memora/tests/contract/test_json_schemas.py validating output against JSON schemas

**Checkpoint**: User Story 4 complete - full access control metadata in all JSON

---

## Phase 7: User Story 5 - Search Index Generation (Priority: P2)

**Goal**: Each plan has a search index JSON for client-side lesson search

**Independent Test**: Generate plan search index, verify it contains all lesson names with correct IDs

### Implementation for User Story 5

- [X] T039 [US5] Implement search indexer in memora/services/cdn_export/search_indexer.py with generate_search_index()
- [X] T040 [US5] Implement index sharding logic in search_indexer.py splitting by subject when >500 lessons
- [X] T041 [US5] Update batch_processor.py rebuild_plan() to call search_indexer after content JSON generation
- [X] T042 [US5] Validate generated search index against contracts/search_index.schema.json

**Checkpoint**: User Story 5 complete - search index available for all plans

---

## Phase 8: User Story 6 - Cache Invalidation on Updates (Priority: P2)

**Goal**: CDN cache is purged when files are updated, ensuring students see corrections immediately

**Independent Test**: Update a lesson, verify cache purge request sent and versioned URL changes

### Implementation for User Story 6

- [X] T043 [US6] Implement cache purge in memora/services/cdn_export/cdn_uploader.py with purge_cdn_cache() calling Cloudflare API
- [X] T044 [US6] Update cdn_uploader.py upload_json() to collect uploaded URLs for batch purge
- [X] T045 [US6] Update batch_processor.py to call purge_cdn_cache() after all uploads complete
- [X] T046 [US6] Implement version timestamp generation in json_generator.py for manifest version field

**Checkpoint**: User Story 6 complete - cache invalidation within 60 seconds

---

## Phase 9: User Story 7 - Monitoring and Error Visibility (Priority: P3)

**Goal**: Admins can view sync queue status and error logs via dashboard

**Independent Test**: Trigger CDN upload failure, verify error logged and visible in Frappe

### Implementation for User Story 7

- [X] T047 [US7] Implement CDN Sync Log creation in batch_processor.py for each plan build (status transitions per data-model.md)
- [X] T048 [US7] Implement retry logic in batch_processor.py with exponential backoff (3 retries, then dead-letter)
- [X] T049 [US7] Create admin API endpoints in memora/api/cdn_admin.py with get_queue_status(), get_recent_failures(), retry_dead_letter()
- [X] T050 [US7] Add dashboard page at memora/memora/page/cdn_export_dashboard/ showing queue count, recent logs, dead-letter items

**Checkpoint**: User Story 7 complete - full monitoring visibility

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T051 Write integration test in memora/tests/integration/test_cdn_export_flow.py covering full create->update->delete cycle
- [X] T052 [P] Add error handling and logging throughout all service modules using frappe.log_error()
- [X] T053 [P] Run memora/specs/002-cdn-content-export/quickstart.md validation - verify all setup steps work
- [X] T054 Update memora/hooks.py comments documenting all doc_events and scheduler_events
- [X] T055 Run bench migrate and verify all new DocTypes created successfully

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 priority - US2 depends on US1's json_generator
  - US3-US7 are P2/P3 - can proceed after US1+US2 foundation
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - Core sync mechanism
- **User Story 2 (P1)**: Depends on US1's json_generator - Adds access control layer
- **User Story 3 (P2)**: Can start after US1 - Independent deletion handling
- **User Story 4 (P2)**: Can start after US2 - Extends access metadata
- **User Story 5 (P2)**: Can start after US1 - Independent search index
- **User Story 6 (P2)**: Can start after US1 - Independent cache invalidation
- **User Story 7 (P3)**: Can start after US1 - Independent monitoring

### Within Each User Story

- Unit tests (T016, T017) MUST be written and FAIL before implementation (TDD per constitution)
- Services before hooks integration
- Core implementation before validation
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003, T004 (directory setup) can run in parallel
- T006, T007, T008 (DocType controllers) can run in parallel
- T009, T010, T011, T012 (schema updates) can run in parallel
- T014, T015 (Redis queue/lock) can run in parallel
- T016, T017 (unit tests) can run in parallel
- US3, US5, US6, US7 can be worked on in parallel after US1+US2 complete

---

## Parallel Example: User Story 1 + 2 (P1 Stories)

```bash
# After Foundational complete, launch US1 core:
Task: "Implement dependency resolver in memora/services/cdn_export/dependency_resolver.py"
Task: "Implement JSON generator base in memora/services/cdn_export/json_generator.py"

# After json_generator exists, US2 can start in parallel with US1 completion:
Task: "Implement access calculator in memora/services/cdn_export/access_calculator.py"
Task: "Implement override processor in memora/services/cdn_export/access_calculator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (basic sync works)
4. Complete Phase 4: User Story 2 (access control works)
5. **STOP and VALIDATE**: Test content sync with overrides
6. Deploy/demo if ready - core CDN export functional

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 + US2 → Test sync with access control → Deploy (MVP!)
3. Add US3 → Test deletion handling → Deploy
4. Add US4 + US5 + US6 in parallel → Test each → Deploy
5. Add US7 → Test monitoring → Deploy (Full feature)

### Parallel Team Strategy

With multiple developers after Foundational complete:
- Developer A: User Story 1 → User Story 2 (sequential, US2 depends on US1)
- Developer B: User Story 3 (deletion) after US1 core is done
- Developer C: User Story 5 (search index) after US1 core is done
- Developer D: User Story 6 (cache) after US1 core is done

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable after US1 foundation
- TDD required for access_calculator and dependency_resolver per constitution Principle IV
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Run `bench migrate` after DocType changes
- Use `frappe.enqueue()` for long-running tasks per research.md patterns
