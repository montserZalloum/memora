# Implementation Plan: SRS High-Performance & Scalability Architecture

**Branch**: `003-srs-scalability` | **Date**: 2026-01-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-srs-scalability/spec.md`

## Summary

Re-engineer the SRS memory engine to handle 1B+ records with <100ms response time. The solution uses a three-tier architecture:
1. **Fast Reads**: Redis Sorted Sets for O(log n) retrieval of due reviews
2. **Scalable Storage**: MariaDB with LIST partitioning by season for efficient data management
3. **Non-blocking Writes**: Frappe background jobs (`frappe.enqueue`) for async database persistence

## Technical Context

**Language/Version**: Python 3.10+ (Frappe Framework v15+)
**Primary Dependencies**: Frappe Framework, Redis (already configured at redis://127.0.0.1:13000), MariaDB/MySQL
**Storage**: MariaDB with LIST partitioning by season; Redis Sorted Sets for hot data
**Testing**: Frappe test framework (pytest-compatible), ruff for linting
**Target Platform**: Linux server (Frappe/bench deployment)
**Project Type**: Frappe app (Python backend with DocTypes)
**Performance Goals**: <100ms p99 for read operations; 10,000 concurrent users; 1B+ total records
**Constraints**: <500ms write confirmation; Safe Mode fallback under 500 req/min; 3-year archive retention
**Scale/Scope**: 1B memory tracker records, 10K concurrent students, season-based partitioning

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Academic-First Architecture** | PASS | Feature does not alter content visibility rules; operates at data layer only |
| **II. Backend Sovereignty** | PASS | All SRS logic remains in Python backend (api/srs.py); Redis is cache layer only |
| **III. Lock-First Security** | PASS | No changes to subscription/access control; season links preserved |
| **IV. Data Integrity & Stable Identity** | PASS | UUID-based question IDs preserved; DB remains source of truth; cache auto-corrects |
| **V. Performance & Scalability** | PASS | This feature directly implements V - payload efficiency, lazy loading, atomic transactions |
| **Testing Philosophy** | PASS | SRS algorithm tests are mandatory per constitution; will include cache/fallback tests |
| **Deployment Gates** | PASS | Schema changes via DocType JSONs; pre-commit hooks enforced |

**Pre-Design Gate**: PASSED - No violations detected.

### Post-Design Re-evaluation

| Principle | Status | Design Verification |
|-----------|--------|---------------------|
| **I. Academic-First Architecture** | PASS | Data model preserves subject/topic links; no content filtering changes |
| **II. Backend Sovereignty** | PASS | SRSRedisManager is Python backend service; all SRS calculations server-side |
| **III. Lock-First Security** | PASS | Season field required in Player Memory Tracker; subscription checks unchanged |
| **IV. Data Integrity & Stable Identity** | PASS | DB is source of truth (FR-018); reconciliation auto-corrects cache; UUID preserved |
| **V. Performance & Scalability** | PASS | Redis ZSET O(log n); partitioning for scale; async writes; lazy loading |
| **Testing Philosophy** | PASS | Tests planned for: SRS Redis manager, Safe Mode, archiver (Golden Rule: touches grades) |
| **Deployment Gates** | PASS | DocType JSON changes; patch for partitioning; no manual DB changes |

**Post-Design Gate**: PASSED - Design aligns with all constitution principles.

## Project Structure

### Documentation (this feature)

```text
specs/003-srs-scalability/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Getting started guide
├── contracts/           # Phase 1: API contracts
│   └── srs-api.yaml     # OpenAPI spec for SRS endpoints
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2: Implementation tasks
```

### Source Code (repository root)

```text
memora/
├── api/
│   ├── srs.py                    # MODIFY: Add Redis integration, Safe Mode logic
│   ├── reviews.py                # MODIFY: Integrate SRSRedisManager
│   └── utils.py                  # MODIFY: Add rate limiting utilities
├── services/                     # NEW: Domain services layer
│   ├── __init__.py
│   ├── srs_redis_manager.py      # NEW: Redis cache wrapper class
│   ├── srs_persistence.py        # NEW: Async DB persistence service
│   ├── srs_reconciliation.py     # NEW: Cache-DB reconciliation service
│   ├── srs_archiver.py           # NEW: Season archiving service
│   └── partition_manager.py      # NEW: DB partition management
├── memora/doctype/
│   ├── game_subscription_season/ # MODIFY: Add caching/archive fields
│   ├── player_memory_tracker/    # MODIFY: Update for partitioning support
│   └── archived_memory_tracker/  # NEW: Archive storage DocType
├── patches/                      # NEW: Migration patches
│   └── v1_0/
│       └── setup_partitioning.py # DB partitioning setup patch
├── hooks.py                      # MODIFY: Add scheduled jobs
└── tests/
    ├── test_srs_redis.py         # NEW: Redis manager tests
    ├── test_srs_safe_mode.py     # NEW: Fallback/rate limiting tests
    └── test_srs_archiver.py      # NEW: Archiving tests
```

**Structure Decision**: Frappe app structure with new `/services/` layer for complex business logic. DocTypes remain in standard Frappe location. Patches folder for database migration scripts.

## Complexity Tracking

No constitution violations requiring justification. The Redis cache layer is explicitly supported by existing infrastructure (redis://127.0.0.1:13000 already configured) and aligns with Constitution Principle V (Performance & Scalability).
