# Research: CDN Content Export System

**Feature**: 002-cdn-content-export
**Date**: 2026-01-25

## Research Tasks

### 1. S3/R2 Upload Strategy with boto3

**Decision**: Use boto3 with S3-compatible API for both AWS S3 and Cloudflare R2

**Rationale**:
- Cloudflare R2 is fully S3-compatible, same boto3 client works for both
- boto3 is the standard Python AWS SDK with mature error handling
- Frappe already uses boto3 for file uploads in some integrations

**Implementation Pattern**:
```python
import boto3
from botocore.config import Config

def get_cdn_client(settings):
    """Get S3-compatible client for either AWS S3 or Cloudflare R2."""
    return boto3.client(
        's3',
        endpoint_url=settings.endpoint_url,  # R2: https://<account_id>.r2.cloudflarestorage.com
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        config=Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
    )

def upload_json(client, bucket, key, data):
    """Upload JSON with proper content type."""
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json; charset=utf-8',
        CacheControl='public, max-age=300'  # 5 min cache, invalidated on update
    )
```

**Alternatives Considered**:
- `s3fs` library: More Pythonic but adds dependency; boto3 is sufficient
- Cloudflare Workers API: Not needed; R2 supports S3 API directly

---

### 2. Cache Purge Strategy

**Decision**: Use Cloudflare API for cache purge; fallback to cache-busting query params

**Rationale**:
- Cloudflare provides zone-level purge API
- Query param versioning (`?v=timestamp`) ensures fresh content even without purge
- Dual approach provides redundancy

**Implementation Pattern**:
```python
import requests

def purge_cdn_cache(zone_id, api_token, file_urls):
    """Purge specific files from Cloudflare cache."""
    response = requests.post(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache",
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        },
        json={"files": file_urls}  # Max 30 URLs per request
    )
    return response.json()

def get_versioned_url(base_url, version_timestamp):
    """Generate cache-busting URL."""
    return f"{base_url}?v={version_timestamp}"
```

**Alternatives Considered**:
- Purge everything: Too aggressive, affects unrelated content
- Short TTL only: Doesn't guarantee immediate update for critical fixes

---

### 3. Redis Queue & Locking Pattern in Frappe

**Decision**: Use `frappe.cache()` Redis interface with Sets for queue, string keys for locks

**Rationale**:
- `frappe.cache()` provides connection pooling and site isolation
- Redis Sets automatically deduplicate plan IDs
- String keys with `setnx` + TTL provide safe distributed locking

**Implementation Pattern**:
```python
import frappe
from frappe.utils import now_datetime

QUEUE_KEY = "cdn_export:pending_plans"
LOCK_PREFIX = "cdn_export:lock:"
DEAD_LETTER_KEY = "cdn_export:dead_letter"

def add_plan_to_queue(plan_id):
    """Add plan to rebuild queue (idempotent via Set)."""
    frappe.cache().sadd(QUEUE_KEY, plan_id)

def get_pending_plans(max_count=50):
    """Pop up to max_count plans from queue."""
    plans = []
    for _ in range(max_count):
        plan_id = frappe.cache().spop(QUEUE_KEY)
        if plan_id is None:
            break
        plans.append(plan_id.decode() if isinstance(plan_id, bytes) else plan_id)
    return plans

def acquire_lock(plan_id, ttl_seconds=300):
    """Acquire exclusive lock for plan build."""
    lock_key = f"{LOCK_PREFIX}{plan_id}"
    return frappe.cache().set(lock_key, now_datetime(), ex=ttl_seconds, nx=True)

def release_lock(plan_id):
    """Release plan build lock."""
    frappe.cache().delete(f"{LOCK_PREFIX}{plan_id}")

def move_to_dead_letter(plan_id, error_msg):
    """Move failed plan to dead-letter queue."""
    frappe.cache().hset(DEAD_LETTER_KEY, plan_id, error_msg)
```

**Alternatives Considered**:
- RQ job queue: Overkill for simple plan ID tracking; RQ is for job execution
- MariaDB queue table: Slower; Redis is already available and faster for this pattern

**Fallback to MariaDB**:
```python
def add_plan_to_fallback_queue(plan_id):
    """Fallback when Redis unavailable."""
    frappe.get_doc({
        "doctype": "CDN Sync Log",
        "plan_id": plan_id,
        "status": "Queued",
        "is_fallback": 1
    }).insert(ignore_permissions=True)
```

---

### 4. Frappe Document Hooks for Change Tracking

**Decision**: Use `doc_events` in hooks.py with specific DocType mappings

**Rationale**:
- Frappe's `doc_events` is the standard pattern for document lifecycle hooks
- Supports `on_update`, `after_insert`, `on_trash`, `after_delete`
- `on_restore` available for untrash operations

**Implementation Pattern** (hooks.py):
```python
doc_events = {
    "Memora Subject": {
        "on_update": "memora.services.cdn_export.change_tracker.on_content_change",
        "after_insert": "memora.services.cdn_export.change_tracker.on_content_change",
        "on_trash": "memora.services.cdn_export.change_tracker.on_content_delete",
        "after_delete": "memora.services.cdn_export.change_tracker.on_content_delete",
    },
    "Memora Track": { ... },  # Same handlers
    "Memora Unit": { ... },
    "Memora Topic": { ... },
    "Memora Lesson": { ... },
    "Memora Lesson Stage": {
        "on_update": "memora.services.cdn_export.change_tracker.on_stage_change",
    },
    "Memora Academic Plan": {
        "on_update": "memora.services.cdn_export.change_tracker.on_plan_change",
        "on_trash": "memora.services.cdn_export.change_tracker.on_plan_delete",
        "after_delete": "memora.services.cdn_export.change_tracker.on_plan_delete",
    },
    "Memora Plan Override": {
        "on_update": "memora.services.cdn_export.change_tracker.on_override_change",
    },
}
```

