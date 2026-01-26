# Feature Specification: JSON Generation Debug & Fix

**Feature Branch**: `006-json-generation-debug`
**Created**: 2026-01-26
**Status**: Draft
**Input**: User description: "Debug and fix JSON file generation failures in CDN export system - trace the problem causing 'Unknown column title in SELECT' error and fix it"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - System Administrator Diagnoses JSON Generation Failure (Priority: P1)

As a system administrator, when I update a subject that belongs to an academic plan, I need the system to generate the corresponding JSON files locally so that the content is available for export and student access. Currently, the rebuild process fails with a database error.

**Why this priority**: This is blocking all JSON generation functionality. Without fixing this, the entire CDN export system is non-functional.

**Independent Test**: Can be fully tested by running the diagnostic function on a test plan and verifying it returns the exact SQL query causing the error, along with the table and column information.

**Acceptance Scenarios**:

1. **Given** a test plan with one subject exists, **When** administrator runs diagnostic tool, **Then** system returns full error traceback showing the exact SQL query that's failing
2. **Given** diagnostic information is available, **When** administrator reviews the error, **Then** the specific table and column name causing "Unknown column 'title'" error is clearly identified
3. **Given** error logs exist in Error Log DocType, **When** administrator searches for recent errors, **Then** all CDN-related errors from the last 30 minutes are displayed with full SQL context

---

### User Story 2 - Developer Isolates Failing JSON Generation Component (Priority: P1)

As a developer debugging the system, I need to test each JSON generation function individually (manifest, search index, subject JSON) so I can identify exactly which component is throwing the database error.

**Why this priority**: Without isolating the specific failing component, we cannot efficiently fix the root cause. This is essential for targeted debugging.

**Independent Test**: Can be fully tested by running each generation function separately with test data and verifying which one throws the error vs which ones succeed.

**Acceptance Scenarios**:

1. **Given** a test plan and subject exist, **When** developer runs `generate_manifest()` alone, **Then** either manifest data is returned successfully OR specific error is thrown with traceback
2. **Given** a test plan exists, **When** developer runs `generate_search_index()` alone, **Then** either search index data is returned successfully OR specific error is thrown with traceback
3. **Given** a test subject and plan exist, **When** developer runs `generate_subject_json()` alone, **Then** either subject JSON is returned successfully OR specific error is thrown with traceback
4. **Given** test results from all three functions, **When** developer reviews outcomes, **Then** the specific function causing the "Unknown column 'title'" error is clearly identified

---

### User Story 3 - Developer Traces Dynamic Query Construction (Priority: P2)

As a developer, I need to identify all dynamic SQL queries and DocType field references in the JSON generation pipeline so I can find queries that might be referencing non-existent columns or using incorrect table names.

**Why this priority**: The error suggests a dynamic query is constructing SQL with a missing column. This investigation will reveal the root cause.

**Independent Test**: Can be fully tested by searching the codebase for all SQL query patterns and validating each against the actual database schema.

**Acceptance Scenarios**:

1. **Given** the JSON generation codebase, **When** developer searches for raw SQL queries, **Then** all instances of `frappe.db.sql()` selecting 'title' are identified
2. **Given** the JSON generation codebase, **When** developer searches for `frappe.get_all()` calls, **Then** all queries requesting 'title' field are identified with their target DocTypes
3. **Given** identified queries, **When** developer validates each against database schema, **Then** any query referencing 'title' on a DocType/table without that column is flagged
4. **Given** a list of child tables and dynamic queries, **When** developer checks for JOIN operations, **Then** any JOIN selecting 'title' from a table without that column is identified

---

### User Story 4 - System Automatically Generates JSON After Fix (Priority: P1)

As a content administrator, after the fix is deployed, when I create or update a subject that belongs to an academic plan, the system should automatically generate JSON files locally without errors so that the content is available for students.

**Why this priority**: This is the core functional requirement - JSON generation must work end-to-end after the fix.

**Independent Test**: Can be fully tested by updating a subject in a test plan and verifying JSON files are created in the expected local directory.

**Acceptance Scenarios**:

1. **Given** CDN is disabled and local_fallback_mode is enabled, **When** administrator updates a subject in an academic plan, **Then** JSON file is generated at `/sites/{site}/public/memora_content/subjects/{subject_id}.json`
2. **Given** a plan rebuild is triggered, **When** system processes the plan, **Then** rebuild returns `True` indicating success (not `False`)
3. **Given** JSON generation completes successfully, **When** administrator checks Error Log DocType, **Then** no "Unknown column 'title'" errors are present
4. **Given** successful JSON generation, **When** administrator verifies generated files, **Then** files contain valid JSON with subject data including tracks, units, topics, and lessons

