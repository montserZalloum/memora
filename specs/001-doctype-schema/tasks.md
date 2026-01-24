# Tasks: Memora DocType Schema Creation

**Input**: Design documents from `/specs/001-doctype-schema/`
**Prerequisites**: plan.md (required), spec.md (required), data-model.md, research.md, quickstart.md

**Tests**: No explicit test tasks (schema verification via `bench migrate` per quickstart.md)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This is a Frappe Custom App with the following structure:
- **App root**: `memora/` (inside bench/apps/)
- **Module**: `memora/memora/`
- **Services**: `memora/services/schema/`
- **Tests**: `memora/tests/`

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure and schema infrastructure

- [ ] T001 Create services/schema directory structure with `__init__.py` files in memora/services/ and memora/services/schema/
- [ ] T002 [P] Create constants module with CONTENT_MIXIN_FIELDS definition in memora/services/schema/constants.py
- [ ] T003 [P] Create doctype_utils module with helper functions (create_doctype, log_operation) in memora/services/schema/doctype_utils.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core schema infrastructure that MUST be complete before user story DocTypes

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create migration_runner module with `run_migration()` entry point and atomic transaction wrapper in memora/services/schema/migration_runner.py
- [ ] T005 Update hooks.py to register after_migrate hook pointing to `memora.services.schema.migration_runner.run_migration` in memora/hooks.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Administrator Deploys Memora App (Priority: P1) MVP

**Goal**: All 19 DocTypes are automatically created when `bench migrate` runs

**Independent Test**: Run `bench migrate` on a fresh site and verify all 19 DocTypes exist with correct fields and indexes

### Child Table DocTypes (must be created first)

- [ ] T006 [P] [US1] Define Memora Lesson Stage child table (istable=1) with title, type (Select), config (JSON) in memora/services/schema/definitions/child_tables.py
- [ ] T007 [P] [US1] Define Memora Plan Subject child table (istable=1) with subject (Link), sort_order in memora/services/schema/definitions/child_tables.py
- [ ] T008 [P] [US1] Define Memora Plan Override child table (istable=1) with target_doctype (Link to DocType), target_name (Dynamic Link), action (Select), override_value in memora/services/schema/definitions/child_tables.py
- [ ] T009 [P] [US1] Define Memora Grant Component child table (istable=1) with target_doctype (Link to DocType), target_name (Dynamic Link) in memora/services/schema/definitions/child_tables.py
- [ ] T010 [P] [US1] Define Memora Player Device child table (istable=1) with device_id, device_name, is_trusted in memora/services/schema/definitions/child_tables.py

### Educational Content DocTypes

- [ ] T011 [P] [US1] Define Memora Subject DocType with autoname: field:title, title, color_code, and mixin fields in memora/services/schema/definitions/content_doctypes.py
- [ ] T012 [P] [US1] Define Memora Track DocType with parent_subject (indexed Link), is_sold_separately, and mixin fields in memora/services/schema/definitions/content_doctypes.py
- [ ] T013 [P] [US1] Define Memora Unit DocType with parent_track (indexed Link), badge_image, and mixin fields in memora/services/schema/definitions/content_doctypes.py
- [ ] T014 [P] [US1] Define Memora Topic DocType with parent_unit (indexed Link) and mixin fields in memora/services/schema/definitions/content_doctypes.py
- [ ] T015 [P] [US1] Define Memora Lesson DocType with parent_topic (indexed Link), stages (Table to Memora Lesson Stage), and mixin fields in memora/services/schema/definitions/content_doctypes.py

### Planning & Products DocTypes

- [ ] T016 [P] [US1] Define Memora Season DocType with autoname: field:title, is_published, start_date, end_date in memora/services/schema/definitions/planning_doctypes.py
- [ ] T017 [P] [US1] Define Memora Stream DocType with autoname: field:title, title field in memora/services/schema/definitions/planning_doctypes.py
- [ ] T018 [P] [US1] Define Memora Academic Plan DocType with season (indexed), stream (indexed), subjects (Table), overrides (Table) in memora/services/schema/definitions/planning_doctypes.py
- [ ] T019 [P] [US1] Define Memora Product Grant DocType with item_code (indexed Link to Item), academic_plan (indexed), grant_type, unlocked_components (Table) in memora/services/schema/definitions/planning_doctypes.py

### Player Profile DocTypes

