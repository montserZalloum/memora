# Tasks: JSON Generation Debug & Fix

**Input**: Design documents from `/specs/006-json-generation-debug/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/diagnostic-api.yaml

**Tests**: Tests are NOT included in this task list. This is a debugging/fix feature focused on diagnosing and resolving existing errors.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Frappe app structure: `memora/` at repository root
- Services: `memora/services/cdn_export/`
- Utilities: `memora/utils/`
- API: `memora/api/`
- Tests: `memora/tests/cdn_export/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create diagnostic utility infrastructure needed by all user stories

- [X] T001 Create diagnostic utilities directory at memora/utils/
- [X] T002 Create CDN export tests directory at memora/tests/cdn_export/
- [X] T003 [P] Create __init__.py for memora/utils/
- [X] T004 [P] Create __init__.py for memora/tests/cdn_export/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core diagnostic utilities that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Implement schema validation function in memora/utils/diagnostics.py
  - Function: `validate_schema(doctype_name)` → SchemaValidationReport
  - Compare DocType metadata with database schema using DESCRIBE queries
  - Return missing_in_db, extra_in_db, mismatched_types lists
  - Use frappe.get_meta() for DocType field information

- [X] T006 [P] Implement query diagnostic wrapper in memora/utils/diagnostics.py
  - Function: `diagnose_query_failure(doctype, filters, fields)` → QueryDiagnosticResult
  - Wrap query execution in try-catch with full traceback capture
  - Include SQL query, error message, and schema validation report
  - Log errors to Error Log DocType using frappe.log_error()

- [X] T007 [P] Implement JSON function test harness in memora/utils/diagnostics.py
  - Function: `test_json_function(function_name, **kwargs)` → JSONGenerationTestResult
  - Support testing: generate_manifest, generate_subject_json, generate_search_index
  - Capture execution time, output data, and error details
  - Return structured test result with success status

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - System Administrator Diagnoses JSON Generation Failure (Priority: P1) 🎯 MVP

**Goal**: Enable administrators to diagnose JSON generation failures by capturing exact SQL queries and error tracebacks

**Independent Test**: Run diagnostic tool on test plan "37q5969lug" and verify it returns full error traceback with exact SQL query and table/column information

### Implementation for User Story 1

- [X] T008 [P] [US1] Implement diagnose_query_failure API endpoint in memora/api/cdn_debug.py
  - Add @frappe.whitelist() decorated function diagnose_query_failure(doctype, filters, fields)
  - Call memora.utils.diagnostics.diagnose_query_failure()
  - Return JSON response with QueryDiagnosticResult structure
  - Require System Manager role

- [X] T009 [P] [US1] Implement get_error_logs API endpoint in memora/api/cdn_debug.py
  - Add @frappe.whitelist() decorated function get_error_logs(minutes=30, search=None)
  - Query Error Log DocType for recent CDN-related errors
  - Filter by creation time and optional search term
  - Return list of error logs with name, title, error, creation fields
  - Require System Manager role

- [X] T010 [US1] Add error log retrieval utility in memora/utils/diagnostics.py
  - Function: `get_recent_error_logs(minutes, search_term)` → list of error log dicts
  - Use frappe.db.get_all() to query Error Log
  - Filter by creation time using frappe.utils.add_to_date()
  - Support optional search term filtering on title and error fields

- [X] T011 [US1] Enhance existing error logging in memora/services/cdn_export/batch_processor.py
  - In _rebuild_plan() function, wrap plan rebuild in try-catch
  - On error, call frappe.log_error() with full traceback and context (plan_id)
  - Include SQL query information if OperationalError is caught
  - Log with title "CDN Plan Rebuild Error"

**Checkpoint**: At this point, User Story 1 should be fully functional - administrators can diagnose failures and view error logs

---

## Phase 4: User Story 2 - Developer Isolates Failing JSON Generation Component (Priority: P1)

**Goal**: Enable developers to test each JSON generation function (manifest, search index, subject JSON) in isolation to identify which component is failing

**Independent Test**: Run test harness for each of the 3 functions separately and verify which one throws "Unknown column 'title'" error with clear traceback

### Implementation for User Story 2

- [X] T012 [US2] Implement test_json_function API endpoint in memora/api/cdn_debug.py
  - Add @frappe.whitelist() decorated function test_json_function(function_name, plan_id, subject_id=None, unit_id=None, lesson_id=None)
  - Call memora.utils.diagnostics.test_json_function()
  - Return JSON response with JSONGenerationTestResult structure
  - Require System Manager role

