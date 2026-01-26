# Implementation Plan: Player Core - Identity, Security & Rewards

**Branch**: `007-player-core` | **Date**: 2026-01-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-player-core/spec.md`

## Summary

Implement secure student identity system with device authorization, single-session enforcement, and high-performance rewards engine (XP & Streak) using Redis caching and batching to minimize database load. The system prevents account sharing through hardware-locked device authorization (max 2 devices) and single active session enforcement, while providing immediate feedback on learning progress through cache-first wallet display.

## Technical Context

**Language/Version**: Python 3.10+ (Frappe Framework v14/v15)
**Primary Dependencies**: Frappe Framework, redis-py (via frappe.cache), RQ (background jobs)
**Storage**: MariaDB (persistent DocTypes), Redis (session/wallet cache, device lists)
**Testing**: pytest (unit/integration), Frappe test framework
**Target Platform**: Linux server (Frappe bench environment)
**Project Type**: Frappe App (DocType-driven backend with API layer)
**Performance Goals**:
  - Device/session verification: <2ms (Redis)
  - Session termination: <2s on conflict
  - XP display latency: <1s
  - Batch sync: <5min for 50k players
  - Support 10k concurrent students
**Constraints**:
  - 90%+ reduction in wallet DB writes via batching
  - 15-minute max lag between cache and DB
  - 99.9% uptime for auth/session
  - Server time authority (prevent client manipulation)
**Scale/Scope**:
  - 3 new DocTypes (Player Profile, Player Wallet, Authorized Device child table)
  - 2 core security flows (device auth, session management)
  - 2 engagement engines (XP accumulation, streak tracking)
  - 1 background job (15-min batch wallet sync)
  - 4 Redis data structures (device sets, session keys, wallet hashes, sync queue)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ CONSTITUTION TEMPLATE IS EMPTY - No gates to evaluate

The project constitution file (`.specify/memory/constitution.md`) contains only placeholder template content with no actual principles defined. Therefore, there are no constitutional requirements to verify or violations to justify for this implementation.

**Recommendation**: Consider defining project constitution principles for future features to establish consistent architectural guidelines.

## Project Structure

### Documentation (this feature)

```text
specs/007-player-core/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (in progress)
├── data-model.md        # Phase 1 output (pending)
├── quickstart.md        # Phase 1 output (pending)
├── contracts/           # Phase 1 output (pending)
│   ├── player_api.yaml  # OpenAPI spec for player endpoints
│   └── wallet_api.yaml  # OpenAPI spec for wallet endpoints
├── checklists/          # Quality validation
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Frappe App Structure (existing)
memora/memora/
├── doctype/
│   ├── memora_player_profile/        # NEW: Player identity DocType
│   │   ├── memora_player_profile.json
│   │   ├── memora_player_profile.py
│   │   ├── memora_player_profile.js
│   │   └── test_memora_player_profile.py
│   ├── memora_player_wallet/         # NEW: Player wallet DocType
│   │   ├── memora_player_wallet.json
│   │   ├── memora_player_wallet.py
│   │   ├── memora_player_wallet.js
│   │   └── test_memora_player_wallet.py
│   └── memora_authorized_device/     # NEW: Authorized device child table DocType
│       ├── memora_authorized_device.json
│       └── memora_authorized_device.py
├── api/
│   └── player.py                     # NEW: Player API endpoints
├── services/
│   ├── device_auth.py                # NEW: Device authorization service
│   ├── session_manager.py            # NEW: Session management service
│   ├── wallet_engine.py              # NEW: XP/Streak calculation engine
│   └── wallet_sync.py                # NEW: Batch sync background job
├── utils/
│   └── redis_keys.py                 # NEW: Redis key patterns
└── tests/
    ├── unit/
    │   ├── test_device_auth.py       # NEW: Device auth unit tests
    │   ├── test_session_manager.py   # NEW: Session management unit tests
    │   ├── test_wallet_engine.py     # NEW: Wallet engine unit tests
    │   └── test_wallet_sync.py       # NEW: Batch sync unit tests
    └── integration/
        ├── test_player_flows.py      # NEW: End-to-end player flows
        └── test_wallet_consistency.py # NEW: Cache-DB consistency tests
```

**Structure Decision**: Using existing Frappe App structure (`memora/memora/`). New feature components follow Frappe conventions:
- DocTypes in `doctype/` for persistent entities
- Services in `services/` for business logic
- API endpoints in `api/` for external interfaces
- Background jobs registered via `hooks.py`
- Redis utilities in `utils/` for cache patterns

## Complexity Tracking

> **No violations to justify** - Constitution file is empty template

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

---

## Phase 0: Research (✅ COMPLETE)

**Status**: Complete
**Output**: [research.md](./research.md)

### Key Decisions Made

1. **Device Identification**: Client-generated UUID v4 in X-Device-ID header
2. **Session Management**: Redis single-session lock with persistent sessions
3. **Caching Strategy**: 4 Redis structures (SET/STRING/HASH/SET) for different patterns
4. **Batch Sync**: RQ 15-min scheduled job, 500-player chunks
5. **Streak Logic**: Date-based with server UTC time
6. **Cache Recovery**: AOF persistence + graceful degradation
7. **Schema**: 3 DocTypes (Profile, Wallet, Device child table)
8. **API Security**: Frappe auth + device middleware + Redis rate limiting

All NEEDS CLARIFICATION items resolved through research and best practices analysis.

---

## Phase 1: Design & Contracts (✅ COMPLETE)

**Status**: Complete
**Outputs**:
- [data-model.md](./data-model.md) - Entity schemas and relationships
- [contracts/player_api.yaml](./contracts/player_api.yaml) - Player & session endpoints
- [contracts/wallet_api.yaml](./contracts/wallet_api.yaml) - Wallet & XP endpoints
- [quickstart.md](./quickstart.md) - Developer onboarding guide
- CLAUDE.md updated with new technologies

### Artifacts Generated

#### Data Model
- 3 DocType schemas with validation rules
- 4 Redis cache structures with key patterns
- Entity relationship diagram
- Data volume estimates (scalable to 100k students)

#### API Contracts
- **Player API**: 7 endpoints (profile, devices, auth, session)
- **Wallet API**: 4 endpoints (wallet, XP, lessons, history)
- OpenAPI 3.0.3 specifications with examples
- Rate limiting specifications per endpoint

#### Developer Guide
- Environment setup instructions
- Service implementation examples
- Testing workflows (unit/integration)
- Common troubleshooting scenarios

---

## Planning Summary

**Total Duration**: ~3 hours
**Phase 0**: 2 hours (research)
**Phase 1**: 1 hour (design artifacts)

### Constitution Re-Check (Post-Design)

**Status**: ✅ PASSED (No gates defined in constitution)

No complexity violations introduced. Design follows Frappe best practices and leverages existing infrastructure (Redis, RQ, MariaDB).

### Next Steps

This plan document is **complete**. The next phase is task breakdown:

```bash
/speckit.tasks
```

This will generate `tasks.md` with implementation tasks derived from this plan.
