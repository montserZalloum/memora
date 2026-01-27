# Data Model: CDN Content Export System

**Feature**: 002-cdn-content-export
**Date**: 2026-01-25

## New DocTypes

### 1. CDN Settings (Single DocType)

Configuration for CDN export system. Single document per site.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | Check | Yes | Enable/disable CDN export |
| `storage_provider` | Select | Yes | "AWS S3" or "Cloudflare R2" |
| `endpoint_url` | Data | Yes | S3/R2 endpoint URL |
| `bucket_name` | Data | Yes | Target bucket name |
| `access_key` | Password | Yes | AWS/R2 access key |
| `secret_key` | Password | Yes | AWS/R2 secret key |
| `cloudflare_zone_id` | Data | No | For cache purge (R2 only) |
| `cloudflare_api_token` | Password | No | For cache purge API |
| `batch_interval_minutes` | Int | Yes | Default: 5 |
| `batch_threshold` | Int | Yes | Default: 50 |
| `signed_url_expiry_hours` | Int | Yes | Default: 4 |
| `cdn_base_url` | Data | Yes | Public CDN URL for manifests |

**Frappe DocType Definition**:
```json
{
  "doctype": "DocType",
  "name": "CDN Settings",
  "module": "Memora",
  "issingle": 1,
  "fields": [...]
}
```

---

### 2. CDN Sync Log

Audit log for sync operations. Supports dashboard queries and dead-letter tracking.

| Field | Type | Required | Indexed | Description |
|-------|------|----------|---------|-------------|
| `plan_id` | Link | Yes | Yes | Reference to Memora Academic Plan |
| `status` | Select | Yes | Yes | "Queued", "Processing", "Success", "Failed", "Dead Letter" |
| `started_at` | Datetime | No | No | Processing start time |
| `completed_at` | Datetime | No | No | Processing end time |
| `files_uploaded` | Int | No | No | Count of files uploaded |
| `files_deleted` | Int | No | No | Count of files deleted |
| `error_message` | Small Text | No | No | Error details if failed |
| `retry_count` | Int | No | No | Number of retry attempts |
| `is_fallback` | Check | No | Yes | True if queued via MariaDB fallback |
| `triggered_by` | Select | No | No | "Scheduler", "Threshold", "Manual", "Fallback Recovery" |

**Indexes**:
- `plan_id` (for plan-specific queries)
- `status` (for dashboard filtering)
- `creation` (for time-based queries - automatic in Frappe)
- Composite: `(status, creation)` for dashboard "recent failures"

---

## Existing DocTypes - Required Fields

The following fields are already present in existing DocTypes (verified from schema):

### Content DocTypes (Subject, Track, Unit, Topic, Lesson)

| Field | Present | Notes |
|-------|---------|-------|
| `is_published` | Yes | Check field, default 0 |
| `is_free_preview` | Yes | Check field, default 0 |
| `sort_order` | Yes | Int field with index |
| `title` | Yes | Data field, required |
| `description` | Yes | Small Text field |
| `image` | Yes | Attach Image field |

### Track-Specific

| Field | Present | Notes |
|-------|---------|-------|
| `is_sold_separately` | Yes | Check field for DLC pattern |

### Missing Fields (Need to Add)

| DocType | Field | Type | Purpose |
|---------|-------|------|---------|
| Memora Subject | `is_published` | Check | Distinguish public vs authenticated |
| Memora Subject | `required_item` | Link to Item | ERPNext Item for paid access |
| Memora Track | `required_item` | Link to Item | ERPNext Item for DLC purchase |
| Memora Track | `parent_item_required` | Check | True if parent Subject purchase unlocks |

---

## Redis Data Structures

### Pending Queue

```
Key: cdn_export:pending_plans
Type: Set
Values: Plan IDs (document names)
```

### Build Locks

```
Key Pattern: cdn_export:lock:{plan_id}
Type: String
Value: Timestamp
TTL: 300 seconds (5 minutes)
```

### Dead Letter Queue

```
Key: cdn_export:dead_letter
Type: Hash
Fields: {plan_id: error_message}
```

### Queue Size Counter (for threshold)

```
Key: cdn_export:queue_size
Type: String (integer)
Purpose: Fast threshold check without SCARD
```

---

## Content Hierarchy (Existing)

```
Memora Academic Plan
├── subjects (Table: Memora Plan Subject)
│   └── subject → Memora Subject
│       └── Memora Track (parent_subject)
│           └── Memora Unit (parent_track)
│               └── Memora Topic (parent_unit)
│                   └── Memora Lesson (parent_topic)
│                       └── stages (Table: Memora Lesson Stage)
└── overrides (Table: Memora Plan Override)
    ├── target_doctype
    ├── target_name
    └── action (Hide, Rename, Set Free, Set Sold Separately)
```

---

## JSON Output Schemas

See `contracts/` directory for detailed JSON Schema definitions:

- `contracts/manifest.schema.json` - Plan manifest
- `contracts/subject.schema.json` - Subject details
- `contracts/unit.schema.json` - Unit content
- `contracts/lesson.schema.json` - Lesson content
- `contracts/search_index.schema.json` - Search index

---

## State Transitions

### CDN Sync Log Status

```
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
    ┌─────────┐     ┌────────────┐     ┌─────────┐ │
    │ Queued  │────▶│ Processing │────▶│ Success │ │
    └─────────┘     └────────────┘     └─────────┘ │
         │               │                         │
         │               │ (retry < 3)             │
         │               ▼                         │
         │          ┌─────────┐                    │
         │          │ Failed  │────────────────────┘
         │          └─────────┘
         │               │ (retry >= 3)
         │               ▼
         │       ┌─────────────┐
         └──────▶│ Dead Letter │
                 └─────────────┘
```

### Content Publish State

```
is_published = 0 (Draft) ──────▶ is_published = 1 (Published)
       │                                │
       │                                │ (on_update hook)
       │                                ▼
       │                         Queue Plan Rebuild
       │                                │
       ▼                                ▼
  Not exported                   Exported to CDN
```

---

## Validation Rules

### CDN Settings

1. `endpoint_url` must be valid URL
2. `bucket_name` must be non-empty
3. If `storage_provider` = "Cloudflare R2" and cache purge needed, `cloudflare_zone_id` and `cloudflare_api_token` required
4. `signed_url_expiry_hours` must be between 1 and 24

### CDN Sync Log

1. `plan_id` must reference existing Academic Plan
2. `retry_count` cannot exceed 3
3. `completed_at` must be >= `started_at` when both present

### Content Export

1. Only `is_published = 1` content is exported
2. Content must have valid parent chain to Plan
3. Orphaned content (no Plan association) is skipped with warning