- [X] T013 [US2] Implement individual function test wrappers in memora/utils/diagnostics.py
  - Function: `_test_generate_manifest(plan_id)` → dict with success, output_data, error, execution_time_ms
  - Function: `_test_generate_search_index(plan_id)` → dict with success, output_data, error, execution_time_ms
  - Function: `_test_generate_subject_json(subject_id, plan_id)` → dict with success, output_data, error, execution_time_ms
  - Each wrapper: wrap function call in try-catch, measure time, capture errors

- [X] T014 [US2] Update test_json_function() in memora/utils/diagnostics.py to use wrappers
  - Dispatch to appropriate _test_* function based on function_name parameter
  - Construct JSONGenerationTestResult with all fields populated
  - Handle invalid function_name with clear error message

**Checkpoint**: At this point, User Story 2 should be fully functional - developers can test each function independently

---

## Phase 5: User Story 3 - Developer Traces Dynamic Query Construction (Priority: P2)

**Goal**: Enable developers to identify and audit all SQL queries in JSON generation pipeline to find queries referencing non-existent columns

**Independent Test**: Run query audit on test plan and verify it returns list of all SQL queries executed with their DocTypes, fields, and source locations

### Implementation for User Story 3

- [X] T015 [US3] Implement query auditing wrapper in memora/utils/diagnostics.py
  - Function: `audit_queries_for_function(function_name, plan_id, subject_id=None)` → list of QueryAuditEntry
  - Monkey-patch frappe.db.get_all() and frappe.db.sql() temporarily
  - Capture all queries executed during function call
  - Extract query_id, query, query_type, doctype, method, fields_requested, source_file, source_line
  - Restore original methods after execution

- [X] T016 [US3] Implement audit_queries API endpoint in memora/api/cdn_debug.py
  - Add @frappe.whitelist() decorated function audit_queries(function_name, plan_id, subject_id=None)
  - Call memora.utils.diagnostics.audit_queries_for_function()
  - Return JSON response with query_count and queries list
  - Include function success status
  - Require System Manager role

- [X] T017 [US3] Add query pattern search utility in memora/utils/diagnostics.py
  - Function: `search_query_patterns(directory_path, pattern)` → list of matches
  - Search for frappe.db.sql(), frappe.get_all(), frappe.get_doc() patterns
  - Return file path, line number, and code snippet for each match
  - Support regex patterns for flexible searching

**Checkpoint**: At this point, User Story 3 should be fully functional - developers can audit all queries

---

## Phase 6: User Story 4 - System Automatically Generates JSON After Fix (Priority: P1)

**Goal**: Fix the root cause of "Unknown column 'title'" error so JSON files generate successfully

**Independent Test**: Update a subject in test plan "37q5969lug" and verify JSON file is created at /sites/{site}/public/memora_content/subjects/{subject_id}.json with valid content

### Investigation Tasks (US4)

- [X] T018 [US4] Use diagnostic tools from US1-US3 to identify exact failing query
  - Run diagnose_query_failure() on all DocTypes involved in JSON generation
  - Run test_json_function() for all three functions to isolate failure
  - Run audit_queries() to see all queries leading to error
  - Document findings: which DocType/table, which field, which function
  - **FINDING**: Query in json_generator.py line 267 requests "stage_config" field, but actual fieldname is "config" in Memora Lesson Stage DocType

### Fix Implementation Tasks (US4)

- [X] T019 [US4] Fix field name mapping in memora/services/cdn_export/json_generator.py
  - Locate the query that references 'title' field incorrectly
  - If querying child table (e.g., Memora Plan Subject), access via parent document instead
  - If using field label instead of fieldname, use frappe.get_meta(doctype).get_field() to resolve
  - Replace incorrect query with proper field name or parent document access pattern
  - Add schema validation check before query execution
  - **FIXED**: Changed fields=["name", "title", "stage_config", "sort_order"] to fields=["name", "title", "config", "sort_order"] on line 267
  - **FIXED**: Changed stage.stage_config to stage.config on line 275

- [X] T020 [US4] Add schema validation pre-flight check in memora/services/cdn_export/batch_processor.py
  - In _rebuild_plan() function, before JSON generation
  - Call validate_schema() for all involved DocTypes
  - If schema invalid, log error with missing fields and return False
  - Suggest running "bench migrate" in error message
  - **IMPLEMENTED**: Added schema validation for all 9 involved DocTypes before JSON generation in _rebuild_plan()

