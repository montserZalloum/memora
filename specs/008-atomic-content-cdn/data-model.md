# Data Model: Atomic JSON Content Generation & CDN Distribution

**Feature**: 008-atomic-content-cdn
**Date**: 2026-01-26

## File Structure Overview

```
/sites/{site}/public/memora_content/
├── plans/
│   └── {plan_id}/
│       ├── manifest.json           # Plan index
│       ├── {subject_id}_h.json     # Subject hierarchy
│       ├── {subject_id}_b.json     # Subject bitmap
│       └── {topic_id}.json         # Topic lessons
└── lessons/
    └── {lesson_id}.json            # Shared lesson content
```

---

## 1. Manifest File (`manifest.json`)

**Path**: `/plans/{plan_id}/manifest.json`
**Purpose**: Entry point for plan content, lists available subjects

### Schema

```json
{
  "plan_id": "string (required)",
  "title": "string (required)",
  "season": "string (optional)",
  "grade": "string (optional)",
  "stream": "string (optional)",
  "version": "integer (required) - Unix timestamp",
  "generated_at": "string (required) - ISO 8601",
  "subjects": [
    {
      "id": "string (required) - Subject document name",
      "title": "string (required)",
      "description": "string (optional)",
      "image": "string (optional) - URL",
      "color_code": "string (optional) - Hex color",
      "is_linear": "boolean (required) - Navigation mode",
      "hierarchy_url": "string (required) - Path to _h.json",
      "bitmap_url": "string (required) - Path to _b.json",
      "access": {
        "is_published": "boolean (required)",
        "access_level": "enum (required) - public|authenticated|paid|free_preview",
        "required_item": "string (optional) - ERPNext Item code"
      }
    }
  ],
  "search_index_url": "string (optional) - Path to search index"
}
```

### Example

```json
{
  "plan_id": "PLAN-GRADE12-2024",
  "title": "Grade 12 Science 2024",
  "season": "2024",
  "grade": "Grade 12",
  "stream": "Scientific",
  "version": 1706270400,
  "generated_at": "2026-01-26T10:00:00Z",
  "subjects": [
    {
      "id": "SUBJ-MATH",
      "title": "Mathematics",
      "description": "Advanced Mathematics for Grade 12",
      "image": "/files/math-icon.png",
      "color_code": "#3B82F6",
      "is_linear": false,
      "hierarchy_url": "plans/PLAN-GRADE12-2024/SUBJ-MATH_h.json",
      "bitmap_url": "plans/PLAN-GRADE12-2024/SUBJ-MATH_b.json",
      "access": {
        "is_published": true,
        "access_level": "paid",
        "required_item": "PROD-MATH-12"
      }
    }
  ],
  "search_index_url": "plans/PLAN-GRADE12-2024/search_index.json"
}
```

---

## 2. Subject Hierarchy File (`{subject_id}_h.json`)

**Path**: `/plans/{plan_id}/{subject_id}_h.json`
**Purpose**: Navigation hierarchy (tracks → units → topics), NO lessons

### Schema

```json
{
  "id": "string (required) - Subject document name",
  "title": "string (required)",
  "description": "string (optional)",
  "image": "string (optional)",
  "color_code": "string (optional)",
  "is_linear": "boolean (required)",
  "version": "integer (required)",
  "generated_at": "string (required)",
  "access": {
    "is_published": "boolean (required)",
    "access_level": "enum (required)",
    "required_item": "string (optional)"
  },
  "tracks": [
    {
      "id": "string (required)",
      "title": "string (required)",
      "description": "string (optional)",
      "is_linear": "boolean (required)",
      "access": { ... },
      "units": [
        {
          "id": "string (required)",
          "title": "string (required)",
          "description": "string (optional)",
          "is_linear": "boolean (required)",
          "access": { ... },
          "topics": [
            {
              "id": "string (required)",
              "title": "string (required)",
              "description": "string (optional)",
              "is_linear": "boolean (required)",
              "topic_url": "string (required) - Path to topic JSON",
              "access": { ... },
              "lesson_count": "integer (required)"
            }
          ]
        }
      ]
    }
  ],
  "stats": {
    "total_tracks": "integer",
    "total_units": "integer",
    "total_topics": "integer",
    "total_lessons": "integer"
  }
}
```

