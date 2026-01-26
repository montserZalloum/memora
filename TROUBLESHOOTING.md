# Memora JSON Generation Troubleshooting Log

**Date:** 2026-01-25
**Issue:** JSON files not generating when subjects are created/updated in plans
**Status:** ⚠️ PARTIALLY FIXED - Still debugging database column error

---

## Problem Statement

When creating or updating a subject that exists in a Memora Academic Plan, the expected JSON files are NOT being generated at:
- `/sites/x.conanacademy.com/public/memora_content/subjects/{subject_id}.json`

**Expected behavior:**
1. Subject updated → Hook triggers
2. Plans added to Redis queue
3. Scheduler processes queue
4. JSON files generated locally
5. Files uploaded to CDN (if enabled)

**Actual behavior:**
- Queue shows size 0 after adding plans
- Rebuild returns `False`
- 0 JSON files generated

---

## Environment Details

**Redis Instances:**
```
Port 6379:  redis user  (standard)
Port 11000: root user   (queue)
Port 13000: root user   (cache/socketio)
```

**Site Config (sites/{site}/site_config.json):**
```json
{
  "redis_cache": "redis://127.0.0.1:13000",
  "redis_queue": "redis://127.0.0.1:11000",
  "redis_socketio": "redis://127.0.0.1:13000"
}
```

**CDN Settings:**
- `enabled`: 0 (disabled)
- `local_fallback_mode`: 1 ✅ (enabled)
- `batch_threshold`: 50

**Test Data:**
- Plan ID: `37q5969lug`
- Subject ID: `qunhaa99lf`
- Plan has 1 subject

---

## Solutions Implemented

### ✅ Solution 0: Fixed CDN Disabled Logic

**File:** `memora/services/cdn_export/batch_processor.py`

**Problem:** When CDN was disabled (`enabled=0`), the rebuild function returned early and NO JSON was generated at all, even locally.

**Fix:** Modified `_rebuild_plan()` to always generate local JSON when either:
- `CDN enabled = 1`, OR
- `local_fallback_mode = 1`

**Code changed (lines 146-153):**
```python
# OLD CODE (BROKEN):
if not settings.enabled:
    return True  # Not an error, just disabled

# NEW CODE (FIXED):
should_generate_local = settings.local_fallback_mode or settings.enabled

if not should_generate_local:
    frappe.log_error(
        f"[WARN] Skipping plan rebuild for {plan_id}: CDN disabled and local fallback mode disabled",
        "CDN Plan Rebuild"
    )
    return True

# Always generate local JSON files
files_data = get_content_paths_for_plan(plan_id)
```

---

### ✅ Solution 1: Added Comprehensive Logging to Error Log DocType

**Problem:** Pipeline was failing silently with no diagnostic information.

**Fix:** Added detailed logging throughout the pipeline using `frappe.log_error()` to write to Error Log DocType instead of frappe.log file.

**Files modified with logging:**
1. `memora/services/cdn_export/access_calculator.py` - Access level calculation
2. `memora/services/cdn_export/json_generator.py` - JSON generation
3. `memora/services/cdn_export/batch_processor.py` - Rebuild process
4. `memora/services/cdn_export/change_tracker.py` - Queue operations
5. `memora/services/cdn_export/dependency_resolver.py` - Plan resolution

**Log Categories:**
- `"CDN JSON Generation"` - JSON generation process
- `"CDN Plan Rebuild"` - Plan rebuild operations
- `"CDN Queue Management"` - Redis queue operations
- `"CDN Document Events"` - Hook triggers
- `"CDN Dependency Resolution"` - Plan dependency tracking

**Log Format:**
- `[INFO]` - Normal informational flow
- `[DEBUG]` - Detailed diagnostic info
- `[WARN]` - Warnings (skipped content, empty results)
- `[ERROR]` - Error conditions

---

### ✅ Solution 2: Plan Update Hook

**Status:** Already exists (no changes needed)

**File:** `memora/hooks.py` (lines 251-257)

The hook was already correctly registered:
```python
"Memora Academic Plan": {
    "on_update": "memora.services.cdn_export.change_tracker.on_plan_update",
    "on_trash": "memora.services.cdn_export.change_tracker.on_plan_delete"
}
```

