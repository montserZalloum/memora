# Research: Local Content Staging & Fallback Engine

**Feature**: 004-local-storage-fallback
**Date**: 2026-01-25

## 1. Atomic File Write Patterns in Python

### Decision: Use `os.replace()` with temporary file

### Rationale
- `os.replace()` is atomic on POSIX systems (Linux) - the operation either completes fully or not at all
- Works across filesystems on the same mount point
- Python 3.3+ standard library, no external dependencies
- Frappe servers run on Linux where this is reliable

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Direct `open().write()` | Not atomic - readers can see partial content |
| `shutil.move()` | Falls back to copy+delete across filesystems, not atomic |
| File locking (`fcntl`) | Complex, platform-specific, doesn't prevent partial reads |
| Write to `.tmp` then rename | Same as chosen approach but `os.replace()` is cleaner |

### Implementation Pattern

```python
import os
import tempfile
import json

def atomic_write_json(filepath: str, data: dict) -> None:
    """Write JSON atomically using temp file + replace."""
    dir_path = os.path.dirname(filepath)
    os.makedirs(dir_path, exist_ok=True)

    # Write to temp file in same directory (same filesystem)
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)  # Atomic on POSIX
    except:
        os.unlink(tmp_path)  # Cleanup on failure
        raise
```

## 2. Frappe Public File Serving

### Decision: Use `/sites/{site_name}/public/` directory

### Rationale
- Frappe's Nginx configuration already serves files from this path at `/files/`
- No additional Nginx configuration needed
- Files accessible at `https://{domain}/files/memora_content/{path}`
- Supports gzip compression via existing Nginx setup

### Path Structure

```
/home/frappe/frappe-bench/sites/
└── {site_name}/
    └── public/
        └── memora_content/           # NEW directory
            ├── plans/
            │   └── {plan_id}/
            │       ├── manifest.json
            │       ├── search_index.json
            │       ├── search/
            │       │   └── {subject_id}.json
            │       └── subjects/
            │           └── {subject_id}.json
            ├── units/
            │   └── {unit_id}.json
            └── lessons/
                └── {lesson_id}.json
```

### Access Pattern
- Local URL: `https://{site_domain}/files/memora_content/plans/{plan_id}/manifest.json`
- CDN URL: `https://{cdn_base_url}/plans/{plan_id}/manifest.json`

## 3. Frappe Cache Strategy for Settings

### Decision: Use `frappe.cache().get_value()` with invalidation on save

### Rationale
- CDN Settings is a Single DocType (one record)
- Settings accessed frequently during JSON generation
- Need immediate propagation when admin changes settings
- Frappe cache uses Redis, shared across workers

### Implementation Pattern

```python
def get_cdn_settings():
    """Get CDN settings with caching."""
    cache_key = "cdn_settings_config"
    settings = frappe.cache().get_value(cache_key)

    if settings is None:
        doc = frappe.get_single("CDN Settings")
        settings = {
            "enabled": doc.enabled,
            "cdn_base_url": doc.cdn_base_url,
            "local_fallback_mode": doc.local_fallback_mode,
        }
        frappe.cache().set_value(cache_key, settings, expires_in_sec=60)

    return settings

# In CDN Settings DocType after_save:
def on_update(self):
    frappe.cache().delete_value("cdn_settings_config")
```

## 4. Disk Space Monitoring

### Decision: Use `shutil.disk_usage()` with 10% threshold

### Rationale
- Standard library function, no dependencies
- Returns total, used, and free bytes
- Simple percentage calculation
- Can be checked before each write operation

### Implementation Pattern

```python
import shutil

def check_disk_space(path: str, threshold_percent: float = 10.0) -> tuple[bool, float]:
    """
    Check if disk has sufficient space.

    Returns:
        (is_ok, free_percent) - is_ok is False if below threshold
    """
    usage = shutil.disk_usage(path)
    free_percent = (usage.free / usage.total) * 100
    return free_percent >= threshold_percent, free_percent
```

## 5. Frappe Notification System for Alerts

### Decision: Use `frappe.sendmail()` + `frappe.publish_realtime()`

### Rationale
- `frappe.sendmail()` sends emails to System Managers
- `frappe.publish_realtime()` shows in-app notifications
- Both are built-in Frappe APIs
- No external notification service needed

