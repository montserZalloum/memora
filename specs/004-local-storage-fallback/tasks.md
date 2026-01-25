# Tasks: Local Content Staging & Fallback Engine

**Input**: Design documents from `/specs/004-local-storage-fallback/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Unit and integration tests included as specified in plan.md constitution check (Test-First approach).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md project structure:
- **Service modules**: `memora/services/cdn_export/`
- **DocTypes**: `memora/memora/doctype/`
- **Tests**: `memora/tests/unit/` and `memora/tests/integration/`
- **Hooks**: `memora/hooks.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: DocType modifications and base module scaffolding

- [X] T001 Add `local_fallback_mode` field to CDN Settings DocType in `memora/memora/doctype/cdn_settings/cdn_settings.json`
- [X] T002 [P] Add `local_path`, `local_hash`, `cdn_hash`, `sync_verified` fields to CDN Sync Log DocType in `memora/memora/doctype/cdn_sync_log/cdn_sync_log.json`
- [X] T003 [P] Create empty module file `memora/services/cdn_export/local_storage.py` with docstring
- [X] T004 [P] Create empty module file `memora/services/cdn_export/url_resolver.py` with docstring
- [X] T005 [P] Create empty module file `memora/services/cdn_export/health_checker.py` with docstring
- [X] T006 Run `bench --site x.conanacademy.com migrate` to apply DocType changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement `get_local_base_path()` function in `memora/services/cdn_export/local_storage.py`
- [X] T008 Implement `check_disk_space()` function in `memora/services/cdn_export/local_storage.py`
- [X] T009 [P] Implement `get_cdn_settings()` cached settings function in `memora/services/cdn_export/url_resolver.py`
- [X] T010 [P] Add `on_update` hook to invalidate settings cache in `memora/memora/doctype/cdn_settings/cdn_settings.py`
- [X] T011 Update `memora/services/cdn_export/__init__.py` to export new modules

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Automatic Local Backup (Priority: P1) MVP

**Goal**: Every generated JSON file is saved to local disk first with atomic writes and version retention

**Independent Test**: Generate a JSON file and verify it exists at `/sites/x.conanacademy.com/public/memora_content/` with correct content

### Tests for User Story 1

- [X] T012 [P] [US1] Create unit test file `memora/tests/unit/test_local_storage.py` with test class structure
- [X] T013 [P] [US1] Write test `test_write_content_file_creates_directory` in `memora/tests/unit/test_local_storage.py`
- [X] T014 [P] [US1] Write test `test_write_content_file_atomic_write` in `memora/tests/unit/test_local_storage.py`
- [X] T015 [P] [US1] Write test `test_write_content_file_creates_prev_version` in `memora/tests/unit/test_local_storage.py`
- [X] T016 [P] [US1] Write test `test_write_content_file_fails_on_low_disk` in `memora/tests/unit/test_local_storage.py`
- [X] T017 [P] [US1] Write test `test_file_exists_returns_correct_value` in `memora/tests/unit/test_local_storage.py`
- [X] T018 [P] [US1] Write test `test_get_file_hash_returns_md5` in `memora/tests/unit/test_local_storage.py`

### Implementation for User Story 1

- [X] T019 [US1] Implement `write_content_file(path, data)` with atomic write pattern in `memora/services/cdn_export/local_storage.py`
- [X] T020 [US1] Add version retention logic (`.prev` files) to `write_content_file()` in `memora/services/cdn_export/local_storage.py`
- [X] T021 [P] [US1] Implement `file_exists(path)` in `memora/services/cdn_export/local_storage.py`
- [X] T022 [P] [US1] Implement `get_file_hash(path)` using MD5 in `memora/services/cdn_export/local_storage.py`
- [X] T023 [US1] Integrate local storage write into `get_content_paths_for_plan()` in `memora/services/cdn_export/json_generator.py`
- [X] T024 [US1] Add error logging for file operation failures in `memora/services/cdn_export/local_storage.py`
- [X] T025 [US1] Run tests: `bench --site x.conanacademy.com run-tests --module memora.tests.unit.test_local_storage`

**Checkpoint**: User Story 1 complete - local files are now created atomically with version retention

---

## Phase 4: User Story 2 - Instant URL Fallback (Priority: P1)

**Goal**: System returns local or CDN URLs based on settings, with immediate propagation

**Independent Test**: Toggle CDN enable setting and verify URLs change within 1 second

### Tests for User Story 2

- [X] T026 [P] [US2] Create unit test file `memora/tests/unit/test_url_resolver.py` with test class structure
- [X] T027 [P] [US2] Write test `test_get_content_url_returns_cdn_when_enabled` in `memora/tests/unit/test_url_resolver.py`
- [X] T028 [P] [US2] Write test `test_get_content_url_returns_local_when_disabled` in `memora/tests/unit/test_url_resolver.py`
- [X] T029 [P] [US2] Write test `test_get_content_url_returns_local_when_fallback_mode` in `memora/tests/unit/test_url_resolver.py`
- [X] T030 [P] [US2] Write test `test_settings_cache_invalidated_on_save` in `memora/tests/unit/test_url_resolver.py`

