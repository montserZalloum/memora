# Implementation Plan: Memora DocType Schema Creation

**Branch**: `001-doctype-schema` | **Date**: 2026-01-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-doctype-schema/spec.md`

## Summary

Create 19 DocTypes for the Memora Gamified LMS using Frappe's programmatic DocType creation via the `after_migrate` hook. The schema includes educational content hierarchy (Subject > Track > Unit > Topic > Lesson > Stages), player profiles with FSRS spaced repetition, academic planning with override system, and commerce integration with ERPNext.

## Technical Context

**Language/Version**: Python 3.10+ (Frappe Framework)
**Primary Dependencies**: Frappe Framework (v14/v15), ERPNext (for Item/Invoice links)
**Storage**: MariaDB (Frappe default) with explicit indexes per constitution
**Testing**: `bench run-tests` (Frappe test framework with pytest)
**Target Platform**: Linux server (Frappe bench environment)
**Project Type**: Frappe Custom App (single module)
**Performance Goals**: 100ms query response for Memory State next_review lookups (indexed)
**Constraints**: Idempotent migrations, atomic rollback on failure, no data loss on updates
**Scale/Scope**: 100,000+ Memory State records, 19 DocTypes, 5 child tables

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Compliance Notes |
|-----------|--------|------------------|
| I. Read/Write Segregation | N/A | Schema-only feature; read model is separate concern |
| II. High-Velocity Data Segregation | COMPLIANT | Interaction Log uses write-only pattern; Memory State indexed for fast reads |
| III. Content-Commerce Decoupling | COMPLIANT | Content DocTypes (Subject, Track, etc.) have no pricing fields; Product Grant is the mapping layer |
| IV. Logic Verification (TDD) | NOTED | Schema creation tested via migration; override system tested at application layer |
| V. Performance-First Schema Design | COMPLIANT | All filter/join columns indexed; JSON fields for Lesson Stage config |

**Technical Constraints Check**:
- Strict Indexing: All Link fields used for filtering have indexes specified in requirements
- JSON Usage: Lesson Stage config uses JSON field (not queried via SQL)
- Partitioning: Memory State and Interaction Log designed for future partitioning (player-based)

**Gate Status**: PASS - Proceeding to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-doctype-schema/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # N/A for this feature (no API endpoints)
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (Frappe App Structure)

```text
memora/                          # App root (inside bench/apps/)
├── hooks.py                     # Register after_migrate hook
├── memora/                      # Module directory
│   ├── doctype/                 # DocType definitions (JSON + Python)
│   │   └── [19 DocType folders] # Created by migration scripts
│   └── __init__.py
├── services/                    # Business logic (future)
│   └── schema/                  # Schema creation services
│       ├── __init__.py
│       ├── doctype_definitions.py    # DocType field definitions
│       ├── schema_creator.py         # DocType creation logic
│       └── migration_runner.py       # after_migrate entry point
├── tests/                       # Test files
│   └── test_schema_migration.py # Migration tests
└── patches/                     # Frappe patch system
```

**Structure Decision**: Frappe Custom App with schema creation logic in `services/schema/` to keep migration code separate from future business logic. DocType creation uses Frappe's programmatic API rather than JSON fixtures for better control and idempotency.

## Complexity Tracking

> No violations identified - using standard Frappe patterns.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| DocType Creation | Programmatic (not fixtures) | Enables idempotent updates and atomic rollback |
| Child Tables | Frappe Table fieldtype | Standard pattern; cascade delete handled by framework |
| Dynamic Links | Link to DocType + Dynamic Link | Enables Desk navigation arrows per spec |