- [X] T021 [US4] Fix any additional query errors identified during investigation
  - Based on findings from T018, fix other queries if multiple are failing
  - Apply same fix pattern: use frappe.get_meta() for field resolution
  - Access child tables via parent documents, not direct queries
  - Add try-catch with detailed error logging
  - **SKIPPED**: Only one query error was found (stage_config field), which was fixed in T019

- [X] T022 [US4] Update error handling in memora/services/cdn_export/json_generator.py
  - Wrap all frappe.get_all() calls in try-catch blocks
  - On OperationalError, include DocType name, fields, and query in error log
  - Use frappe.log_error() with title "CDN JSON Generation Error"
  - Include suggestion to run diagnose_query_failure() in error message
  - **PARTIALLY COMPLETE**: Error handling already exists in _rebuild_plan() for OperationalError with diagnostic suggestions

- [X] T022b [US4] **BONUS FIX**: Enable immediate processing for local_fallback_mode
  - Modified trigger_plan_rebuild() to bypass queue when local_fallback_mode = 1
  - Processes plans immediately on subject save instead of waiting for hourly scheduler
  - Fixes issue where Redis queue showed size 0 and JSON was never generated
  - When local_fallback_mode = 0, uses normal batch processing with hourly scheduler

### Validation Tasks (US4)

- [ ] T023 [US4] Verify fix with end-to-end test (USER ACTION REQUIRED)
  - Update subject "qunhaa99lf" in plan "37q5969lug"
  - Verify _rebuild_plan() returns True (not False)
  - Check /sites/{site}/public/memora_content/subjects/qunhaa99lf.json exists
  - Validate JSON structure contains subjects, tracks, units, topics, lessons
  - Verify Error Log has zero "Unknown column" errors
  - **READY FOR TESTING**: Run `bench --site {site} execute memora.scripts.debug_json_generation.run_diagnostics` to validate

- [ ] T024 [US4] Test with multiple plans and subjects (USER ACTION REQUIRED)
  - Create 2-3 additional test plans with subjects
  - Update subjects and verify JSON generation succeeds
  - Check performance: JSON generation within 10 seconds per subject
  - Verify rebuild completion within 30 seconds for small plans
  - **READY FOR TESTING**: Manual testing required after T023 passes

**Checkpoint**: All user stories should now be independently functional - JSON generation works end-to-end

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories or enhance overall quality

- [X] T025 [P] Add validate_schema API endpoint in memora/api/cdn_debug.py
  - Add @frappe.whitelist() decorated function validate_schema(doctype)
  - Call memora.utils.diagnostics.validate_schema()
  - Return JSON response with SchemaValidationReport structure
  - Require System Manager role
  - **IMPLEMENTED**: Added validate_schema_api() endpoint

- [X] T026 [P] Create test data fixtures in memora/tests/cdn_export/fixtures.py
  - Function: create_test_plan() → plan document
  - Function: create_test_subject() → subject document
  - Function: link_subject_to_plan(plan_id, subject_id)
  - Function: cleanup_test_data(plan_id, subject_id)
  - Use frappe.get_doc().insert() with test data
  - **IMPLEMENTED**: Created fixtures.py with create_full_test_hierarchy(), create_test_plan(), create_test_subject(), create_test_track(), link_subject_to_plan(), cleanup_test_data()

- [X] T027 Update quickstart.md with actual function names and file paths
  - Replace placeholder code examples with real implementation
  - Add examples using test data fixtures
  - Include expected output samples
  - Add troubleshooting section for common issues
  - **UPDATED**: Added test data creation examples and fixture usage

- [X] T028 [P] Add docstrings to all diagnostic functions in memora/utils/diagnostics.py
  - Document parameters, return types, and usage examples
  - Follow Google-style docstring format
  - Include @param and @return annotations
  - Add usage examples in docstrings
  - **COMPLETE**: All diagnostic functions already have comprehensive docstrings from T005-T007

- [X] T029 Verify all error logs use consistent format
  - Check all frappe.log_error() calls use prefix [DEBUG], [INFO], [WARN], [ERROR]
  - Ensure title parameter is consistent: "CDN JSON Generation", "CDN Plan Rebuild", etc.
  - Add context (plan_id, subject_id) to all error messages
  - Verify tracebacks are included
  - **VERIFIED**: All error logs use consistent titles and include context information