### Key Differences from Current

1. **No lessons inline** - Topics have `topic_url` to separate file
2. **`is_linear` at every level** - Supports navigation mode overrides
3. **`lesson_count` on topics** - Enables UI to show topic size without loading lessons

---

## 3. Subject Bitmap File (`{subject_id}_b.json`)

**Path**: `/plans/{plan_id}/{subject_id}_b.json`
**Purpose**: Progress engine bit mappings for all lessons in subject

### Schema

```json
{
  "subject_id": "string (required)",
  "version": "integer (required)",
  "generated_at": "string (required)",
  "total_lessons": "integer (required)",
  "mappings": {
    "{lesson_id}": {
      "bit_index": "integer (required) - 0-based",
      "topic_id": "string (required)"
    }
  }
}
```

### Example

```json
{
  "subject_id": "SUBJ-MATH",
  "version": 1706270400,
  "generated_at": "2026-01-26T10:00:00Z",
  "total_lessons": 150,
  "mappings": {
    "LESSON-MATH-001": { "bit_index": 0, "topic_id": "TOPIC-ALGEBRA-1" },
    "LESSON-MATH-002": { "bit_index": 1, "topic_id": "TOPIC-ALGEBRA-1" },
    "LESSON-MATH-003": { "bit_index": 2, "topic_id": "TOPIC-ALGEBRA-2" }
  }
}
```

---

## 4. Topic File (`{topic_id}.json`)

**Path**: `/plans/{plan_id}/{topic_id}.json`
**Purpose**: Lesson list for a topic with bit_index references

### Schema

```json
{
  "id": "string (required) - Topic document name",
  "title": "string (required)",
  "description": "string (optional)",
  "is_linear": "boolean (required)",
  "version": "integer (required)",
  "generated_at": "string (required)",
  "parent": {
    "unit_id": "string (required)",
    "unit_title": "string (required)",
    "track_id": "string (required)",
    "track_title": "string (required)",
    "subject_id": "string (required)",
    "subject_title": "string (required)"
  },
  "access": {
    "is_published": "boolean (required)",
    "access_level": "enum (required)",
    "required_item": "string (optional)"
  },
  "lessons": [
    {
      "id": "string (required)",
      "title": "string (required)",
      "description": "string (optional)",
      "bit_index": "integer (required)",
      "lesson_url": "string (required) - Path to shared lesson JSON",
      "access": {
        "is_published": "boolean (required)",
        "access_level": "enum (required)"
      },
      "stage_count": "integer (required)"
    }
  ]
}
```

### Example

```json
{
  "id": "TOPIC-ALGEBRA-1",
  "title": "Introduction to Algebra",
  "description": "Fundamentals of algebraic expressions",
  "is_linear": true,
  "version": 1706270400,
  "generated_at": "2026-01-26T10:00:00Z",
  "parent": {
    "unit_id": "UNIT-ALGEBRA",
    "unit_title": "Algebra Fundamentals",
    "track_id": "TRACK-MATH-CORE",
    "track_title": "Core Mathematics",
    "subject_id": "SUBJ-MATH",
    "subject_title": "Mathematics"
  },
  "access": {
    "is_published": true,
    "access_level": "paid",
    "required_item": "PROD-MATH-12"
  },
  "lessons": [
    {
      "id": "LESSON-MATH-001",
      "title": "Variables and Expressions",
      "description": "Learn about variables",
      "bit_index": 0,
      "lesson_url": "lessons/LESSON-MATH-001.json",
      "access": {
        "is_published": true,
        "access_level": "paid"
      },
      "stage_count": 5
    }
  ]
}
```

---

## 5. Lesson File (`{lesson_id}.json`)

**Path**: `/lessons/{lesson_id}.json`
**Purpose**: Shared lesson content with stages (plan-agnostic)

### Schema