### Implementation Pattern

```python
def send_disk_space_alert(free_percent: float):
    """Alert admins about low disk space."""
    subject = f"[Memora] Low Disk Space Warning: {free_percent:.1f}% remaining"
    message = f"""
    Disk space on the server is critically low ({free_percent:.1f}% remaining).

    Content generation has been paused to prevent data corruption.

    Please free up disk space and manually resume operations.
    """

    # Email to System Managers
    system_managers = frappe.get_all(
        "Has Role",
        filters={"role": "System Manager", "parenttype": "User"},
        pluck="parent"
    )

    for user in system_managers:
        frappe.sendmail(
            recipients=[user],
            subject=subject,
            message=message
        )

        # In-app notification
        frappe.publish_realtime(
            event="msgprint",
            message=subject,
            user=user
        )
```

## 6. Exponential Backoff Implementation

### Decision: Implement backoff schedule [30s, 1m, 2m, 5m, 15m] with max 1 hour total

### Rationale
- Matches clarification session decision
- Progressive delays prevent overwhelming recovering CDN
- ~1 hour total before marking as failed
- Backoff intervals: 30s, 60s, 120s, 300s, 900s (5 retries)

### Implementation Pattern

```python
from datetime import datetime, timedelta

BACKOFF_SCHEDULE = [30, 60, 120, 300, 900]  # seconds

def calculate_next_retry(retry_count: int) -> datetime | None:
    """
    Calculate next retry time based on retry count.
    Returns None if retries exhausted.
    """
    if retry_count >= len(BACKOFF_SCHEDULE):
        return None  # Exhausted

    delay_seconds = BACKOFF_SCHEDULE[retry_count]
    return datetime.now() + timedelta(seconds=delay_seconds)

def get_backoff_delay(retry_count: int) -> int:
    """Get delay in seconds for given retry count."""
    if retry_count >= len(BACKOFF_SCHEDULE):
        return BACKOFF_SCHEDULE[-1]  # Use max delay
    return BACKOFF_SCHEDULE[retry_count]
```

## 7. Health Check Scheduling

### Decision: Use Frappe scheduler hooks with conditional execution

### Rationale
- Frappe has built-in scheduler (`hooks.py`)
- `hourly` events run every hour
- `daily` events run once per day (configurable time)
- Business hours check can be done in code

### Implementation in hooks.py

```python
scheduler_events = {
    "hourly": [
        "memora.services.cdn_export.health_checker.hourly_health_check"
    ],
    "daily": [
        "memora.services.cdn_export.health_checker.daily_full_scan"
    ]
}
```

### Business Hours Logic

```python
from datetime import datetime

def is_business_hours() -> bool:
    """Check if current time is within business hours (8am-6pm)."""
    now = datetime.now()
    return 8 <= now.hour < 18 and now.weekday() < 5  # Mon-Fri

def hourly_health_check():
    """Run quick health check during business hours only."""
    if not is_business_hours():
        return

    run_quick_health_check()
```

## 8. File Hash Verification

### Decision: Use MD5 for content verification (not security)

### Rationale
- MD5 is fast and sufficient for content integrity checking
- Not used for security purposes (CDN files are public)
- SHA-256 would be overkill for this use case
- hashlib is stdlib, no dependencies

### Implementation Pattern

```python
import hashlib

def get_file_hash(filepath: str) -> str:
    """Calculate MD5 hash of file content."""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()

def verify_sync(local_path: str, cdn_etag: str) -> bool:
    """Verify local file matches CDN (S3 ETag is MD5 for single-part uploads)."""
    local_hash = get_file_hash(local_path)
    # S3 ETag includes quotes: "abc123..."
    cdn_hash = cdn_etag.strip('"')
    return local_hash == cdn_hash
```

## Summary

All technical unknowns have been resolved:

| Topic | Decision |
|-------|----------|
| Atomic writes | `os.replace()` with temp file |
| File serving | Frappe public directory |
| Settings caching | Redis cache with invalidation |
| Disk monitoring | `shutil.disk_usage()` |
| Admin alerts | Frappe email + realtime notifications |
| Retry backoff | [30s, 1m, 2m, 5m, 15m] schedule |
| Health scheduling | Frappe scheduler hooks |
| Hash verification | MD5 via hashlib |