**Handler Pattern**:
```python
def on_content_change(doc, method):
    """Track content changes and queue affected plans."""
    plan_ids = get_affected_plan_ids(doc.doctype, doc.name)
    for plan_id in plan_ids:
        add_plan_to_queue(plan_id)
```

---

### 5. Scheduled Task for Batch Processing

**Decision**: Use Frappe's `scheduler_events` with `cron` pattern

**Rationale**:
- Native Frappe scheduler integrates with RQ workers
- Cron pattern provides precise 5-minute intervals
- Supports immediate trigger via manual API call

**Implementation Pattern** (hooks.py):
```python
scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "memora.services.cdn_export.batch_processor.process_pending_plans"
        ]
    }
}
```

**Threshold Trigger** (optional via doc_events):
```python
def check_queue_threshold():
    """Check if queue has reached 50 plans, trigger immediate processing."""
    queue_size = frappe.cache().scard(QUEUE_KEY)
    if queue_size >= 50:
        frappe.enqueue(
            "memora.services.cdn_export.batch_processor.process_pending_plans",
            queue="long",
            job_name="cdn_export_threshold_trigger"
        )
```

---

### 6. Signed URL Generation for Video Content

**Decision**: Use boto3 `generate_presigned_url` with 4-hour expiry

**Rationale**:
- Standard S3 presigning works with R2
- 4-hour window covers typical study sessions
- Generated at JSON build time, not runtime

**Implementation Pattern**:
```python
def generate_signed_url(client, bucket, key, expiry_seconds=14400):
    """Generate 4-hour signed URL for sensitive content."""
    return client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=expiry_seconds
    )
```

**Note**: Video URLs in Lesson Stage `config` JSON are replaced with signed URLs during export.

---

### 7. Content Hierarchy Traversal (Dependency Resolution)

**Decision**: Reverse traversal from changed node to Plan using parent links

**Rationale**:
- Existing schema has `parent_*` Link fields with indexes
- Efficient single-query lookups per level
- Frappe's `get_value` is optimized for indexed lookups

**Implementation Pattern**:
```python
HIERARCHY = {
    "Memora Lesson Stage": ("Memora Lesson", "parent"),  # Child table via parent
    "Memora Lesson": ("Memora Topic", "parent_topic"),
    "Memora Topic": ("Memora Unit", "parent_unit"),
    "Memora Unit": ("Memora Track", "parent_track"),
    "Memora Track": ("Memora Subject", "parent_subject"),
    "Memora Subject": ("Memora Plan Subject", "subject"),  # Reverse lookup
}

def get_affected_plan_ids(doctype, docname):
    """Traverse up hierarchy to find all affected Plan IDs."""
    current_doctype = doctype
    current_name = docname

    while current_doctype != "Memora Subject":
        if current_doctype not in HIERARCHY:
            return []
        parent_doctype, parent_field = HIERARCHY[current_doctype]

        if current_doctype == "Memora Lesson Stage":
            # Child table: get parent document
            current_name = frappe.db.get_value(
                "Memora Lesson", {"name": frappe.db.get_value(current_doctype, current_name, "parent")}, "name"
            )
            current_doctype = "Memora Lesson"
        else:
            current_name = frappe.db.get_value(current_doctype, current_name, parent_field)
            current_doctype = parent_doctype

    # Now at Subject level - find all plans containing this subject
    return frappe.db.get_all(
        "Memora Plan Subject",
        filters={"subject": current_name},
        pluck="parent"
    )
```

---

### 8. Access Level Calculation Algorithm

**Decision**: Top-down inheritance with override application

**Rationale**:
- Parent access level cascades to children
- `is_free_preview` flag breaks inheritance
- Plan overrides applied last

**Implementation Pattern**:
```python
def calculate_access_level(node, parent_access=None, plan_overrides=None):
    """Calculate access level with inheritance and overrides."""
    # Check plan-specific overrides first
    if plan_overrides and node.name in plan_overrides:
        override = plan_overrides[node.name]
        if override.action == "Hide":
            return None  # Exclude from export
        if override.action == "Set Free":
            return "free_preview"

    # Check free preview flag
    if getattr(node, 'is_free_preview', False):
        return "free_preview"

    # Check if content has required_item (paid)
    if getattr(node, 'required_item', None):
        return "paid"

    # Inherit from parent
    if parent_access == "paid":
        return "paid"

    # Check if explicitly public
    if getattr(node, 'is_published', False):
        return "public"

    # Default: authenticated (non-public, non-paid parent)
    return "authenticated" if parent_access != "public" else "public"
```

---

## Summary of Technology Choices

| Component | Technology | Notes |
|-----------|------------|-------|
| CDN Storage | boto3 (S3 API) | Works with AWS S3 and Cloudflare R2 |
| Cache Purge | Cloudflare API + Query Params | Dual approach for reliability |
| Queue | Redis Set via frappe.cache() | Automatic deduplication |
| Locking | Redis SETNX with TTL | Distributed lock pattern |
| Scheduling | Frappe scheduler_events (cron) | 5-minute intervals |
| Document Hooks | Frappe doc_events | Standard lifecycle hooks |
| Background Jobs | Frappe RQ (enqueue) | For long-running builds |

## Unresolved Items

None - all technical approaches validated against Frappe patterns and constitution requirements.
