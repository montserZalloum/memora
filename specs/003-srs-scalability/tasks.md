# Tasks: SRS High-Performance & Scalability Architecture

**Input**: Design documents from `/specs/003-srs-scalability/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/srs-api.yaml

**Tests**: Tests are included as this feature involves core SRS logic (Constitution: "If it touches Money or Grades, it must be tested").

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Frappe app**: `memora/` at repository root
- **API modules**: `memora/api/`
- **Services**: `memora/services/` (new)
- **DocTypes**: `memora/memora/doctype/`
- **Tests**: `memora/tests/`
- **Patches**: `memora/patches/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and services layer structure

- [x] T001 Create services package directory structure at memora/services/__init__.py
- [x] T002 [P] Create patches directory structure at memora/patches/v1_0/__init__.py
- [x] T003 [P] Verify Redis connectivity using redis-cli -p 13000 ping

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

### DocType Updates

- [x] T004 [P] Add new fields (partition_created, enable_redis, auto_archive) to Game Subscription Season DocType JSON at memora/memora/doctype/game_subscription_season/game_subscription_season.json
- [x] T005 [P] Update Player Memory Tracker DocType to make season field required at memora/memora/doctype/player_memory_tracker/player_memory_tracker.json
- [x] T006 Create Archived Memory Tracker DocType with all fields (player, season, question_id, stability, next_review_date, last_review_date, subject, topic, archived_at, eligible_for_deletion) at memora/memora/doctype/archived_memory_tracker/

### Core Service: SRSRedisManager

- [x] T007 Implement SRSRedisManager class with Redis connection handling in memora/services/srs_redis_manager.py
- [x] T008 Add add_item() method to SRSRedisManager for ZADD operations in memora/services/srs_redis_manager.py
- [x] T009 Add get_due_items() method to SRSRedisManager for ZRANGEBYSCORE operations in memora/services/srs_redis_manager.py
- [x] T010 Add remove_item() method to SRSRedisManager for ZREM operations in memora/services/srs_redis_manager.py
- [x] T011 Add is_available() health check method to SRSRedisManager in memora/services/srs_redis_manager.py
- [x] T012 Add batch operations (add_batch, get_all_scores) to SRSRedisManager in memora/services/srs_redis_manager.py

### Database Migration

- [x] T013 Run bench migrate to apply DocType changes
- [x] T014 Create data migration patch to set season for existing NULL records at memora/patches/v1_0/fix_null_seasons.py
- [x] T015 Create partitioning setup patch with LIST COLUMNS partitioning at memora/patches/v1_0/setup_partitioning.py
- [x] T016 Create composite index patch for Safe Mode queries (player, season, next_review_date) at memora/patches/v1_0/add_safe_mode_index.py

### Foundational Tests

- [x] T017 [P] Create test file for SRSRedisManager at memora/tests/test_srs_redis.py
- [x] T018 Write unit tests for add_item, get_due_items, remove_item, is_available in memora/tests/test_srs_redis.py

**Checkpoint**: Foundation ready - SRSRedisManager operational, DocTypes updated, partitioning applied

---

## Phase 3: User Story 1 - Student Retrieves Due Review Questions (Priority: P1)

**Goal**: Students can retrieve due review questions in <100ms using Redis cache with Safe Mode fallback

**Independent Test**: Request due reviews for a student with 1000+ tracked questions, verify response in <100ms

### Tests for User Story 1

- [x] T019 [P] [US1] Write test for get_review_session with cache hit in memora/tests/test_srs_redis.py
- [x] T020 [P] [US1] Write test for lazy loading on cache miss in memora/tests/test_srs_redis.py
- [x] T021 [P] [US1] Create Safe Mode test file at memora/tests/test_srs_safe_mode.py
- [x] T022 [US1] Write tests for Safe Mode fallback query in memora/tests/test_srs_safe_mode.py
- [x] T023 [US1] Write tests for rate limiting (500 req/min, 1 req/30s per user) in memora/tests/test_srs_safe_mode.py

### Implementation for User Story 1

