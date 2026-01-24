# Quickstart: Memora DocType Schema

**Feature**: 001-doctype-schema
**Date**: 2026-01-24

## Prerequisites

- Frappe bench installed and configured
- Memora app installed in bench: `bench get-app memora`
- ERPNext installed (for Item and Sales Invoice links)
- Site created: `bench new-site [site-name]`

## Quick Verification Steps

### 1. Run Migration

```bash
cd ~/frappe-bench
bench --site [site-name] migrate
```

**Expected Output**:
```
Migrating [site-name]
Updating DocTypes for memora: DocType operation: created - Memora Lesson Stage
Updating DocTypes for memora: DocType operation: created - Memora Plan Subject
...
Updating DocTypes for memora: DocType operation: created - Memora Subscription Transaction
Success: All 19 DocTypes created
```

### 2. Verify DocTypes Exist

```bash
bench --site [site-name] console
```

```python
import frappe

# List all Memora DocTypes
memora_doctypes = frappe.get_all("DocType", filters={"module": "memora"}, pluck="name")
print(f"Total Memora DocTypes: {len(memora_doctypes)}")
print(memora_doctypes)

# Expected: 19 DocTypes
assert len(memora_doctypes) == 19, f"Expected 19, got {len(memora_doctypes)}"
```

### 3. Verify Idempotency

Run migrate again - should complete without errors or changes:

```bash
bench --site [site-name] migrate
```

**Expected Output**:
```
Migrating [site-name]
Updating DocTypes for memora: DocType operation: unchanged - Memora Lesson Stage
Updating DocTypes for memora: DocType operation: unchanged - Memora Plan Subject
...
Success: Migration complete (no changes)
```

---

## Test Scenarios

### User Story 1: Administrator Deploys Memora App

**Scenario 1.1**: Fresh site migration
```bash
# Create fresh site
bench new-site test-memora.local --admin-password admin

# Install apps
bench --site test-memora.local install-app erpnext
bench --site test-memora.local install-app memora

# Verify all 19 DocTypes exist
bench --site test-memora.local console
>>> import frappe
>>> len(frappe.get_all("DocType", {"module": "memora"}))
19
```

**Scenario 1.2**: Repeated migration (idempotency)
```bash
bench --site test-memora.local migrate
bench --site test-memora.local migrate
bench --site test-memora.local migrate
# Should complete without errors each time
```

**Scenario 1.3**: Verify indexes exist
```bash
bench --site test-memora.local console
>>> import frappe
>>> # Check Memory State next_review index (critical)
>>> result = frappe.db.sql("""
...     SHOW INDEX FROM `tabMemora Memory State`
...     WHERE Column_name = 'next_review'
... """)
>>> assert len(result) > 0, "next_review index missing!"
>>> print("next_review index exists")
```

---

### User Story 2: Content Manager Creates Educational Hierarchy

**Scenario 2.1**: Create Subject via Desk
```
1. Log in to Frappe Desk as System Manager
2. Navigate to: Search > "Memora Subject"
3. Click "Add Memora Subject"
4. Fill:
   - Title: "Mathematics"
   - Color Code: "#3498db"
   - Is Published: checked
5. Click Save
6. Verify: Document saved with ID "Mathematics"
```

**Scenario 2.2**: Create Track linked to Subject
```
1. Navigate to: Search > "Memora Track"
2. Click "Add Memora Track"
3. Fill:
   - Title: "Algebra"
   - Parent Subject: select "Mathematics" (should show in dropdown)
   - Is Sold Separately: unchecked
   - Sort Order: 1
4. Click Save
5. Verify: Document saved with hash ID, Parent Subject link works
```

**Scenario 2.3**: Create full hierarchy
```python
# Console test
import frappe

# Create hierarchy
subject = frappe.get_doc({
    "doctype": "Memora Subject",
    "title": "Test Subject",
    "is_published": 1
}).insert()

track = frappe.get_doc({
    "doctype": "Memora Track",
    "title": "Test Track",
    "parent_subject": subject.name,
    "sort_order": 1
}).insert()

unit = frappe.get_doc({
    "doctype": "Memora Unit",
    "title": "Test Unit",
    "parent_track": track.name,
    "sort_order": 1
}).insert()

topic = frappe.get_doc({
    "doctype": "Memora Topic",
    "title": "Test Topic",
    "parent_unit": unit.name,
    "sort_order": 1
}).insert()

lesson = frappe.get_doc({
    "doctype": "Memora Lesson",
    "title": "Test Lesson",
    "parent_topic": topic.name,
    "sort_order": 1,
    "stages": [
        {"title": "Introduction", "type": "Text", "config": "{}"},
        {"title": "Video Explanation", "type": "Video", "config": '{"url": "https://example.com/video.mp4"}'},
        {"title": "Practice Question", "type": "Question", "config": '{"question_id": "q123"}'}
    ]
}).insert()

frappe.db.commit()

# Verify hierarchy
assert frappe.db.exists("Memora Subject", subject.name)
assert frappe.db.exists("Memora Track", track.name)
assert frappe.db.exists("Memora Unit", unit.name)
assert frappe.db.exists("Memora Topic", topic.name)
assert frappe.db.exists("Memora Lesson", lesson.name)

# Verify child table
assert len(lesson.stages) == 3
print("Full hierarchy created successfully!")
```

