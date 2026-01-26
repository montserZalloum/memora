# Tasks: Player Core - Identity, Security & Rewards

**Input**: Design documents from `/specs/007-player-core/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are OPTIONAL and only included if explicitly requested in the feature specification. This feature does NOT explicitly request TDD, so test tasks are provided for reference but implementation can proceed without them.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Frappe App structure at `memora/memora/`:
- DocTypes: `memora/memora/doctype/`
- Services: `memora/memora/services/`
- API: `memora/memora/api/`
- Utils: `memora/memora/utils/`
- Tests: `memora/memora/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Frappe app structure preparation

- [X] T001 Create directory structure for Player Core components in memora/memora/
- [X] T002 [P] Create Redis utility module in memora/memora/utils/redis_keys.py with key pattern constants
- [X] T003 [P] Configure hooks.py to register background job scheduler for wallet sync
- [X] T004 [P] Create base test fixtures in memora/memora/tests/fixtures/ for test users and profiles

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core DocTypes and infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create Memora Authorized Device child table DocType in memora/memora/doctype/memora_authorized_device/
- [X] T006 Create Memora Player Profile DocType with authorized_devices table in memora/memora/doctype/memora_player_profile/
- [X] T007 Create Memora Player Wallet DocType in memora/memora/doctype/memora_player_wallet/
- [X] T008 Implement Player Profile validation hooks (2-device limit, auto-first-device) in memora_player_profile.py
- [X] T009 Implement Player Wallet validation hooks (non-negative XP/streak) in memora_player_wallet.py
- [X] T010 Implement after_insert hook on Player Profile to auto-create wallet in memora_player_profile.py
- [X] T011 [P] Run bench migrate to create database tables and verify schema
- [X] T012 [P] Implement Redis cache population on Player Profile save in memora_player_profile.py (device sets)
- [X] T013 [P] Implement Redis cache population on Player Wallet insert in memora_player_wallet.py (wallet hashes)

**Checkpoint**: Foundation ready - DocTypes created, validation working, Redis cache integration ready

---

## Phase 3: User Story 1 - Secure Single-Device Authentication (Priority: P1) 🎯 MVP

**Goal**: Students can log in from authorized devices only. First device auto-authorized, subsequent devices require admin approval. Maximum 2 devices per student.

**Independent Test**: Create test student, login from first device (auto-authorized), attempt login from second unauthorized device (rejected), admin authorizes second device, login succeeds.

### Implementation for User Story 1

- [X] T014 [P] [US1] Implement is_device_authorized() function in memora/memora/services/device_auth.py
- [X] T015 [P] [US1] Implement add_authorized_device() function in memora/memora/services/device_auth.py
- [X] T016 [P] [US1] Implement remove_authorized_device() function in memora/memora/services/device_auth.py
- [X] T017 [P] [US1] Implement rebuild_device_cache() utility in memora/memora/services/device_auth.py
- [X] T018 [US1] Create @require_authorized_device decorator in memora/memora/api/player.py
- [X] T019 [US1] Implement /check_device_authorization endpoint in memora/memora/api/player.py
- [X] T020 [US1] Implement /register_device endpoint (admin-only) in memora/memora/api/player.py
- [X] T021 [US1] Implement /remove_device endpoint (admin-only) in memora/memora/api/player.py
- [X] T022 [US1] Implement custom login flow with device validation in memora/memora/api/player.py /login endpoint
- [X] T023 [US1] Add device_id extraction from X-Device-ID header in memora/memora/api/player.py
- [X] T024 [US1] Implement first-device auto-authorization logic in login endpoint
- [X] T025 [US1] Add proper error responses for unauthorized devices (403 with user-friendly message)
- [X] T026 [US1] Add logging for device authorization attempts in device_auth.py

**Checkpoint**: User Story 1 complete - Device authorization working, first device auto-authorized, admin can manage devices

---

## Phase 4: User Story 2 - Single Active Session Enforcement (Priority: P1) 🎯 MVP

**Goal**: Only one active session per student. Logging in from another device invalidates the previous session within 2 seconds.

**Independent Test**: Login from Device A, verify session active. Login from Device B (authorized), verify Device A session invalidated. Attempt action on Device A, get session expired error.

### Implementation for User Story 2

