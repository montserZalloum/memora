# Quickstart: Debugging JSON Generation Failures

**Feature**: 006-json-generation-debug
**Audience**: Developers debugging JSON generation issues in Memora CDN export system
**Time**: 10-15 minutes

---

## Problem Context

When subjects are updated in academic plans, the system should automatically generate JSON files locally. Currently, the rebuild process fails with:

```
OperationalError: (1054, "Unknown column 'title' in 'SELECT'")
```

This guide helps you identify and fix the root cause.

---

## Prerequisites

- Access to Frappe console: `bench --site {site_name} console`
- System Manager permissions in Frappe
- Test data: At least 1 Academic Plan with 1 Subject
  - Example test data: Plan ID `37q5969lug`, Subject ID `qunhaa99lf`
  - Or create test data using `memora.tests.cdn_export.fixtures`
- Local fallback mode enabled: `CDN Settings.local_fallback_mode = 1`

---

## Quick Diagnosis (5 minutes)

### Step 1: Get Full Error Details

Open Frappe console and run:

```python
import frappe
from frappe.utils import now_datetime, add_to_date

# Get recent errors
logs = frappe.db.get_all(
    "Error Log",
    filters={"creation": [">", add_to_date(now_datetime(), minutes=-30)]},
    fields=["name", "title", "creation"],
    order_by="creation desc",
    limit=10
)

# Display full error for each
for log in logs:
    if "Unknown column" in log.title or "CDN" in log.title:
        doc = frappe.get_doc("Error Log", log.name)
        print(f"\n{'='*80}")
        print(f"Title: {doc.title}")
        print(f"Time: {doc.creation}")
        print(f"\nError:")
        print(doc.error[:2000])  # First 2000 chars
        print(f"{'='*80}")
```

**What to look for**:
- The exact SQL query that failed
- Which table/DocType is missing the column
- Which Python function triggered the error

---

### Step 2: Test Each JSON Generation Function

Test each function in isolation to identify which one is failing:

```python
import frappe

# Use your test data
PLAN_ID = "37q5969lug"  # Replace with your plan ID
SUBJECT_ID = "qunhaa99lf"  # Replace with your subject ID

plan_doc = frappe.get_doc("Memora Academic Plan", PLAN_ID)
subject_doc = frappe.get_doc("Memora Subject", SUBJECT_ID)

# Test 1: Manifest Generation
print("\n=== Test 1: Generate Manifest ===")
try:
    from memora.services.cdn_export.json_generator import generate_manifest
    manifest = generate_manifest(plan_doc)
    print(f"✅ SUCCESS: Generated manifest with {len(manifest.get('subjects', []))} subjects")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Search Index Generation
print("\n=== Test 2: Generate Search Index ===")
try:
    from memora.services.cdn_export.json_generator import generate_search_index
    search_index = generate_search_index(PLAN_ID)
    print(f"✅ SUCCESS: Generated search index")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Subject JSON Generation
print("\n=== Test 3: Generate Subject JSON ===")
try:
    from memora.services.cdn_export.json_generator import generate_subject_json
    subject_json = generate_subject_json(subject_doc, plan_id=PLAN_ID)
    if subject_json:
        print(f"✅ SUCCESS: Generated subject JSON with {len(subject_json.get('tracks', []))} tracks")
    else:
        print(f"⚠️  WARNING: Function returned None")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
```

**Expected output**: One or more tests will fail with the SQL error, pinpointing the problematic function.

---

### Step 3: Validate Schema

Once you know which function is failing, validate the schema of involved DocTypes:

```python
import frappe

def validate_schema(doctype_name):
    """Check if database schema matches DocType definition."""
    meta = frappe.get_meta(doctype_name)
    table_name = f"tab{doctype_name}"

    # Get expected fields
    expected_fields = {f.fieldname: f.label for f in meta.fields}

    # Get actual columns
    columns = frappe.db.sql(f"DESCRIBE `{table_name}`", as_dict=True)
    actual_columns = {col['Field'] for col in columns}

    # Find mismatches
    missing = set(expected_fields.keys()) - actual_columns
    extra = actual_columns - set(expected_fields.keys())

    print(f"\n{'='*60}")
    print(f"Schema Validation: {doctype_name}")
    print(f"{'='*60}")
    print(f"Expected fields: {len(expected_fields)}")
    print(f"Actual columns:  {len(actual_columns)}")

    if missing:
        print(f"\n❌ Missing in database:")
        for field in missing:
            label = expected_fields[field]
            print(f"  - {field} (label: '{label}')")

    if extra:
        print(f"\n⚠️  Extra in database (not in DocType):")
        for col in extra:
            print(f"  - {col}")

    if not missing and not extra:
        print(f"\n✅ Schema is valid!")
    else:
        print(f"\n💡 Suggested action: Run 'bench migrate'")

    return {"valid": not bool(missing), "missing": list(missing), "extra": list(extra)}

# Validate all relevant DocTypes
doctypes_to_check = [
    "Memora Academic Plan",
    "Memora Subject",
    "Memora Track",
    "Memora Unit",
    "Memora Topic",
    "Memora Lesson",
    "Memora Plan Subject",  # Child table
    "Memora Lesson Stage"    # Child table
]

for doctype in doctypes_to_check:
    validate_schema(doctype)
```

**What to look for**:
- Fields marked as "Missing in database" - these cause "Unknown column" errors
- Check if the missing field is a label vs fieldname mismatch

---

## Common Issues & Fixes

### Issue 1: Field Label vs Fieldname Mismatch

**Symptom**: DocType JSON has a field with `label: "Title"` but `fieldname: "subject_title"`

**Fix**: Update queries to use correct fieldname:

```python
# WRONG: Using label
subjects = frappe.get_all("Memora Subject", fields=["Title"])

# CORRECT: Using fieldname
subjects = frappe.get_all("Memora Subject", fields=["subject_title"])

# BEST: Use frappe.get_meta to resolve field
meta = frappe.get_meta("Memora Subject")
title_field = meta.get_field("Title") or meta.get_field("title")
fieldname = title_field.fieldname if title_field else "name"
subjects = frappe.get_all("Memora Subject", fields=[fieldname])
```

---

### Issue 2: Child Table Missing Fields

**Symptom**: Querying child table directly for fields it doesn't have

**Fix**: Access child data via parent document:

```python
# WRONG: Direct child table query
subject_links = frappe.get_all("Memora Plan Subject",
    filters={"parent": plan_id},
    fields=["title"])  # Child table doesn't have 'title'!

# CORRECT: Access via parent
plan = frappe.get_doc("Memora Academic Plan", plan_id)
for subject_link in plan.subjects:  # plan.subjects is the child table
    subject = frappe.get_doc("Memora Subject", subject_link.subject)
    print(subject.title)  # Now accessing parent Subject's title
```

---

### Issue 3: Pending Migrations

**Symptom**: Schema validation shows missing fields that should exist

**Fix**: Run migrations:

```bash
# Check migration status
bench --site {site_name} migrate --show-migration-status

# Run migrations
bench migrate

# Force sync (if migrations fail)
bench --site {site_name} migrate --skip-failing
```

---

## Advanced Debugging

### Enable SQL Query Logging

For deep debugging, enable SQL query logging:

```python
import frappe

# Enable query logging (ONLY in development!)
frappe.db.sql_log = True

# Run your failing function
from memora.services.cdn_export.batch_processor import _rebuild_plan
_rebuild_plan("37q5969lug")

# Check logged queries
for query in frappe.db.sql_queries:
    print(query)

# Disable when done
frappe.db.sql_log = False
```

**Warning**: This generates a lot of output. Use only for targeted debugging.

---

### Trace Function Call Stack

Find where the failing query originates:

```python
import traceback
import frappe

def trace_query():
    """Print call stack when query fails."""
    try:
        from memora.services.cdn_export.batch_processor import _rebuild_plan
        _rebuild_plan("37q5969lug")
    except Exception as e:
        print("="*80)
        print("EXCEPTION CAUGHT:")
        print(f"Error: {e}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("="*80)

        # Get stack frames
        tb = traceback.extract_tb(e.__traceback__)
        print("\nCall Stack (from error to origin):")
        for frame in reversed(tb):
            print(f"  File: {frame.filename}:{frame.lineno}")
            print(f"  Function: {frame.name}")
            print(f"  Code: {frame.line}")
            print()

trace_query()
```

