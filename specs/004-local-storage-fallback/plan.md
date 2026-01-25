# Implementation Plan: Local Content Staging & Fallback Engine

**Branch**: `004-local-storage-fallback` | **Date**: 2026-01-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-local-storage-fallback/spec.md`

## Summary

Implement a local storage layer that serves as the source of truth for all generated JSON content, with an intelligent URL resolver that automatically switches between CDN and local server URLs based on configuration. This builds on the existing CDN export infrastructure (`memora/services/cdn_export/`) by inserting a local file persistence step before CDN upload and modifying URL generation to support fallback.

## Technical Context

**Language/Version**: Python 3.10+ (Frappe Framework v14/v15)
**Primary Dependencies**: Frappe Framework, boto3 (existing), shutil/os (stdlib for file ops)
**Storage**: Local filesystem (`/sites/{site_name}/public/memora_content/`), MariaDB (existing), S3/R2 (existing CDN)
**Testing**: pytest with Frappe test framework (existing pattern in `memora/tests/`)
**Target Platform**: Linux server (Frappe bench environment)
**Project Type**: Web application (Frappe app)
**Performance Goals**: <500ms local file write, <1s URL switch propagation, 1000 concurrent static file requests
**Constraints**: Atomic file writes, immediate settings effect, 100% CDN/local parity
**Scale/Scope**: Same scale as existing CDN export (~thousands of JSON files per plan)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution template is not fully configured for this project. Applying general best practices:

| Gate | Status | Notes |
|------|--------|-------|
| Test-First | PASS | Will implement unit tests for local storage manager, URL resolver |
| Integration Testing | PASS | Contract tests for file structure, integration tests for CDN/local sync |
| Simplicity | PASS | Minimal new code, extends existing cdn_export service |
| Observability | PASS | Logging for file operations, health check reporting |

## Project Structure

### Documentation (this feature)

```text
specs/004-local-storage-fallback/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
memora/
├── memora/
│   └── doctype/
│       ├── cdn_settings/           # Existing - add local_fallback_mode field
│       │   ├── cdn_settings.json   # DocType definition
│       │   └── cdn_settings.py     # Validation logic
│       └── cdn_sync_log/           # Existing - add local_path field
│           ├── cdn_sync_log.json
│           └── cdn_sync_log.py
├── services/
│   └── cdn_export/
│       ├── __init__.py
│       ├── local_storage.py        # NEW: Local file manager
│       ├── url_resolver.py         # NEW: get_content_url() function
│       ├── health_checker.py       # NEW: Health check & monitoring
│       ├── json_generator.py       # Existing - integrate local storage
│       ├── cdn_uploader.py         # Existing - upload from local files
│       └── batch_processor.py      # Existing - orchestrate local-first flow
└── tests/
    ├── unit/
    │   ├── test_local_storage.py   # NEW
    │   ├── test_url_resolver.py    # NEW
    │   └── test_health_checker.py  # NEW
    └── integration/
        └── test_local_cdn_sync.py  # NEW
```

**Structure Decision**: Extends existing `cdn_export` service with 3 new modules. No new DocTypes needed - extends CDN Settings and CDN Sync Log. Tests follow existing pattern in `memora/tests/`.

## Complexity Tracking

No constitution violations requiring justification.

## Key Design Decisions

### 1. Local Storage Path Strategy

Files stored at: `/sites/{site_name}/public/memora_content/{cdn_path}`

This mirrors CDN structure exactly:
- `plans/{plan_id}/manifest.json`
- `plans/{plan_id}/subjects/{subject_id}.json`
- `units/{unit_id}.json`
- `lessons/{lesson_id}.json`

### 2. Atomic Write Strategy

Use Python's `tempfile` + `shutil.move()` for atomic writes:
1. Write to `{target}.tmp.{uuid}`
2. `os.replace()` (atomic on POSIX) to final path
3. This ensures readers never see partial files

### 3. Version Retention Strategy

Before overwrite:
1. If `{file}.prev` exists, delete it
2. Rename current `{file}` to `{file}.prev`
3. Write new file atomically

### 4. URL Resolver Integration

Single function `get_content_url(path)` called by:
- `json_generator.py` for internal links
- API endpoints returning content URLs
- Reads CDN Settings once per request (cached via `frappe.cache`)

### 5. Health Check Scheduling

Uses Frappe's scheduler hooks:
- `hourly`: Quick health check during business hours (configurable)
- `daily`: Full filesystem scan overnight

## Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| CDN Settings DocType | Configuration storage | Exists - needs 1 new field |
| CDN Sync Log DocType | Sync status tracking | Exists - needs 1 new field |
| json_generator.py | Content generation | Exists - needs local storage integration |
| cdn_uploader.py | CDN upload | Exists - needs local file source |
| batch_processor.py | Orchestration | Exists - needs local-first flow |
| Frappe scheduler | Health check scheduling | Built-in |
| Frappe notifications | Admin alerts | Built-in |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Disk full during write | Check space before write, alert at 10% threshold |
| Permission errors | Validate on startup, clear error messages |
| Race conditions | Atomic writes, last-writer-wins semantics |
| CDN/local drift | Health check detects mismatches, triggers re-sync |
| Settings cache stale | Use `frappe.cache` with short TTL or invalidate on save |

## Implementation Phases

### Phase 1: Local Storage Foundation (P1)
- Local storage manager with atomic writes
- Version retention (.prev files)
- Directory structure creation
- File deletion on content delete

### Phase 2: URL Resolver (P1)
- `get_content_url()` function
- CDN Settings field additions
- Integration with json_generator.py
- Immediate settings propagation

### Phase 3: CDN Sync from Local (P2)
- Modify cdn_uploader to read from local files
- Hash verification
- Sync status tracking

### Phase 4: Health Check & Monitoring (P2)
- Scheduled health checks
- Disk space monitoring
- Admin notifications
- Retry exhaustion handling

### Phase 5: Cleanup & Edge Cases (P3)
- Cascade delete for plan directories
- Orphan file detection
- Manual retry mechanism
