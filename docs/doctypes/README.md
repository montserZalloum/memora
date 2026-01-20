# Memora DocTypes Documentation

Complete reference for all Memora data models (DocTypes) in the Frappe framework.

## Table of Contents

- [Overview](#overview)
- [DocType Categories](#doctype-categories)
- [Core DocTypes](#core-doctypes)
  - [Player Profile](#player-profile)
  - [Player Memory Tracker](#player-memory-tracker)
  - [Gameplay Session](#gameplay-session)
- [Content DocTypes](#content-doctypes)
  - [Game Subject](#game-subject)
  - [Game Topic](#game-topic)
  - [Game Lesson](#game-lesson)
  - [Game Stage](#game-stage)
- [Academic Structure DocTypes](#academic-structure-doctypes)
  - [Game Academic Grade](#game-academic-grade)
  - [Game Academic Stream](#game-academic-stream)
  - [Game Academic Plan](#game-academic-plan)
  - [Game Learning Track](#game-learning-track)
  - [Game Unit](#game-unit)
- [Subscription DocTypes](#subscription-doctypes)
  - [Game Subscription Season](#game-subscription-season)
  - [Game Subscription Access](#game-subscription-access)
  - [Game Player Subscription](#game-player-subscription)
  - [Game Purchase Request](#game-purchase-request)
  - [Game Sales Item](#game-sales-item)
- [Gamification DocTypes](#gamification-doctypes)
  - [Player Subject Score](#player-subject-score)
  - [Game Daily Quest](#game-daily-quest)
- [System DocTypes](#system-doctypes)
  - [Archived Memory Tracker](#archived-memory-tracker)
  - [Game Player Device](#game-player-device)
- [DocType Relationships](#doctype-relationships)

## Overview

Memora uses Frappe's DocType system to define data models. Each DocType represents a database table with fields, permissions, and business logic.

### DocType Structure

```json
{
  "name": "DocType Name",
  "module": "Memora",
  "fields": [...],
  "permissions": [...],
  "indexes": [...]
}
```

### File Structure

```
memora/memora/doctype/
├── player_profile/
│   ├── player_profile.json    # Schema definition
│   ├── player_profile.py      # Controller logic
│   └── test_player_profile.py # Tests
├── player_memory_tracker/
├── gameplay_session/
└── ...
```

## DocType Categories

### 1. Core DocTypes
Essential data models for player management and gameplay tracking.

### 2. Content DocTypes
Educational content structure (subjects, topics, lessons).

### 3. Academic Structure DocTypes
Academic hierarchy (grades, streams, plans, tracks).

### 4. Subscription DocTypes
Subscription and purchase management.

### 5. Gamification DocTypes
XP, scores, quests, and leaderboards.

### 6. System DocTypes
System-level data and archival.

## Core DocTypes

### Player Profile

**Module**: [`memora/memora/doctype/player_profile/`](../../memora/memora/doctype/player_profile/)

**Purpose**: Stores player profile information including XP, gems, and academic details.

**Naming**: `PROFILE-{user}` (auto-generated)

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user` | Link (User) | Yes | Linked Frappe User account |
| `total_xp` | Int | No | Total experience points earned |
| `gems_balance` | Int | No | Gems balance (deprecated) |
| `current_grade` | Link (Game Academic Grade) | No | Current academic grade |
| `current_stream` | Link (Game Academic Stream) | No | Current academic stream |
| `academic_year` | Data | No | Current academic year |
| `devices` | Table (Game Player Device) | No | Registered devices |

#### Permissions

- **System Manager**: Full access (create, read, write, delete, share, export, print, email, report)

#### Usage

```python
# Get player profile
profile = frappe.get_doc("Player Profile", {"user": user})

# Update XP
profile.total_xp += 100
profile.save()
```

---

### Player Memory Tracker

**Module**: [`memora/memora/doctype/player_memory_tracker/`](../../memora/memora/doctype/player_memory_tracker/)

**Purpose**: Tracks SRS (Spaced Repetition System) data for each question-player interaction.

**Naming**: Random hash (auto-generated)

**Partitioning**: LIST COLUMNS by `season` for performance

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player who interacted with question |
| `question_id` | Data | Yes | Unique question identifier |
| `subject` | Link (Game Subject) | No | Subject the question belongs to |
| `topic` | Link (Game Topic) | No | Topic the question belongs to |
| `stability` | Float | No | SRS stability level (0.0-4.0) |
| `next_review_date` | Datetime | No | When question should be reviewed next |
| `last_review_date` | Datetime | No | Last time question was reviewed |
| `season` | Link (Game Subscription Season) | Yes | Season for partitioning |

#### Stability Levels

| Level | Name | Description |
|-------|------|-------------|
| 0.0 - 1.0 | New | Recently introduced question |
| 1.0 - 2.0 | Learning | In learning phase |
| 2.0 - 3.0 | Review | Regular review needed |
| 3.0 - 4.0 | Mature | Well-learned, infrequent reviews |
| 4.0+ | Mastered | Fully mastered |

#### Permissions

- **System Manager**: Full access

#### Usage

```python
# Create memory tracker
tracker = frappe.get_doc({
    "doctype": "Player Memory Tracker",
    "player": user,
    "question_id": "q-123",
    "subject": "mathematics",
    "topic": "algebra",
    "stability": 1.0,
    "next_review_date": frappe.utils.add_days(frappe.utils.now(), 1),
    "season": "2024-2025"
})
tracker.insert()
```

---

### Gameplay Session

**Module**: [`memora/memora/doctype/gameplay_session/`](../../memora/memora/doctype/gameplay_session/)

**Purpose**: Archives gameplay session data including interactions, XP earned, and scores.

**Naming**: Random hash (auto-generated)

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player who completed the session |
| `lesson` | Link (Game Lesson) | Yes | Lesson completed |
| `raw_data` | Code (JSON) | No | Full interaction data |
| `xp_earned` | Int | No | XP earned in this session |
| `score` | Int | No | Score achieved in this session |

#### Permissions

- **System Manager**: Full access

#### Usage

```python
# Create gameplay session
session = frappe.get_doc({
    "doctype": "Gameplay Session",
    "player": user,
    "lesson": "lesson-123",
    "raw_data": json.dumps(interactions),
    "xp_earned": 100,
    "score": 85
})
session.insert()
```

---

## Content DocTypes

### Game Subject

**Module**: [`memora/memora/doctype/game_subject/`](../../memora/memora/doctype/game_subject/)

**Purpose**: Defines educational subjects (e.g., Mathematics, Science).

**Naming**: Based on `title` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Subject name (unique) |
| `icon` | Attach Image | No | Subject icon/image |
| `is_published` | Check | No | Whether subject is published |
| `is_paid` | Check | No | Whether subject requires subscription |
| `full_price` | Currency | No | Full price |
| `discounted_price` | Currency | No | Discounted price |

#### Permissions

- **System Manager**: Full access

---

### Game Topic

**Module**: [`memora/memora/doctype/game_topic/`](../../memora/memora/doctype/game_topic/)

**Purpose**: Defines topics within subjects (e.g., Algebra within Mathematics).

**Naming**: Based on `title` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Topic name |
| `subject` | Link (Game Subject) | Yes | Parent subject |
| `description` | Text | No | Topic description |
| `is_published` | Check | No | Whether topic is published |

---

### Game Lesson

**Module**: [`memora/memora/doctype/game_lesson/`](../../memora/memora/doctype/game_lesson/)

**Purpose**: Defines lessons with multiple stages (videos, quizzes, etc.).

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Lesson title |
| `subject` | Link (Game Subject) | Yes | Parent subject |
| `topic` | Link (Game Topic) | Yes | Parent topic |
| `unit` | Link (Game Unit) | Yes | Parent unit |
| `xp_reward` | Int | No | XP reward for completion |
| `stages` | Table (Game Stage) | No | Lesson stages |

#### Stages

Each lesson contains multiple stages with different types:
- **Video**: Video content
- **Quiz**: Quiz questions
- **Interactive**: Interactive exercises
- **Reading**: Reading material

---

### Game Stage

**Module**: [`memora/memora/doctype/game_stage/`](../../memora/memora/doctype/game_stage/)

**Purpose**: Defines individual stages within a lesson.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | Data | Yes | Stage title |
| `type` | Select | Yes | Stage type (video, quiz, etc.) |
| `config` | Code (JSON) | No | Stage configuration |
| `order` | Int | No | Stage order within lesson |

---

## Academic Structure DocTypes

### Game Academic Grade

**Module**: [`memora/memora/doctype/game_academic_grade/`](../../memora/memora/doctype/game_academic_grade/)

**Purpose**: Defines academic grades (e.g., Grade 9, Grade 10).

**Naming**: Based on `grade_name` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grade_name` | Data | Yes | Grade name |
| `order` | Int | No | Display order |

---

### Game Academic Stream

**Module**: [`memora/memora/doctype/game_academic_stream/`](../../memora/memora/doctype/game_academic_stream/)

**Purpose**: Defines academic streams (e.g., Science, Arts, Commerce).

**Naming**: Based on `stream_name` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stream_name` | Data | Yes | Stream name |
| `order` | Int | No | Display order |

---

### Game Academic Plan

**Module**: [`memora/memora/doctype/game_academic_plan/`](../../memora/memora/doctype/game_academic_plan/)

**Purpose**: Defines academic plans for specific grade/stream/year combinations (e.g., CBSE Grade 10 Science).

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `grade` | Link (Game Academic Grade) | Yes | Academic grade |
| `stream` | Link (Game Academic Stream) | No | Academic stream |
| `year` | Data | Yes | Academic year |
| `subjects` | Table (Game Plan Subject) | Yes | Subjects in plan |

#### Game Plan Subject (Child Table)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | Link (Game Subject) | Yes | Subject |
| `display_name` | Data | No | Custom display name |
| `is_mandatory` | Check | No | Whether subject is mandatory |

---

### Game Learning Track

**Module**: [`memora/memora/doctype/game_learning_track/`](../../memora/memora/doctype/game_learning_track/)

**Purpose**: Defines learning tracks within subjects (e.g., Basic Track, Advanced Track).

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | Link (Game Subject) | Yes | Parent subject |
| `track_name` | Data | Yes | Track name |
| `is_default` | Check | No | Whether this is the default track |
| `unlock_level` | Int | No | Level required to unlock |
| `icon` | Attach Image | No | Track icon |
| `description` | Text | No | Track description |

---

### Game Unit

**Module**: [`memora/memora/doctype/game_unit/`](../../memora/memora/doctype/game_unit/)

**Purpose**: Defines units within learning tracks (e.g., Unit 1: Linear Equations).

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `learning_track` | Link (Game Learning Track) | Yes | Parent track |
| `subject` | Link (Game Subject) | Yes | Subject |
| `topic` | Link (Game Topic) | Yes | Topic |
| `unit_name` | Data | Yes | Unit name |
| `order` | Int | No | Display order |

---

## Subscription DocTypes

### Game Subscription Season

**Module**: [`memora/memora/doctype/game_subscription_season/`](../../memora/memora/doctype/game_subscription_season/)

**Purpose**: Defines subscription seasons (e.g., "2024-2025").

**Naming**: Based on `season_name` field

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `season_name` | Data | Yes | Season name |
| `start_date` | Date | Yes | Season start date |
| `end_date` | Date | Yes | Season end date |
| `is_active` | Check | No | Whether season is active |
| `auto_archive` | Check | No | Whether to auto-archive after season |

---

### Game Subscription Access

**Module**: [`memora/memora/doctype/game_subscription_access/`](../../memora/memora/doctype/game_subscription_access/)

**Purpose**: Controls access to content based on subscriptions.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `season` | Link (Game Subscription Season) | Yes | Season |
| `subject` | Link (Game Subject) | No | Subject (if specific) |
| `access_type` | Select | Yes | Access type (full, limited, trial) |
| `expiry_date` | Date | No | Access expiry date |

---

### Game Player Subscription

**Module**: [`memora/memora/doctype/game_player_subscription/`](../../memora/memora/doctype/game_player_subscription/)

**Purpose**: Stores player subscription information.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `season` | Link (Game Subscription Season) | Yes | Season |
| `subscription_type` | Select | Yes | Subscription type |
| `start_date` | Date | Yes | Start date |
| `end_date` | Date | Yes | End date |
| `is_active` | Check | No | Whether subscription is active |

---

### Game Purchase Request

**Module**: [`memora/memora/doctype/game_purchase_request/`](../../memora/memora/doctype/game_purchase_request/)

**Purpose**: Tracks in-app purchase requests.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `item` | Link (Game Sales Item) | Yes | Item to purchase |
| `amount` | Currency | Yes | Purchase amount |
| `status` | Select | Yes | Purchase status |
| `payment_method` | Select | No | Payment method |
| `transaction_id` | Data | No | Transaction ID |

---

### Game Sales Item

**Module**: [`memora/memora/doctype/game_sales_item/`](../../memora/memora/doctype/game_sales_item/)

**Purpose**: Defines items available for purchase.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_name` | Data | Yes | Item name |
| `item_type` | Select | Yes | Item type (subscription, bundle, gems) |
| `price` | Currency | Yes | Item price |
| `currency` | Data | Yes | Currency code |
| `is_active` | Check | No | Whether item is available |

---

## Gamification DocTypes

### Player Subject Score

**Module**: [`memora/memora/doctype/player_subject_score/`](../../memora/memora/doctype/player_subject_score/)

**Purpose**: Tracks player scores and XP per subject.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `subject` | Link (Game Subject) | Yes | Subject |
| `total_xp` | Int | No | Total XP in subject |
| `level` | Int | No | Current level in subject |
| `rank` | Int | No | Current rank |

---

### Game Daily Quest

**Module**: [`memora/memora/doctype/game_daily_quest/`](../../memora/memora/doctype/game_daily_quest/)

**Purpose**: Defines daily quests for players.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `quest_title` | Data | Yes | Quest title |
| `quest_type` | Select | Yes | Quest type |
| `target` | Int | Yes | Target value |
| `xp_reward` | Int | Yes | XP reward |
| `is_active` | Check | No | Whether quest is active |

---

## System DocTypes

### Archived Memory Tracker

**Module**: [`memora/memora/doctype/archived_memory_tracker/`](../../memora/memora/doctype/archived_memory_tracker/)

**Purpose**: Stores archived SRS data from old seasons.

**Naming**: Auto-generated

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `question_id` | Data | Yes | Question ID |
| `subject` | Link (Game Subject) | No | Subject |
| `topic` | Link (Game Topic) | No | Topic |
| `stability` | Float | No | Stability level |
| `next_review_date` | Datetime | No | Next review date |
| `last_review_date` | Datetime | No | Last review date |
| `season` | Link (Game Subscription Season) | Yes | Archived season |
| `archived_at` | Datetime | No | When record was archived |
| `eligible_for_deletion` | Check | No | Whether record can be deleted |

---

### Game Player Device

**Module**: [`memora/memora/doctype/game_player_device/`](../../memora/memora/doctype/game_player_device/)

**Purpose**: Tracks player devices for multi-device support.

#### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `player` | Link (User) | Yes | Player |
| `device_id` | Data | Yes | Unique device ID |
| `device_type` | Select | Yes | Device type (mobile, tablet, desktop) |
| `device_name` | Data | No | Device name |
| `last_active` | Datetime | No | Last active timestamp |

---

## DocType Relationships

### Hierarchy Diagram

```
Game Academic Grade
    └── Game Academic Stream
            └── Game Academic Plan
                    └── Game Subject
                            ├── Game Learning Track
                            │       └── Game Unit
                            │               └── Game Lesson
                            │                       └── Game Stage
                            └── Game Topic
                                    └── Game Lesson
```

### Player Data Flow

```
User
    ├── Player Profile
    ├── Player Memory Tracker
    ├── Player Subject Score
    ├── Gameplay Session
    └── Game Player Subscription
```

### Subscription Flow

```
Game Sales Item
    └── Game Purchase Request
            └── Game Player Subscription
                    └── Game Subscription Access
```

---

## DocType Best Practices

### Creating New DocTypes

1. **Define Purpose**: Clearly define what the DocType represents
2. **Choose Naming**: Use descriptive, consistent naming conventions
3. **Set Permissions**: Configure appropriate role-based permissions
4. **Add Indexes**: Add indexes for frequently queried fields
5. **Write Tests**: Create comprehensive test coverage

### Modifying Existing DocTypes

1. **Check Dependencies**: Verify no breaking changes to dependent code
2. **Create Migration**: Use Frappe patches for schema changes
3. **Update Tests**: Ensure all tests pass after changes
4. **Document Changes**: Update documentation with modifications

### Performance Considerations

1. **Partitioning**: Use LIST COLUMNS partitioning for large tables (e.g., Player Memory Tracker)
2. **Indexes**: Add composite indexes for common query patterns
3. **Caching**: Implement Redis caching for frequently accessed data
4. **Archival**: Archive old data to maintain performance

---

**Last Updated**: 2026-01-20
**Frappe Version**: Compatible with Frappe v15+