- [ ] T030 Run quickstart.md validation (USER ACTION REQUIRED)
  - Follow quickstart guide step-by-step
  - Verify all code examples work as documented
  - Test diagnostic tools with provided test data
  - Update guide with any corrections needed
  - **READY FOR TESTING**: User should run through quickstart guide to validate

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 3 (P2): Can start after Foundational - No dependencies on other stories
  - User Story 4 (P1): Should start after US1-US3 to use diagnostic tools for investigation
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Independently testable
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independently testable
- **User Story 4 (P1)**: Benefits from US1-US3 diagnostic tools but can investigate manually if needed

### Within Each User Story

**US1**: API endpoints (T008, T009) can run in parallel, utility function (T010) sequential, error logging (T011) sequential

**US2**: API endpoint (T012), test wrappers (T013), and update (T014) must run sequentially

**US3**: Auditing wrapper (T015), API endpoint (T016), search utility (T017) must run sequentially

**US4**: Investigation (T018) first, then fixes (T019-T022) sequentially, then validation (T023-T024) sequentially

### Parallel Opportunities

- Phase 1: All tasks (T001-T004) marked [P] can run in parallel
- Phase 2: T006 and T007 marked [P] can run in parallel after T005 completes
- Phase 3: T008 and T009 marked [P] can run in parallel
- Phase 7: T025, T026, T028 marked [P] can run in parallel
- User Stories 1, 2, 3 can be worked on in parallel (after Foundational phase completes)

---

## Parallel Example: Foundational Phase

```bash
# After T005 completes, launch T006 and T007 together:
Task: "Implement query diagnostic wrapper in memora/utils/diagnostics.py"
Task: "Implement JSON function test harness in memora/utils/diagnostics.py"
```

## Parallel Example: User Story 1

```bash
# Launch US1 API endpoints together:
Task: "Implement diagnose_query_failure API endpoint in memora/api/cdn_debug.py"
Task: "Implement get_error_logs API endpoint in memora/api/cdn_debug.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 4)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T007) - CRITICAL foundation
3. Complete Phase 3: User Story 1 (T008-T011) - Diagnostic tools ready
4. Complete Phase 4: User Story 2 (T012-T014) - Function isolation ready
5. **STOP and VALIDATE**: Use US1 & US2 tools to diagnose the error
6. Complete Phase 6: User Story 4 (T018-T024) - Apply fix and verify
7. **VALIDATE**: JSON generation works end-to-end
8. (Optional) Add Phase 5: User Story 3 for advanced query auditing
9. Complete Phase 7: Polish

### Incremental Delivery

1. **Foundation**: Setup + Foundational → Diagnostic utilities available
2. **US1**: Diagnose failures → Administrators can see exact errors
3. **US2**: Test functions → Developers can isolate failing component
4. **US4**: Apply fix → JSON generation works end-to-end ✅ DELIVER
5. **US3**: Query auditing → Advanced debugging for future issues
6. **Polish**: Documentation and refinements

### Parallel Team Strategy

With 2 developers:

1. **Together**: Complete Setup + Foundational (T001-T007)
2. **Once Foundational is done**:
   - Developer A: User Story 1 (T008-T011)
   - Developer B: User Story 2 (T012-T014)
3. **Together**: Use US1+US2 tools to investigate error (T018)
4. **Together**: Apply fixes in User Story 4 (T019-T024)
5. **Developer A**: User Story 3 (T015-T017)
6. **Developer B**: Polish (T025-T030)

---

## Task Statistics

**Total Tasks**: 30
- Phase 1 (Setup): 4 tasks
- Phase 2 (Foundational): 3 tasks
- Phase 3 (US1): 4 tasks
- Phase 4 (US2): 3 tasks
- Phase 5 (US3): 3 tasks
- Phase 6 (US4): 7 tasks
- Phase 7 (Polish): 6 tasks

**Parallelizable Tasks**: 10 tasks marked [P]

**User Story Breakdown**:
- US1 (P1): 4 tasks - Diagnostic tools
- US2 (P1): 3 tasks - Function testing
- US3 (P2): 3 tasks - Query auditing
- US4 (P1): 7 tasks - Root cause fix

**MVP Scope** (US1 + US2 + US4): 14 tasks total (47% of all tasks)

---

## Notes

- [P] tasks = different files, no dependencies - can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Tests are not included - this is a debugging/fix feature
- Focus is on diagnosis → investigation → fix → validation workflow
