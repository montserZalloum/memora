# Research: JSON Generation Debug & Fix

**Feature**: 006-json-generation-debug
**Date**: 2026-01-26
**Status**: Complete

## Research Questions & Findings

### 1. Frappe ORM Field Name Resolution

**Question**: How does Frappe ORM map field labels to database column names, and can it cause "Unknown column" errors?

**Decision**: Use `frappe.get_meta(doctype_name)` to retrieve field metadata and resolve actual database column names from labels.

**Rationale**:
- Frappe DocTypes can have a field with `label: "Title"` but `fieldname: "subject_title"` or `fieldname: "name"`
- The ORM uses `fieldname` for database columns, not `label`
- When queries use field labels instead of fieldnames, MariaDB throws "Unknown column" errors
- `frappe.get_meta(doctype).get_field(label_or_fieldname)` returns the correct `Field` object with actual `fieldname`

**Alternatives Considered**:
- **Direct schema inspection**: Rejected because it requires extra database queries and doesn't leverage Frappe's metadata cache
- **Hardcoded field mappings**: Rejected because it's brittle and breaks when DocType schemas change
- **Try-catch around all queries**: Rejected because it doesn't fix the root cause, just masks errors

**Best Practices**:
- Always use `fields` parameter in `frappe.get_all()` with explicit fieldnames, not labels
- For dynamic queries, validate field existence: `frappe.get_meta(doctype).has_field(fieldname)`
- Use `frappe.get_doc()` for single documents - it handles field mapping automatically

**References**:
- Frappe Framework documentation: https://frappeframework.com/docs/user/en/api/database
- DocType Meta API: `frappe.model.meta.get_meta()`

---

### 2. Frappe Query Patterns and Child Table Queries

**Question**: What query patterns in Frappe can cause column reference errors, especially with child tables?

**Decision**: Audit all `frappe.db.get_all()`, `frappe.db.sql()`, and child table iterations for proper field name usage.

**Rationale**:
- Child tables (like `Memora Plan Subject`) have different schemas than parent DocTypes
- Joining parent and child tables requires explicit field qualification: `parent.title` vs `child.name`
- `frappe.get_all("DocType", fields=["*"])` can fail if DocType has fields that conflict with standard fields
- Child tables accessed via `parent_doc.child_table_fieldname` don't require explicit queries

**Alternatives Considered**:
- **Use raw SQL for all queries**: Rejected because it bypasses Frappe's permission system and field mapping
- **Fetch all data and filter in Python**: Rejected for performance reasons with large datasets
- **Avoid child tables**: Not applicable - child tables are core to Frappe's data model

**Best Practices**:
- For child tables, access via parent document: `plan_doc.subjects` instead of querying `tabMemora Plan Subject`
- If querying child tables directly, always specify `parent` field to link back
- Use table aliases in SQL queries: `SELECT p.title, c.name FROM tabParent p JOIN tabChild c ON c.parent = p.name`
- Validate child table schema before constructing dynamic queries

**Common Frappe Query Patterns**:
```python
# GOOD: Explicit fields
subjects = frappe.get_all("Memora Subject",
    filters={"name": ["in", subject_ids]},
    fields=["name", "title", "description"])

# BAD: Using "*" can cause conflicts
subjects = frappe.get_all("Memora Subject", fields=["*"])

# GOOD: Child table access via parent
plan = frappe.get_doc("Memora Academic Plan", plan_id)
for subject_link in plan.subjects:  # subjects is child table
    subject = frappe.get_doc("Memora Subject", subject_link.subject)

# BAD: Direct child table query without proper field names
subject_links = frappe.get_all("Memora Plan Subject",
    filters={"parent": plan_id},
    fields=["title"])  # ERROR: child table doesn't have 'title'
```

**References**:
- Frappe Database API: https://frappeframework.com/docs/user/en/api/database
- Child Tables: https://frappeframework.com/docs/user/en/basics/doctypes/child-doctype

---

### 3. Diagnostic Tools and Error Tracing in Frappe

**Question**: What's the best way to capture full SQL queries and tracebacks in Frappe for debugging?

**Decision**: Implement custom diagnostic wrapper functions that capture query execution with try-catch blocks and log to Error Log DocType.

**Rationale**:
- `frappe.log_error(message, title)` writes to Error Log DocType with full traceback
- Frappe's built-in query logging (`frappe.db.sql_list`) doesn't capture errors well
- Error Log provides UI visibility without requiring log file access
- Can enable SQL query logging temporarily: `frappe.db.sql_log = True` (for development only)

**Alternatives Considered**:
- **Python logging module**: Rejected because it writes to files, harder for non-technical users to access
- **Print statements**: Rejected because output is lost in background jobs
- **Database triggers**: Rejected as too invasive and not portable across Frappe versions

**Best Practices**:
- Wrap risky query sections in try-except blocks
- Log full traceback: `import traceback; frappe.log_error(traceback.format_exc(), "Error Title")`
- Include context in error messages: query parameters, DocType names, IDs
- For debugging, temporarily enable: `frappe.conf.developer_mode = 1` and `frappe.db.sql_log = True`

**Diagnostic Code Pattern**:
```python
import frappe
import traceback

def safe_query_with_logging(doctype, filters, fields):
    """Execute query with full error logging."""
    try:
        frappe.log_error(
            f"[DEBUG] Querying {doctype} with fields: {fields}",
            "CDN Debug"
        )
        result = frappe.get_all(doctype, filters=filters, fields=fields)
        return result
    except Exception as e:
        error_msg = f"""
        DocType: {doctype}
        Filters: {filters}
        Fields: {fields}

        Error: {str(e)}

        Traceback:
        {traceback.format_exc()}
        """
        frappe.log_error(error_msg, "CDN Query Error")
        raise
```