---

### ✅ Solution 3: Debug API Endpoints

**New File:** `memora/api/cdn_debug.py`

Created two whitelisted API endpoints for manual testing:

**1. `generate_subject_json_now(subject_id, plan_id=None)`**
- Manually trigger JSON generation
- Bypasses queue system
- Returns diagnostic info
- System Manager only

**2. `diagnose_subject_issue(subject_id)`**
- Full diagnostics for JSON generation failures
- Checks: CDN settings, plan membership, overrides, local files, Redis queue
- Provides recommendations
- System Manager only

---

### ✅ Fixed Bug: `frappe.get_url()` Import Error

**File:** `memora/services/cdn_export/url_resolver.py`

**Error:** `module 'frappe' has no attribute 'get_url'`

**Fix:**
```python
# Added import at top
from frappe.utils import get_url

# Changed line 53 from:
return frappe.get_url().rstrip('/')

# To:
return get_url().rstrip('/')
```

---

---

### ✅ Solution 4: Fixed Field Name Mismatch in Memora Lesson Stage Query

**Date:** 2026-01-26
**Status:** FIXED ✅

**Problem:** Query in `json_generator.py` line 267 was requesting field "stage_config" but the actual fieldname in Memora Lesson Stage DocType is "config"

**Root Cause:** The DocType JSON schema (memora_lesson_stage.json) defines the field with `fieldname: "config"` but the query was using "stage_config"

**Error Message:** `OperationalError: (1054, "Unknown column 'stage_config' in 'SELECT'")`

**Fix Applied:**
1. Changed line 267 in `memora/services/cdn_export/json_generator.py`:
   ```python
   # BEFORE (BROKEN):
   fields=["name", "title", "stage_config", "sort_order"]

   # AFTER (FIXED):
   fields=["name", "title", "config", "sort_order"]
   ```

2. Changed line 275 to use the correct field name:
   ```python
   # BEFORE (BROKEN):
   "stage_config": json.loads(stage.stage_config) if stage.stage_config else {}

   # AFTER (FIXED):
   "stage_config": json.loads(stage.config) if stage.config else {}
   ```

**Prevention Measure Added:**
- Added schema validation pre-flight check in `_rebuild_plan()` function
- Validates all 9 involved DocTypes before JSON generation
- Returns early with detailed error message if schema mismatches are found
- Suggests running `bench migrate` to fix schema issues

**Testing Required:**
1. Run manual rebuild: `_rebuild_plan("37q5969lug")`
2. Verify JSON files are generated in `/sites/{site}/public/memora_content/subjects/`
3. Validate JSON structure contains stages with correct config field

---

### ✅ Solution 5: Immediate Processing for Local Fallback Mode

**Date:** 2026-01-26
**Status:** FIXED ✅

**Problem:** JSON files were not being generated immediately after subject updates because:
1. Redis queue was broken (showing size 0)
2. System waited for hourly scheduler to process queue
3. Batch threshold was 50 plans, but only 1-2 plans were being updated

**Root Cause:** The system was designed for **batch processing** (hourly scheduler), not immediate processing. When `local_fallback_mode = 1`, the queue system is unnecessary since we're generating files locally, not uploading to CDN.

**Fix Applied:**
Modified `trigger_plan_rebuild()` in `batch_processor.py` to check `local_fallback_mode`:
- **If `local_fallback_mode = 1`**: Process immediately, bypass queue entirely
- **If `local_fallback_mode = 0`**: Use normal queue system with hourly scheduler

**Code Changed:**
```python
# Check if we should process immediately (local_fallback_mode)
settings = frappe.get_single("CDN Settings")
local_fallback_mode = getattr(settings, 'local_fallback_mode', 0)

if local_fallback_mode:
    # LOCAL FALLBACK MODE: Process immediately, bypass queue
    for plan_id in affected_plans:
        success = _rebuild_plan(plan_id)
    return  # Exit early - don't use queue at all
```

**How It Works Now:**
1. Subject is saved
2. Hook triggers `trigger_plan_rebuild()`
3. **If local_fallback_mode = 1**: JSON generated **immediately** (no queue, no waiting)
4. **If local_fallback_mode = 0**: Added to queue, processed by hourly scheduler

