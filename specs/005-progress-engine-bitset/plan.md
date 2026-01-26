# Implementation Plan: Progress Tracking and Smart Unlocking Engine (Bitset Edition)

**Branch**: `005-progress-engine-bitset` | **Date**: 2026-01-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-progress-engine-bitset/spec.md`

## Summary

Build a high-performance progress tracking engine using Redis Bitmaps to represent lesson completion states. The system supports linear/non-linear unlock logic, computes container states (Topic/Unit/Track) dynamically, provides `suggested_next_lesson_id` for "Continue Learning" functionality, and implements a record-breaking XP bonus system for lesson replays. Target: 20ms response time, 100K concurrent users, 1000 updates/sec.

## Technical Context

**Language/Version**: Python 3.10+ (Frappe Framework v14/v15)
**Primary Dependencies**: Frappe Framework, redis-py (via frappe.cache), RQ (background jobs)
**Storage**: MariaDB (persistent snapshots), Redis (fast bitmap storage), Local JSON files (subject structure)
**Testing**: pytest with frappe test harness
**Target Platform**: Linux server (Frappe bench environment)
**Project Type**: Frappe app module extension
**Performance Goals**: 20ms progress retrieval, 1000 updates/sec, 100K concurrent users
**Constraints**: <20ms p95 for reads, 30-second batch sync to MariaDB, <150 bytes per student-subject bitmap
**Scale/Scope**: 1000 lessons per subject max, 100K concurrent users

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Read/Write Segregation | PASS | Redis bitmap (read) + MariaDB snapshot (write) follows Generator Pattern |
| II. High-Velocity Data Segregation | PASS | Progress updates go through Redis; batched to MariaDB every 30s |
| III. Content-Commerce Decoupling | PASS | Progress engine is content-only; access checks are external |
| IV. Logic Verification (TDD) | REQUIRED | Unlock logic (linear/non-linear) requires 100% unit test coverage |
| V. Performance-First Schema Design | PASS | Bitmap storage is pre-calculated; JSON structure avoids joins |

## Project Structure

### Documentation (this feature)

```text
specs/005-progress-engine-bitset/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
memora/
├── memora/
│   └── doctype/
│       ├── memora_subject/           # Add: next_bit_index field
│       ├── memora_lesson/            # Add: bit_index field
│       ├── memora_structure_progress/# Add: passed_lessons_bitset, best_hearts_data fields
│       └── memora_player_wallet/     # Existing: total_xp (add XP here)
├── services/
│   └── progress_engine/              # NEW: Core progress service
│       ├── __init__.py
│       ├── bitmap_manager.py         # Redis bitmap operations
│       ├── unlock_calculator.py      # Linear/non-linear unlock logic
│       ├── progress_computer.py      # Main compute_progress function
│       ├── xp_calculator.py          # XP calculation with record-breaking bonus
│       ├── snapshot_syncer.py        # 30-second batch sync to MariaDB
│       └── cache_warmer.py           # Restore from MariaDB on cache miss
├── api/
│   └── progress.py                   # NEW: Progress API endpoints
└── tests/
    ├── unit/progress_engine/         # Unit tests for unlock logic, XP calc
    ├── integration/                  # Progress API integration tests
    └── contract/                     # Contract tests for API responses
```

**Structure Decision**: Frappe app single-module pattern. New `services/progress_engine/` directory for core logic, following the existing `services/cdn_export/` pattern.

## Complexity Tracking

> No constitution violations requiring justification.

## Existing Schema Analysis

### Fields Already Present

| DocType | Field | Status |
|---------|-------|--------|
| Memora Subject | `is_linear` | EXISTS (Check, default=1) |
| Memora Subject | `next_bit_index` | NEEDS ADDING |
| Memora Track | `is_linear` | EXISTS (Check, default=1) |
| Memora Unit | `is_linear` | EXISTS (Check, default=1) |
| Memora Topic | `is_linear` | NEEDS ADDING |
| Memora Lesson | `bit_index` | NEEDS ADDING |
| Memora Structure Progress | `passed_lessons_bitset` | NEEDS ADDING (rename from passed_lessons_data) |
| Memora Structure Progress | `best_hearts_data` | NEEDS ADDING |
| Memora Player Wallet | `total_xp` | EXISTS |

### JSON Structure Enhancement

The existing `json_generator.py` produces subject JSON. We need to ensure `is_linear` and `bit_index` are included in the output for progress computation.

## Constitution Check (Post-Design)

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Verification |
|-----------|--------|--------------|
| I. Read/Write Segregation | PASS | Redis bitmap for reads, MariaDB for durable writes. JSON structure files separate from transactional DB. |
| II. High-Velocity Data Segregation | PASS | Completions buffered in Redis, batched to MariaDB every 30s. No direct DB writes on hot path. |
| III. Content-Commerce Decoupling | PASS | Progress engine tracks completion only. Access control (hearts, enrollment) is checked but not managed here. |
| IV. Logic Verification (TDD) | PLANNED | `unlock_calculator.py` and `xp_calculator.py` require 100% unit test coverage before implementation. |
| V. Performance-First Schema Design | PASS | Bitmap (125 bytes/1000 lessons), LRU-cached JSON, pre-computed `bit_index` per lesson. No joins on hot path. |

## Phase 1 Deliverables

| Artifact | Path | Status |
|----------|------|--------|
| Research | `specs/005-progress-engine-bitset/research.md` | COMPLETE |
| Data Model | `specs/005-progress-engine-bitset/data-model.md` | COMPLETE |
| API Contract | `specs/005-progress-engine-bitset/contracts/progress-api.json` | COMPLETE |
| Structure Schema | `specs/005-progress-engine-bitset/contracts/subject-structure.json` | COMPLETE |
| Quickstart | `specs/005-progress-engine-bitset/quickstart.md` | COMPLETE |

## Next Steps

Run `/speckit.tasks` to generate the implementation task list with dependencies.
