# Implementation Plan: CDN Content Export System

**Branch**: `002-cdn-content-export` | **Date**: 2026-01-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-cdn-content-export/spec.md`

## Summary

Build an automated static JSON generation system that exports educational content from Frappe/MariaDB to CDN (S3/Cloudflare R2). The system tracks changes via Redis Sets, batches rebuilds every 5 minutes or 50 plans, applies plan-specific overrides for access control, and maintains cache invalidation. This implements the "Generator Pattern" from the constitution - compiling complex hierarchical content into static JSON payloads via background jobs.

## Technical Context

**Language/Version**: Python 3.10+ (Frappe Framework v14/v15)
**Primary Dependencies**: Frappe Framework, Redis (frappe.cache), boto3 (S3/R2), RQ (background jobs)
**Storage**: MariaDB (source data), Redis (queue/locks), S3/Cloudflare R2 (CDN target)
**Testing**: pytest with frappe test harness
**Target Platform**: Linux server (Frappe bench environment)
**Project Type**: Frappe app module (single app within bench)
**Performance Goals**: 1000 content changes/hour without backlog; CDN sync within 10 minutes
**Constraints**: <60s cache invalidation; <100KB search index shards; 4-hour signed URL expiry
**Scale/Scope**: Multiple academic plans, ~500-2000 lessons per plan, ~10-50 subjects per plan

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Implementation Notes |
|-----------|--------|---------------------|
| **I. Read/Write Segregation (Generator Pattern)** | PASS | Core purpose of this feature - compiles hierarchical content to static JSON via background jobs |
| **II. High-Velocity Data Segregation** | PASS | Uses Redis for queue/locks; no high-velocity writes to MariaDB during normal operation |
| **III. Content-Commerce Decoupling** | PASS | Access determined via `required_item` link to ERPNext Item; no pricing in content DocTypes |
| **IV. Logic Verification (TDD)** | REQUIRES | Access inheritance algorithm and override merging need 100% test coverage |
| **V. Performance-First Schema** | PASS | Pre-calculated JSON; no runtime joins; uses existing indexed fields |

**Database & Indexing Constraints**:
- Existing DocTypes already have `search_index: 1` on parent Link fields (verified)
- New `CDN Sync Log` DocType will need indexes on `plan_id`, `status`, `creation`

**API & Concurrency Constraints**:
- Redis locking prevents concurrent plan builds (FR-024/025/026)
- No public APIs exposed - internal background job system only

## Project Structure

### Documentation (this feature)

```text
specs/002-cdn-content-export/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (JSON schemas)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
memora/
├── memora/
│   └── doctype/
│       ├── cdn_sync_log/           # NEW: Audit log DocType
│       └── cdn_settings/           # NEW: Configuration DocType
├── services/
│   └── cdn_export/                 # NEW: Core export service
│       ├── __init__.py
│       ├── change_tracker.py       # Redis queue management
│       ├── dependency_resolver.py  # Bottom-up rebuild logic
│       ├── json_generator.py       # Content to JSON conversion
│       ├── access_calculator.py    # Access level inheritance
│       ├── search_indexer.py       # Search index generation
│       ├── cdn_uploader.py         # S3/R2 upload + cache purge
│       └── batch_processor.py      # Main orchestration
├── hooks.py                        # doc_events + scheduler_events
└── api/
    └── cdn_admin.py                # Dashboard API endpoints

tests/
├── unit/
│   └── cdn_export/
│       ├── test_access_calculator.py
│       ├── test_dependency_resolver.py
│       └── test_json_generator.py
├── integration/
│   └── test_cdn_export_flow.py
└── contract/
    └── test_json_schemas.py
```

**Structure Decision**: Frappe app structure with new `services/cdn_export/` module for business logic separation. DocTypes for configuration and logging. Service modules follow single-responsibility pattern.

## Complexity Tracking

No constitution violations requiring justification.
