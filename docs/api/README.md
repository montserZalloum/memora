# Memora API Documentation

Complete reference for all Memora API endpoints organized by domain modules.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Response Format](#response-format)
- [API Modules](#api-modules)
  - [Subjects & Tracks](#subjects--tracks)
  - [Map Engine](#map-engine)
  - [Sessions](#sessions)
  - [Reviews (SRS)](#reviews-srs)
  - [Profile](#profile)
  - [Quests](#quests)
  - [Leaderboard](#leaderboard)
  - [Onboarding](#onboarding)
  - [Store](#store)
  - [SRS Admin](#srs-admin)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## Overview

The Memora API is organized into domain-specific modules for better maintainability. All endpoints are whitelisted using Frappe's `@frappe.whitelist()` decorator and can be called from client-side applications.

### API Architecture

```
Client Application
        │
        ▼
┌─────────────────────┐
│  API Gateway        │  (api/__init__.py)
│  (Re-exports)      │
└──────────┬──────────┘
           │
    ┌──────┼──────┬─────────┬────────┐
    │      │      │         │        │
    ▼      ▼      ▼         ▼        ▼
Subjects Map  Sessions  Reviews  Profile  ...
```

## Authentication

All API endpoints require authentication through Frappe's session system:

- **Session-based**: User must be logged in via Frappe login
- **Token-based**: API keys can be used for programmatic access
- **Whitelisted**: All endpoints are protected by `@frappe.whitelist()` decorator

### Authentication Headers

```http
Cookie: sid=<session_id>
Authorization: token <api_key>:<api_secret>
```

## Base URL

```
https://your-domain.com/api/method/memora.api.<module>.<function>
```

### Example

```http
GET /api/method/memora.api.subjects.get_subjects
```

## Response Format

### Success Response

```json
{
  "message": {
    "data": {...},
    "status": "success"
  }
}
```

### Error Response

```json
{
  "exc": "Error message",
  "exc_type": "ValidationError",
  "_server_messages": "[\"Error details\"]"
}
```

## API Modules

### Subjects & Tracks

Module: [`memora/api/subjects.py`](../../memora/api/subjects.py)

#### `get_subjects()`

Get subjects based on user's academic plan with Arabic display names.

**Endpoint**: `GET /api/method/memora.api.subjects.get_subjects`

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "name": "mathematics",
      "title": "رياضيات",
      "icon": "📐",
      "is_paid": false
    }
  ]
}
```

**Logic**:
1. Fetch user's grade, stream, and academic year from Player Profile
2. Find matching Academic Plan
3. Return subjects with display names from plan
4. Returns empty list if onboarding not completed

---

#### `get_my_subjects()`

Get subjects specific to current user's Academic Plan with metadata.

**Endpoint**: `GET /api/method/memora.api.subjects.get_my_subjects`

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "id": "mathematics",
      "name": "رياضيات",
      "icon": "📐",
      "display_name": "رياضيات",
      "is_mandatory": true
    }
  ]
}
```

---

#### `get_game_tracks(subject)`

Get learning tracks for a given subject.

**Endpoint**: `GET /api/method/memora.api.subjects.get_game_tracks`

**Parameters**:
- `subject` (string, required): Subject name/ID

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "name": "track-1",
      "track_name": "Basic Track",
      "is_default": true,
      "unlock_level": 1,
      "icon": "🎯",
      "description": "Track description"
    }
  ]
}
```

---

### Map Engine

Module: [`memora/api/map_engine.py`](../../memora/api/map_engine.py)

#### `get_map_data(subject, track)`

Get learning map data for a subject and track.

**Endpoint**: `GET /api/method/memora.api.map_engine.get_map_data`

**Parameters**:
- `subject` (string, required): Subject name
- `track` (string, required): Track name

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "units": [
      {
        "name": "unit-1",
        "title": "Algebra",
        "topics": [...]
      }
    ]
  }
}
```

---

#### `get_track_details(track)`

Get detailed information about a learning track.

**Endpoint**: `GET /api/method/memora.api.map_engine.get_track_details`

**Parameters**:
- `track` (string, required): Track name

**Authentication**: Required

---

#### `get_topic_details(topic_id)`

Get detailed information about a topic.

**Endpoint**: `GET /api/method/memora.api.map_engine.get_topic_details`

**Parameters**:
- `topic_id` (string, required): Topic ID

**Authentication**: Required

---

#### `get_unit_topics(unit_id)`

Get topics within a unit.

**Endpoint**: `GET /api/method/memora.api.map_engine.get_unit_topics`

**Parameters**:
- `unit_id` (string, required): Unit ID

**Authentication**: Required

---

### Sessions

Module: [`memora/api/sessions.py`](../../memora/api/sessions.py)

#### `get_lesson_details(lesson_id)`

Get lesson content with stages configuration.

**Endpoint**: `GET /api/method/memora.api.sessions.get_lesson_details`

**Parameters**:
- `lesson_id` (string, required): Lesson ID

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "name": "lesson-1",
    "title": "Linear Equations",
    "xp_reward": 100,
    "stages": [
      {
        "id": "stage-1",
        "title": "Introduction",
        "type": "video",
        "config": {...}
      }
    ]
  }
}
```

**Error**: Returns error if lesson not found or not published

---

#### `submit_session(session_meta, gamification_results, interactions)`

Submit gameplay session with XP, score, and SRS tracking.

**Endpoint**: `POST /api/method/memora.api.sessions.submit_session`

**Parameters**:
- `session_meta` (object, required): Session metadata
  - `lesson_id` (string): Lesson ID
- `gamification_results` (object, required): Results data
  - `xp_earned` (number): XP earned
  - `score` (number): Score achieved
- `interactions` (array, required): Question interactions
  - Each interaction includes question ID, answer, correctness

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "status": "success",
    "message": "Session Saved ✅"
  }
}
```

**Process**:
1. Archives gameplay session
2. Updates global XP
3. Updates subject progression (leaderboard)
4. Updates SRS memory tracking
5. All in single database transaction

---

### Reviews (SRS)

Module: [`memora/api/reviews.py`](../../memora/api/reviews.py)

#### `get_review_session(subject=None, topic_id=None)`

Get due questions for review session with Redis caching.

**Endpoint**: `GET /api/method/memora.api.reviews.get_review_session`

**Parameters**:
- `subject` (string, optional): Filter by subject
- `topic_id` (string, optional): Filter by topic

**Authentication**: Required

**Performance**: <100ms via Redis cache

**Response**:
```json
{
  "message": {
    "questions": [
      {
        "id": "q-1",
        "question_text": "...",
        "options": [...],
        "srs_data": {...}
      }
    ],
    "is_degraded": false,
    "season": "2024-2025"
  }
}
```

**Features**:
- Redis cache for instant retrieval
- Safe Mode fallback with rate limiting
- Lazy loading on cache miss
- Subject and topic filtering

---

#### `submit_review_session(session_data)`

Submit review session with async persistence.

**Endpoint**: `POST /api/method/memora.api.reviews.submit_review_session`

**Parameters**:
- `session_data` (object, required): Review session data
  - `questions` (array): Question answers
  - `subject` (string): Subject
  - `topic_id` (string): Topic ID

**Authentication**: Required

**Performance**: <500ms confirmation

**Response**:
```json
{
  "message": {
    "xp_earned": 120,
    "remaining_items": 45,
    "persistence_job_id": "job_12345"
  }
}
```

**Process**:
1. Synchronous Redis update
2. Asynchronous database persistence
3. Returns job ID for tracking
4. Audit logging

---

### Profile

Module: [`memora/api/profile.py`](../../memora/api/profile.py)

#### `get_player_profile()`

Get basic player profile data on app load.

**Endpoint**: `GET /api/method/memora.api.profile.get_player_profile`

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "xp": 1500,
    "gems": 50,
    "current_grade": "Grade 10",
    "current_stream": "Science"
  }
}
```

---

#### `get_full_profile_stats(subject=None)`

Get comprehensive profile statistics with level, streak, and mastery.

**Endpoint**: `GET /api/method/memora.api.profile.get_full_profile_stats`

**Parameters**:
- `subject` (string, optional): Filter by subject

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "fullName": "John Doe",
    "avatarUrl": "/files/avatar.jpg",
    "level": 5,
    "levelTitle": "حارس الذاكرة",
    "nextLevelProgress": 65,
    "xpInLevel": 350,
    "xpToNextLevel": 500,
    "streak": 7,
    "gems": 0,
    "totalXP": 1500,
    "totalLearned": 250,
    "weeklyActivity": [
      {
        "day": "سبت",
        "full_date": "2026-01-20",
        "xp": 120,
        "isToday": true
      }
    ],
    "mastery": {
      "new": 50,
      "learning": 100,
      "mature": 100
    }
  }
}
```

**Calculations**:
- **Level**: `int(0.07 * sqrt(xp)) + 1`
- **Streak**: Consecutive days of activity
- **Mastery**: Based on SRS stability levels

---

### Quests

Module: [`memora/api/quests.py`](../../memora/api/quests.py)

#### `get_daily_quests()`

Get daily quests for the current user.

**Endpoint**: `GET /api/method/memora.api.quests.get_daily_quests`

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "id": "quest-1",
      "title": "Complete 3 Lessons",
      "description": "Complete 3 lessons today",
      "xp_reward": 50,
      "progress": 1,
      "target": 3,
      "completed": false
    }
  ]
}
```

---

### Leaderboard

Module: [`memora/api/leaderboard.py`](../../memora/api/leaderboard.py)

#### `get_leaderboard(subject=None, period="weekly")`

Get leaderboard rankings.

**Endpoint**: `GET /api/method/memora.api.leaderboard.get_leaderboard`

**Parameters**:
- `subject` (string, optional): Filter by subject
- `period` (string, optional): Time period (daily, weekly, monthly, all-time)

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "rankings": [
      {
        "rank": 1,
        "player": "John Doe",
        "xp": 2500,
        "level": 8,
        "avatar": "/files/avatar1.jpg"
      }
    ],
    "current_user_rank": 5
  }
}
```