### Implementation for User Story 2

- [X] T031 [US2] Implement `get_content_url(path)` with CDN/local logic in `memora/services/cdn_export/url_resolver.py`
- [X] T032 [US2] Implement `invalidate_settings_cache()` in `memora/services/cdn_export/url_resolver.py`
- [X] T033 [US2] Update `generate_manifest()` to use `get_content_url()` for subject URLs in `memora/services/cdn_export/json_generator.py`
- [X] T034 [US2] Update `generate_subject_json()` to use `get_content_url()` for internal links in `memora/services/cdn_export/json_generator.py`
- [X] T035 [US2] Run tests: `bench --site x.conanacademy.com run-tests --module memora.tests.unit.test_url_resolver`

**Checkpoint**: User Story 2 complete - URLs switch immediately when settings change

---

## Phase 5: User Story 3 - CDN Sync from Local (Priority: P2)

**Goal**: CDN upload reads from local files with hash verification for 100% consistency

**Independent Test**: Generate content locally, trigger sync, compare file hashes

### Tests for User Story 3

- [X] T036 [P] [US3] Create integration test file `memora/tests/integration/test_local_cdn_sync.py`
- [X] T037 [P] [US3] Write test `test_cdn_upload_reads_from_local_file` in `memora/tests/integration/test_local_cdn_sync.py`
- [X] T038 [P] [US3] Write test `test_sync_records_local_and_cdn_hashes` in `memora/tests/integration/test_local_cdn_sync.py`
- [X] T039 [P] [US3] Write test `test_sync_detects_hash_mismatch` in `memora/tests/integration/test_local_cdn_sync.py`

### Implementation for User Story 3

- [X] T040 [US3] Modify `upload_json()` to read from local file instead of memory in `memora/services/cdn_export/cdn_uploader.py`
- [X] T041 [US3] Add `local_path` tracking to sync process in `memora/services/cdn_export/batch_processor.py`
- [X] T042 [US3] Record `local_hash` and `cdn_hash` in CDN Sync Log after upload in `memora/services/cdn_export/batch_processor.py`
- [X] T043 [US3] Implement hash comparison and set `sync_verified` flag in `memora/services/cdn_export/batch_processor.py`
- [X] T044 [US3] Run tests: `bench --site x.conanacademy.com run-tests --module memora.tests.integration.test_local_cdn_sync`

**Checkpoint**: User Story 3 complete - CDN content is verified identical to local

---

## Phase 6: User Story 4 - Health Monitoring (Priority: P2)

**Goal**: Scheduled health checks with disk monitoring and admin alerts

**Independent Test**: Run health check and verify it reports missing files and disk status

### Tests for User Story 4

- [X] T045 [P] [US4] Create unit test file `memora/tests/unit/test_health_checker.py`
- [X] T046 [P] [US4] Write test `test_hourly_check_skips_outside_business_hours` in `memora/tests/unit/test_health_checker.py`
- [X] T047 [P] [US4] Write test `test_hourly_check_samples_files` in `memora/tests/unit/test_health_checker.py`
- [X] T048 [P] [US4] Write test `test_daily_scan_finds_missing_files` in `memora/tests/unit/test_health_checker.py`
- [X] T049 [P] [US4] Write test `test_daily_scan_finds_orphan_files` in `memora/tests/unit/test_health_checker.py`
- [X] T050 [P] [US4] Write test `test_disk_alert_sent_below_threshold` in `memora/tests/unit/test_health_checker.py`

### Implementation for User Story 4

- [X] T051 [US4] Implement `is_business_hours()` helper in `memora/services/cdn_export/health_checker.py`
- [X] T052 [US4] Implement `hourly_health_check()` with file sampling in `memora/services/cdn_export/health_checker.py`
- [X] T053 [US4] Implement `daily_full_scan()` with database comparison in `memora/services/cdn_export/health_checker.py`
- [X] T054 [US4] Implement `send_disk_alert()` using Frappe notifications in `memora/services/cdn_export/health_checker.py`
- [X] T055 [US4] Implement `send_sync_failure_alert()` for retry exhaustion in `memora/services/cdn_export/health_checker.py`
- [X] T056 [US4] Add scheduler hooks for hourly and daily jobs in `memora/hooks.py`
- [X] T057 [US4] Implement exponential backoff retry logic in `memora/services/cdn_export/batch_processor.py`
- [X] T058 [US4] Add Dead Letter status transition after retry exhaustion in `memora/services/cdn_export/batch_processor.py`
- [X] T059 [US4] Run tests: `bench --site x.conanacademy.com run-tests --module memora.tests.unit.test_health_checker`

**Checkpoint**: User Story 4 complete - health monitoring active with admin alerts

---

## Phase 7: User Story 5 - Automatic Cleanup (Priority: P3)

**Goal**: Local files deleted when content is deleted from backend

**Independent Test**: Delete a Plan/Subject/Unit and verify local files are removed

### Tests for User Story 5

