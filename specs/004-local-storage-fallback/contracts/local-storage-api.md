# Local Storage API Contract

**Feature**: 004-local-storage-fallback
**Date**: 2026-01-25

## Module: `memora.services.cdn_export.local_storage`

### Functions

#### `write_content_file(path: str, data: dict) -> tuple[bool, str | None]`

Atomically write JSON content to local storage with version retention.

**Parameters**:
- `path` (str): Relative path within memora_content (e.g., `plans/PLAN-001/manifest.json`)
- `data` (dict): JSON-serializable data to write

**Returns**:
- `tuple[bool, str | None]`: (success, error_message)

**Behavior**:
1. Check disk space (≥10% free required)
2. Create directory structure if needed
3. If file exists, rename to `.prev` (delete old `.prev` first)
4. Write to temporary file
5. Atomic rename to final path

**Errors**:
- `"Insufficient disk space: {percent}% remaining"` - Disk below 10%
- `"Permission denied: {path}"` - Write permission error
- `"IO error: {details}"` - General filesystem error

---

#### `delete_content_file(path: str) -> tuple[bool, str | None]`

Delete a content file and its `.prev` version.

**Parameters**:
- `path` (str): Relative path within memora_content

**Returns**:
- `tuple[bool, str | None]`: (success, error_message)

**Behavior**:
1. Delete `.prev` file if exists
2. Delete main file if exists
3. Remove empty parent directories

---

#### `delete_content_directory(path: str) -> tuple[int, int, list[str]]`

Delete an entire directory (e.g., plan folder) and all contents.

**Parameters**:
- `path` (str): Relative directory path (e.g., `plans/PLAN-001`)

**Returns**:
- `tuple[int, int, list[str]]`: (files_deleted, errors_count, error_messages)

---

#### `file_exists(path: str) -> bool`

Check if a content file exists locally.

**Parameters**:
- `path` (str): Relative path within memora_content

**Returns**:
- `bool`: True if file exists

---

#### `get_file_hash(path: str) -> str | None`

Get MD5 hash of a local content file.

**Parameters**:
- `path` (str): Relative path within memora_content

**Returns**:
- `str | None`: MD5 hex digest, or None if file doesn't exist

---

#### `get_local_base_path() -> str`

Get the absolute path to the memora_content directory.

**Returns**:
- `str`: e.g., `/home/frappe/frappe-bench/sites/mysite/public/memora_content`

---

#### `check_disk_space() -> tuple[bool, float]`

Check available disk space.

**Returns**:
- `tuple[bool, float]`: (is_ok, free_percent) - is_ok is False if below 10%

---

## Module: `memora.services.cdn_export.url_resolver`

### Functions

#### `get_content_url(path: str) -> str`

Resolve a content path to full URL based on CDN settings.

**Parameters**:
- `path` (str): Relative path (e.g., `plans/PLAN-001/manifest.json`)

**Returns**:
- `str`: Full URL

**Logic**:
```python
settings = get_cdn_settings()  # Cached
if settings.local_fallback_mode:
    return f"{get_site_url()}/files/memora_content/{path}"
elif settings.enabled:
    return f"{settings.cdn_base_url}/{path}"
else:
    return f"{get_site_url()}/files/memora_content/{path}"
```

---

#### `get_cdn_settings() -> dict`

Get cached CDN settings.

**Returns**:
- `dict`: `{"enabled": bool, "cdn_base_url": str, "local_fallback_mode": bool}`

**Caching**: 60-second TTL, invalidated on CDN Settings save

---

#### `invalidate_settings_cache() -> None`

Clear the CDN settings cache. Called from CDN Settings `on_update`.

---

## Module: `memora.services.cdn_export.health_checker`

### Functions

#### `hourly_health_check() -> dict`

Quick health check for scheduler (business hours only).

**Returns**:
- `dict`: Health check report (see data-model.md)

**Behavior**:
1. Skip if outside business hours (8am-6pm Mon-Fri)
2. Check disk space
3. Sample 100 random files for existence
4. Return report

---

#### `daily_full_scan() -> dict`

Comprehensive filesystem scan.

**Returns**:
- `dict`: Full scan report (see data-model.md)

**Behavior**:
1. Check disk space
2. Query all expected files from database
3. Verify each file exists
4. Identify orphan files
5. Queue regeneration for missing files
6. Return report

---

#### `send_disk_alert(free_percent: float) -> None`

Send disk space alert to System Managers.

**Parameters**:
- `free_percent` (float): Current free disk percentage

**Behavior**:
- Send email via `frappe.sendmail()`
- Send in-app notification via `frappe.publish_realtime()`

---

#### `send_sync_failure_alert(sync_log_name: str) -> None`

Send alert when CDN sync retries are exhausted.

**Parameters**:
- `sync_log_name` (str): CDN Sync Log document name

---

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `DISK_FULL` | Disk space below 10% | Pause operations, alert admin |
| `PERMISSION_DENIED` | Cannot write to directory | Alert admin, check permissions |
| `FILE_NOT_FOUND` | Expected file missing | Queue regeneration |
| `HASH_MISMATCH` | Local/CDN content differs | Queue re-sync |
| `RETRY_EXHAUSTED` | CDN upload failed after all retries | Mark as Dead Letter, alert admin |