---

### Onboarding

Module: [`memora/api/onboarding.py`](../../memora/api/onboarding.py)

#### `get_academic_masters()`

Get available academic grades, streams, and plans.

**Endpoint**: `GET /api/method/memora.api.onboarding.get_academic_masters`

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "grades": ["Grade 9", "Grade 10", "Grade 11"],
    "streams": ["Science", "Arts", "Commerce"],
    "plans": ["CBSE", "ICSE", "State Board"]
  }
}
```

---

#### `set_academic_profile(grade, stream, academic_year)`

Set user's academic profile during onboarding.

**Endpoint**: `POST /api/method/memora.api.onboarding.set_academic_profile`

**Parameters**:
- `grade` (string, required): Academic grade
- `stream` (string, optional): Academic stream
- `academic_year` (string, required): Academic year

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "status": "success",
    "profile_updated": true
  }
}
```

---

### Store

Module: [`memora/api/store.py`](../../memora/api/store.py)

#### `get_store_items()`

Get available items in the in-app store.

**Endpoint**: `GET /api/method/memora.api.store.get_store_items`

**Authentication**: Required

**Response**:
```json
{
  "message": [
    {
      "id": "item-1",
      "name": "Premium Subscription",
      "description": "Full access to all content",
      "price": 9.99,
      "currency": "USD",
      "type": "subscription"
    }
  ]
}
```

