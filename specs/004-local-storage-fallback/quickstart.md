# Quickstart: Local Content Staging & Fallback Engine

**Feature**: 004-local-storage-fallback
**Date**: 2026-01-25

## Prerequisites

- Frappe bench environment with Memora app installed
- CDN export feature (002-cdn-content-export) already implemented
- Write permissions on `/sites/{site_name}/public/` directory

## Setup Steps

### 1. Update CDN Settings DocType

Add the `local_fallback_mode` field to CDN Settings:

```json
{
  "fieldname": "local_fallback_mode",
  "fieldtype": "Check",
  "label": "Local Fallback Mode",
  "default": "0",
  "description": "Force all URLs to point to local server instead of CDN"
}
```

Run migration:
```bash
bench --site {site_name} migrate
```

### 2. Create Local Storage Directory

The directory will be created automatically, but you can verify permissions:

```bash
# Check/create directory
mkdir -p /home/frappe/frappe-bench/sites/{site_name}/public/memora_content

# Ensure frappe user owns it
chown -R frappe:frappe /home/frappe/frappe-bench/sites/{site_name}/public/memora_content

# Verify permissions
ls -la /home/frappe/frappe-bench/sites/{site_name}/public/memora_content
```

### 3. Verify Nginx Serves Static Files

Frappe's default Nginx config should already serve files from `/public/`. Verify:

```bash
# Test local file serving (after creating a test file)
curl -I https://{your-site}/files/memora_content/test.json
```

### 4. Configure CDN Settings

In Frappe desk, navigate to **CDN Settings** and configure:

| Field | Value | Notes |
|-------|-------|-------|
| Enabled | ✓ | Enable CDN uploads |
| Local Fallback Mode | ☐ | Keep unchecked for normal operation |
| CDN Base URL | `https://cdn.example.com` | Your CDN domain |

### 5. Test the Feature

#### Test Local Storage

```python
# In bench console
import frappe
from memora.services.cdn_export.local_storage import write_content_file, file_exists

# Write a test file
success, error = write_content_file("test/hello.json", {"message": "Hello World"})
print(f"Write: {success}, Error: {error}")

# Check existence
exists = file_exists("test/hello.json")
print(f"Exists: {exists}")
```

#### Test URL Resolver

```python
from memora.services.cdn_export.url_resolver import get_content_url

# With CDN enabled
url = get_content_url("plans/PLAN-001/manifest.json")
print(f"URL: {url}")
# Expected: https://cdn.example.com/plans/PLAN-001/manifest.json

# Enable fallback mode in CDN Settings, then:
url = get_content_url("plans/PLAN-001/manifest.json")
print(f"Fallback URL: {url}")
# Expected: https://your-site.com/files/memora_content/plans/PLAN-001/manifest.json
```

#### Test Health Check

```python
from memora.services.cdn_export.health_checker import hourly_health_check

report = hourly_health_check()
print(report)
```

## Common Operations

### Enable Fallback Mode (CDN Outage)

1. Go to **CDN Settings** in Frappe desk
2. Check **Local Fallback Mode**
3. Save

All URLs will immediately point to local server.

### View Health Check Status

```bash
# Check scheduler logs
bench --site {site_name} show-scheduler-status

# View recent health check logs
bench --site {site_name} execute memora.services.cdn_export.health_checker.daily_full_scan
```

### Manual Retry Failed Syncs

```python
# Find failed syncs
failed = frappe.get_all("CDN Sync Log", filters={"status": "Dead Letter"}, pluck="name")

# Queue for retry
for log_name in failed:
    log = frappe.get_doc("CDN Sync Log", log_name)
    log.status = "Queued"
    log.retry_count = 0
    log.save()

frappe.db.commit()
```

### Check Disk Space

```python
from memora.services.cdn_export.local_storage import check_disk_space

is_ok, free_percent = check_disk_space()
print(f"Disk OK: {is_ok}, Free: {free_percent:.1f}%")
```

## Troubleshooting

### Files Not Served Locally

1. Check Nginx is running: `sudo systemctl status nginx`
2. Verify file exists: `ls -la /path/to/public/memora_content/...`
3. Check Nginx config includes Frappe's static file rules
4. Check file permissions (should be readable by nginx user)

### CDN Settings Not Taking Effect

1. Clear cache: `bench --site {site_name} clear-cache`
2. Verify settings saved: Check CDN Settings in desk
3. Check for errors in logs: `tail -f /home/frappe/frappe-bench/logs/worker.error.log`

### Disk Space Alerts Not Received

1. Verify email settings in Frappe
2. Check user has System Manager role
3. Check scheduler is running: `bench --site {site_name} show-scheduler-status`

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Content Generation                        │
│                    (json_generator.py)                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Local Storage Layer                         │
│                    (local_storage.py)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Atomic Write│  │  .prev      │  │ Disk Check  │             │
│  │ (temp+move) │  │  Versioning │  │ (10% min)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
┌─────────────────┐    ┌─────────────────────────────────────────┐
│  Local Files    │    │           CDN Upload                     │
│  /public/       │───▶│        (cdn_uploader.py)                │
│  memora_content/│    │  - Reads from local files               │
└────────┬────────┘    │  - Hash verification                    │
         │             │  - Exponential backoff retry            │
         │             └─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        URL Resolver                              │
│                    (url_resolver.py)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ if local_fallback_mode → local URL                       │   │
│  │ elif cdn_enabled      → CDN URL                          │   │
│  │ else                  → local URL                        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Next Steps

After setup:

1. Run a test sync for one plan
2. Verify files appear in both local storage and CDN
3. Test fallback by enabling Local Fallback Mode
4. Monitor health check logs for the first week