---

### User Story 3: Academic Planner Configures Plans

**Scenario 3.1**: Create Season and Stream
```python
import frappe

season = frappe.get_doc({
    "doctype": "Memora Season",
    "title": "Gen-2026",
    "is_published": 1,
    "start_date": "2026-01-01",
    "end_date": "2026-12-31"
}).insert()

stream = frappe.get_doc({
    "doctype": "Memora Stream",
    "title": "Scientific"
}).insert()

frappe.db.commit()
print(f"Season: {season.name}, Stream: {stream.name}")
```

**Scenario 3.2**: Create Academic Plan with Override
```python
import frappe

# Assumes Subject "Mathematics" and Track exist
plan = frappe.get_doc({
    "doctype": "Memora Academic Plan",
    "title": "Scientific 2026 Plan",
    "season": "Gen-2026",
    "stream": "Scientific",
    "subjects": [
        {"subject": "Mathematics", "sort_order": 1}
    ],
    "overrides": [
        {
            "target_doctype": "Memora Track",
            "target_name": "[track_name]",  # Replace with actual track
            "action": "Hide"
        }
    ]
}).insert()

frappe.db.commit()

# Verify Dynamic Link works
assert plan.overrides[0].target_doctype == "Memora Track"
print(f"Academic Plan created: {plan.name}")
```

---

### User Story 4: System Tracks Player Progress

**Scenario 4.1**: Create Player Profile
```python
import frappe

# Get a user
user = frappe.get_all("User", filters={"user_type": "System User"}, limit=1)[0].name

profile = frappe.get_doc({
    "doctype": "Memora Player Profile",
    "user": user,
    "display_name": "Test Player",
    "devices": [
        {"device_id": "device-001", "device_name": "iPhone", "is_trusted": 1}
    ]
}).insert()

wallet = frappe.get_doc({
    "doctype": "Memora Player Wallet",
    "player": profile.name,
    "total_xp": 0,
    "current_streak": 0
}).insert()

frappe.db.commit()
print(f"Player Profile: {profile.name}, Wallet: {wallet.name}")
```

**Scenario 4.2**: Create Memory State (FSRS)
```python
import frappe
from datetime import datetime, timedelta

memory_state = frappe.get_doc({
    "doctype": "Memora Memory State",
    "player": "[player_profile_name]",  # Replace
    "question_id": "q-uuid-12345",
    "stability": 1.0,
    "difficulty": 0.3,
    "next_review": datetime.now() + timedelta(days=1),
    "state": "New"
}).insert()

frappe.db.commit()

# Verify index works - query due reviews
due = frappe.get_all(
    "Memora Memory State",
    filters={"next_review": ["<=", datetime.now()]},
    limit=100
)
print(f"Due reviews: {len(due)}")
```

---

### User Story 5: System Logs Interactions

**Scenario 5.1**: Create Interaction Log
```python
import frappe

log = frappe.get_doc({
    "doctype": "Memora Interaction Log",
    "player": "[player_profile_name]",  # Replace
    "academic_plan": "[plan_name]",  # Replace
    "question_id": "q-uuid-12345",
    "student_answer": "42",
    "correct_answer": "42",
    "is_correct": 1,
    "time_taken": 15
}).insert()

frappe.db.commit()
print(f"Interaction logged: {log.name}")
```

**Scenario 5.2**: Create Subscription Transaction
```python
import frappe

tx = frappe.get_doc({
    "doctype": "Memora Subscription Transaction",
    "player": "[player_profile_name]",  # Replace
    "transaction_type": "Purchase",
    "payment_method": "Payment Gateway",
    "status": "Pending Approval",
    "amount": 100.00
}).insert()

frappe.db.commit()

# Verify naming series
assert tx.name.startswith("SUB-TX-2026-")
print(f"Transaction: {tx.name}")
```

---

## Cleanup

```bash
# Remove test site
bench drop-site test-memora.local --force
```

---

## Troubleshooting

### Migration fails with "DocType already exists"
- This shouldn't happen with idempotent creation
- Check: `frappe.db.exists("DocType", "Memora Subject")` returns True
- Solution: Migration logic should skip existing DocTypes

### Index not created
- Check MariaDB logs
- Verify field has `search_index: 1` in definition
- Run: `bench --site [site] console` then `frappe.db.sql("SHOW INDEX FROM \`tabMemora Memory State\`")`

### Child table not showing
- Verify child DocType has `istable: 1`
- Verify parent has `fieldtype: "Table"` with correct `options`
- Clear cache: `bench --site [site] clear-cache`

### Dynamic Link not showing navigation arrow
- Verify `target_doctype` is `fieldtype: "Link"` to `DocType` (not Select)
- Verify `target_name` is `fieldtype: "Dynamic Link"` with `options: "target_doctype"`