---

#### `request_purchase(item_id, payment_method)`

Request purchase of an item.

**Endpoint**: `POST /api/method/memora.api.store.request_purchase`

**Parameters**:
- `item_id` (string, required): Item ID
- `payment_method` (string, required): Payment method

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "status": "success",
    "purchase_id": "purchase-123",
    "redirect_url": "https://payment-gateway.com/..."
  }
}
```

---

### SRS Admin

Module: [`memora/api/srs.py`](../../memora/api/srs.py)

#### `get_cache_status()`

Monitor Redis cache health and statistics.

**Endpoint**: `GET /api/method/memora.api.srs.get_cache_status`

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "redis_connected": true,
    "is_safe_mode": false,
    "memory_used_mb": 245.67,
    "total_keys": 125000,
    "keys_by_season": {
      "2024-2025": 85000,
      "2023-2024": 40000
    }
  }
}
```

---

#### `rebuild_season_cache(season_name)`

Trigger full cache rebuild for a season.

**Endpoint**: `POST /api/method/memora.api.srs.rebuild_season_cache`

**Parameters**:
- `season_name` (string, required): Season name (e.g., "2024-2025")

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "status": "started",
    "job_id": "cache_rebuild_2024-2025_2024-01-20",
    "estimated_records": 85000
  }
}
```

---

#### `archive_season(season_name, confirm=False)`

Archive season data to cold storage.

**Endpoint**: `POST /api/method/memora.api.srs.archive_season`

**Parameters**:
- `season_name` (string, required): Season name
- `confirm` (boolean, required): Must be true to confirm

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "success": true,
    "archived_count": 45000,
    "message": "Season archived successfully"
  }
}
```