- [x] T024 [US1] Add SafeModeManager class with is_safe_mode_active() method in memora/api/utils.py
- [x] T025 [US1] Add check_rate_limit() method with global and per-user limits in memora/api/utils.py
- [x] T026 [US1] Add get_reviews_safe_mode() fallback query function in memora/api/reviews.py
- [x] T027 [US1] Add _rehydrate_user_cache() lazy loading method to SRSRedisManager in memora/services/srs_redis_manager.py
- [x] T028 [US1] Modify get_review_session() to use SRSRedisManager.get_due_items() in memora/api/reviews.py
- [x] T029 [US1] Add Safe Mode fallback logic to get_review_session() with rate limiting in memora/api/reviews.py
- [x] T030 [US1] Add is_degraded flag to get_review_session() response in memora/api/reviews.py
- [x] T031 [US1] Add subject filtering support to Redis queries in memora/api/reviews.py

**Checkpoint**: User Story 1 complete - Students can retrieve reviews with <100ms response, Safe Mode works on cache failure

---

## Phase 4: User Story 2 - Student Completes Review and Progress is Saved (Priority: P1)

**Goal**: Students receive instant save confirmation (<500ms) with async database persistence

**Independent Test**: Submit 20 review responses, verify instant confirmation and eventual DB persistence

### Tests for User Story 2

- [x] T032 [P] [US2] Write test for submit_review_session with Redis update in memora/tests/test_srs_redis.py
- [x] T033 [P] [US2] Write test for background persistence job in memora/tests/test_srs_redis.py
- [x] T034 [US2] Write test for read-after-write consistency (cache reflects new schedule) in memora/tests/test_srs_redis.py

### Implementation for User Story 2

- [x] T035 [US2] Create srs_persistence module at memora/services/srs_persistence.py
- [x] T036 [US2] Implement persist_review_batch() background job in memora/services/srs_persistence.py
- [x] T037 [US2] Add retry logic with exponential backoff to persist_review_batch() in memora/services/srs_persistence.py
- [x] T038 [US2] Modify submit_review_session() to update Redis synchronously in memora/api/reviews.py
- [x] T039 [US2] Add frappe.enqueue() call to submit_review_session() for async DB persistence in memora/api/reviews.py
- [x] T040 [US2] Return persistence_job_id in submit_review_session() response in memora/api/reviews.py
- [x] T041 [US2] Add audit logging for submitted reviews in memora/services/srs_persistence.py

**Checkpoint**: User Story 2 complete - Students get instant confirmation, DB persistence happens in background

---

## Phase 5: User Story 3 - Administrator Creates New Season with Auto Infrastructure (Priority: P2)

**Goal**: New seasons automatically get database partitions and Redis caching enabled

**Independent Test**: Create new season, verify partition is created and partition_created flag is set

### Tests for User Story 3

- [x] T042 [P] [US3] Write test for season after_insert hook partition creation in memora/tests/test_srs_redis.py
- [x] T043 [US3] Write test for partition idempotency (skip if exists) in memora/tests/test_srs_redis.py

### Implementation for User Story 3

- [x] T044 [US3] Create partition_manager module at memora/services/partition_manager.py
- [x] T045 [US3] Implement create_season_partition() function with raw SQL in memora/services/partition_manager.py
- [x] T046 [US3] Implement check_partition_exists() function in memora/services/partition_manager.py
- [x] T047 [US3] Add after_insert hook to Game Subscription Season DocType in memora/memora/doctype/game_subscription_season/game_subscription_season.py
- [x] T048 [US3] Call create_season_partition() and set partition_created=1 in after_insert hook
- [x] T049 [US3] Add validation to prevent archiving active seasons in memora/memora/doctype/game_subscription_season/game_subscription_season.py

**Checkpoint**: User Story 3 complete - New seasons get automatic partition setup

---

## Phase 6: User Story 4 - System Automatically Archives Old Season Data (Priority: P3)

**Goal**: Seasons marked for auto-archive have data moved to archive storage and cache cleared

**Independent Test**: Mark season for auto-archive, run nightly job, verify data moved and cache cleared

### Tests for User Story 4