- [X] T060 [P] [US5] Write test `test_delete_content_file_removes_file_and_prev` in `memora/tests/unit/test_local_storage.py`
- [X] T061 [P] [US5] Write test `test_delete_content_directory_removes_all` in `memora/tests/unit/test_local_storage.py`
- [X] T062 [P] [US5] Write test `test_delete_removes_empty_parent_dirs` in `memora/tests/unit/test_local_storage.py`

### Implementation for User Story 5

- [X] T063 [US5] Implement `delete_content_file(path)` in `memora/services/cdn_export/local_storage.py`
- [X] T064 [US5] Implement `delete_content_directory(path)` for plan folders in `memora/services/cdn_export/local_storage.py`
- [X] T065 [US5] Add `on_trash` hook to Memora Academic Plan to delete local plan folder in `memora/memora/doctype/memora_academic_plan/memora_academic_plan.py`
- [X] T066 [US5] Add `on_trash` hook to Memora Subject to delete local subject file in `memora/memora/doctype/memora_subject/memora_subject.py`
- [X] T067 [US5] Add `on_trash` hook to Memora Unit to delete local unit file in `memora/memora/doctype/memora_unit/memora_unit.py`
- [X] T068 [US5] Add `on_trash` hook to Memora Lesson to delete local lesson file in `memora/memora/doctype/memora_lesson/memora_lesson.py`
- [X] T069 [US5] Run tests: `bench --site x.conanacademy.com run-tests --module memora.tests.unit.test_local_storage`

**Checkpoint**: User Story 5 complete - orphan files automatically cleaned up

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and improvements across all stories

- [X] T070 [P] Add comprehensive docstrings to all public functions in `memora/services/cdn_export/local_storage.py`
- [X] T071 [P] Add comprehensive docstrings to all public functions in `memora/services/cdn_export/url_resolver.py`
- [X] T072 [P] Add comprehensive docstrings to all public functions in `memora/services/cdn_export/health_checker.py`
- [ ] T073 Run full test suite: `bench --site x.conanacademy.com run-tests --app memora`
- [ ] T074 Validate quickstart.md scenarios manually
- [ ] T075 Performance test: Verify <500ms local file write time
- [ ] T076 Performance test: Verify <1s URL switch propagation
- [X] T077 Update module exports in `memora/services/cdn_export/__init__.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 - complete US1 first as US2 depends on local files existing
  - US3 depends on US1 (local files must exist)
  - US4 can start after US1 (needs local storage module)
  - US5 can start after US1 (needs delete functions)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
        │
        ▼
    US1 (P1) ◀─────────── MVP: Local backup working
        │
        ├──────▶ US2 (P1): URL resolver (can start after US1 T019-T024)
        │
        ├──────▶ US3 (P2): CDN sync (needs US1 complete)
        │
        ├──────▶ US4 (P2): Health monitoring (can start after US1)
        │
        └──────▶ US5 (P3): Cleanup (can start after US1)
```

### Within Each User Story

1. Tests written first (FAIL before implementation)
2. Core functions before integrations
3. Run tests to verify (PASS after implementation)

### Parallel Opportunities

**Phase 1 (Setup)**:
- T002, T003, T004, T005 can all run in parallel

**Phase 2 (Foundational)**:
- T009, T010 can run in parallel

**User Story Tests**:
- All tests within a story marked [P] can run in parallel

**User Story Implementation**:
- T021, T022 can run in parallel (after T019)
- US3, US4, US5 can potentially start in parallel after US1 core is done

---

## Parallel Example: User Story 1

```bash
# Launch all tests for US1 together:
T012, T013, T014, T015, T016, T017, T018  # All [P] - parallel

# After tests written, implement core:
T019  # write_content_file - sequential (core)
T020  # version retention - sequential (extends T019)

# Then parallel utilities:
T021, T022  # file_exists, get_file_hash - parallel

# Then integration and validation:
T023, T024, T025  # sequential
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (DocType changes)
2. Complete Phase 2: Foundational (base utilities)
3. Complete Phase 3: User Story 1 (local backup)
4. Complete Phase 4: User Story 2 (URL fallback)
5. **STOP and VALIDATE**: Both P1 stories are working
6. Deploy/demo - system now has local backup + fallback capability

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 → Local backup working → Deploy (MVP!)
3. Add US2 → URL fallback working → Deploy
4. Add US3 → CDN consistency verified → Deploy
5. Add US4 → Monitoring active → Deploy
6. Add US5 → Automatic cleanup → Deploy (Feature complete)

### Task Count Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Setup | 6 | DocType changes, module scaffolding |
| Foundational | 5 | Core utilities |
| US1 | 14 | Local backup (7 tests + 7 impl) |
| US2 | 10 | URL fallback (5 tests + 5 impl) |
| US3 | 9 | CDN sync (4 tests + 5 impl) |
| US4 | 15 | Health monitoring (6 tests + 9 impl) |
| US5 | 10 | Cleanup (3 tests + 7 impl) |
| Polish | 8 | Validation, performance |
| **Total** | **77** | |

---

## Notes

- [P] tasks = different files, no dependencies
- [USn] label maps task to specific user story
- Tests use Frappe test framework pattern
- Run `bench --site x.conanacademy.com migrate` after DocType changes
- Commit after each logical group of tasks
- Performance targets: <500ms file write, <1s URL propagation