**References**:
- Frappe Error Log: https://frappeframework.com/docs/user/en/api/frappe-utils
- Debugging Frappe: https://frappeframework.com/docs/user/en/guides/debugging

---

### 4. Schema Validation Strategies

**Question**: How to validate that database schema matches DocType JSON definitions to prevent column errors?

**Decision**: Implement schema validation utility that compares DocType metadata with actual database columns using `DESCRIBE` queries.

**Rationale**:
- `frappe.get_meta(doctype).fields` returns expected fields from DocType JSON
- `frappe.db.sql("DESCRIBE `tab{doctype}`")` returns actual database columns
- Mismatches indicate pending migrations or schema drift
- Validation can run before JSON generation to prevent errors

**Alternatives Considered**:
- **Trust migrations**: Rejected because migrations can fail or be skipped
- **Try queries and handle errors**: Rejected because it's reactive, not proactive
- **Manual schema inspection**: Rejected as not scalable and error-prone

**Best Practices**:
- Run schema validation as a pre-flight check before complex operations
- Cache validation results to avoid repeated database queries
- Provide clear error messages: "Field 'title' expected but not found in table 'tabMemora Plan Subject'"
- Suggest remediation: "Run: bench migrate to apply pending migrations"

**Schema Validation Pattern**:
```python
def validate_doctype_schema(doctype_name):
    """Validate database schema matches DocType definition."""
    meta = frappe.get_meta(doctype_name)
    table_name = f"tab{doctype_name}"

    # Get expected fields from DocType
    expected_fields = {f.fieldname for f in meta.fields}

    # Get actual columns from database
    columns = frappe.db.sql(f"DESCRIBE `{table_name}`", as_dict=True)
    actual_columns = {col['Field'] for col in columns}

    # Find mismatches
    missing_in_db = expected_fields - actual_columns
    extra_in_db = actual_columns - expected_fields

    if missing_in_db:
        return {
            "valid": False,
            "missing": list(missing_in_db),
            "message": f"Fields missing in database: {missing_in_db}"
        }

    return {"valid": True, "message": "Schema valid"}
```

**References**:
- Frappe Migrations: https://frappeframework.com/docs/user/en/guides/database-migrations
- DocType Meta: https://frappeframework.com/docs/user/en/api/document

---

### 5. Test Isolation Strategies for JSON Generation

**Question**: How to test individual JSON generation functions in isolation when they have complex dependencies?

**Decision**: Create test fixtures with minimal DocType data and mock Frappe context for unit testing.

**Rationale**:
- Frappe's test framework (`frappe.test_runner`) provides test site with isolated database
- Can create minimal test data: 1 plan, 1 subject, 1 track, 1 unit
- Mocking external dependencies (Redis, CDN uploader) allows testing JSON generation logic only
- Test runner handles setup/teardown of Frappe context

**Alternatives Considered**:
- **Test in production**: Rejected as unsafe and non-reproducible
- **Manual console testing only**: Rejected because it's not automated and can't be run in CI/CD
- **Integration tests only**: Rejected because they don't isolate which function is failing

**Best Practices**:
- Use `frappe.set_user("Administrator")` in tests to bypass permissions
- Create test fixtures in `setUp()` method, clean up in `tearDown()`
- Use `frappe.flags.in_test = True` to skip external API calls
- Mock Redis operations: `frappe.cache().get = lambda x: None`

**Test Pattern**:
```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestJSONGeneration(FrappeTestCase):
    def setUp(self):
        """Create minimal test data."""
        self.plan = frappe.get_doc({
            "doctype": "Memora Academic Plan",
            "title": "Test Plan",
            "name": "TEST-PLAN-001"
        }).insert()

        self.subject = frappe.get_doc({
            "doctype": "Memora Subject",
            "title": "Test Subject",
            "name": "TEST-SUBJ-001"
        }).insert()

        # Link subject to plan
        self.plan.append("subjects", {
            "subject": self.subject.name,
            "sort_order": 1
        })
        self.plan.save()

    def test_generate_manifest(self):
        """Test manifest generation in isolation."""
        from memora.services.cdn_export.json_generator import generate_manifest

        manifest = generate_manifest(self.plan)

        self.assertIsNotNone(manifest)
        self.assertIn("subjects", manifest)
        self.assertEqual(len(manifest["subjects"]), 1)

    def tearDown(self):
        """Clean up test data."""
        frappe.delete_doc("Memora Academic Plan", self.plan.name)
        frappe.delete_doc("Memora Subject", self.subject.name)
```

**References**:
- Frappe Testing: https://frappeframework.com/docs/user/en/guides/automated-testing
- Test Utils: https://github.com/frappe/frappe/blob/develop/frappe/tests/utils.py

---

## Summary of Technical Decisions

| Area | Decision | Key Benefit |
|------|----------|-------------|
| Field Name Resolution | Use `frappe.get_meta()` for field metadata | Prevents label vs fieldname confusion |
| Query Patterns | Explicit field lists, avoid `*` | Reduces ambiguity and errors |
| Error Tracing | Wrap queries in try-catch with `frappe.log_error()` | Full visibility in Error Log UI |
| Schema Validation | Pre-flight checks with `DESCRIBE` queries | Proactive error prevention |
| Test Isolation | Frappe test framework with minimal fixtures | Fast, automated, reproducible |

---

## Implementation Readiness

All research questions resolved. No remaining "NEEDS CLARIFICATION" items. Ready to proceed to Phase 1: Design & Contracts.

**Next Steps**:
1. Create `data-model.md` documenting diagnostic data structures
2. Define contracts for diagnostic API endpoints
3. Create `quickstart.md` for developers debugging JSON generation issues