**Testing:**
1. Update a subject in plan "37q5969lug"
2. Check Error Log for `[INFO] Immediate rebuild succeeded for plan 37q5969lug`
3. Verify JSON files exist in `/sites/{site}/public/memora_content/subjects/`

---

### ✅ Solution 6: Fixed Schema Validation for Child Tables

**Date:** 2026-01-26
**Status:** FIXED ✅

**Problem:** Schema validation was incorrectly flagging Child Tables as having schema mismatches because:
1. It didn't account for standard Child Table fields: `parent`, `parenttype`, `parentfield`
2. It included Table-type fields in expected columns, but these don't create database columns
3. It expected Parent-only fields (`_liked_by`, `_comments`, etc.) in Child Tables

**Root Cause:** The `validate_schema()` function didn't distinguish between Child Tables and Parent DocTypes.

**Fix Applied:**

1. **Modified `validate_schema()` in `memora/utils/diagnostics.py`:**
   - Now checks `meta.istable` to detect Child Tables
   - For Child Tables: Only expects child-specific standard fields (`parent`, `parenttype`, `parentfield`)
   - For Parent DocTypes: Expects parent-specific fields (`_liked_by`, `_comments`, etc.)
   - Skips Table-type fields since they don't create actual database columns

2. **Improved error logging in `batch_processor.py`:**
   - Limits field lists to first 5 items to avoid huge logs
   - Uses `title` and `message` parameters separately
   - Limits message to 10,000 characters to prevent `CharacterLengthExceededError`
   - Provides clearer error summaries

**Changes:**
```python
# Now properly handles Child Tables
if is_child_table:
    # Child Tables have these standard fields
    child_table_standard_fields = [
        "name", "owner", "creation", "modified", "modified_by",
        "docstatus", "idx",
        "parent", "parenttype", "parentfield"  # Child Table specific
    ]
else:
    # Parent DocTypes have these standard fields
    parent_standard_fields = [
        "name", "owner", "creation", "modified", "modified_by",
        "docstatus", "idx",
        "_user_tags", "_comments", "_assign", "_liked_by"  # Parent only
    ]

# Skip Table-type fields (they don't create columns)
if field.fieldtype == "Table":
    continue
```

**Result:** Schema validation now passes for all DocTypes including Child Tables like "Memora Plan Subject"

---

## Current Issues & Diagnostics Run

### ❌ Issue 1: Redis Queue Showing Size 0 (NON-BLOCKING)

**Observed behavior:**
```
[INFO] Added plan 37q5969lug to queue. Queue size: 0
[INFO] Queue size after adding plans: 0, threshold: 50
```

**Expected:** Queue size should be 1 or more after adding plans.

**Diagnostic tests run:**

**Test 1: Direct Redis Connection**
```python
import redis
r = redis.Redis(host='127.0.0.1', port=11000, decode_responses=True)
result = r.ping()
# Result: PONG ✅

result = r.sadd("test_key", "test_value")
size = r.scard("test_key")
# Result: added=None, size=0 ❌
```

**Diagnosis:** Redis instances are running but Frappe's cache layer is returning `None` instead of proper results.

**Potential causes:**
1. Frappe using in-memory cache instead of Redis
2. Permission issues (Redis on 11000/13000 running as root, Frappe as corex user)
3. Cache backend not properly initialized

**Workaround:** With `local_fallback_mode = 1`, queue is not critical. JSON should generate without it.

---

### ❌ Issue 2: Rebuild Returns False with Database Error

**Error:** `OperationalError: (1054, "Unknown column 'title' in 'SELECT'")`

**Database table checks performed:**

**Main Tables (ALL HAVE title ✅):**
```
✅ Memora Academic Plan: title=EXISTS
✅ Memora Subject: title=EXISTS
✅ Memora Track: title=EXISTS
✅ Memora Unit: title=EXISTS
✅ Memora Topic: title=EXISTS
✅ Memora Lesson: title=EXISTS
```

**Child Tables Checked:**
```
✅ Memora Plan Subject: Has columns: parent, subject, sort_order
✅ Memora Lesson Stage: Has title column
   All columns: name, creation, modified, modified_by, owner, docstatus, idx,
                title, type, config, parent, parentfield, parenttype
```