- [X] T027 [P] [US2] Implement create_session() function in memora/memora/services/session_manager.py
- [X] T028 [P] [US2] Implement validate_session() function in memora/memora/services/session_manager.py
- [X] T029 [P] [US2] Implement invalidate_session() function in memora/memora/services/session_manager.py
- [X] T030 [US2] Integrate session creation in /login endpoint with Redis active_session key
- [X] T031 [US2] Update @require_authorized_device decorator to also validate session
- [X] T032 [US2] Implement /validate_session endpoint in memora/memora/api/player.py
- [X] T033 [US2] Implement /logout endpoint with session invalidation in memora/memora/api/player.py
- [X] T034 [US2] Add session invalidation on device removal in device_auth.py remove_authorized_device()
- [X] T035 [US2] Add proper error responses for invalidated sessions (401 with clear message)
- [X] T036 [US2] Implement session metadata storage in Redis (user_id, device_id, created_at)
- [X] T037 [US2] Add logging for session creation, validation, and invalidation events

**Checkpoint**: User Story 2 complete - Single session enforcement working, old sessions invalidated on new login

---

## Phase 5: User Story 3 - Daily Learning Streak Tracking (Priority: P2)

**Goal**: Track consecutive days of lesson completion. Streak starts at 0, becomes 1 on first success, increments on consecutive days, resets to 1 after gaps.

**Independent Test**: Complete lesson on Day 1 (streak=1), Day 2 (streak=2), skip Day 3, complete on Day 4 (streak=1). Verify streak increments only once per day.

### Implementation for User Story 3

- [X] T038 [P] [US3] Implement update_streak() function in memora/memora/services/wallet_engine.py
- [X] T039 [P] [US3] Implement is_consecutive_day() helper in memora/memora/services/wallet_engine.py
- [X] T040 [P] [US3] Implement get_wallet() function (cache-first read) in memora/memora/services/wallet_engine.py
- [X] T041 [US3] Implement /complete_lesson endpoint in memora/memora/api/player.py
- [X] T042 [US3] Integrate update_streak() call in complete_lesson endpoint
- [X] T043 [US3] Implement server time (UTC) retrieval for all streak calculations
- [X] T044 [US3] Add Redis HSET operations for streak and last_success_date updates
- [X] T045 [US3] Add user to pending_wallet_sync set after streak update
- [X] T046 [US3] Implement same-day duplicate prevention (no increment if already updated today)
- [X] T047 [US3] Add validation for hearts_earned > 0 requirement for streak update
- [X] T048 [US3] Return detailed streak update result (old_streak, new_streak, streak_action)
- [X] T049 [US3] Add logging for all streak transitions (first, increment, maintain, reset)

**Checkpoint**: User Story 3 complete - Streak tracking working with correct logic for all scenarios

---

## Phase 6: User Story 4 - Experience Points Accumulation (Priority: P2)

**Goal**: Students earn XP for activities, visible immediately in cache-first wallet view. XP batch-syncs to database every 15 minutes.

**Independent Test**: Award XP to student, verify immediate update in Redis. Check wallet reflects new total instantly. Verify queued for batch sync.

### Implementation for User Story 4

- [X] T050 [P] [US4] Implement add_xp() function in memora/memora/services/wallet_engine.py
- [X] T051 [P] [US4] Implement get_wallet_safe() with Redis fallback to DB in memora/memora/services/wallet_engine.py
- [X] T052 [US4] Implement /get_wallet endpoint in memora/memora/api/player.py
- [X] T053 [US4] Implement /add_xp endpoint in memora/memora/api/player.py
- [X] T054 [US4] Use Redis HINCRBY for atomic XP increments in add_xp()
- [X] T055 [US4] Add user to pending_wallet_sync set after XP update
- [X] T056 [US4] Integrate XP award into /complete_lesson endpoint (hearts * 10 formula)
- [X] T057 [US4] Implement cache-first wallet display (always read from Redis per FR-019a)
- [X] T058 [US4] Add proper error handling for negative XP attempts
- [X] T059 [US4] Return new_total_xp in response for immediate UI update
- [X] T060 [US4] Add logging for XP awards and wallet reads

**Checkpoint**: User Story 4 complete - XP accumulation working, cache-first display, queued for batch sync

---

## Phase 7: User Story 5 - Activity Timestamp Tracking (Priority: P3)

**Goal**: Track last_played_at timestamp with 15-minute throttled DB writes. Immediate Redis update, periodic DB sync.

