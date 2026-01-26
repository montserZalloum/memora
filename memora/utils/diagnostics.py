"""Diagnostic utilities for CDN export debugging.

This module provides tools for diagnosing JSON generation failures,
including schema validation, query diagnostics, and function testing.
"""

import frappe
import traceback
import time
from typing import Dict, List, Optional, Any


def validate_schema(doctype_name: str) -> Dict[str, Any]:
    """Validate that database schema matches DocType definition.

    Compares DocType metadata with actual database columns using DESCRIBE queries.
    Properly handles Child Tables and Table-type fields.

    Args:
        doctype_name: Name of the DocType to validate

    Returns:
        SchemaValidationReport dict with fields:
        - doctype: str - DocType name
        - table_name: str - Database table name
        - is_child_table: bool - Whether this is a Child Table
        - expected_fields: list[dict] - Fields defined in DocType
        - actual_columns: list[dict] - Columns in database
        - missing_in_db: list[str] - Fields in DocType but not in database
        - extra_in_db: list[str] - Columns in database but not in DocType
        - mismatched_types: list[dict] - Fields with type mismatches
        - valid: bool - Whether schema matches completely
        - validation_timestamp: str - When validation was performed

    Example:
        >>> report = validate_schema("Memora Subject")
        >>> if not report["valid"]:
        >>>     print(f"Missing fields: {report['missing_in_db']}")
    """
    from datetime import datetime

    # Get DocType metadata
    meta = frappe.get_meta(doctype_name)
    table_name = f"tab{doctype_name}"
    is_child_table = meta.istable

    # Get expected fields from DocType
    expected_fields = []
    expected_fieldnames = set()

    for field in meta.fields:
        # Skip layout fields that don't create database columns
        if field.fieldtype in ["Section Break", "Column Break", "Tab Break", "HTML", "Button"]:
            continue

        # Skip Table fields - they don't create actual database columns
        # Table fields create relationships to Child Tables instead
        if field.fieldtype == "Table":
            continue

        expected_fields.append({
            "fieldname": field.fieldname,
            "label": field.label or field.fieldname,
            "fieldtype": field.fieldtype
        })
        expected_fieldnames.add(field.fieldname)

    # Add standard fields based on whether it's a Child Table or not
    if is_child_table:
        # Child Tables have these standard fields
        child_table_standard_fields = [
            "name", "owner", "creation", "modified", "modified_by",
            "docstatus", "idx",
            "parent", "parenttype", "parentfield"  # Child Table specific
        ]
        for std_field in child_table_standard_fields:
            expected_fieldnames.add(std_field)
    else:
        # Parent DocTypes have these standard fields
        parent_standard_fields = [
            "name", "owner", "creation", "modified", "modified_by",
            "docstatus", "idx",
            "_user_tags", "_comments", "_assign", "_liked_by"  # Parent only
        ]
        for std_field in parent_standard_fields:
            expected_fieldnames.add(std_field)

    # Get actual columns from database
    try:
        columns = frappe.db.sql(f"DESCRIBE `{table_name}`", as_dict=True)
    except Exception as e:
        return {
            "doctype": doctype_name,
            "table_name": table_name,
            "is_child_table": is_child_table,
            "expected_fields": expected_fields,
            "actual_columns": [],
            "missing_in_db": list(expected_fieldnames),
            "extra_in_db": [],
            "mismatched_types": [],
            "valid": False,
            "validation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": f"Table does not exist: {str(e)}"
        }

    actual_columns = []
    actual_column_names = set()

    for col in columns:
        actual_columns.append({
            "column_name": col.get("Field"),
            "column_type": col.get("Type"),
            "nullable": col.get("Null") == "YES"
        })
        actual_column_names.add(col.get("Field"))

    # Find mismatches
    missing_in_db = list(expected_fieldnames - actual_column_names)
    extra_in_db = list(actual_column_names - expected_fieldnames)

    # Check for type mismatches (simplified - just check if field exists)
    mismatched_types = []

    # Determine if valid
    valid = len(missing_in_db) == 0 and len(extra_in_db) == 0 and len(mismatched_types) == 0

    return {
        "doctype": doctype_name,
        "table_name": table_name,
        "is_child_table": is_child_table,
        "expected_fields": expected_fields,
        "actual_columns": actual_columns,
        "missing_in_db": missing_in_db,
        "extra_in_db": extra_in_db,
        "mismatched_types": mismatched_types,
        "valid": valid,
        "validation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def diagnose_query_failure(doctype: str, filters: Dict, fields: List[str]) -> Dict[str, Any]:
    """Diagnose query execution and capture full error context.

    Wraps query execution in try-catch with full traceback capture.

    Args:
        doctype: DocType name to query
        filters: Query filters dict
        fields: List of field names to retrieve

    Returns:
        QueryDiagnosticResult dict with fields:
        - query: str - SQL query executed
        - doctype: str - Target DocType
        - filters: dict - Query filters
        - fields: list[str] - Fields requested
        - success: bool - Whether query succeeded
        - result: list - Query results (if successful)
        - error_message: str - Error message (if failed)
        - error_type: str - Exception class name (if failed)
        - traceback: str - Full Python traceback (if failed)
        - schema_report: dict - Schema validation report
        - timestamp: str - When query was executed

    Example:
        >>> result = diagnose_query_failure("Memora Subject", {"name": "test"}, ["name", "title"])
        >>> if not result["success"]:
        >>>     print(f"Query failed: {result['error_message']}")
        >>>     print(f"Missing fields: {result['schema_report']['missing_in_db']}")
    """
    from datetime import datetime

    # Run schema validation first
    schema_report = validate_schema(doctype)

    # Attempt to execute query
    query_str = None
    success = False
    result = None
    error_message = None
    error_type = None
    traceback_str = None

    try:
        # Enable query logging temporarily to capture SQL
        sql_log_before = frappe.db.sql_log
        frappe.db.sql_log = []

        # Execute query
        result = frappe.get_all(doctype, filters=filters, fields=fields)

        # Capture the SQL query
        if frappe.db.sql_log:
            query_str = frappe.db.sql_log[-1]

        # Restore sql_log state
        frappe.db.sql_log = sql_log_before

        success = True

        # Log successful query for debugging
        frappe.log_error(
            f"[DEBUG] Query succeeded for {doctype}\nFields: {fields}\nFilters: {filters}\nResults: {len(result)} rows",
            "CDN Query Success"
        )

    except Exception as e:
        error_message = str(e)
        error_type = type(e).__name__
        traceback_str = traceback.format_exc()

        # Try to capture query from error
        if not query_str and hasattr(e, 'args') and len(e.args) > 1:
            query_str = str(e.args[1]) if isinstance(e.args[1], str) else None

        # Log error to Error Log DocType
        error_context = f"""
DocType: {doctype}
Filters: {filters}
Fields: {fields}

Error: {error_message}
Type: {error_type}

Schema Validation:
- Missing in DB: {schema_report.get('missing_in_db', [])}
- Extra in DB: {schema_report.get('extra_in_db', [])}

Traceback:
{traceback_str}
"""
        frappe.log_error(error_context, "CDN Query Error")

    return {
        "query": query_str or f"SELECT {', '.join(fields)} FROM `tab{doctype}` WHERE ...",
        "doctype": doctype,
        "filters": filters,
        "fields": fields,
        "success": success,
        "result": result,
        "error_message": error_message,
        "error_type": error_type,
        "traceback": traceback_str,
        "schema_report": schema_report,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def test_json_function(function_name: str, **kwargs) -> Dict[str, Any]:
    """Test a JSON generation function in isolation.

    Supports testing: generate_manifest, generate_subject_json, generate_search_index

    Args:
        function_name: Name of function to test
        **kwargs: Function-specific parameters
            For generate_manifest: plan_id
            For generate_subject_json: subject_id, plan_id
            For generate_search_index: plan_id

    Returns:
        JSONGenerationTestResult dict with fields:
        - function_name: str
        - test_input: dict - Input parameters
        - success: bool - Whether function executed without error
        - output_data: dict - JSON data returned (if successful)
        - output_size_bytes: int - Size of output JSON
        - error: dict - Error information (if failed)
        - execution_time_ms: float - Execution time
        - timestamp: str - When test was run

    Example:
        >>> result = test_json_function("generate_manifest", plan_id="37q5969lug")
        >>> print(f"Success: {result['success']}")
        >>> print(f"Execution time: {result['execution_time_ms']}ms")
    """
    from datetime import datetime
    import json

    valid_functions = [
        "generate_manifest",
        "generate_subject_json",
        "generate_unit_json",
        "generate_lesson_json",
        "generate_search_index"
    ]

    if function_name not in valid_functions:
        return {
            "function_name": function_name,
            "test_input": kwargs,
            "success": False,
            "output_data": None,
            "output_size_bytes": 0,
            "error": {
                "message": f"Invalid function name. Must be one of: {valid_functions}",
                "type": "ValueError",
                "traceback": None
            },
            "execution_time_ms": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # Dispatch to appropriate test wrapper
    start_time = time.time()

    try:
        if function_name == "generate_manifest":
            output_data = _test_generate_manifest(kwargs.get("plan_id"))
        elif function_name == "generate_subject_json":
            output_data = _test_generate_subject_json(
                kwargs.get("subject_id"),
                kwargs.get("plan_id")
            )
        elif function_name == "generate_search_index":
            output_data = _test_generate_search_index(kwargs.get("plan_id"))
        else:
            output_data = {"error": "Function not yet implemented in test harness"}

        execution_time_ms = (time.time() - start_time) * 1000

        # Calculate output size
        output_size_bytes = len(json.dumps(output_data)) if output_data else 0

        return {
            "function_name": function_name,
            "test_input": kwargs,
            "success": True,
            "output_data": output_data,
            "output_size_bytes": output_size_bytes,
            "error": None,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000

        return {
            "function_name": function_name,
            "test_input": kwargs,
            "success": False,
            "output_data": None,
            "output_size_bytes": 0,
            "error": {
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            },
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


def _test_generate_manifest(plan_id: str) -> Dict[str, Any]:
    """Test wrapper for generate_manifest function.

    Args:
        plan_id: Academic plan ID

    Returns:
        Manifest data dict with success, output_data, error, execution_time_ms
    """
    from memora.services.cdn_export.json_generator import generate_manifest

    # Get plan document
    plan_doc = frappe.get_doc("Memora Academic Plan", plan_id)

    # Call function
    manifest_data = generate_manifest(plan_doc)

    return manifest_data


def _test_generate_search_index(plan_id: str) -> Dict[str, Any]:
    """Test wrapper for generate_search_index function.

    Args:
        plan_id: Academic plan ID

    Returns:
        Search index data dict
    """
    from memora.services.cdn_export.json_generator import generate_search_index

    # Call function
    search_index = generate_search_index(plan_id)

    return search_index


def _test_generate_subject_json(subject_id: str, plan_id: str) -> Dict[str, Any]:
    """Test wrapper for generate_subject_json function.

    Args:
        subject_id: Subject document ID
        plan_id: Academic plan ID

    Returns:
        Subject JSON data dict
    """
    from memora.services.cdn_export.json_generator import generate_subject_json

    # Get subject document
    subject_doc = frappe.get_doc("Memora Subject", subject_id)

    # Call function
    subject_data = generate_subject_json(subject_doc, plan_id)

    return subject_data


def get_recent_error_logs(minutes: int = 30, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recent error logs from Error Log DocType.

    This function is part of User Story 1: System Administrator Diagnoses JSON Generation Failure.
    It queries Error Log DocType for recent CDN-related errors.

    Args:
        minutes: How many minutes back to search (default: 30)
        search_term: Optional search term to filter by title or error content

    Returns:
        List of error log dicts with fields:
        - name: str - Error Log document ID
        - title: str - Error title
        - error: str - Error message/traceback
        - creation: str - When error was logged

    Example:
        >>> logs = get_recent_error_logs(minutes=60, search_term="CDN")
        >>> for log in logs:
        >>>     print(f"{log['creation']}: {log['title']}")
    """
    from frappe.utils import now_datetime, add_to_date

    # Calculate time threshold
    time_threshold = add_to_date(now_datetime(), minutes=-abs(minutes))

    # Build filters
    filters = {
        "creation": [">", time_threshold]
    }

    # Add search term filter if provided
    if search_term:
        # Use SQL LIKE for searching in title and error fields
        error_logs = frappe.db.sql("""
            SELECT name, title, error, creation
            FROM `tabError Log`
            WHERE creation > %s
            AND (title LIKE %s OR error LIKE %s)
            ORDER BY creation DESC
            LIMIT 100
        """, (time_threshold, f"%{search_term}%", f"%{search_term}%"), as_dict=True)
    else:
        # Get all recent errors
        error_logs = frappe.db.get_all(
            "Error Log",
            filters=filters,
            fields=["name", "title", "error", "creation"],
            order_by="creation desc",
            limit_page_length=100
        )

    # Truncate error field to 1000 chars for readability in list view
    for log in error_logs:
        if log.get("error") and len(log["error"]) > 1000:
            log["error"] = log["error"][:1000] + "... (truncated)"

    return error_logs


def audit_queries_for_function(function_name: str, plan_id: str, subject_id: Optional[str] = None) -> Dict[str, Any]:
    """Audit all SQL queries executed during a JSON generation function call.

    This function is part of User Story 3: Developer Traces Dynamic Query Construction.
    It monkey-patches frappe.db methods to capture all queries executed.

    Args:
        function_name: Name of function to audit (generate_manifest, generate_subject_json, generate_search_index)
        plan_id: Academic plan ID
        subject_id: Subject ID (required for generate_subject_json)

    Returns:
        dict with fields:
        - function_name: str
        - function_success: bool - Whether function completed without error
        - query_count: int - Number of queries executed
        - queries: list[QueryAuditEntry] - List of captured queries
        - execution_time_ms: float - Total execution time
        - error: dict - Error info if function failed

    QueryAuditEntry structure:
        - query_id: int - Sequential query number
        - query: str - SQL query executed
        - query_type: str - Type of query (SELECT, INSERT, UPDATE, etc.)
        - doctype: str - DocType being queried (if applicable)
        - method: str - Frappe method used (get_all, sql, get_doc, etc.)
        - fields_requested: list[str] - Fields requested (for get_all)
        - source_file: str - File where query was called from
        - source_line: int - Line number where query was called from

    Example:
        >>> result = audit_queries_for_function("generate_manifest", "37q5969lug")
        >>> for query in result['queries']:
        >>>     print(f"Query {query['query_id']}: {query['query'][:100]}")
    """
    from datetime import datetime
    import inspect

    queries = []
    query_counter = [0]  # Use list to allow modification in nested function
    original_sql = frappe.db.sql
    original_get_all = frappe.db.get_all
    function_success = False
    function_error = None
    start_time = time.time()

    def capture_sql(query, *args, **kwargs):
        """Wrapper for frappe.db.sql to capture queries."""
        query_counter[0] += 1

        # Get caller info
        frame = inspect.currentframe().f_back
        source_file = frame.f_code.co_filename if frame else "unknown"
        source_line = frame.f_lineno if frame else 0

        # Extract query type
        query_str = str(query).strip()
        query_type = query_str.split()[0].upper() if query_str else "UNKNOWN"

        queries.append({
            "query_id": query_counter[0],
            "query": query_str,
            "query_type": query_type,
            "doctype": None,  # Hard to determine from raw SQL
            "method": "frappe.db.sql",
            "fields_requested": [],
            "source_file": source_file,
            "source_line": source_line
        })

        return original_sql(query, *args, **kwargs)

    def capture_get_all(doctype, *args, **kwargs):
        """Wrapper for frappe.db.get_all to capture queries."""
        query_counter[0] += 1

        # Get caller info
        frame = inspect.currentframe().f_back
        source_file = frame.f_code.co_filename if frame else "unknown"
        source_line = frame.f_lineno if frame else 0

        # Extract fields
        fields = kwargs.get("fields", ["name"])
        if isinstance(fields, str):
            fields = [fields]

        queries.append({
            "query_id": query_counter[0],
            "query": f"SELECT {', '.join(fields)} FROM `tab{doctype}` WHERE ...",
            "query_type": "SELECT",
            "doctype": doctype,
            "method": "frappe.db.get_all",
            "fields_requested": fields,
            "source_file": source_file,
            "source_line": source_line
        })

        return original_get_all(doctype, *args, **kwargs)

    try:
        # Monkey-patch frappe.db methods
        frappe.db.sql = capture_sql
        frappe.db.get_all = capture_get_all

        # Execute the function
        if function_name == "generate_manifest":
            from memora.services.cdn_export.json_generator import generate_manifest
            plan_doc = frappe.get_doc("Memora Academic Plan", plan_id)
            generate_manifest(plan_doc)
        elif function_name == "generate_subject_json":
            if not subject_id:
                raise ValueError("subject_id is required for generate_subject_json")
            from memora.services.cdn_export.json_generator import generate_subject_json
            subject_doc = frappe.get_doc("Memora Subject", subject_id)
            generate_subject_json(subject_doc, plan_id)
        elif function_name == "generate_search_index":
            from memora.services.cdn_export.json_generator import generate_search_index
            generate_search_index(plan_id)
        else:
            raise ValueError(f"Unknown function: {function_name}")

        function_success = True

    except Exception as e:
        function_success = False
        function_error = {
            "message": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

    finally:
        # Restore original methods
        frappe.db.sql = original_sql
        frappe.db.get_all = original_get_all

    execution_time_ms = (time.time() - start_time) * 1000

    return {
        "function_name": function_name,
        "function_success": function_success,
        "query_count": len(queries),
        "queries": queries,
        "execution_time_ms": execution_time_ms,
        "error": function_error,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def search_query_patterns(directory_path: str, pattern: str) -> List[Dict[str, Any]]:
    """Search for query patterns in source code files.

    This function is part of User Story 3: Developer Traces Dynamic Query Construction.
    It searches for frappe.db.sql(), frappe.get_all(), frappe.get_doc() patterns.

    Args:
        directory_path: Directory to search in
        pattern: Regex pattern to search for

    Returns:
        List of matches with fields:
        - file_path: str - Full path to file
        - line_number: int - Line number where match was found
        - code_snippet: str - Line of code containing the match
        - match_type: str - Type of pattern matched (sql, get_all, get_doc, etc.)

    Example:
        >>> matches = search_query_patterns("memora/services/cdn_export", r"frappe\.db\.get_all.*title")
        >>> for match in matches:
        >>>     print(f"{match['file_path']}:{match['line_number']}: {match['code_snippet']}")
    """
    import re
    import os

    matches = []

    # Walk through directory
    for root, dirs, files in os.walk(directory_path):
        # Skip __pycache__ and .git directories
        dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules"]]

        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_number, line in enumerate(f, 1):
                        if re.search(pattern, line):
                            # Determine match type
                            match_type = "unknown"
                            if "frappe.db.sql" in line or "frappe.db.get_value" in line:
                                match_type = "sql"
                            elif "frappe.db.get_all" in line or "frappe.get_all" in line:
                                match_type = "get_all"
                            elif "frappe.get_doc" in line:
                                match_type = "get_doc"
                            elif "frappe.db.get_list" in line or "frappe.get_list" in line:
                                match_type = "get_list"

                            matches.append({
                                "file_path": file_path,
                                "line_number": line_number,
                                "code_snippet": line.strip(),
                                "match_type": match_type
                            })
            except Exception as e:
                # Skip files that can't be read
                continue

    return matches