---

### Edge Cases

- What happens when a DocType schema has 'title' as a label but a different 'fieldname' (e.g., 'name' or 'subject_title')?
- How does the system handle JOIN queries that select from child tables without a 'title' column?
- What if the error is in a subquery or Common Table Expression (CTE) that's not immediately visible?
- How does the system behave when dynamic queries iterate through child tables that have different schemas?
- What happens if database migrations are pending and schema is out of sync with DocType JSON definitions?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a diagnostic tool that captures and displays the exact SQL query causing the "Unknown column 'title'" error with full traceback
- **FR-002**: System MUST allow testing of `generate_manifest()`, `generate_search_index()`, and `generate_subject_json()` functions independently to isolate which component is failing
- **FR-003**: System MUST identify all SQL queries (raw SQL and ORM) that reference the 'title' column across all DocTypes involved in JSON generation
- **FR-004**: System MUST validate that all referenced columns exist in their target database tables before executing queries
- **FR-005**: System MUST generate JSON files locally when `local_fallback_mode = 1` regardless of CDN enabled status (this was already fixed in Solution 0)
- **FR-006**: System MUST complete plan rebuild process successfully (return `True`) when all data is valid and schema is correct
- **FR-007**: System MUST log detailed error information to Error Log DocType when JSON generation fails, including SQL query, table name, and column name
- **FR-008**: System MUST handle DocTypes where 'title' is a label but the actual fieldname is different (e.g., use `frappe.get_meta()` to get correct field mapping)
- **FR-009**: System MUST execute database migrations before JSON generation if schema is out of sync with DocType definitions
- **FR-010**: System MUST verify all child table schemas match expected structure before constructing JOIN queries

### Key Entities

- **Error Log Entry**: Captures failed JSON generation attempts with full SQL query, error message, traceback, and timestamp
- **Diagnostic Result**: Contains identified failing SQL query, target table/DocType, missing column name, and line number in code where query originates
- **JSON Generation Test Result**: For each generation function (manifest, search index, subject), captures success/failure status, output data or error, and execution time
- **Schema Validation Report**: Maps DocType field labels to actual database column names, identifies mismatches between DocType JSON and database schema

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can identify the exact failing SQL query and table within 5 minutes using the diagnostic tool
- **SC-002**: All three JSON generation functions (manifest, search index, subject JSON) can be tested independently and return clear success/failure results within 30 seconds each
- **SC-003**: 100% of plans with valid subjects generate JSON files successfully without "Unknown column 'title'" errors
- **SC-004**: Plan rebuild process completes successfully (returns `True`) for all test cases after fix is deployed
- **SC-005**: JSON files are generated in local directory within 10 seconds of subject update when `local_fallback_mode = 1`
- **SC-006**: Error logs contain zero "Unknown column 'title'" errors after fix deployment for 48 hours of normal operation
- **SC-007**: All SQL queries in JSON generation pipeline are validated against actual database schema before execution, preventing similar errors in future

## Assumptions

- The database schema for main tables (Memora Academic Plan, Memora Subject, Memora Track, Memora Unit, Memora Topic, Memora Lesson) all have 'title' columns as verified in troubleshooting log
- Child tables like Memora Plan Subject and Memora Lesson Stage have been verified to have correct columns
- The error is likely in a dynamic query, JOIN operation, or query involving a table/DocType not yet checked
- Frappe ORM may be constructing queries using field labels instead of actual database column names in some cases
- Database migrations are up to date (or will be verified as part of the fix)
- The Redis queue issue (returning size 0) is a separate problem and not blocking JSON generation with `local_fallback_mode = 1`

## Out of Scope

- Fixing the Redis queue size returning 0 issue (separate problem, documented but not blocking with local fallback mode enabled)
- Implementing CDN upload functionality (focus is on local JSON generation)
- Performance optimization of JSON generation (focus is on fixing the error, not speed)
- Refactoring the entire CDN export system architecture
- Adding new features to JSON generation (only fixing existing broken functionality)

## Dependencies

- Access to Error Log DocType with recent error entries
- Ability to run diagnostic code snippets in Frappe console
- Database access to verify schema and run DESCRIBE queries
- Understanding of Frappe ORM query construction and DocType meta information
- Test data: Plan ID `37q5969lug`, Subject ID `qunhaa99lf` (or similar test cases)

## Constraints

- Cannot modify database schema or add/remove columns from existing tables
- Must maintain backward compatibility with existing JSON file structure
- Must preserve all existing logging functionality added in previous solutions
- Cannot change DocType field definitions without understanding broader impact
- Must work with existing Frappe framework version (v14/v15)
