# Data Model: Local Content Staging & Fallback Engine

**Feature**: 004-local-storage-fallback
**Date**: 2026-01-25

## Overview

This feature extends existing DocTypes rather than creating new ones. The primary data artifacts are JSON files on the filesystem, with metadata tracked in existing database tables.

## DocType Modifications

### 1. CDN Settings (Existing - Modified)

**Type**: Single DocType (one record per site)

#### New Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `local_fallback_mode` | Check | 0 | When enabled, forces URL resolver to return local URLs regardless of CDN enabled status |

#### Existing Fields (unchanged)

- `enabled` (Check) - Master CDN enable/disable
- `cdn_base_url` (Data) - CDN URL prefix
- `storage_provider` (Select) - AWS S3 or Cloudflare R2
- `endpoint_url`, `bucket_name`, `access_key`, `secret_key` - CDN credentials
- `batch_interval_minutes`, `batch_threshold` - Sync timing
- `signed_url_expiry_hours` - Video URL expiry

#### Validation Rules

```python
# URL resolver logic (pseudo-code):
if local_fallback_mode:
    return local_url
elif enabled:
    return cdn_url
else:
    return local_url
```

### 2. CDN Sync Log (Existing - Modified)

**Type**: Regular DocType (multiple records)

#### New Fields

| Field | Type | Description |
|-------|------|-------------|
| `local_path` | Data | Local filesystem path where content was written |
| `local_hash` | Data | MD5 hash of local file content |
| `cdn_hash` | Data | ETag/hash from CDN after upload |
| `sync_verified` | Check | Whether local and CDN hashes match |

#### Existing Fields (unchanged)

- `plan_id` (Link) - Reference to Memora Academic Plan
- `status` (Select) - Queued, Processing, Success, Failed, Dead Letter
- `started_at`, `completed_at` (Datetime)
- `files_uploaded`, `files_deleted` (Int)
- `error_message` (Small Text)
- `retry_count` (Int)
- `next_retry_at` (Datetime)
- `is_fallback` (Check)
- `triggered_by` (Select)

#### State Transitions

```
Queued → Processing → Success
                   ↓
               Failed → (retry) → Processing
                   ↓
            Dead Letter (after retry exhaustion)
```

## Filesystem Data Model

### Directory Structure

```
/sites/{site_name}/public/memora_content/
├── plans/
│   └── {plan_id}/
│       ├── manifest.json
│       ├── manifest.json.prev          # Previous version (rollback)
│       ├── search_index.json
│       ├── search_index.json.prev
│       ├── search/
│       │   └── {subject_id}.json
│       └── subjects/
│           └── {subject_id}.json
├── units/
│   ├── {unit_id}.json
│   └── {unit_id}.json.prev
└── lessons/
    ├── {lesson_id}.json
    └── {lesson_id}.json.prev
```

### File Naming Conventions

| Pattern | Example | Description |
|---------|---------|-------------|
| `{entity_type}/{id}.json` | `units/UNIT-001.json` | Current version |
| `{entity_type}/{id}.json.prev` | `units/UNIT-001.json.prev` | Previous version |
| `{entity_type}/{id}.json.tmp.{uuid}` | `units/UNIT-001.json.tmp.abc123` | Temporary during write |

### File Lifecycle

```
1. CREATE:
   - Write to .tmp.{uuid}
   - Atomic rename to final path

2. UPDATE:
   - Delete existing .prev (if exists)
   - Rename current to .prev
   - Write new to .tmp.{uuid}
   - Atomic rename to final path

3. DELETE:
   - Delete .prev (if exists)
   - Delete current file
   - Delete parent directory if empty
```

## Entity Relationships

```
CDN Settings (1)
    │
    ├── controls → URL Resolver behavior
    │
    └── referenced by → CDN Sync Log (many)
                            │
                            └── tracks → Local Content Files (filesystem)
                                            │
                                            └── mirrors → CDN Files (S3/R2)
```

## Cache Keys

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `cdn_settings_config` | 60s | Cached CDN Settings values |
| `local_content_exists:{path}` | 300s | Quick existence check cache |
| `disk_space_check` | 60s | Cached disk space status |

## Health Check Data

### Quick Health Check Output

```json
{
  "timestamp": "2026-01-25T10:00:00Z",
  "disk_free_percent": 45.2,
  "disk_ok": true,
  "sample_files_checked": 100,
  "missing_files": [],
  "status": "healthy"
}
```

### Full Scan Output

```json
{
  "timestamp": "2026-01-25T02:00:00Z",
  "disk_free_percent": 45.2,
  "total_files_expected": 5432,
  "total_files_found": 5430,
  "missing_files": ["plans/PLAN-001/manifest.json", "units/UNIT-999.json"],
  "orphan_files": ["units/UNIT-DELETED.json"],
  "hash_mismatches": [],
  "status": "warning",
  "action_taken": "Queued regeneration for missing files"
}
```

## Validation Rules Summary

| Entity | Rule | Error Message |
|--------|------|---------------|
| Local path | Must be under `public/memora_content/` | "Invalid local storage path" |
| File write | Disk space ≥ 10% | "Insufficient disk space" |
| Sync verification | Local hash = CDN ETag | "Content mismatch detected" |
| Retry count | ≤ 5 attempts | "Retry limit exceeded" |

## Migration Notes

### CDN Settings

1. Add `local_fallback_mode` field with default `0`
2. No data migration needed (new field)

### CDN Sync Log

1. Add `local_path`, `local_hash`, `cdn_hash`, `sync_verified` fields
2. Existing records will have NULL values (acceptable)
3. New syncs will populate all fields
