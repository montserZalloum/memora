# Research: Memora DocType Schema Creation

**Feature**: 001-doctype-schema
**Date**: 2026-01-24
**Status**: Complete

## Research Summary

This document consolidates research findings for implementing 19 DocTypes via Frappe's `after_migrate` hook with idempotent creation, atomic rollback, and proper indexing.

---

## Decision 1: DocType Creation Approach

**Decision**: Programmatic creation via Python (not JSON fixtures)

**Rationale**:
- Enables idempotent updates (create or skip if exists)
- Supports atomic rollback via `@frappe.db.atomic` decorator
- Allows structured logging of each operation
- Better error handling and debugging
- JSON fixtures are static and don't support conditional logic

**Alternatives Considered**:
- JSON fixtures in `doctype/` folders - Rejected: No idempotency, no atomic rollback
- Bench command with fixtures - Rejected: Requires manual intervention, not automatic on migrate

---

## Decision 2: after_migrate Hook Pattern

**Decision**: Register migration function in `hooks.py`, implement in `services/schema/migration_runner.py`

**Rationale**:
- Separation of concerns (hooks.py stays clean)
- Schema logic grouped in `services/schema/` for maintainability
- Easy to test migration logic independently

**Implementation**:
```python
# hooks.py
after_migrate = [
    "memora.services.schema.migration_runner.run_migration",
]
```

**Alternatives Considered**:
- Inline implementation in hooks.py - Rejected: Poor maintainability for 19 DocTypes
- Using patches instead of after_migrate - Rejected: Patches run once, after_migrate runs every migration

---

## Decision 3: Idempotency Pattern

**Decision**: Check existence with `frappe.db.exists()` before creation, use `ignore_if_duplicate=True`

**Rationale**:
- Running `bench migrate` multiple times produces identical results
- Existing DocTypes are skipped silently (logged for observability)
- No errors on repeated migrations

**Implementation**:
```python
def create_doctype(name: str, definition: dict) -> bool:
    if frappe.db.exists("DocType", name):
        frappe.logger().info(f"DocType '{name}' already exists - unchanged")
        return False

    doc = frappe.get_doc({"doctype": "DocType", **definition})
    doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
    frappe.logger().info(f"DocType '{name}' created")
    return True
```

**Alternatives Considered**:
- Delete and recreate - Rejected: Would lose data
- Update existing fields - Considered for future enhancement if schema evolution is needed

---

## Decision 4: Atomic Rollback Strategy

**Decision**: Use `@frappe.db.atomic` decorator for all-or-nothing transaction

**Rationale**:
- If any DocType creation fails, entire migration is rolled back
- No partial schema state that could cause errors
- Aligns with FR-004a (atomic rollback requirement)

**Implementation**:
```python
@frappe.db.atomic
def create_all_doctypes():
    """Create all DocTypes in atomic transaction"""
    for definition in DOCTYPE_DEFINITIONS:
        create_doctype(definition["name"], definition)
```

**Alternatives Considered**:
- Savepoints per DocType - Rejected: Spec requires complete rollback on any failure
- Manual try/catch with rollback - Rejected: `@frappe.db.atomic` is cleaner and more reliable

---

## Decision 5: Child Table Creation Order

**Decision**: Create child table DocTypes BEFORE parent DocTypes that reference them

**Rationale**:
- Frappe validates `Table` field `options` reference exists
- Creation order: Child tables (istable=1) → Parent DocTypes
- 5 child tables must be created first: Lesson Stage, Plan Subject, Plan Override, Grant Component, Player Device

**Implementation Order**:
1. Memora Lesson Stage (child)
2. Memora Plan Subject (child)
3. Memora Plan Override (child)
4. Memora Grant Component (child)
5. Memora Player Device (child)
6. All parent DocTypes (in dependency order)

---

## Decision 6: Index Strategy

**Decision**: Use `search_index: 1` field property for all indexed fields

**Rationale**:
- Frappe automatically creates database indexes on `search_index: 1` fields
- Works on Link, Date, Datetime, Int, Data, Select fields
- Cannot index Text/Long Text/JSON fields (use them for config only)

**Indexed Fields (from spec)**:
| DocType | Field | Type | Rationale |
|---------|-------|------|-----------|
| Memora Track | parent_subject | Link | Content hierarchy queries |
| Memora Unit | parent_track | Link | Content hierarchy queries |
| Memora Topic | parent_unit | Link | Content hierarchy queries |
| Memora Lesson | parent_topic | Link | Content hierarchy queries |
| Memora Academic Plan | season | Link | Plan filtering |
| Memora Academic Plan | stream | Link | Plan filtering |
| Memora Player Profile | user | Link | User lookup (unique) |
| Memora Player Profile | current_plan | Link | Plan lookup |
| Memora Player Wallet | player | Link | Player lookup (unique) |
| Memora Interaction Log | player | Link | Player queries |
| Memora Interaction Log | academic_plan | Link | Plan queries |
| Memora Interaction Log | question_id | Data | Question lookup |
| Memora Memory State | player | Link | Player queries |
| Memora Memory State | question_id | Data | Question lookup |
| Memora Memory State | next_review | Datetime | **Critical**: FSRS scheduling |
| Memora Product Grant | item_code | Link | Item lookup |
| Memora Product Grant | academic_plan | Link | Plan lookup |
| Memora Subscription Transaction | player | Link | Player lookup |
| Memora Subscription Transaction | related_grant | Link | Grant lookup |
| All content DocTypes | sort_order | Int | Ordering queries |