- [ ] T020 [P] [US1] Define Memora Player Profile DocType with user (unique indexed Link), display_name, avatar, current_plan (indexed), devices (Table) in memora/services/schema/definitions/player_doctypes.py
- [ ] T021 [P] [US1] Define Memora Player Wallet DocType with player (unique indexed Link), total_xp, current_streak, last_played_at in memora/services/schema/definitions/player_doctypes.py

### Engine & Logs DocTypes

- [ ] T022 [P] [US1] Define Memora Interaction Log DocType with player (indexed), academic_plan (indexed), question_id (indexed), answer fields, is_correct, time_taken, timestamp in memora/services/schema/definitions/engine_doctypes.py
- [ ] T023 [P] [US1] Define Memora Memory State DocType with player (indexed), question_id (indexed), stability, difficulty, next_review (indexed Datetime), state (Select) in memora/services/schema/definitions/engine_doctypes.py

### Commerce DocTypes

- [ ] T024 [P] [US1] Define Memora Subscription Transaction DocType with naming_series, player (indexed), transaction_type, payment_method, status, amount, related_grant (indexed), erpnext_invoice in memora/services/schema/definitions/commerce_doctypes.py

### Integration

- [ ] T025 [US1] Create doctype_definitions.py that imports and exports all DocType definitions in correct order (child tables first) in memora/services/schema/doctype_definitions.py
- [ ] T026 [US1] Update migration_runner.py to iterate through DOCTYPE_DEFINITIONS and create each DocType with logging in memora/services/schema/migration_runner.py
- [ ] T027 [US1] Verify migration by running `bench migrate` and confirming all 19 DocTypes exist

**Checkpoint**: User Story 1 complete - all 19 DocTypes can be created via migration

---

## Phase 4: User Story 2 - Content Manager Creates Educational Hierarchy (Priority: P2)

**Goal**: Content hierarchy DocTypes work correctly in Frappe Desk with proper linking

**Independent Test**: Create Subject > Track > Unit > Topic > Lesson > Lesson Stages via Frappe Desk

### Desk UI Enhancements

- [ ] T028 [P] [US2] Add form_grid_templates configuration for Lesson Stage child table display in memora/services/schema/definitions/content_doctypes.py
- [ ] T029 [P] [US2] Verify sort_order field is indexed on all content DocTypes for ordering queries in memora/services/schema/definitions/content_doctypes.py
- [ ] T030 [US2] Test content hierarchy creation via Frappe Desk: create Subject, Track, Unit, Topic, Lesson with Lesson Stages

**Checkpoint**: User Story 2 complete - content hierarchy can be created and navigated in Desk

---

## Phase 5: User Story 3 - Academic Planner Configures Plans and Products (Priority: P2)

**Goal**: Academic Plans with override system and Product Grants work correctly

**Independent Test**: Create Season, Stream, Academic Plan with subjects/overrides, and Product Grant

### Dynamic Link Filter Scripts

- [ ] T031 [P] [US3] Create client script for Plan Override to filter target_doctype to Track/Unit/Topic/Lesson in memora/memora/doctype/memora_plan_override/memora_plan_override.js
- [ ] T032 [P] [US3] Create client script for Grant Component to filter target_doctype to Subject/Track/Unit/Topic/Lesson in memora/memora/doctype/memora_grant_component/memora_grant_component.js
- [ ] T033 [US3] Test Academic Plan creation with subjects table and override rules via Frappe Desk
- [ ] T034 [US3] Test Product Grant creation linking ERPNext Item to Academic Plan with grant components

**Checkpoint**: User Story 3 complete - academic planning and commerce linking works

---

## Phase 6: User Story 4 - System Tracks Player Progress with FSRS (Priority: P2)

**Goal**: Player Profile, Wallet, and Memory State DocTypes support FSRS algorithm

**Independent Test**: Create Player Profile linked to User, verify Memory State with indexed next_review field

### Player System Verification

- [ ] T035 [P] [US4] Verify Player Profile has unique constraint on user field in memora/services/schema/definitions/player_doctypes.py
- [ ] T036 [P] [US4] Verify Player Wallet has unique constraint on player field in memora/services/schema/definitions/player_doctypes.py
- [ ] T037 [US4] Verify Memory State next_review field has search_index=1 for FSRS scheduling performance in memora/services/schema/definitions/engine_doctypes.py
- [ ] T038 [US4] Test Player Profile creation with devices child table via Frappe Desk
- [ ] T039 [US4] Test Memory State creation and verify next_review index exists in database

