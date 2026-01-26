# Data Model: Progress Engine Bitset

**Feature**: 005-progress-engine-bitset
**Date**: 2026-01-25

## Schema Changes

### 1. Memora Subject (Modification)

Add field for bit index counter.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `next_bit_index` | Int | 0 | Counter for assigning unique bit indices to lessons. Incremented when a new lesson is created. Never decremented. |

**Frappe JSON Addition**:
```json
{
  "fieldname": "next_bit_index",
  "fieldtype": "Int",
  "default": "0",
  "label": "Next Bit Index",
  "read_only": 1,
  "hidden": 1,
  "description": "Internal counter for lesson bit indices"
}
```

### 2. Memora Lesson (Modification)

Add immutable bit index field.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `bit_index` | Int | -1 | Unique identifier within the subject for bitmap tracking. Assigned on creation, never changes. -1 indicates unassigned. |

**Frappe JSON Addition**:
```json
{
  "fieldname": "bit_index",
  "fieldtype": "Int",
  "default": "-1",
  "label": "Bit Index",
  "read_only": 1,
  "hidden": 1,
  "description": "Immutable bitmap position within subject"
}
```

**Controller Logic** (memora_lesson.py):
```python
def before_insert(self):
    """Assign bit_index from subject's next_bit_index counter."""
    if self.bit_index == -1:
        topic = frappe.get_doc("Memora Topic", self.parent_topic)
        unit = frappe.get_doc("Memora Unit", topic.parent_unit)
        track = frappe.get_doc("Memora Track", unit.parent_track)
        subject = frappe.get_doc("Memora Subject", track.parent_subject)

        self.bit_index = subject.next_bit_index
        subject.next_bit_index += 1
        subject.save(ignore_permissions=True)
```

### 3. Memora Topic (Modification)

Add `is_linear` field (missing from current schema).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `is_linear` | Check | 1 | If true, lessons within this topic must be completed sequentially. |

**Frappe JSON Addition**:
```json
{
  "fieldname": "is_linear",
  "fieldtype": "Check",
  "default": "1",
  "label": "Is Linear",
  "description": "Sequential unlock rule for child lessons"
}
```

### 4. Memora Structure Progress (Modification)

Rename and add fields for bitmap and best hearts storage.

| Field | Type | Description |
|-------|------|-------------|
| `passed_lessons_bitset` | Long Text | Base64-encoded bitmap of passed lessons. Replaces `passed_lessons_data`. |
| `best_hearts_data` | JSON | Map of lesson_id → best hearts achieved. For record-breaking bonus calculation. |

**Frappe JSON Modifications**:
```json
{
  "fieldname": "passed_lessons_bitset",
  "fieldtype": "Long Text",
  "label": "Passed Lessons Bitset",
  "description": "Base64-encoded bitmap of completed lessons"
},
{
  "fieldname": "best_hearts_data",
  "fieldtype": "JSON",
  "label": "Best Hearts Data",
  "description": "Per-lesson best hearts for XP bonus calculation"
}
```

**Note**: Keep `passed_lessons_data` during migration, then deprecate.

## Redis Key Schema

### Bitmap Storage

| Key Pattern | Value Type | TTL | Description |
|-------------|------------|-----|-------------|
| `user_prog:{player_id}:{subject_id}` | bytes | None | Lesson completion bitmap |
| `best_hearts:{player_id}:{subject_id}` | JSON string | None | Best hearts per lesson |
| `progress_dirty_keys` | Set | None | Keys pending MariaDB sync |

### Example

```
Key: user_prog:PLAYER-001:SUBJ-001
Value: b'\x07'  # Binary: 00000111 = lessons 0, 1, 2 passed

Key: best_hearts:PLAYER-001:SUBJ-001
Value: '{"LESSON-001": 5, "LESSON-002": 3, "LESSON-003": 4}'

Key: progress_dirty_keys
Value: {"user_prog:PLAYER-001:SUBJ-001", "user_prog:PLAYER-002:SUBJ-001"}
```

## JSON Structure Schema