- [x] T050 [P] [US4] Create archiver test file at memora/tests/test_srs_archiver.py
- [x] T051 [US4] Write test for archive_season() data migration in memora/tests/test_srs_archiver.py
- [x] T052 [US4] Write test for cache cleanup after archiving in memora/tests/test_srs_archiver.py
- [x] T053 [US4] Write test for retention flagging (3+ years) in memora/tests/test_srs_archiver.py

### Implementation for User Story 4

- [x] T054 [US4] Create srs_archiver module at memora/services/srs_archiver.py
- [x] T055 [US4] Implement archive_season() function to copy records to Archived Memory Tracker in memora/services/srs_archiver.py
- [x] T056 [US4] Add DELETE from Player Memory Tracker after successful copy in archive_season()
- [x] T057 [US4] Add Redis cache cleanup using SCAN and DELETE pattern in archive_season()
- [x] T058 [US4] Implement process_auto_archive() scheduled job to find and archive eligible seasons in memora/services/srs_archiver.py
- [x] T059 [US4] Implement flag_eligible_for_deletion() for 3+ year old records in memora/services/srs_archiver.py
- [x] T060 [US4] Add archive_season API endpoint with confirmation requirement in memora/api/srs.py
- [x] T061 [US4] Register process_auto_archive in hooks.py scheduler_events["daily"] at memora/hooks.py
- [x] T062 [US4] Register flag_eligible_for_deletion in hooks.py cron (weekly) at memora/hooks.py

**Checkpoint**: User Story 4 complete - Old seasons archive automatically, cache clears, retention enforced

---

## Phase 7: User Story 5 - Administrator Monitors Season Configuration (Priority: P3)

**Goal**: Administrators can view cache status, trigger rebuilds, and run reconciliation

**Independent Test**: Toggle cache settings, trigger rebuild, verify cache rebuilds with progress tracking

### Tests for User Story 5

- [x] T063 [P] [US5] Write test for get_cache_status() endpoint in memora/tests/test_srs_redis.py
- [x] T064 [P] [US5] Write test for rebuild_season_cache() background job in memora/tests/test_srs_redis.py
- [x] T065 [US5] Write test for trigger_reconciliation() discrepancy detection in memora/tests/test_srs_redis.py

### Implementation for User Story 5

- [x] T066 [US5] Create srs_reconciliation module at memora/services/srs_reconciliation.py
- [x] T067 [US5] Implement reconcile_cache_with_database() with sample-based checking in memora/services/srs_reconciliation.py
- [x] T068 [US5] Add auto-correction logic (DB as source of truth) to reconciliation in memora/services/srs_reconciliation.py
- [x] T069 [US5] Add alert trigger when discrepancy rate >0.1% in memora/services/srs_reconciliation.py
- [x] T070 [US5] Implement rebuild_season_cache() background job with progress tracking in memora/services/srs_redis_manager.py
- [x] T071 [US5] Add get_cache_status() API endpoint in memora/api/srs.py
- [x] T072 [US5] Add rebuild_season_cache() API endpoint with admin permission check in memora/api/srs.py
- [x] T073 [US5] Add trigger_reconciliation() API endpoint in memora/api/srs.py
- [x] T074 [US5] Add on_update hook to Game Subscription Season for enable_redis changes in memora/memora/doctype/game_subscription_season/game_subscription_season.py
- [x] T075 [US5] Register reconcile_cache_with_database in hooks.py scheduler_events["daily"] at memora/hooks.py
- [x] T076 [US5] Add "Rebuild Cache" button to Game Subscription Season form view in
  memora/memora/doctype/game_subscription_season/game_subscription_season.js

**Checkpoint**: User Story 5 complete - Admins can monitor and manage cache layer

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and hardening