**Independent Test**: Perform multiple API calls within 15 minutes, verify Redis updates but DB writes throttled. Wait 15+ minutes, verify next call triggers DB write.

### Implementation for User Story 5

- [X] T061 [P] [US5] Implement update_last_played_at() function in memora/memora/services/wallet_engine.py
- [X] T062 [US5] Add middleware to update last_played_at on every authenticated API request
- [X] T063 [US5] Implement Redis-based throttling check (last_played_at_synced:{user_id} key with 15-min TTL)
- [X] T064 [US5] Update last_played_at in Redis immediately, check throttle before DB write
- [X] T065 [US5] Add last_played_at to wallet hash updates in Redis
- [X] T066 [US5] Integrate last_played_at into batch sync job (sync along with XP/streak)
- [X] T067 [US5] Add logging for last_played_at updates (with throttle indicator)

**Checkpoint**: ✅ User Story 5 complete - Activity tracking with throttled writes working

---

## Phase 8: Batch Wallet Synchronization (Cross-Story Infrastructure)

**Goal**: Background job syncs pending wallet updates from Redis to MariaDB every 15 minutes in 500-player chunks.

**Independent Test**: Queue 1000+ players for sync, trigger job, verify all synced to DB in under 5 minutes, pending queue cleared.

### Implementation for Batch Sync

- [X] T068 [P] Implement sync_pending_wallets() job in memora/memora/services/wallet_sync.py
- [X] T069 [P] Implement chunk_list() helper in memora/memora/services/wallet_sync.py
- [X] T070 Implement bulk wallet data read from Redis in wallet_sync.py
- [X] T071 Implement bulk update to MariaDB using frappe.db.bulk_update in wallet_sync.py
- [X] T072 Implement atomic removal from pending_wallet_sync set after successful sync
- [X] T073 Register scheduled job in hooks.py (cron: */15 * * * *)
- [X] T074 Add comprehensive error handling and retry logic for sync failures
- [X] T075 Add sync job telemetry (count synced, duration, errors) and logging
- [X] T076 Implement manual trigger endpoint /trigger_wallet_sync for admin testing

**Checkpoint**: Batch sync complete - 15-min scheduled sync working, 90%+ DB write reduction achieved

---

## Phase 9: API Rate Limiting & Security Hardening (Cross-Story)

**Goal**: Implement rate limiting per endpoint to prevent abuse. Add security headers and error handling.

### Implementation for Rate Limiting

- [X] T077 [P] Implement @rate_limit() decorator in memora/memora/api/player.py
- [X] T078 [P] Implement Redis-based rate limit counter with TTL in rate_limit decorator
- [X] T079 Apply rate limits per endpoint specification (login: 5/min, complete_lesson: 10/min, get_wallet: 60/min)
- [X] T080 Add X-RateLimit-* response headers (Limit, Remaining, Reset)
- [X] T081 Implement proper 429 Too Many Requests responses with retry-after
- [X] T082 Add rate limit bypass for admin/system users
- [X] T083 [P] Add request logging for security audit trail (device_id, endpoint, result)
- [X] T084 [P] Implement input validation for all API endpoints (UUID format, XP range, etc.)

**Checkpoint**: Security hardening complete - Rate limiting active, proper error responses, audit logging

---

## Phase 10: Testing & Validation (Optional - Reference Only)

**Purpose**: Comprehensive test coverage if TDD approach desired

**Note**: Tests are optional per feature spec. Include only if explicit testing requirement exists.

### Unit Tests (Optional)

- [ ] T085 [P] Unit test for device_auth.py: is_device_authorized() with mocked Redis
- [ ] T086 [P] Unit test for device_auth.py: add_authorized_device() with 2-device limit
- [ ] T087 [P] Unit test for session_manager.py: create_session() and validate_session()
- [ ] T088 [P] Unit test for wallet_engine.py: update_streak() all scenarios (first, increment, maintain, reset)
- [ ] T089 [P] Unit test for wallet_engine.py: add_xp() atomic increments
- [ ] T090 [P] Unit test for wallet_sync.py: sync_pending_wallets() with chunking

### Integration Tests (Optional)

