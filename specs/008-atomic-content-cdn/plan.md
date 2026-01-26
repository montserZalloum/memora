# Implementation Plan: Atomic JSON Content Generation & CDN Distribution

**Branch**: `008-atomic-content-cdn` | **Date**: 2026-01-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-atomic-content-cdn/spec.md`

## Summary

This feature refactors the existing CDN export system from monolithic JSON files to an atomic file structure. The key change is splitting the current `subjects/{subject_id}.json` (which contains the entire hierarchy) into multiple smaller files:
- `plans/{plan_id}/manifest.json` - Plan index with subject list
- `plans/{plan_id}/{subject_id}_h.json` - Subject hierarchy (tracks → units → topics, no lessons)
- `plans/{plan_id}/{subject_id}_b.json` - Subject bitmap mapping for progress engine
- `plans/{plan_id}/{topic_id}.json` - Topic with lesson list (bit_index references)
- `lessons/{lesson_id}.json` - Shared lesson content with stages (plan-agnostic)

This atomic structure ensures sub-second loading, shared lesson content across plans, and enables granular cache invalidation.

## Technical Context

**Language/Version**: Python 3.10+ (Frappe Framework v14/v15)
**Primary Dependencies**: Frappe Framework, redis-py (via frappe.cache), RQ (background jobs), boto3 (S3/R2 CDN)
**Storage**: MariaDB (DocTypes), Redis (queue/locks), Local filesystem (`/sites/{site}/public/memora_content/`), S3/Cloudflare R2 (CDN target)
**Testing**: pytest with Frappe test harness
**Target Platform**: Linux server (Frappe bench environment)
**Project Type**: Frappe app (single project with services)
**Performance Goals**: Sub-second manifest loading (<1s), atomic file writes, no partial updates visible
**Constraints**: Backward compatibility with existing CDN export pipeline, atomic consistency across file uploads
**Scale/Scope**: Support thousands of lessons per plan without file size degradation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution is a template placeholder. Based on the project_overview memory, the following principles apply:

| Principle | Compliance | Notes |
|-----------|------------|-------|
| I. Read/Write Segregation (Generator Pattern) | ✅ PASS | This feature IS the generator pattern - compiling DocTypes into static JSON |
| II. High-Velocity Data Segregation | ✅ PASS | No interaction logs involved, this is content generation |
| III. Content-Commerce Decoupling | ✅ PASS | Content JSON uses required_item links, not prices |
| IV. Logic Verification (TDD) | ⚠️ GATE | Access calculation and override application require comprehensive unit tests |
| V. Performance-First Schema Design | ✅ PASS | Atomic files = smaller payloads, pre-calculated access levels |

**Gate IV Action**: Implementation tasks must include test-first development for `access_calculator.py` enhancements and new file generators.

## Project Structure

### Documentation (this feature)

```text
specs/008-atomic-content-cdn/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (JSON schemas)
│   ├── manifest.schema.json
│   ├── subject_hierarchy.schema.json
│   ├── subject_bitmap.schema.json
│   ├── topic.schema.json
│   └── lesson.schema.json
└── tasks.md             # Phase 2 output (by /speckit.tasks)
```

### Source Code (repository root)

```text
memora/
├── services/
│   └── cdn_export/
│       ├── __init__.py
│       ├── json_generator.py       # MODIFY: Split into atomic generators
│       ├── access_calculator.py    # MODIFY: Add Set Access Level, Set Linear
│       ├── batch_processor.py      # MODIFY: Atomic file orchestration
│       ├── change_tracker.py       # MODIFY: Granular change detection
│       ├── local_storage.py        # EXISTING: No changes needed
│       ├── cdn_uploader.py         # EXISTING: No changes needed
│       └── schemas/                # MODIFY: Add new schemas
│           ├── manifest.schema.json
│           ├── subject_hierarchy.schema.json  # NEW
│           ├── subject_bitmap.schema.json     # NEW
│           ├── topic.schema.json              # NEW
│           └── lesson.schema.json             # MODIFY
├── memora/
│   └── doctype/
│       └── memora_plan_override/
│           └── memora_plan_override.json  # MODIFY: Add new override actions
└── tests/
    └── unit/
        └── cdn_export/
            ├── test_access_calculator.py   # MODIFY: Add tests for new overrides
            ├── test_json_generator.py      # MODIFY: Add tests for atomic files
            └── test_atomic_consistency.py  # NEW: Atomic consistency tests

**Structure Decision**: Using existing Frappe app structure. Changes are modifications to existing services, not new modules.
```

## Complexity Tracking

No constitution violations requiring justification. The feature extends existing patterns rather than introducing new complexity.

---

## Phase 0: Research Complete

See [research.md](./research.md) for detailed findings.

## Phase 1: Design Complete

See:
- [data-model.md](./data-model.md) - File structure and data schemas
- [contracts/](./contracts/) - JSON Schema definitions
- [quickstart.md](./quickstart.md) - Developer onboarding
