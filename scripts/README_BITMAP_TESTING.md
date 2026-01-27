# Bitmap Generation Testing Scripts

These scripts help debug why `{subject.name}_b.json` has empty `mappings: {}`.

## Scripts

### 1. create_test_bitmap_data.py
Creates a complete test hierarchy in your development database:

```
TEST-PLAN-BITMAP-001 (Plan)
└── TEST-SUBJECT-MATH-001 (Subject: Mathematics)
    └── TEST-TRACK-ALGEBRA-001 (Track: Algebra Basics)
        └── TEST-UNIT-EQUATIONS-001 (Unit: Linear Equations)
            └── TEST-TOPIC-SIMPLE-001 (Topic: Simple Equations)
                ├── TEST-LESSON-LESSON001-001 (Lesson 1, submitted)
                └── TEST-LESSON-LESSON002-001 (Lesson 2, submitted)
```

**Usage:**
```bash
bench --site [site-name] run python scripts/create_test_bitmap_data.py
```

**What it does:**
- Creates 1 Academic Plan
- Creates 1 Subject
- Links Subject to Plan
- Creates 1 Track
- Creates 1 Unit
- Creates 1 Topic
- Creates 2 Lessons (both submitted with `docstatus=1`)

**Verify data:**
```bash
bench --site [site-name] run python scripts/create_test_bitmap_data.py --verify TEST-PLAN-BITMAP-001
```

### 2. test_bitmap_rebuild.py
Rebuilds a plan and checks if bitmap file is correctly generated.

**Usage:**
```bash
bench --site [site-name] run python scripts/test_bitmap_rebuild.py TEST-PLAN-BITMAP-001
```

**What it does:**
1. Checks if plan exists
2. Gets all plan subjects
3. Shows bitmap file state **before** rebuild
4. Triggers `plan.rebuild_plan()`
5. Shows bitmap file state **after** rebuild
6. Runs database queries to debug hierarchy
7. Checks if lessons are submitted (docstatus=1)

## Expected Output

### Success (mappings populated):
```
[INFO] Generated plans/TEST-PLAN-BITMAP-001/TEST-SUBJECT-MATH-001_b.json
[INFO] Generated bitmap JSON for TEST-SUBJECT-MATH-001 with 2 lessons
```

Bitmap file contents:
```json
{
  "subject_id": "TEST-SUBJECT-MATH-001",
  "version": 1706270400,
  "generated_at": "2026-01-26T10:00:00",
  "total_lessons": 2,
  "mappings": {
    "TEST-LESSON-LESSON001-001": {
      "bit_index": 0,
      "topic_id": "TEST-TOPIC-SIMPLE-001"
    },
    "TEST-LESSON-LESSON002-001": {
      "bit_index": 1,
      "topic_id": "TEST-TOPIC-SIMPLE-001"
    }
  }
}
```

### Problem (mappings empty):
```
[INFO] Generated plans/TEST-PLAN-BITMAP-001/TEST-SUBJECT-MATH-001_b.json
[INFO] Generated bitmap JSON for TEST-SUBJECT-MATH-001 with 0 lessons
```

Bitmap file contents:
```json
{
  "subject_id": "TEST-SUBJECT-MATH-001",
  "version": 1706270400,
  "generated_at": "2026-01-26T10:00:00",
  "total_lessons": 0,
  "mappings": {}
}
```

## Debugging Checklist

If mappings are empty, check:

### 1. Lessons not submitted
**Symptom:** Lessons exist in database but `mappings: {}`

**Fix:**
```sql
-- Check lesson docstatus
SELECT name, lesson_name, docstatus 
FROM `tabMemora Lesson`
WHERE parent_topic = 'TEST-TOPIC-SIMPLE-001';

-- Submit lessons
UPDATE `tabMemora Lesson` 
SET docstatus = 1 
WHERE docstatus = 0;
```

### 2. Broken hierarchy links
**Symptom:** One of the levels (tracks, units, topics) returns empty

**Check in Frappe Desk:**
1. Open Subject → Check "Tracks" child table
2. Open Track → Check "Units" child table
3. Open Unit → Check "Topics" child table
4. Open Topic → Check "Lessons" child table

**Verify in Database:**
```sql
-- Check subject has tracks
SELECT COUNT(*) FROM `tabMemora Track` 
WHERE parent_subject = 'TEST-SUBJECT-MATH-001';

-- Check track has units
SELECT COUNT(*) FROM `tabMemora Unit` 
WHERE parent_track = 'TEST-TRACK-ALGEBRA-001';

-- Check unit has topics
SELECT COUNT(*) FROM `tabMemora Topic` 
WHERE parent_unit = 'TEST-UNIT-EQUATIONS-001';

-- Check topic has lessons
SELECT COUNT(*) FROM `tabMemora Lesson` 
WHERE parent_topic = 'TEST-TOPIC-SIMPLE-001';
```

### 3. Incorrect field names
**Symptom:** Queries return empty because field names don't match

**Expected field structure:**
- `Memora Track.parent_subject` → Subject name
- `Memora Unit.parent_track` → Track name
- `Memora Topic.parent_unit` → Unit name
- `Memora Lesson.parent_topic` → Topic name

## Quick Test

Run these commands in order:

```bash
# 1. Create test data
bench --site [site-name] run python scripts/create_test_bitmap_data.py

# 2. Verify data was created
bench --site [site-name] run python scripts/create_test_bitmap_data.py --verify TEST-PLAN-BITMAP-001

# 3. Rebuild and check bitmap
bench --site [site-name] run python scripts/test_bitmap_rebuild.py TEST-PLAN-BITMAP-001

# 4. Check the actual file
cat sites/[site-name]/public/memora_content/plans/TEST-PLAN-BITMAP-001/TEST-SUBJECT-MATH-001_b.json
```

## Expected Result

If everything works:
- Bitmap file should have `total_lessons: 2`
- `mappings` should have 2 lessons with `bit_index: 0` and `bit_index: 1`
- Both lessons should have `topic_id: TEST-TOPIC-SIMPLE-001`

If not working:
- Check Frappe Error Log for `[BITMAP DEBUG]` messages
- Check database query results in script output
- Verify hierarchy links in Frappe Desk