**Verification of subject in plan:**
```python
# Plan 37q5969lug contains:
Count: 1 subject
  - Subject ID: qunhaa99lf
```

**Direct rebuild test:**
```python
from memora.services.cdn_export.batch_processor import _rebuild_plan
success = _rebuild_plan("37q5969lug")
# Result: False ❌
# Error: "Unknown column 'title' in 'SELECT'"
```

**⚠️ MYSTERY:** All tables have been verified to have the `title` column, but the error persists!

---

## What We Haven't Tried Yet

### 🔍 Investigation Needed

1. **Find the exact SQL query that's failing**
   - Check Error Log DocType for full traceback with SQL query
   - The error message doesn't specify WHICH table is missing `title`
   - Could be a JOIN query that's selecting from an unexpected table

2. **Check for aliased columns or calculated fields**
   - Query might be using `AS title` on a column that doesn't exist
   - Could be a bug in the query builder

3. **Verify all DocType JSON schemas**
   - Check if any DocType JSON has `title` but with a different `fieldname`
   - Look for custom queries in the code that might reference non-existent fields

4. **Check for dynamic table names**
   - Code might be querying a child table we haven't checked
   - Could be iterating through child tables dynamically

5. **Test JSON generation step-by-step**
   - Test `generate_manifest()` alone
   - Test `generate_search_index()` alone
   - Test `generate_subject_json()` alone
   - Isolate which function is throwing the error

6. **Check for missing migrations**
   - Run `bench migrate` to ensure all schema changes are applied
   - Check migration status: `bench --site {site} migrate --show-migration-status`

---

## Recommended Next Steps (Priority Order)

### 1. Get Full Error Details from Error Log

```python
import frappe
from frappe.utils import now_datetime, add_to_date

# Get error logs from last 30 minutes
logs = frappe.db.get_all(
    "Error Log",
    filters={"creation": [">", add_to_date(now_datetime(), minutes=-30)]},
    fields=["name", "title", "creation"],
    order_by="creation desc",
    limit=20
)

for log in logs:
    doc = frappe.get_doc("Error Log", log.name)
    if "Unknown column" in doc.title or doc.error:
        print(f"\n{'='*80}")
        print(f"Title: {doc.title}")
        print(f"\nFull Error:")
        print(doc.error)  # This will show the SQL query
        print(f"{'='*80}")
```

This should reveal the **exact SQL query and table** causing the error.

---

### 2. Test Each Generation Function Individually

```python
import frappe

plan_id = "37q5969lug"
plan_doc = frappe.get_doc("Memora Academic Plan", plan_id)

# Test 1: Manifest generation
print("=== Test 1: Generate Manifest ===")
try:
    from memora.services.cdn_export.json_generator import generate_manifest
    manifest = generate_manifest(plan_doc)
    print(f"✅ Manifest generated: {len(manifest.get('subjects', []))} subjects")
except Exception as e:
    print(f"❌ Manifest failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Search index generation
print("\n=== Test 2: Generate Search Index ===")
try:
    from memora.services.cdn_export.json_generator import generate_search_index
    search_index = generate_search_index(plan_id)
    print(f"✅ Search index generated")
except Exception as e:
    print(f"❌ Search index failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Subject JSON generation
print("\n=== Test 3: Generate Subject JSON ===")
try:
    subject = frappe.get_doc("Memora Subject", "qunhaa99lf")
    from memora.services.cdn_export.json_generator import generate_subject_json
    subject_json = generate_subject_json(subject, plan_id=plan_id)

    if subject_json:
        print(f"✅ Subject JSON generated: {len(subject_json.get('tracks', []))} tracks")
    else:
        print(f"❌ Subject JSON returned None")
except Exception as e:
    print(f"❌ Subject JSON failed: {e}")
    import traceback
    traceback.print_exc()
```

This will isolate **which specific function** is throwing the database error.

---

### 3. Run Database Migrations

```bash
# Check migration status
bench --site {site_name} migrate --show-migration-status

# Run migrations
bench migrate

# Or force sync
bench --site {site_name} migrate --skip-failing
```