- [ ] T091 [P] Integration test for Player Profile creation with auto-wallet in memora/memora/tests/integration/test_player_flows.py
- [ ] T092 [P] Integration test for device authorization flow (first device, second device, rejection)
- [ ] T093 [P] Integration test for session invalidation on secondary login
- [ ] T094 [P] Integration test for streak tracking across multiple days
- [ ] T095 [P] Integration test for XP accumulation and cache-DB consistency
- [ ] T096 [P] Integration test for batch wallet sync with pending queue
- [ ] T097 Integration test for rate limiting enforcement across endpoints

### Contract Tests (Optional)

- [ ] T098 [P] Contract test for /login endpoint per OpenAPI spec
- [ ] T099 [P] Contract test for /get_wallet endpoint per OpenAPI spec
- [ ] T100 [P] Contract test for /complete_lesson endpoint per OpenAPI spec
- [ ] T101 [P] Contract test for /register_device endpoint per OpenAPI spec

**Checkpoint**: Testing complete (if included) - All tests passing, coverage >80%

---

## Phase 11: Documentation & Polish

**Purpose**: Final documentation, code cleanup, and deployment preparation

- [X] T102 [P] Update memora/memora/api/player.py with comprehensive docstrings
- [X] T103 [P] Update all service modules with docstrings (device_auth, session_manager, wallet_engine, wallet_sync)
- [ ] T104 [P] Add inline comments for complex logic (streak calculation, session invalidation)
- [ ] T105 [P] Create migration script for existing users if needed
- [ ] T106 Verify quickstart.md examples work with actual implementation
- [X] T107 Update CLAUDE.md with final Player Core summary (technologies, endpoints, DocTypes)
- [X] T108 [P] Code review and refactoring for consistency
- [X] T109 [P] Security audit of Redis key patterns and session handling
- [ ] T110 Run full test suite if implemented (pytest, integration, contract)
- [ ] T111 Performance profiling for 10k concurrent user simulation
- [ ] T112 Deploy to staging environment and validate all user stories independently

**Checkpoint**: Polish complete - Documentation updated, code reviewed, ready for production

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 & US2 are both P1 and form the MVP security layer
  - US3 & US4 are P2 and can run in parallel after US1+US2
  - US5 is P3 and can run independently after Foundational
- **Batch Sync (Phase 8)**: Depends on US4 (XP) and US5 (last_played_at) for full functionality
- **Rate Limiting (Phase 9)**: Can run in parallel with user stories after Foundational
- **Testing (Phase 10)**: Optional, runs parallel to or after implementation phases
- **Polish (Phase 11)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Device authorization - No dependencies on other stories, foundation for all
- **User Story 2 (P1)**: Session management - Depends on US1 device checks, can share same API endpoints
- **User Story 3 (P2)**: Streak tracking - Depends on US1 (authentication), independent of US2/US4
- **User Story 4 (P2)**: XP accumulation - Depends on US1 (authentication), independent of US2/US3
- **User Story 5 (P3)**: Activity tracking - Depends on US1 (authentication), independent of all others

### Recommended MVP Scope

**MVP = User Story 1 + User Story 2 (Both P1)**

This delivers:
- Secure device authorization (prevents account sharing at hardware level)
- Single session enforcement (prevents account sharing at session level)
- Complete foundational security for platform
- Independently testable and deployable
- Blocks no other features

After MVP, incrementally add:
1. User Story 3 (Streak) - Adds engagement
2. User Story 4 (XP) - Adds progression
3. User Story 5 (Activity tracking) - Adds analytics

### Parallel Opportunities

**Within Foundational Phase**:
- T005, T006, T007 (DocType creation) can run in parallel
- T012, T013 (Redis cache setup) can run in parallel

**User Story 1 (Device Auth)**:
- T014, T015, T016, T017 (all device_auth.py functions) can run in parallel

**User Story 2 (Session)**:
- T027, T028, T029 (all session_manager.py functions) can run in parallel

**User Story 3 (Streak)**:
- T038, T039, T040 (wallet_engine.py functions) can run in parallel

**User Story 4 (XP)**:
- T050, T051 (wallet_engine.py additional functions) can run in parallel

**Across User Stories** (after Foundational complete):
- US1 + US2 should complete together (MVP)
- US3 + US4 can run in parallel (both P2, independent)
- US5 can run independently

**Testing Phase** (if included):
- All unit tests (T085-T090) can run in parallel
- All integration tests (T091-T097) can run in parallel
- All contract tests (T098-T101) can run in parallel

---

## Parallel Example: MVP (US1 + US2)