---

#### `get_archive_status(season_name)`

Get archive status for a season.

**Endpoint**: `GET /api/method/memora.api.srs.get_archive_status`

**Parameters**:
- `season_name` (string, required): Season name

**Authentication**: Required

**Response**:
```json
{
  "message": {
    "active_records": 0,
    "archived_records": 45000,
    "eligible_for_deletion": 12000,
    "archived_at": "2024-01-15T10:30:00"
  }
}
```

---

#### `delete_eligible_archived_records(season_name=None, confirm=False)`

Delete archived records marked for deletion.

**Endpoint**: `POST /api/method/memora.api.srs.delete_eligible_archived_records`

**Parameters**:
- `season_name` (string, optional): Filter by season
- `confirm` (boolean, required): Must be true to confirm

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "success": true,
    "deleted_count": 12000,
    "message": "Deleted 12,000 eligible records"
  }
}
```

---

#### `trigger_reconciliation()`

Manually trigger cache reconciliation.

**Endpoint**: `POST /api/method/memora.api.srs.trigger_reconciliation`

**Authentication**: Required (System Manager role)

**Response**:
```json
{
  "message": {
    "status": "started",
    "job_id": "reconciliation_2024-01-20"
  }
}
```

---

## Error Handling

### Common Error Codes

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `ValidationError` | Invalid input data | 400 |
| `PermissionError` | Insufficient permissions | 403 |
| `NotFoundError` | Resource not found | 404 |
| `RateLimitError` | Too many requests | 429 |
| `ServerError` | Internal server error | 500 |

### Error Response Format

```json
{
  "exc": "Validation Error: Lesson ID is missing",
  "exc_type": "ValidationError",
  "_server_messages": "[\"Validation Error: Lesson ID is missing\"]"
}
```

## Rate Limiting

### Safe Mode Rate Limits

When Redis is unavailable, the system enters Safe Mode with rate limiting:

- **Global Limit**: 500 requests per minute
- **Per-User Limit**: 1 request per 30 seconds
- **Result Limit**: Maximum 15 items per request

### Rate Limit Response

```json
{
  "message": "Rate limit exceeded. Please try again later."
}
```

---

## API Versioning

Current API version: **v1**

All endpoints are version-agnostic. Breaking changes will be announced in advance.

## Best Practices

1. **Always handle errors**: Check for error responses and handle gracefully
2. **Use caching**: Leverage Redis caching for SRS operations
3. **Batch requests**: Minimize API calls by batching related operations
4. **Monitor rate limits**: Respect rate limits, especially in Safe Mode
5. **Validate inputs**: Always validate data before sending to API
6. **Handle async operations**: For `submit_review_session`, track persistence job if needed

## Testing

### Example cURL Commands

```bash
# Get subjects
curl -X GET "https://your-domain.com/api/method/memora.api.subjects.get_subjects" \
  -H "Cookie: sid=<session_id>"

# Submit session
curl -X POST "https://your-domain.com/api/method/memora.api.sessions.submit_session" \
  -H "Cookie: sid=<session_id>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_meta": {"lesson_id": "lesson-1"},
    "gamification_results": {"xp_earned": 100, "score": 85},
    "interactions": [...]
  }'
```

---

**Last Updated**: 2026-01-20
**API Version**: 1.0
