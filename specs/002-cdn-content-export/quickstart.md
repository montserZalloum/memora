# Quickstart: CDN Content Export System

**Feature**: 002-cdn-content-export
**Date**: 2026-01-25

## Prerequisites

1. **Frappe/ERPNext Bench** with Memora app installed
2. **Redis** running (standard Frappe requirement)
3. **S3-compatible storage** (AWS S3 or Cloudflare R2)
4. **Python packages**: `boto3` (add to `pyproject.toml`)

## Setup Steps

### 1. Install Dependencies

```bash
cd ~/frappe-bench
bench pip install boto3
```

### 2. Configure CDN Settings

Navigate to: **Memora > Settings > CDN Settings**

| Field | Example Value |
|-------|---------------|
| Enabled | ✓ |
| Storage Provider | Cloudflare R2 |
| Endpoint URL | `https://<account_id>.r2.cloudflarestorage.com` |
| Bucket Name | `memora-cdn` |
| Access Key | `<your_access_key>` |
| Secret Key | `<your_secret_key>` |
| Cloudflare Zone ID | `<zone_id>` (optional, for cache purge) |
| Cloudflare API Token | `<api_token>` (optional) |
| Batch Interval (minutes) | 5 |
| Batch Threshold | 50 |
| Signed URL Expiry (hours) | 4 |
| CDN Base URL | `https://cdn.memora.app` |

### 3. Verify Redis Connection

```bash
bench console
>>> import frappe
>>> frappe.cache().ping()
True
```

### 4. Test S3/R2 Connection

```bash
bench console
>>> from memora.services.cdn_export.cdn_uploader import test_connection
>>> test_connection()
{'status': 'success', 'bucket': 'memora-cdn'}
```

### 5. Migrate (Create New DocTypes)

```bash
bench migrate
```

## Usage

### Automatic Sync

Once enabled, the system automatically:
1. Tracks changes on content DocTypes via document hooks
2. Queues affected Plan IDs in Redis
3. Processes queue hourly via scheduler (or immediately when 50+ plans queued)
4. Uploads JSON files to CDN
5. Invalidates cache

### Manual Trigger

From Frappe desk or console:

```python
# Trigger immediate processing
from memora.services.cdn_export.batch_processor import process_pending_plans
frappe.enqueue(process_pending_plans, queue="long")

# Rebuild specific plan
from memora.services.cdn_export.batch_processor import rebuild_plan
rebuild_plan("PLAN-00001")
```

### Monitor Status

1. **Dashboard**: Memora > CDN Export Status
   - Pending plans count
   - Recent sync logs
   - Dead-letter queue

2. **Logs**: Memora > CDN Sync Log
   - Filter by status, plan, date

## CDN File Structure

After sync, files are organized as:

```
https://cdn.memora.app/
├── plans/
│   └── {plan_id}/
│       ├── manifest.json
│       ├── search_index.json
│       ├── search/
│       │   └── {subject_id}.json  (if sharded)
│       └── subjects/
│           └── {subject_id}.json
├── units/
│   └── {unit_id}.json
└── lessons/
    └── {lesson_id}.json
```

## Frontend Integration

### Fetch Plan Manifest

```javascript
const planId = "PLAN-00001";
const version = Date.now();
const response = await fetch(
  `https://cdn.memora.app/plans/${planId}/manifest.json?v=${version}`
);
const manifest = await response.json();
```

### Handle Access Control

```javascript
function canAccessContent(item, userPurchases) {
  switch (item.access.access_level) {
    case "public":
      return true;
    case "authenticated":
      return !!currentUser;
    case "free_preview":
      return true;
    case "paid":
      return userPurchases.includes(item.access.required_item);
  }
}
```

## Troubleshooting

### Queue Not Processing

```bash
# Check scheduler status
bench doctor

# Check RQ workers
bench show-workers

# Manual process
bench console
>>> from memora.services.cdn_export.batch_processor import process_pending_plans
>>> process_pending_plans()
```

### Upload Failures

```bash
# Check CDN Sync Log for errors
bench console
>>> frappe.get_all("CDN Sync Log", filters={"status": "Failed"}, fields=["plan_id", "error_message"])

# Check dead-letter queue
>>> import frappe
>>> frappe.cache().hgetall("cdn_export:dead_letter")
```

### Cache Not Invalidating

1. Verify Cloudflare credentials in CDN Settings
2. Check zone ID is correct
3. Test purge API manually:

```python
from memora.services.cdn_export.cdn_uploader import purge_cdn_cache
result = purge_cdn_cache(["https://cdn.memora.app/plans/PLAN-00001/manifest.json"])
print(result)
```

## Development

### Run Tests

```bash
cd ~/frappe-bench/apps/memora
bench run-tests --app memora --module memora.services.cdn_export
```

### Debug Mode

```python
# In services/cdn_export/batch_processor.py
import frappe
frappe.flags.in_cdn_debug = True  # Enables verbose logging
```