```json
{
  "id": "string (required) - Lesson document name",
  "title": "string (required)",
  "description": "string (optional)",
  "version": "integer (required)",
  "generated_at": "string (required)",
  "stages": [
    {
      "idx": "integer (required) - 1-based order",
      "title": "string (required)",
      "type": "enum (required) - Video|Question|Text|Interactive",
      "weight": "number (optional) - XP weight",
      "target_time": "integer (optional) - Seconds",
      "is_skippable": "boolean (optional) - Default false",
      "config": "object (required) - Type-specific data"
    }
  ],
  "navigation": {
    "is_standalone": "boolean (required) - Always true for shared lesson"
  }
}
```

### Key Changes from Current

1. **No `access` block** - Access is determined by topic, not lesson
2. **No `parent` block** - Lesson is shared, parent varies by plan
3. **`is_standalone: true`** - Indicates shared lesson (no plan-specific navigation)

### Example

```json
{
  "id": "LESSON-MATH-001",
  "title": "Variables and Expressions",
  "description": "Learn about variables and algebraic expressions",
  "version": 1706270400,
  "generated_at": "2026-01-26T10:00:00Z",
  "stages": [
    {
      "idx": 1,
      "title": "Introduction Video",
      "type": "Video",
      "weight": 1.0,
      "target_time": 180,
      "is_skippable": false,
      "config": {
        "video_url": "https://cdn.example.com/videos/intro.mp4",
        "thumbnail": "https://cdn.example.com/thumbs/intro.jpg"
      }
    },
    {
      "idx": 2,
      "title": "Practice Question",
      "type": "Question",
      "weight": 2.0,
      "target_time": 60,
      "is_skippable": false,
      "config": {
        "question": "What is 2x when x=3?",
        "options": ["4", "5", "6", "7"],
        "correct_answer": 2
      }
    }
  ],
  "navigation": {
    "is_standalone": true
  }
}
```

---

## DocType Schema Changes

### Memora Plan Override

**Current Actions**: Hide, Rename, Set Free, Set Sold Separately

**New Actions to Add**:
1. `Set Access Level` - `override_value` contains: public|authenticated|paid|free_preview
2. `Set Linear` - `override_value` contains: 0|1

**Updated Options**:
```
Hide
Rename
Set Free
Set Sold Separately
Set Access Level
Set Linear
```

---

## Access Control Inheritance Rules

Priority order (highest to lowest):
1. Plan override (Hide, Set Access Level, Set Free, Set Sold Separately)
2. `is_free_preview` flag on node
3. `required_item` field (→ paid)
4. `is_published` flag on node
5. Parent access level (inheritance)
6. Default: `authenticated`

### Inheritance Flow

```
Subject (access_level: paid)
  └── Track (inherits: paid)
       └── Unit (is_free_preview: true → access_level: free_preview)
            └── Topic (inherits: free_preview)
                 └── Lesson (inherits: free_preview)
```

### Override Behavior

| Override Action | Effect |
|-----------------|--------|
| Hide | Node and all descendants excluded from JSON |
| Set Free | Node becomes `free_preview`, descendants inherit |
| Set Sold Separately | Node becomes independent `paid` with own `required_item` |
| Set Access Level | Node set to specified level, descendants inherit |
| Set Linear | Node's `is_linear` flag set to specified value |
| Rename | NOT IMPLEMENTED for JSON (display-only) |

---

## Relationship to Existing DocTypes

| DocType | File(s) Generated | Notes |
|---------|-------------------|-------|
| Memora Academic Plan | manifest.json | Entry point |
| Memora Subject | {subject_id}_h.json, {subject_id}_b.json | Hierarchy + Bitmap |
| Memora Track | Embedded in _h.json | No separate file |
| Memora Unit | Embedded in _h.json | No separate file |
| Memora Topic | {topic_id}.json | Lesson list |
| Memora Lesson | {lesson_id}.json | Shared content |
| Memora Lesson Stage | Embedded in lesson | No separate file |
| Memora Plan Override | Affects all files | Applied during generation |
