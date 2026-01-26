# Implementation Plan: JSON Generation Debug & Fix

**Branch**: `006-json-generation-debug` | **Date**: 2026-01-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-json-generation-debug/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Debug and fix the "Unknown column 'title' in SELECT" database error that prevents JSON file generation in the CDN export system. The primary requirement is to identify the exact SQL query causing the error, isolate which JSON generation component is failing, trace dynamic query construction patterns, and implement a fix that enables successful local JSON file generation when `local_fallback_mode = 1`.

Technical approach: Implement diagnostic tools to capture full SQL tracebacks, create isolated test harnesses for each JSON generation function (manifest, search index, subject JSON), audit all database queries for schema validation, and apply fixes to ensure proper field name mapping using Frappe ORM metadata.

## Technical Context

**Language/Version**: Python 3.10+ (Frappe Framework v14/v15)
**Primary Dependencies**: Frappe Framework, MariaDB (database), Redis (cache/queue), frappe.db ORM
**Storage**: MariaDB for DocTypes (Memora Academic Plan, Subject, Track, Unit, Topic, Lesson), Local filesystem for JSON files (`/sites/{site}/public/memora_content/`)
**Testing**: Frappe's built-in testing framework (frappe.test_runner), manual console testing via `bench console`
**Target Platform**: Linux server (Frappe deployment)
**Project Type**: Single backend service (Frappe app)
**Performance Goals**: JSON generation within 10 seconds per subject, rebuild completion within 30 seconds for small plans
**Constraints**: Cannot modify database schema, must preserve backward compatibility with existing JSON structure, must work with Frappe v14/v15
**Scale/Scope**: Small debugging feature - affects 3 JSON generation functions, ~10 files in `memora/services/cdn_export/`, debugging tools for 1 test plan with 1 subject

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: N/A - No project constitution exists yet

Since no constitution file exists at `.specify/memory/constitution.md` (file contains only template placeholders), this feature will establish baseline practices for debugging and diagnostics in the Memora project. No constitutional gates to validate.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
memora/
├── services/
│   └── cdn_export/                    # Existing CDN export service (TO BE DEBUGGED)
│       ├── json_generator.py          # FAILING: Contains generate_manifest(), generate_subject_json()
│       ├── batch_processor.py         # FAILING: Contains _rebuild_plan()
│       ├── access_calculator.py       # Helper: Access level calculation
│       ├── dependency_resolver.py     # Helper: Plan dependency resolution
│       ├── change_tracker.py          # Helper: Queue management
│       └── url_resolver.py            # Helper: URL generation
│
├── api/
│   └── cdn_debug.py                   # Existing debug endpoints (TO BE ENHANCED)
│
└── memora/
    └── doctype/                        # DocType definitions
        ├── memora_academic_plan/
        ├── memora_subject/
        ├── memora_track/
        ├── memora_unit/
        ├── memora_topic/
        └── memora_lesson/

# New diagnostic/debugging utilities (TO BE CREATED)
memora/
├── utils/
│   └── diagnostics.py                 # NEW: Diagnostic tools for schema validation
│
└── tests/
    └── cdn_export/                    # NEW: Test harnesses for JSON generation
        ├── test_json_generator.py     # NEW: Isolated function tests
        └── test_schema_validation.py  # NEW: Schema validation tests
```

**Structure Decision**: Frappe app structure (single backend). This is a debugging/fix feature that:
1. Enhances existing `memora/services/cdn_export/` modules
2. Adds new diagnostic utilities in `memora/utils/diagnostics.py`
3. Creates test harnesses in `memora/tests/cdn_export/`
4. Works within Frappe's app structure conventions

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No project constitution exists, therefore no violations to track. This feature establishes baseline debugging practices.

---

## Phase Completion Status

### Phase 0: Research ✅ COMPLETE

**Artifacts Generated**:
- `research.md` - All technical unknowns resolved

**Key Decisions**:
1. Use `frappe.get_meta()` for field name resolution
2. Audit all query patterns for proper field usage
3. Implement diagnostic wrappers with `frappe.log_error()`
4. Pre-flight schema validation using `DESCRIBE` queries
5. Frappe test framework with minimal fixtures

**No NEEDS CLARIFICATION remaining** - All research questions answered.

---

### Phase 1: Design & Contracts ✅ COMPLETE

**Artifacts Generated**:
- `data-model.md` - 4 diagnostic data structures defined
- `contracts/diagnostic-api.yaml` - OpenAPI 3.0 specification with 5 endpoints
- `quickstart.md` - Developer debugging guide
- `CLAUDE.md` - Updated with new technologies

**Design Decisions**:
1. **Data Structures**: SQL Query Diagnostic Result, Schema Validation Report, JSON Generation Test Result, Query Audit Entry
2. **API Endpoints**: 
   - `POST /diagnose_query_failure` - Diagnose SQL errors
   - `POST /test_json_function` - Test functions in isolation
   - `POST /validate_schema` - Validate DocType schemas
   - `POST /audit_queries` - Audit all queries in function
   - `GET /get_error_logs` - Retrieve recent CDN errors
3. **Test Strategy**: Isolated unit tests with minimal fixtures, Frappe test framework
4. **Error Handling**: Full traceback logging to Error Log DocType for UI visibility

**Constitution Re-check**: N/A (no constitution exists)

---

## Next Steps

This plan is now complete. The next command is:

```bash
/speckit.tasks
```

This will generate `tasks.md` with actionable, dependency-ordered implementation tasks.

---

## Plan Metadata

**Created**: 2026-01-26
**Last Updated**: 2026-01-26
**Status**: Complete - Ready for task generation
**Approver**: N/A (auto-approved, no constitution gates)
