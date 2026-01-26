# Data Model: JSON Generation Debug & Fix

**Feature**: 006-json-generation-debug
**Date**: 2026-01-26
**Purpose**: Define data structures for diagnostic and debugging operations

---

## Diagnostic Data Structures

### 1. SQL Query Diagnostic Result

**Purpose**: Capture full context when a SQL query fails during JSON generation

**Fields**:
- `query` (str): The SQL query that failed or was executed
- `doctype` (str): Target DocType being queried
- `filters` (dict): Query filters applied
- `fields` (list[str]): Fields requested in the query
- `error_message` (str): Error message from database (e.g., "Unknown column 'title'")
- `error_type` (str): Python exception class name (e.g., "OperationalError")
- `traceback` (str): Full Python traceback
- `timestamp` (datetime): When the error occurred
- `context` (dict): Additional context (plan_id, subject_id, function_name)

**Validation Rules**:
- `query` must not be empty
- `doctype` must be a valid Frappe DocType name
- `error_message` required if query failed
- `timestamp` defaults to current time

**Example**:
```python
{
    "query": "SELECT `title` FROM `tabMemora Plan Subject` WHERE `parent` = '37q5969lug'",
    "doctype": "Memora Plan Subject",
    "filters": {"parent": "37q5969lug"},
    "fields": ["title"],
    "error_message": "(1054, \"Unknown column 'title' in field list\")",
    "error_type": "OperationalError",
    "traceback": "Traceback (most recent call last):\n  File ...",
    "timestamp": "2026-01-26 10:30:45",
    "context": {
        "plan_id": "37q5969lug",
        "function_name": "generate_manifest"
    }
}
```

---

### 2. Schema Validation Report

**Purpose**: Compare DocType metadata with actual database schema to detect mismatches

**Fields**:
- `doctype` (str): DocType name being validated
- `table_name` (str): Database table name (e.g., "tabMemora Subject")
- `expected_fields` (list[dict]): Fields defined in DocType JSON
  - `fieldname` (str): Field name
  - `label` (str): Field label
  - `fieldtype` (str): Frappe field type (e.g., "Data", "Link")
- `actual_columns` (list[dict]): Columns in database table
  - `column_name` (str): Database column name
  - `column_type` (str): SQL column type (e.g., "varchar(140)")
  - `nullable` (bool): Whether column allows NULL
- `missing_in_db` (list[str]): Fields in DocType but not in database
- `extra_in_db` (list[str]): Columns in database but not in DocType
- `mismatched_types` (list[dict]): Fields with type mismatches
  - `fieldname` (str)
  - `expected_type` (str)
  - `actual_type` (str)
- `valid` (bool): Whether schema matches completely
- `validation_timestamp` (datetime): When validation was performed

**Validation Rules**:
- `doctype` must exist in Frappe
- `table_name` must exist in database
- `valid` is `False` if any of: `missing_in_db`, `extra_in_db`, or `mismatched_types` are non-empty

**Example**:
```python
{
    "doctype": "Memora Plan Subject",
    "table_name": "tabMemora Plan Subject",
    "expected_fields": [
        {"fieldname": "title", "label": "Title", "fieldtype": "Data"},
        {"fieldname": "subject", "label": "Subject", "fieldtype": "Link"}
    ],
    "actual_columns": [
        {"column_name": "parent", "column_type": "varchar(140)", "nullable": False},
        {"column_name": "subject", "column_type": "varchar(140)", "nullable": True}
    ],
    "missing_in_db": ["title"],
    "extra_in_db": ["parent"],
    "mismatched_types": [],
    "valid": False,
    "validation_timestamp": "2026-01-26 10:35:00"
}
```

---

### 3. JSON Generation Test Result

**Purpose**: Capture results when testing individual JSON generation functions in isolation

**Fields**:
- `function_name` (str): Function tested (e.g., "generate_manifest", "generate_subject_json")
- `test_input` (dict): Input parameters provided
  - For `generate_manifest`: `plan_doc` or `plan_id`
  - For `generate_subject_json`: `subject_doc`, `plan_id`
  - For `generate_search_index`: `plan_id`
- `success` (bool): Whether function executed without error
- `output_data` (dict|None): JSON data returned by function (if successful)
- `output_size_bytes` (int): Size of output JSON in bytes
- `error` (dict|None): Error information (if failed)
  - `message` (str)
  - `type` (str)
  - `traceback` (str)
- `execution_time_ms` (float): How long function took to execute
- `timestamp` (datetime): When test was run

**Validation Rules**:
- `function_name` must be one of: `["generate_manifest", "generate_subject_json", "generate_unit_json", "generate_lesson_json", "generate_search_index"]`
- If `success` is `True`, `output_data` must not be None
- If `success` is `False`, `error` must not be None
- `execution_time_ms` must be >= 0

**Example (Success)**:
```python
{
    "function_name": "generate_manifest",
    "test_input": {
        "plan_id": "37q5969lug"
    },
    "success": True,
    "output_data": {
        "plan_id": "37q5969lug",
        "subjects": [
            {"id": "qunhaa99lf", "title": "Mathematics", "tracks": 3}
        ]
    },
    "output_size_bytes": 245,
    "error": None,
    "execution_time_ms": 125.5,
    "timestamp": "2026-01-26 10:40:00"
}
```