```bash
# After Foundational Phase completes, launch MVP implementation:

# User Story 1 - Device Authorization (parallel functions)
Task: "Implement is_device_authorized() in services/device_auth.py"
Task: "Implement add_authorized_device() in services/device_auth.py"
Task: "Implement remove_authorized_device() in services/device_auth.py"
Task: "Implement rebuild_device_cache() in services/device_auth.py"

# User Story 2 - Session Management (parallel functions)
Task: "Implement create_session() in services/session_manager.py"
Task: "Implement validate_session() in services/session_manager.py"
Task: "Implement invalidate_session() in services/session_manager.py"

# Then integrate into API layer sequentially
```

---

## Parallel Example: Engagement Features (US3 + US4)

```bash
# After MVP complete, launch P2 features in parallel:

# User Story 3 - Streak (parallel functions)
Task: "Implement update_streak() in services/wallet_engine.py"
Task: "Implement is_consecutive_day() in services/wallet_engine.py"
Task: "Implement get_wallet() in services/wallet_engine.py"

# User Story 4 - XP (parallel functions, same file but different functions)
Task: "Implement add_xp() in services/wallet_engine.py"
Task: "Implement get_wallet_safe() in services/wallet_engine.py"

# Both integrate into same /complete_lesson endpoint sequentially
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T013) - CRITICAL blocking phase
3. Complete Phase 3: User Story 1 - Device Auth (T014-T026)
4. Complete Phase 4: User Story 2 - Session (T027-T037)
5. **STOP and VALIDATE**: Test US1+US2 independently
   - Device authorization works
   - Session invalidation works
   - Security layer complete
6. Deploy/demo MVP

**MVP Delivers**: Complete security foundation preventing account sharing

### Incremental Delivery (After MVP)

1. Add User Story 3 - Streak (T038-T049)
   - Test independently: Streak logic correct
   - Deploy/demo with MVP
2. Add User Story 4 - XP (T050-T060)
   - Test independently: XP accumulation correct
   - Deploy/demo with MVP+US3
3. Add Batch Sync (T068-T076)
   - Required for production-scale XP/streak
   - Test independently: Batch sync reduces DB writes by 90%+
4. Add User Story 5 - Activity Tracking (T061-T067)
   - Test independently: Timestamp throttling works
   - Deploy/demo complete feature
5. Add Rate Limiting (T077-T084) - Security hardening
6. Polish & Documentation (T102-T112)

### Parallel Team Strategy

With 3 developers after Foundational phase:

1. **Team completes Setup + Foundational together** (T001-T013)
2. Once Foundational done:
   - **Developer A**: User Story 1 (Device Auth) - T014-T026
   - **Developer B**: User Story 2 (Session) - T027-T037
   - **Developer C**: Redis utilities + Rate limiting prep
3. **MVP Integration**: A+B integrate US1+US2 into unified API
4. **Post-MVP parallel**:
   - **Developer A**: User Story 3 (Streak) - T038-T049
   - **Developer B**: User Story 4 (XP) - T050-T060
   - **Developer C**: Batch Sync - T068-T076
5. Stories integrate independently without conflicts

---

## Task Summary

**Total Tasks**: 112
- **Setup**: 4 tasks
- **Foundational**: 9 tasks (BLOCKING)
- **User Story 1 (P1)**: 13 tasks
- **User Story 2 (P1)**: 11 tasks
- **User Story 3 (P2)**: 12 tasks
- **User Story 4 (P2)**: 11 tasks
- **User Story 5 (P3)**: 7 tasks
- **Batch Sync**: 9 tasks
- **Rate Limiting**: 8 tasks
- **Testing (Optional)**: 17 tasks
- **Polish**: 11 tasks

**Parallel Opportunities**: 45 tasks marked [P] can run in parallel

**MVP Scope**: Setup + Foundational + US1 + US2 = 37 tasks (excludes optional testing)

**Full Feature**: All phases except optional testing = 95 tasks

**Estimated Duration**:
- MVP: 5-7 days (with 2 developers)
- Full Feature: 10-14 days (with 3 developers)

---

## Notes

- [P] tasks = different files or independent functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests (Phase 10) are optional - include only if TDD explicitly requested
- Frappe's built-in test framework used where applicable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Redis patterns follow research.md decisions
- All file paths use memora/memora/ prefix per Frappe conventions