**Checkpoint**: User Story 4 complete - player system and FSRS schema ready

---

## Phase 7: User Story 5 - System Logs Interactions and Processes Transactions (Priority: P3)

**Goal**: Interaction Logs and Subscription Transactions work correctly

**Independent Test**: Create Interaction Logs and Subscription Transactions with proper naming series

### Commerce Verification

- [ ] T040 [P] [US5] Verify Interaction Log has proper indexes on player, academic_plan, question_id in memora/services/schema/definitions/engine_doctypes.py
- [ ] T041 [P] [US5] Verify Subscription Transaction naming_series produces SUB-TX-YYYY-##### format in memora/services/schema/definitions/commerce_doctypes.py
- [ ] T042 [US5] Test Interaction Log creation with all required fields via console
- [ ] T043 [US5] Test Subscription Transaction creation and verify naming series format (e.g., SUB-TX-2026-00001)

**Checkpoint**: User Story 5 complete - logging and commerce transactions work

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation

- [ ] T044 Run full migration test on fresh site: `bench new-site test.local && bench --site test.local install-app memora && bench --site test.local migrate`
- [ ] T045 Verify idempotency: run `bench --site test.local migrate` multiple times without errors
- [ ] T046 [P] Verify all 19 DocTypes exist with correct field counts via console script
- [ ] T047 [P] Verify all indexed fields have database indexes via SQL query
- [ ] T048 Run quickstart.md test scenarios to validate all user stories
- [ ] T049 Clean up test site: `bench drop-site test.local --force`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (Phase 3) must complete before US2-5 can be verified
  - US2, US3, US4 can proceed in parallel after US1
  - US5 depends on US3 (Product Grant) and US4 (Player Profile)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundational - no dependencies on other stories (MVP)
- **User Story 2 (P2)**: Requires US1 DocTypes (Subject, Track, Unit, Topic, Lesson)
- **User Story 3 (P2)**: Requires US1 DocTypes (Season, Stream, Academic Plan, Product Grant)
- **User Story 4 (P2)**: Requires US1 DocTypes (Player Profile, Player Wallet, Memory State)
- **User Story 5 (P3)**: Requires US4 (Player Profile) and US3 (Product Grant)

### Within Each User Story

- Child table definitions before parent DocType definitions
- DocType definitions before integration tasks
- Integration before verification tests

### Parallel Opportunities

**Phase 1 Setup (all parallel)**:
```
T002 (constants) | T003 (doctype_utils)
```

**Phase 3 Child Tables (all parallel)**:
```
T006 (Lesson Stage) | T007 (Plan Subject) | T008 (Plan Override) | T009 (Grant Component) | T010 (Player Device)
```

**Phase 3 Content DocTypes (all parallel)**:
```
T011 (Subject) | T012 (Track) | T013 (Unit) | T014 (Topic) | T015 (Lesson)
```

**Phase 3 Planning DocTypes (all parallel)**:
```
T016 (Season) | T017 (Stream) | T018 (Academic Plan) | T019 (Product Grant)
```

**Phase 3 Player/Engine DocTypes (all parallel)**:
```
T020 (Player Profile) | T021 (Player Wallet) | T022 (Interaction Log) | T023 (Memory State) | T024 (Subscription Transaction)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 - All 19 DocType definitions
4. **STOP and VALIDATE**: Run `bench migrate` and verify all DocTypes exist
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational Foundation ready
2. Add User Story 1 Test via migrate Deploy/Demo (MVP!)
3. Add User Story 2 Test content hierarchy Deploy/Demo
4. Add User Story 3 Test academic plans Deploy/Demo
5. Add User Story 4 Test player/FSRS Deploy/Demo
6. Add User Story 5 Test logging/commerce Deploy/Demo
7. Each story adds value without breaking previous stories

### Single Developer Strategy

Execute phases sequentially:
1. Phase 1 + 2: Setup and Foundation
2. Phase 3: All DocType definitions (T006-T027)
3. Phase 4-7: Verification and UI enhancements
4. Phase 8: Polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Child tables MUST be defined before parent DocTypes reference them
- All DocType definitions go in `memora/services/schema/definitions/` directory
- Verify tests use `bench migrate` and Frappe Desk, not unit tests
- Commit after each task or logical group