---

## Decision 7: Dynamic Link Configuration

**Decision**: Use Link to DocType + Dynamic Link pattern (not Select + Dynamic Link)

**Rationale**:
- Link to DocType field shows navigation arrow icon in Frappe Desk
- Select field would work functionally but loses Desk UI navigation
- Filter via `link_filters` in field definition

**Implementation**:
```python
{
    "fieldname": "target_doctype",
    "fieldtype": "Link",
    "label": "Target DocType",
    "options": "DocType",
    "reqd": 1,
    # Filter to only show relevant DocTypes
},
{
    "fieldname": "target_name",
    "fieldtype": "Dynamic Link",
    "label": "Target Name",
    "options": "target_doctype",  # References the Link field above
    "reqd": 1,
}
```

**Filter Implementation**: Add client script to restrict DocType options to valid targets (Track, Unit, Topic, Lesson for Plan Override).

---

## Decision 8: Autoname Strategy

**Decision**: Follow spec naming table exactly

**Rationale**:
- Human-readable IDs for lookup tables (Subject, Season, Stream)
- Sequential IDs for transactions (Subscription Transaction)
- Hash-based IDs for data tables (allows duplicate titles)

**Implementation**:
| DocType | Autoname | Field Definition |
|---------|----------|------------------|
| Memora Subject | `field:title` | `autoname: "field:title"` |
| Memora Season | `field:title` | `autoname: "field:title"` |
| Memora Stream | `field:title` | `autoname: "field:title"` |
| Memora Subscription Transaction | `naming_series:` | `autoname: "naming_series:"` with naming_series field |
| All others | Default (hash) | No autoname property (Frappe generates hash) |

---

## Decision 9: Standard Mixin Fields

**Decision**: Define mixin fields once, apply to 5 content DocTypes

**Rationale**:
- DRY principle for is_published, is_free_preview, sort_order, image, description
- Consistent behavior across Subject, Track, Unit, Topic, Lesson
- Easy to maintain and extend

**Implementation**:
```python
CONTENT_MIXIN_FIELDS = [
    {"fieldname": "is_published", "fieldtype": "Check", "label": "Is Published", "default": 0},
    {"fieldname": "is_free_preview", "fieldtype": "Check", "label": "Is Free Preview", "default": 0},
    {"fieldname": "sort_order", "fieldtype": "Int", "label": "Sort Order", "default": 0, "search_index": 1},
    {"fieldname": "image", "fieldtype": "Attach Image", "label": "Image"},
    {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"},
]
```

---

## Decision 10: Structured Logging

**Decision**: Use `frappe.logger()` with structured messages for each operation

**Rationale**:
- FR-004b requires structured logs with timestamps and operation type
- Frappe logger includes timestamps automatically
- Log operation type: created/updated/unchanged

**Implementation**:
```python
import frappe

def log_operation(doctype_name: str, operation: str):
    """Log DocType operation with structured message"""
    frappe.logger("memora.schema").info(
        f"DocType operation: {operation}",
        title=doctype_name,
        data={"doctype": doctype_name, "operation": operation}
    )
```

---

## Technical Notes

### Frappe Field Types Reference

| Spec Field Type | Frappe fieldtype | Notes |
|-----------------|------------------|-------|
| Check | Check | Boolean (0/1) |
| Int | Int | Integer |
| Float | Float | Decimal |
| Data | Data | Short text (varchar) |
| Small Text | Small Text | Medium text |
| Text | Text | Long text |
| JSON | JSON | Stored as longtext, validated JSON |
| Date | Date | Date only |
| Datetime | Datetime | Date + time |
| Currency | Currency | Decimal with currency formatting |
| Select | Select | Options separated by \n |
| Link | Link | Foreign key to another DocType |
| Dynamic Link | Dynamic Link | Polymorphic foreign key |
| Table | Table | Child table reference |
| Attach Image | Attach Image | File attachment (image only) |

### Permission Defaults

All DocTypes require permissions to be created:
```python
"permissions": [
    {
        "role": "System Manager",
        "read": 1, "write": 1, "create": 1, "delete": 1,
        "submit": 0, "cancel": 0, "amend": 0,
    }
]
```

### Module Registration

All DocTypes use module `memora` (matches app name and modules.txt).

---

## References

- Frappe Framework Migration Documentation: https://docs.frappe.io/framework/v15/user/en/database-migrations
- Frappe Database API: https://docs.frappe.io/framework/v15/user/en/api/database
- Frappe DocType class: https://github.com/frappe/frappe/blob/develop/frappe/core/doctype/doctype/doctype.py
- Constitution: `.specify/memory/constitution.md`