- [x] T077 [P] Update memora/api/__init__.py to export new endpoints
- [x] T078 [P] Add docstrings to all new API endpoints in memora/api/srs.py
- [x] T079 [P] Add docstrings to all service classes and methods
- [x] T080 Run ruff check on all new files and fix any issues
- [ ] T081 [P] Update memora/api/README.md with new SRS scalability endpoints documentation
- [ ] T082 Run all tests (bench run-tests --app memora) and verify passing
- [ ] T083 Validate against quickstart.md checklist
- [x] T084 Performance test: Load 100K records and verify <100ms read response
- [x] T085 Perform manual Safe Mode test by stopping Redis and verifying fallback

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - US1 and US2 can proceed in parallel (both P1)
  - US3, US4, US5 can proceed after US1+US2 (or in parallel if team allows)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Can Start After | Depends On Other Stories |
|-------|-----------------|--------------------------|
| **US1 (P1)** | Phase 2 complete | None - independent |
| **US2 (P1)** | Phase 2 complete | None - independent (uses same SRSRedisManager) |
| **US3 (P2)** | Phase 2 complete | None - independent |
| **US4 (P3)** | Phase 2 complete | US3 (uses partition_manager) - can test independently |
| **US5 (P3)** | Phase 2 complete | None - independent |

### Within Each Phase

- Tests (T0XX) should be written first, verify they FAIL
- DocType changes before service implementations
- Services before API endpoints
- Core functionality before edge cases

### Parallel Opportunities

**Phase 2 Parallelization:**
```
T004, T005, T006 (DocTypes) → can run in parallel
T007-T012 (SRSRedisManager) → sequential within class
T014, T015, T016 (patches) → can run in parallel after T013
T017, T018 (tests) → can run in parallel with implementation
```

**User Story Parallelization:**
```
US1 and US2 can be developed by two developers simultaneously
US3, US4, US5 can all proceed in parallel after US1+US2
```

---

## Parallel Example: Phase 2 Foundation

```bash
# Run in parallel - different DocType files:
Task: "Add new fields to Game Subscription Season DocType"
Task: "Update Player Memory Tracker DocType"
Task: "Create Archived Memory Tracker DocType"

# Run in parallel - different patch files:
Task: "Create fix_null_seasons.py patch"
Task: "Create setup_partitioning.py patch"
Task: "Create add_safe_mode_index.py patch"
```

## Parallel Example: User Story 1

```bash
# Run in parallel - test files:
Task: "Write test for get_review_session with cache hit"
Task: "Write test for lazy loading on cache miss"
Task: "Create Safe Mode test file"

# Run in parallel - different aspects:
Task: "Add SafeModeManager class in utils.py"
Task: "Add _rehydrate_user_cache() to SRSRedisManager"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (fast reads)
4. Complete Phase 4: User Story 2 (fast writes)
5. **STOP and VALIDATE**: Test core read/write flow end-to-end
6. Deploy MVP - students can use high-performance reviews

### Incremental Delivery

1. **MVP**: Setup → Foundation → US1 + US2 → Core functionality live
2. **+US3**: Season partition automation → Scalability for new seasons
3. **+US4**: Auto-archiving → Long-term system health
4. **+US5**: Admin tools → Operational visibility
5. **Polish**: Documentation, hardening, performance validation

### Parallel Team Strategy

With 2+ developers after Foundation complete:

- **Developer A**: User Story 1 (read path)
- **Developer B**: User Story 2 (write path)
- Then:
  - **Developer A**: User Story 3 + 4 (infrastructure + archiving)
  - **Developer B**: User Story 5 (admin tools)

---

## Summary

| Phase | Tasks | Parallel Tasks | Estimated Complexity |
|-------|-------|----------------|----------------------|
| Phase 1: Setup | 3 | 2 | Low |
| Phase 2: Foundational | 15 | 6 | High |
| Phase 3: US1 (P1) | 13 | 5 | High |
| Phase 4: US2 (P1) | 10 | 3 | Medium |
| Phase 5: US3 (P2) | 8 | 2 | Medium |
| Phase 6: US4 (P3) | 13 | 2 | High |
| Phase 7: US5 (P3) | 14 | 3 | Medium |
| Phase 8: Polish | 9 | 4 | Low |
| **Total** | **85** | **27** | - |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Constitution requires tests for SRS logic ("touches Grades")
- Redis is already configured at redis://127.0.0.1:13000
- Frappe workers handle background jobs via RQ
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