**Example (Failure)**:
```python
{
    "function_name": "generate_manifest",
    "test_input": {
        "plan_id": "37q5969lug"
    },
    "success": False,
    "output_data": None,
    "output_size_bytes": 0,
    "error": {
        "message": "(1054, \"Unknown column 'title' in field list\")",
        "type": "OperationalError",
        "traceback": "Traceback (most recent call last):\n..."
    },
    "execution_time_ms": 42.3,
    "timestamp": "2026-01-26 10:40:00"
}
```

---

### 4. Query Audit Entry

**Purpose**: Track all SQL queries executed during JSON generation for pattern analysis

**Fields**:
- `query_id` (str): Unique identifier for this query execution
- `query` (str): SQL query executed
- `query_type` (str): Type of query ("SELECT", "INSERT", "UPDATE", "DELETE")
- `doctype` (str): Primary DocType being queried
- `method` (str): Frappe method used ("frappe.get_all", "frappe.db.sql", "frappe.get_doc")
- `fields_requested` (list[str]): Fields/columns requested
- `filters` (dict): Query filters
- `source_file` (str): Python file where query originated
- `source_line` (int): Line number in source file
- `execution_context` (dict): Context when query ran
  - `plan_id` (str|None)
  - `subject_id` (str|None)
  - `function_name` (str)
- `result_count` (int|None): Number of rows returned (for SELECT)
- `success` (bool): Whether query succeeded
- `timestamp` (datetime): When query was executed

**Validation Rules**:
- `query` must not be empty
- `query_type` must be one of: ["SELECT", "INSERT", "UPDATE", "DELETE"]
- `method` must be valid Frappe DB method
- `source_file` and `source_line` should be captured from traceback

**Example**:
```python
{
    "query_id": "q_20260126_104500_001",
    "query": "SELECT `name`, `title` FROM `tabMemora Subject` WHERE `name` IN ('qunhaa99lf')",
    "query_type": "SELECT",
    "doctype": "Memora Subject",
    "method": "frappe.get_all",
    "fields_requested": ["name", "title"],
    "filters": {"name": ["in", ["qunhaa99lf"]]},
    "source_file": "memora/services/cdn_export/json_generator.py",
    "source_line": 145,
    "execution_context": {
        "plan_id": "37q5969lug",
        "subject_id": "qunhaa99lf",
        "function_name": "generate_subject_json"
    },
    "result_count": 1,
    "success": True,
    "timestamp": "2026-01-26 10:45:00"
}
```

---

## Relationships Between Entities

```
[Plan Rebuild Attempt]
        |
        ├─── [SQL Query Diagnostic Result]  (if query fails)
        |
        ├─── [JSON Generation Test Result]  (for each function: manifest, search, subject)
        |           |
        |           └─── [Query Audit Entry]*  (multiple queries per function)
        |
        └─── [Schema Validation Report]*  (for each DocType involved)
```

---

## State Transitions

### Schema Validation Report

```
[Initial] → [Validating] → [Valid] or [Invalid]
                              |
                              ├─ Missing Fields → [Run Migration] → [Re-validate]
                              ├─ Extra Fields → [Review Schema] → [Re-validate]
                              └─ Type Mismatch → [Run Migration] → [Re-validate]
```

### JSON Generation Test Result

```
[Not Run] → [Running] → [Success] or [Failed]
                           |            |
                           |            └─ [Diagnose] → [Fixed] → [Re-test]
                           |
                           └─ [Deploy to Production]
```

---

## Data Retention

**Diagnostic Results**: Retained for 30 days for debugging purposes
**Query Audit Entries**: Retained for 7 days (high volume)
**Schema Validation Reports**: Retained for 90 days (low volume, useful for schema drift detection)
**Test Results**: Retained indefinitely for regression tracking

---

## Usage Examples

### 1. Diagnose Failing Query

```python
from memora.utils.diagnostics import diagnose_query_failure

result = diagnose_query_failure(
    doctype="Memora Plan Subject",
    filters={"parent": "37q5969lug"},
    fields=["title", "subject"]
)

if not result["success"]:
    print(f"Query failed: {result['error_message']}")
    print(f"Missing fields: {result['schema_report']['missing_in_db']}")
```

### 2. Test JSON Generation Function

```python
from memora.utils.diagnostics import test_json_function

test_result = test_json_function(
    function_name="generate_manifest",
    plan_id="37q5969lug"
)

print(f"Success: {test_result['success']}")
print(f"Execution time: {test_result['execution_time_ms']}ms")
if test_result['error']:
    print(f"Error: {test_result['error']['message']}")
```

### 3. Validate Schema

```python
from memora.utils.diagnostics import validate_schema

report = validate_schema("Memora Plan Subject")

if not report["valid"]:
    print(f"Schema invalid!")
    print(f"Missing in DB: {report['missing_in_db']}")
    print(f"Suggested action: Run 'bench migrate'")
```

---

## Notes

- All datetime fields use ISO 8601 format: `YYYY-MM-DD HH:MM:SS`
- All data structures are designed to be serializable to JSON for API responses
- Field names use snake_case to match Python conventions
- Size limits: `query` and `traceback` fields limited to 10,000 characters to prevent Error Log bloat