Enhanced subject JSON with progress-related fields.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SubjectStructure",
  "type": "object",
  "required": ["id", "title", "is_linear", "tracks"],
  "properties": {
    "id": {"type": "string"},
    "title": {"type": "string"},
    "is_linear": {"type": "boolean", "default": true},
    "tracks": {
      "type": "array",
      "items": {"$ref": "#/definitions/Track"}
    }
  },
  "definitions": {
    "Track": {
      "type": "object",
      "required": ["id", "title", "is_linear", "sort_order", "units"],
      "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "is_linear": {"type": "boolean", "default": true},
        "sort_order": {"type": "integer"},
        "units": {
          "type": "array",
          "items": {"$ref": "#/definitions/Unit"}
        }
      }
    },
    "Unit": {
      "type": "object",
      "required": ["id", "title", "is_linear", "sort_order", "topics"],
      "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "is_linear": {"type": "boolean", "default": true},
        "sort_order": {"type": "integer"},
        "topics": {
          "type": "array",
          "items": {"$ref": "#/definitions/Topic"}
        }
      }
    },
    "Topic": {
      "type": "object",
      "required": ["id", "title", "is_linear", "sort_order", "lessons"],
      "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "is_linear": {"type": "boolean", "default": true},
        "sort_order": {"type": "integer"},
        "lessons": {
          "type": "array",
          "items": {"$ref": "#/definitions/Lesson"}
        }
      }
    },
    "Lesson": {
      "type": "object",
      "required": ["id", "title", "bit_index", "sort_order"],
      "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "bit_index": {"type": "integer", "minimum": 0},
        "sort_order": {"type": "integer"}
      }
    }
  }
}
```

## Entity Relationships

```
┌─────────────────────┐
│   Memora Subject    │
│  ─────────────────  │
│  next_bit_index     │◄──────────────┐
│  is_linear          │               │
└─────────┬───────────┘               │
          │ 1:N                       │
          ▼                           │
┌─────────────────────┐               │
│    Memora Track     │               │
│  ─────────────────  │               │
│  is_linear          │               │
│  parent_subject ────┼───────────────┘
└─────────┬───────────┘
          │ 1:N
          ▼
┌─────────────────────┐
│    Memora Unit      │
│  ─────────────────  │
│  is_linear          │
│  parent_track       │
└─────────┬───────────┘
          │ 1:N
          ▼
┌─────────────────────┐
│    Memora Topic     │
│  ─────────────────  │
│  is_linear (NEW)    │
│  parent_unit        │
└─────────┬───────────┘
          │ 1:N
          ▼
┌─────────────────────┐
│   Memora Lesson     │
│  ─────────────────  │
│  bit_index (NEW)    │◄─── assigned from Subject.next_bit_index
│  parent_topic       │
└─────────────────────┘


┌──────────────────────────────┐
│  Memora Structure Progress   │
│  ────────────────────────────│
│  player ──────────────────────┼──► Memora Player Profile
│  subject ─────────────────────┼──► Memora Subject
│  academic_plan ───────────────┼──► Memora Academic Plan
│  passed_lessons_bitset (NEW)  │
│  best_hearts_data (NEW)       │
│  completion_percentage        │
│  total_xp_earned              │
│  last_synced_at               │
└──────────────────────────────┘


┌─────────────────────┐
│ Memora Player Wallet│
│  ─────────────────  │
│  player ────────────┼──► Memora Player Profile
│  total_xp           │◄── XP added here
│  current_streak     │
└─────────────────────┘
```

## State Transitions

### Lesson Status

```
              ┌─────────┐
              │ LOCKED  │
              └────┬────┘
                   │ (unlock conditions met)
                   ▼
              ┌──────────┐
              │ UNLOCKED │
              └────┬─────┘
                   │ (lesson completed with hearts > 0)
                   ▼
              ┌─────────┐
              │ PASSED  │
              └─────────┘
```

### Container Status (Topic/Unit/Track)

```
              ┌─────────┐
              │ LOCKED  │ (parent locked OR linear prev sibling not passed)
              └────┬────┘
                   │
                   ▼
              ┌──────────┐
              │ UNLOCKED │ (accessible, some children incomplete)
              └────┬─────┘
                   │ (ALL children PASSED)
                   ▼
              ┌─────────┐
              │ PASSED  │
              └─────────┘
```

## Validation Rules

| Rule | Entity | Condition | Error Message |
|------|--------|-----------|---------------|
| VR-001 | Lesson | `bit_index >= 0` after insert | "Lesson must have valid bit_index" |
| VR-002 | Lesson | `bit_index` is unique within subject | "Duplicate bit_index in subject" |
| VR-003 | Subject | `next_bit_index >= 0` | "Invalid bit index counter" |
| VR-004 | Structure Progress | `player + subject + academic_plan` unique | "Duplicate progress record" |
| VR-005 | Complete Lesson | `hearts >= 0 AND hearts <= 5` | "Hearts must be 0-5" |
| VR-006 | Complete Lesson | Player has remaining hearts | "No hearts remaining" |

## Migration Plan

### Phase 1: Add New Fields (Non-Breaking)
1. Add `next_bit_index` to Memora Subject (default 0)
2. Add `bit_index` to Memora Lesson (default -1)
3. Add `is_linear` to Memora Topic (default 1)
4. Add `passed_lessons_bitset` to Memora Structure Progress
5. Add `best_hearts_data` to Memora Structure Progress

### Phase 2: Backfill Existing Data
1. For each Subject, count lessons and set `next_bit_index`
2. For each Lesson (ordered by creation), assign sequential `bit_index`
3. Convert existing `passed_lessons_data` JSON to bitmap format

### Phase 3: Deprecate Old Fields
1. Remove `passed_lessons_data` field (after verification)