---

## Verification After Fix

Once you've identified and fixed the issue, verify:

### 1. Test Individual Functions Again

Re-run Step 2 tests - all should pass:

```python
# All three tests should show ✅ SUCCESS
```

### 2. Test Full Rebuild

```python
from memora.services.cdn_export.batch_processor import _rebuild_plan

success = _rebuild_plan("37q5969lug")
print(f"Rebuild success: {success}")  # Should be True
```

### 3. Check Generated Files

```bash
ls -lah sites/{site_name}/public/memora_content/subjects/
```

You should see `{subject_id}.json` files.

### 4. Verify JSON Content

```python
import frappe
import json

SUBJECT_ID = "qunhaa99lf"
file_path = f"sites/{frappe.local.site}/public/memora_content/subjects/{SUBJECT_ID}.json"

with open(file_path, 'r') as f:
    data = json.load(f)
    print(json.dumps(data, indent=2))
```

---

## Next Steps

After fixing the immediate issue:

1. **Add Tests**: Create automated tests to prevent regression
   - See `memora/tests/cdn_export/test_json_generator.py`

2. **Document the Fix**: Update TROUBLESHOOTING.md with:
   - Root cause identified
   - Fix applied
   - Prevention measures

3. **Monitor Error Logs**: Check Error Log DocType daily for a week
   - Filter by: Title contains "CDN"
   - Ensure no new "Unknown column" errors

4. **Consider Preventive Measures**:
   - Add schema validation checks before JSON generation
   - Implement pre-flight checks in `_rebuild_plan()`
   - Add query audit logging for production debugging

---

## Getting Help

If this guide doesn't resolve your issue:

1. **Capture Full Context**:
   - Error Log entries (with full traceback)
   - Schema validation results for all DocTypes
   - Test results from Step 2
   - SQL query that's failing

2. **Check Frappe Forums**:
   - https://discuss.frappe.io/
   - Search for "Unknown column" errors

3. **Review Frappe Database API Docs**:
   - https://frappeframework.com/docs/user/en/api/database

4. **Create GitHub Issue** (if bug in Memora):
   - Include all information from step 1
   - Specify Frappe version: `bench version`
   - Include MariaDB version: `mysql --version`

---

## Appendix: Reference Data

### Creating Test Data

You can create test data using the provided fixtures:

```python
from memora.tests.cdn_export.fixtures import create_full_test_hierarchy, cleanup_test_data

# Create test hierarchy
test_data = create_full_test_hierarchy(
    plan_id="TEST-PLAN-DEBUG",
    subject_id="TEST-SUBJ-DEBUG",
    track_id="TEST-TRACK-DEBUG"
)

print(f"Created plan: {test_data['plan'].name}")
print(f"Created subject: {test_data['subject'].name}")
print(f"Created track: {test_data['track'].name}")

# Clean up when done
cleanup_test_data(
    plan_id="TEST-PLAN-DEBUG",
    subject_id="TEST-SUBJ-DEBUG",
    track_id="TEST-TRACK-DEBUG"
)
```

### Test Data IDs
- Production Plan ID: `37q5969lug`
- Production Subject ID: `qunhaa99lf`
- Test Plan ID: `TEST-PLAN-DEBUG` (created via fixtures)
- Test Subject ID: `TEST-SUBJ-DEBUG` (created via fixtures)

### File Paths
- JSON output: `/sites/{site}/public/memora_content/subjects/{subject_id}.json`
- Error logs: Frappe UI → Error Log DocType
- Source code: `memora/services/cdn_export/json_generator.py`

### Key Functions
- `generate_manifest(plan_doc)` - Generates plan manifest JSON
- `generate_subject_json(subject_doc, plan_id)` - Generates subject JSON
- `generate_search_index(plan_id)` - Generates search index
- `_rebuild_plan(plan_id)` - Rebuilds all JSON for a plan

### DocTypes Involved
- Memora Academic Plan (parent)
- Memora Subject (parent)
- Memora Track (parent)
- Memora Unit (parent)
- Memora Topic (parent)
- Memora Lesson (parent)
- Memora Plan Subject (child table)
- Memora Lesson Stage (child table)