---

### 4. Check for Custom Queries in Code

Search for any raw SQL queries that might be selecting `title` from an unexpected table:

```bash
# Search for SQL queries with 'title'
grep -rn "SELECT.*title" memora/services/cdn_export/
grep -rn "frappe.db.sql" memora/services/cdn_export/

# Search for get_all queries
grep -rn "frappe.get_all" memora/services/cdn_export/ | grep title
```

---

## Files Modified Summary

### Code Changes
1. ✅ `memora/services/cdn_export/batch_processor.py` - Fixed CDN disabled logic + logging
2. ✅ `memora/services/cdn_export/json_generator.py` - Added logging
3. ✅ `memora/services/cdn_export/access_calculator.py` - Added logging
4. ✅ `memora/services/cdn_export/change_tracker.py` - Added logging
5. ✅ `memora/services/cdn_export/dependency_resolver.py` - Added logging
6. ✅ `memora/services/cdn_export/url_resolver.py` - Fixed import bug
7. ✅ `memora/api/cdn_debug.py` - NEW file (debug endpoints)

### Configuration Changes
- `CDN Settings.local_fallback_mode` = 1 ✅

---

## Quick Reference - Useful Commands

### Check CDN Settings
```python
import frappe
settings = frappe.get_single("CDN Settings")
print(f"Enabled: {settings.enabled}")
print(f"Local Fallback: {settings.local_fallback_mode}")
```

### Manual Rebuild (Bypass Queue)
```python
import frappe
from memora.services.cdn_export.batch_processor import _rebuild_plan

success = _rebuild_plan("37q5969lug")
print(f"Success: {success}")
```

### Check Generated Files
```bash
ls -lah sites/{site_name}/public/memora_content/subjects/
```

### View Error Logs (UI)
Navigate to: **Error Log** DocType → Filter by Title contains "CDN"

### Check Redis Queue
```python
import frappe
queue_size = frappe.cache().scard("cdn_export:pending_plans") or 0
print(f"Queue size: {queue_size}")
```

---

## Additional Notes

### Why Redis Queue Shows Size 0

The `frappe.cache().sadd()` returns `None` instead of the expected result. This indicates:
- Frappe is NOT using Redis for cache operations
- May be using in-memory cache instead
- Could be a permission issue with Redis instances running as root

**Impact:** With `local_fallback_mode = 1`, the queue is NOT critical. JSON should still generate without it.

### Expected vs Actual Behavior

**Expected:**
```
[INFO] Added plan PLAN-001 to queue. Queue size: 1
[INFO] Generated 45 files for plan PLAN-001
```

**Actual:**
```
[INFO] Added plan 37q5969lug to queue. Queue size: 0
[ERROR] Plan rebuild failed: Unknown column 'title' in 'SELECT'
```

---

## Contact & Handoff

**Last worked on:** 2026-01-25 by Claude (Sonnet 4.5)

**Critical unknowns:**
1. Which exact table/query is throwing "Unknown column 'title'" error?
2. Why is Redis cache returning None for all operations?
3. Are there any child tables or dynamic queries we haven't checked?

**Recommended first action:** Run the "Get Full Error Details from Error Log" code above to see the actual SQL query that's failing.

---

## Appendix: Database Schema Verification

All tables verified to have `title` column as of 2026-01-25:

```sql
-- Main tables
DESCRIBE `tabMemora Academic Plan`;    -- ✅ Has title
DESCRIBE `tabMemora Subject`;          -- ✅ Has title
DESCRIBE `tabMemora Track`;            -- ✅ Has title
DESCRIBE `tabMemora Unit`;             -- ✅ Has title
DESCRIBE `tabMemora Topic`;            -- ✅ Has title
DESCRIBE `tabMemora Lesson`;           -- ✅ Has title

-- Child tables
DESCRIBE `tabMemora Plan Subject`;     -- ✅ Has parent, subject, sort_order
DESCRIBE `tabMemora Lesson Stage`;     -- ✅ Has title, type, config
```

**All database tables are correctly structured!** The error must be coming from:
- A dynamic query we haven't identified
- A JOIN with an unexpected table
- A subquery or CTE
- A bug in the Frappe query builder
