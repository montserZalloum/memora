# Memora Documentation

**Table of Contents**
- [Overview](#overview)
- [Architecture](#architecture)
- [API Endpoints](#api-endpoints)
- [Services](#services)
  - [Player Core Services](#player-core-services)
  - [CDN Export Services](#cdn-export-services)
  - [Progress Engine Services](#progress-engine-services)
- [DocTypes](#doctypes)
- [Utilities](#utilities)
- [Hooks](#hooks)

---

## Overview

Memora is a gamified educational platform built on the Frappe Framework (v14/v15) with Python 3.10+. It provides:

- **Player Identity System**: Device authorization, session management, and rewards tracking (XP & Streaks)
- **CDN Content Delivery**: Atomic JSON generation and S3/Cloudflare R2 distribution for educational content
- **Progress Tracking**: Bitmap-based lesson completion tracking with unlock state calculation

### Key Features

- Device authorization (max 2 devices per student)
- Single active session enforcement
- XP and streak tracking with cache-first performance
- Atomic CDN content generation and upload
- High-performance bitmap progress tracking (Redis-backed)

### Technology Stack

- **Backend**: Python 3.10+ with Frappe Framework v14/v15
- **Database**: MariaDB (persistent data)
- **Cache/Queue**: Redis (sessions, progress, job queues)
- **CDN**: S3/Cloudflare R2 with Cloudflare cache purging
- **Background Jobs**: RQ (Redis Queue)
- **Batch Processing**: 500-player chunks for wallet sync

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frappe Application Layer               │
├─────────────────────────────────────────────────────────────────┤
│  API Layer              │  DocTypes          │  Hooks    │
│  (player.py,           │  (Player Profile,  │  (Event    │
│   progress.py)          │   Wallet, Content) │   Handlers)│
├─────────────────────────────────────────────────────────────────┤
│                   Services Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ Player Core  │  │ CDN Export   │  │ Progress │ │
│  │              │  │              │  │ Engine   │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    Data Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │  Redis    │  │ MariaDB  │  │ S3/R2 CDN   │ │
│  │ (Cache,   │  │ (DB)     │  │ (Content)    │ │
│  │ Sessions) │  │          │  │              │ │
│  └──────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Player API (`memora/api/player.py`)

RESTful API for player authentication, device management, and wallet operations.

#### `validate_uuid(uuid_str, param_name="uuid")`
Validate UUID v4 format.

**Args:**
- `uuid_str` (str): String to validate
- `param_name` (str): Parameter name for error messages

**Raises:** `frappe.ValidationError` if UUID is invalid

#### `validate_xp_amount(xp_amount)`
Validate XP amount is within allowed range (1-1000).

**Args:**
- `xp_amount` (int): XP amount to validate

**Raises:** `frappe.ValidationError` if XP amount is invalid

#### `validate_hearts_earned(hearts)`
Validate hearts earned from lesson (0-3).

**Args:**
- `hearts` (int): Hearts earned (0-3)

**Raises:** `frappe.ValidationError` if hearts value is invalid

#### `validate_email(email)`
Validate email format.

**Args:**
- `email` (str): Email to validate

**Raises:** `frappe.ValidationError` if email is invalid

#### `log_security_event(event_type, user_id, device_id, endpoint, result, **kwargs)`
Log security events for audit trail.

**Args:**
- `event_type` (str): Type of security event (e.g., "login", "rate_limit_exceeded")
- `user_id` (str): User identifier
- `device_id` (str): Device identifier
- `endpoint` (str): API endpoint name
- `result` (str): Result of operation (success/failure)
- `**kwargs`: Additional context

#### `rate_limit(max_requests=100, window_seconds=60)`
Decorator to enforce rate limiting per user per endpoint using Redis INCR with TTL.

**Args:**
- `max_requests` (int): Maximum requests allowed in time window
- `window_seconds` (int): Time window in seconds

**Returns:** Decorated function with rate limiting applied

#### `require_authorized_device(fn)`
Decorator to enforce device authorization and session validation on API endpoints.

**Performance:** Device/session check: <2ms (Redis)

**Returns:** Wrapped function that checks device authorization and session validity

#### `login(usr, pwd, device_name=None)` (POST, guest allowed)
Student login with device authorization. First device is auto-authorized.

**Features:**
- First device auto-authorized on account creation
- Enforces single active session
- Invalidates previous session on new login

**Args:**
- `usr` (str): Student email
- `pwd` (str): Student password
- `device_name` (str, optional): Device name for first device auto-authorization

**Returns:**
```python
{
  "message": "Logged in successfully",
  "session_id": "session_id",
  "is_first_device": True,
  "devices_authorized": 1
}
```

#### `check_device_authorization()` (GET)
Check if current device is authorized.

**Performance:** Complete check in <2ms (Redis-backed)

**Returns:**
```python
{
  "authorized": True,
  "device_count": 2
}
```

#### `register_device(student_email, device_id, device_name)` (POST)
Register a new authorized device (admin only). Maximum 2 devices per student.

**Args:**
- `student_email` (str): Student's email
- `device_id` (str): UUID v4 device identifier
- `device_name` (str): Human-readable device name

**Raises:** `frappe.PermissionError` if not System Manager

#### `remove_device(student_email, device_id)` (POST)
Remove an authorized device (admin only). Invalidates active session.

**Side Effects:**
- Invalidates active session if student was logged in on this device
- Removes device from Redis cache immediately

**Args:**
- `student_email` (str): Student's email
- `device_id` (str): UUID v4 device identifier

#### `validate_session()` (GET)
Validate current session.

**Performance:** Session validation in <2ms (Redis-backed)

**Returns:**
```python
{
  "valid": True,
  "session_id": "session_id"
}
```

#### `logout()` (POST)
Logout and invalidate current session.

**Performance:** Session invalidation completes in <2s (Redis-backed)

**Returns:** `{"message": "Logged out successfully"}`

#### `complete_lesson(lesson_id, hearts_earned)` (POST)
Complete a lesson and update streak and XP.

**Features:**
- Streak increments only once per day
- Server time authority (prevents client manipulation)
- XP awarded based on hearts * 10 formula

**Args:**
- `lesson_id` (str): ID of completed lesson
- `hearts_earned` (int): Hearts earned from lesson (must be > 0)

**Returns:**
```python
{
  "message": "Lesson completed successfully",
  "xp": {
    "awarded": 20,
    "new_total": 150
  },
  "streak": {
    "old_streak": 3,
    "new_streak": 4,
    "action": "incremented",
    "last_success_date": "2026-01-27"
  }
}
```

#### `get_wallet()` (GET)
Get current player wallet (cache-first).

**Performance:** Always read from Redis first for <1s response time

**Returns:**
```python
{
  "total_xp": 150,
  "current_streak": 4,
  "last_success_date": "2026-01-27",
  "last_played_at": "2026-01-27T10:30:00"
}
```

#### `add_xp(xp_amount)` (POST)
Award XP to player with immediate Redis update and batch sync queueing.

**Args:**
- `xp_amount` (int): XP to add (must be between 1-1000)

**Returns:**
```python
{
  "message": "XP awarded successfully",
  "xp_awarded": 50,
  "new_total_xp": 200
}
```

#### `trigger_wallet_sync(force=False)` (POST)
Manually trigger wallet sync (System Manager only).

**Args:**
- `force` (bool): If True, sync all active users regardless of queue

**Returns:**
```python
{
  "message": "Manual wallet sync completed",
  "force": False,
  "synced": 150,
  "duration": 3.5,
  "errors": 0
}
```

### Progress API (`memora/api/progress.py`)

Endpoints for lesson completion and progress tracking.

#### `complete_lesson(lesson_id, hearts)` (whitelisted)
Mark a lesson as completed and award XP.

**Features:**
- Validates request and updates progress bitmap in Redis
- Calculates XP based on hearts and record-breaking bonuses
- Awards XP to player's wallet
- Logs completion event

**Args:**
- `lesson_id` (str): The unique identifier of lesson being completed
- `hearts` (int): Number of hearts remaining at lesson completion (0-5)

**Returns:**
```python
{
  "success": True,
  "xp_earned": 20,
  "new_total_xp": 150,
  "is_first_completion": True,
  "is_new_record": True
}
```

#### `get_progress(subject_id)` (whitelisted)
Get full progress tree for a subject with unlock states.

**Features:**
- Retrieves complete progress tree with unlock states
- Computes completion percentage and next lesson suggestion
- Returns total XP and passed lessons count

**Args:**
- `subject_id` (str): The unique identifier of subject

**Returns:**
```python
{
  "subject_id": "SUBJ-001",
  "root": {...},  # Complete progress tree
  "completion_percentage": 45.5,
  "total_xp_earned": 500,
  "suggested_next_lesson_id": "LESSON-010",
  "total_lessons": 100,
  "passed_lessons": 45
}
```

---

## Services

### Player Core Services

#### Device Authorization (`memora/services/device_auth.py`)

Manages device authorization and device list cache for Player Core.

##### `is_device_authorized(user_id, device_id)`
Check if device is authorized for user (O(1) Redis lookup).

**Args:**
- `user_id` (str): Frappe User.name
- `device_id` (str): UUID v4 device identifier

**Returns:** `bool` - True if device is authorized

**Performance:** <2ms (Redis SISMEMBER)

##### `add_authorized_device(player_profile, device_id, device_name)`
Add new device to authorized list (max 2 per user).

**Args:**
- `player_profile` (str): Player Profile DocType name
- `device_id` (str): UUID v4
- `device_name` (str): Human-readable name

**Raises:** `frappe.ValidationError` if device limit exceeded or UUID invalid

##### `remove_authorized_device(player_profile, device_id)`
Remove device from authorized list and invalidate session.

**Args:**
- `player_profile` (str): Player Profile DocType name
- `device_id` (str): UUID v4 to remove

**Raises:** `frappe.ValidationError` if device not found

##### `rebuild_device_cache()`
Rebuild Redis device cache from database for all players.

**Use Case:** Cache recovery after Redis failure or data corruption

**Note:** Idempotent - safe to run multiple times

#### Session Management (`memora/services/session_manager.py`)

Manages single active session enforcement for Player Core.

##### `create_session(user_id, device_id, session_id=None)`
Create or replace active session for user.

**Features:**
- Single-session enforcement: Last login wins (GETSET atomic operation)
- Session metadata stored in Redis hash (user_id, device_id, created_at)
- Persistent sessions: No TTL on session keys (explicit invalidation only)

**Args:**
- `user_id` (str): Frappe User.name
- `device_id` (str): UUID v4 device identifier
- `session_id` (str, optional): Session ID from Frappe session

**Returns:** `str` - Active session ID

**Performance:** <2ms (Redis)

**Side Effects:** Replaces any existing session for user

##### `validate_session(user_id, session_id)`
Validate if session is still active for user.

**Args:**
- `user_id` (str): Frappe User.name
- `session_id` (str): Session ID to validate

**Returns:** `bool` - True if session is active, False otherwise

**Performance:** <2ms (Redis GET)

##### `invalidate_session(user_id)`
Invalidate active session for user.

**Performance:** Session invalidation completes in <2s (Redis DELETE)

**Args:**
- `user_id` (str): Frappe User.name

**Side Effects:**
- Deletes active_session key for user
- Logs invalidation event

#### Wallet Engine (`memora/services/wallet_engine.py`)

Manages XP accumulation and streak tracking with cache-first strategy.

##### `update_streak(user_id, hearts_earned)`
Update streak based on consecutive day logic.

**Streak Logic (server UTC time):**
- First lesson: 0 → 1
- Next day (consecutive): N → N+1
- Same day: No change
- Gap > 1 day: Reset to 1 (not 0)

**Args:**
- `user_id` (str): Frappe User.name
- `hearts_earned` (int): Hearts from lesson (must be > 0 for streak update)

**Returns:**
```python
{
  "old_streak": 3,
  "new_streak": 4,
  "streak_action": "incremented",
  "last_success_date": "2026-01-27"
}
```

##### `add_xp(user_id, xp_amount)`
Award XP to student with immediate Redis update.

**Args:**
- `user_id` (str): Frappe User.name
- `xp_amount` (int): XP to add (must be positive)

**Returns:** `int` - New total XP after increment

**Raises:** `frappe.ValidationError` if xp_amount is negative

##### `get_wallet(user_id)`
Cache-first wallet read.

**Args:**
- `user_id` (str): Frappe User.name

**Returns:**
```python
{
  "total_xp": 150,
  "current_streak": 4,
  "last_success_date": "2026-01-27",
  "last_played_at": "2026-01-27T10:30:00"
}
```

##### `get_wallet_safe(user_id)`
Cache-first wallet read with Redis fallback to DB.

**Args:**
- `user_id` (str): Frappe User.name

**Returns:** Same as `get_wallet()` but with fallback to DB on cache miss

##### `update_last_played_at(user_id)`
Record timestamp of last student interaction.

**Features:**
- Cache updates immediately even when DB write is throttled
- Throttle DB writes to every 15 minutes per student

**Args:**
- `user_id` (str): Frappe User.name

**Returns:**
```python
{
  "timestamp": "2026-01-27T10:30:00",
  "sync_required": True,
  "throttle_status": "sync_queued"
}
```

#### Wallet Sync (`memora/services/wallet_sync.py`)

Manages batch synchronization of wallet updates from Redis to MariaDB.

##### `sync_pending_wallets()`
Main sync job (runs every 15 minutes). Processes pending wallet updates in chunks.

**Sync Pattern:**
1. Read pending user IDs from Redis SET
2. Chunk into groups of 500 players
3. Bulk read wallet data from Redis
4. Bulk update MariaDB using SQL CASE (optimal performance)
5. Remove synced users from pending queue

**Performance:** <5min for 50k players, 90%+ DB write reduction

**Returns:**
```python
{
  "synced": 150,
  "duration": 3.5,
  "errors": 0
}
```

##### `_bulk_update_wallets(wallet_updates)`
Bulk update wallets to MariaDB using SQL CASE statement for optimal performance.

**Args:**
- `wallet_updates` (list): List of dicts with wallet update data

**Raises:** Exception if SQL update fails

##### `chunk_list(lst, chunk_size)`
Utility to split a list into chunks of specified size.

**Args:**
- `lst` (list): List to chunk
- `chunk_size` (int): Maximum items per chunk

**Returns:** List of chunks (each chunk is a list)

##### `trigger_wallet_sync(force=False)`
Manually trigger wallet sync for admin testing.

**Args:**
- `force` (bool): If True, skip Redis queue and sync all active users

**Returns:** Sync results

### CDN Export Services

#### Batch Processor (`memora/services/cdn_export/batch_processor.py`)

Handles batch processing of pending plan rebuilds.

##### `process_pending_plans(max_plans=10)`
Process up to max_plans from the pending queue.

**Features:**
- Acquires lock for each plan (prevents concurrent builds)
- Creates sync log entries for tracking
- Implements exponential backoff retry schedule: [30s, 1m, 2m, 5m, 15m]
- Moves to dead-letter queue after 5 failed retries
- Schema validation pre-flight check

**Retry Schedule:**
- Retry 1: 30 seconds delay
- Retry 2: 1 minute delay
- Retry 3: 2 minutes delay
- Retry 4: 5 minutes delay
- Retry 5: 15 minutes delay
- After 5 failures: Dead Letter queue

**Args:**
- `max_plans` (int): Maximum number of plans to process in one batch

**Returns:**
```python
{
  "processed": 8,
  "failed": 2,
  "skipped": 0,
  "errors": []
}
```

##### `_rebuild_plan(plan_id)`
Rebuild all JSON files for a specific plan.

**Features:**
- Always generate local JSON files (atomic writes with .tmp staging)
- Schema validation before generation
- Hash verification (local vs CDN)
- Cloudflare cache purge after upload
- Enhanced error logging with SQL context

**Args:**
- `plan_id` (str): Plan document name

**Returns:** `bool` - True if successful, False otherwise

##### `_generate_atomic_files_for_plan(plan_id)`
Generate all atomic JSON files for a plan.

**Files Generated:**
- `plans/{plan_id}/manifest.json` - Plan manifest with hierarchy/bitmap URLs
- `plans/{plan_id}/{subject_id}_h.json` - Subject hierarchy (tracks → units → topics)
- `plans/{plan_id}/{subject_id}_b.json` - Subject bitmap (lesson → bit_index mappings)
- `plans/{plan_id}/{topic_id}.json` - Topic JSON with lesson list
- `lessons/{lesson_id}.json` - Shared lesson JSON (plan-agnostic)

**Args:**
- `plan_id` (str): Plan document name

**Returns:**
```python
(True, files_written, errors)
```

##### `trigger_plan_rebuild(doctype, docname)`
Trigger a plan rebuild when content is changed.

**Features:**
- Gets affected plans via dependency resolution
- Local fallback mode: Process immediately, bypass queue
- Normal mode: Add to queue for batch processing
- Threshold-based immediate processing (default: 50 plans)

**Args:**
- `doctype` (str): The DocType that was changed
- `docname` (str): The document name that was changed

##### `validate_json_schema(json_data, schema_name)`
Validate JSON data against a JSON schema from schemas directory.

**Args:**
- `json_data` (dict): JSON data to validate
- `schema_name` (str): Name of schema file (e.g., 'lesson.schema.json')

**Returns:** `(is_valid, errors)` where errors is list of error messages

##### `validate_all_json_files(files_data)`
Validate all JSON files against their respective schemas.

**Args:**
- `files_data` (dict): Dictionary of {path: json_data} to validate

**Returns:**
```python
{
  'valid': True,
  'errors': {},
  'valid_count': 45,
  'invalid_count': 0
}
```

##### `get_queue_status()`
Get current queue status for monitoring.

**Returns:**
```python
{
  'pending_plans': 10,
  'dead_letter_count': 2,
  'recent_failures': [...],
  'last_processed': '2026-01-27T10:30:00'
}
```

#### JSON Generator (`memora/services/cdn_export/json_generator.py`)

Generates all JSON files for CDN distribution.

##### `generate_manifest(plan_doc)`
Generate plan manifest JSON.

**Returns:**
```python
{
  "plan_id": "PLAN-001",
  "title": "Grade 5 Math",
  "version": 1737974400,
  "generated_at": "2026-01-27T10:30:00",
  "season": "2026",
  "grade": "5",
  "subjects": [...]
}
```

##### `generate_manifest_atomic(plan_doc)`
Generate plan manifest JSON for atomic CDN distribution.

**Atomic Structure:**
- Includes `hierarchy_url` and `bitmap_url` for each subject
- Enables granular cache invalidation
- Shared lesson content

**Returns:** Same as `generate_manifest()` but with hierarchy/bitmap URLs

##### `generate_subject_hierarchy(subject_doc, plan_id=None)`
Generate subject hierarchy JSON (tracks → units → topics, NO lessons).

**Features:**
- Each topic includes `topic_url` pointing to separate topic JSON
- Includes `lesson_count` for UI display without loading lesson details
- Skips if subject is hidden by plan override

**Returns:** Subject hierarchy data or `None` if hidden

##### `generate_bitmap_json(subject_doc)`
Generate subject bitmap JSON with lesson → bit_index mappings.

**Purpose:** Maps each lesson in a subject to its bit_index in progress engine, enabling efficient progress tracking via bitmaps

**Returns:**
```python
{
  "subject_id": "SUBJ-001",
  "version": 1737974400,
  "generated_at": "2026-01-27T10:30:00",
  "total_lessons": 100,
  "mappings": {
    "LESSON-001": {"bit_index": 0, "topic_id": "TOPIC-001"},
    "LESSON-002": {"bit_index": 1, "topic_id": "TOPIC-001"},
    ...
  }
}
```

##### `generate_topic_json(topic_doc, plan_id=None, subject_id=None)`
Generate topic JSON with lesson list.

**Features:**
- Includes parent breadcrumb (unit_id, track_id, subject_id)
- Access control information
- Lessons are shared across plans via `lesson_url` pointers
- Stage count for each lesson

**Returns:** Topic data or `None` if hidden

##### `generate_lesson_json_shared(lesson_doc)`
Generate shared lesson JSON with stages, NO access/parent blocks.

**Features:**
- Plan-agnostic content that can be referenced by multiple topics
- Contains only content (stages) and navigation information
- No plan-specific access control or parent information
- Allows lessons to be shared and cached across plans

**Returns:** Lesson data conforming to lesson.schema.json

##### `get_content_paths_for_plan(plan_name)`
Generate all file paths that need to be generated for a plan (non-atomic).

**Returns:** Dictionary of `{path: data}` for all CDN files

##### `get_atomic_content_paths_for_plan(plan_name)`
Get all atomic file paths for a plan.

**Returns:**
```python
{
  "manifest": "plans/{plan_name}/manifest.json",
  "hierarchies": ["plans/{plan_name}/{subj}_h.json", ...],
  "bitmaps": ["plans/{plan_name}/{subj}_b.json", ...],
  "topics": ["plans/{plan_name}/{t}.json", ...],
  "lessons": ["lessons/{l}.json", ...]
}
```

#### Change Tracker (`memora/services/cdn_export/change_tracker.py`)

Tracks content changes and queues plans for CDN rebuild.

##### `add_plan_to_queue(plan_id)`
Add plan to rebuild queue (idempotent via Set).

**Features:**
- Checks threshold and triggers immediate processing if needed
- Redis SET prevents duplicate queue entries

##### `check_and_trigger_immediate_processing()`
Check if queue size exceeds threshold and trigger immediate processing.

**Threshold:** Default 50 plans (configurable via CDN Settings)

##### `get_pending_plans(max_count=50)`
Pop up to max_count plans from queue.

**Fallback:** MariaDB if Redis fails

##### `add_plan_to_fallback_queue(plan_id)`
Fallback when Redis unavailable - adds to CDN Sync Log table.

##### `acquire_lock(plan_id, ttl_seconds=300)`
Acquire exclusive lock for plan build.

**TTL:** 5 minutes (default)

**Returns:** `bool` - True if lock acquired

##### `release_lock(plan_id)`
Release plan build lock.

##### `move_to_dead_letter(plan_id, error_msg)`
Move failed plan to dead-letter queue.

##### Document Event Handlers
- `on_subject_update`, `on_subject_delete`, `on_subject_restore`
- `on_track_update`, `on_track_delete`, `on_track_restore`
- `on_unit_update`, `on_unit_delete`, `on_unit_restore`
- `on_topic_update`, `on_topic_delete`, `on_topic_restore`
- `on_lesson_update`, `on_lesson_delete`, `on_lesson_restore`
- `on_lesson_stage_update`, `on_lesson_stage_delete`, `on_lesson_stage_restore`
- `on_plan_update`, `on_plan_delete`
- `on_override_update`, `on_override_delete`

#### CDN Uploader (`memora/services/cdn_export/cdn_uploader.py`)

Handles S3/Cloudflare R2 upload operations.

##### `get_cdn_client(settings)`
Get S3-compatible client for either AWS S3 or Cloudflare R2.

**Returns:** Boto3 S3 client with retry configuration

##### `test_connection()`
Test connection to CDN and bucket.

**Returns:**
```python
{'status': 'success', 'bucket': 'memora-content'}
```

##### `purge_cdn_cache(zone_id, api_token, file_urls)`
Purge specific files from Cloudflare cache.

**Limit:** Max 30 URLs per request (Cloudflare API constraint)

**Returns:** Cloudflare API response JSON

##### `generate_signed_url(client, bucket, key, expiry_seconds=14400)`
Generate 4-hour signed URL for sensitive content.

**Use Case:** Video content protection

**Returns:** Pre-signed S3/R2 URL

##### `upload_json(client, bucket, key, data)`
Upload JSON with proper content type and cache control.

**Cache Control:** `public, max-age=300` (5 min cache, invalidated on update)

**Returns:** `(success, error_message, etag)`

##### `upload_json_from_file(client, bucket, key, file_path)`
Upload JSON from local file path with proper content type and cache control.

**Returns:** `(success, error_message, etag)`

##### `delete_json(client, bucket, key)`
Delete a JSON file from CDN.

##### `delete_folder(client, bucket, prefix)`
Delete all objects with a given prefix (folder-like structure).

**Batch Size:** Max 1000 objects per delete request

**Returns:** `(success_count, error_count, errors)`

##### `upload_plan_files(client, bucket, plan_name, files_data)`
Upload all files for a plan and return uploaded URLs for cache purging.

**Returns:** `(uploaded_urls, errors)`

##### `upload_plan_files_from_local(client, bucket, plan_name, files_info)`
Upload files from local storage for a plan and return upload results.

**Returns:** `(uploaded_urls, upload_results, errors)`

##### `get_cdn_base_url(settings)`
Get base URL for CDN content.

**Fallback:** Constructs URL from bucket and endpoint if CDN base URL not set

##### `delete_plan_folder(settings, plan_id)`
Delete entire plan folder from CDN.

**Returns:** `(success_count, error_count, errors)`

#### Dependency Resolver (`memora/services/cdn_export/dependency_resolver.py`)

Resolves content dependencies to identify affected plans.

##### `get_affected_plan_ids(doctype, docname)`
Given a doctype and docname, find all Academic Plans that need rebuilding.

**Flow:**
1. Walk up content hierarchy (Lesson → Topic → Unit → Track → Subject)
2. Find plans that reference the document
3. Prevent infinite loops with processed_docs tracking

**Hierarchy:**
```
Memora Lesson Stage → Memora Lesson → Memora Topic → Memora Unit → Memora Track → Memora Subject → Memora Academic Plan
```

**Returns:** List of plan document names that need rebuilding

##### `get_direct_plans_for_content(doctype, docname)`
Get Academic Plans that directly reference given content document.

**Faster than:** Full hierarchy traversal for direct relationships

**Returns:** List of plan document names

#### Access Calculator (`memora/services/cdn_export/access_calculator.py`)

Calculates access levels with inheritance and override application.

##### `apply_plan_overrides(plan_id)`
Load and index plan-specific overrides for fast lookup.

**Returns:** Dictionary `{node_name: {action, fields}}`

##### `calculate_access_level(node, parent_access=None, plan_overrides=None)`
Calculate access level with inheritance and override application.

**Access Level Hierarchy:**
1. Plan-specific overrides (Hide, Set Free, Set Sold Separately)
2. is_free_preview flag
3. required_item (paid)
4. Parent access level (inheritance)
5. is_public flag
6. Default: authenticated

**Access Levels:**
- `public` - No authentication required
- `authenticated` - Login required
- `free_preview` - Free to view, enrollment required for full access
- `paid` - Purchase required
- `None` - Hidden (not included in JSON)

**Returns:** `str` or `None` - Access level or None if hidden

##### `calculate_linear_mode(node, plan_overrides=None)`
Calculate is_linear flag with override application.

**Linear Mode Hierarchy:**
1. Plan-specific overrides (Set Linear)
2. is_linear flag on node
3. Default: False (non-linear navigation)

**Returns:** `bool` - True if linear mode, False if non-linear

#### Local Storage (`memora/services/cdn_export/local_storage.py`)

Atomic file writes with .tmp staging and hash verification.

##### `write_content_file(path, data)`
Write content file atomically.

**Process:**
1. Write to `path.tmp`
2. Hash the file
3. Rename from `.tmp` to final path (atomic)
4. Update hash registry

**Returns:** `(success, error_message)`

##### `read_content_file(path)`
Read content file from local storage.

##### `get_file_hash(path)`
Calculate MD5 hash of a file.

##### `get_local_base_path()`
Get base path for local content storage.

**Default:** `/sites/{site_name}/public/memora_content/`

##### `delete_content_file(path)`
Delete content file atomically.

#### Search Indexer (`memora/services/cdn_export/search_indexer.py`)

Generates search indexes for content discovery.

##### `generate_search_index(plan_name)`
Generate master search index for a plan.

**Features:**
- Shard-based indexing for large plans
- Full-text searchable fields (title, description)
- Access level filtering

**Returns:**
```python
{
  "plan_id": "PLAN-001",
  "total_items": 500,
  "is_sharded": True,
  "shards": [{"subject_id": "SUBJ-001", "shard_url": "plans/PLAN-001/search/SUBJ-001.json"}]
}
```

##### `generate_subject_shard(plan_name, subject_id)`
Generate search shard for a specific subject.

**SHARD_THRESHOLD:** 100 items per shard

#### Health Checker (`memora/services/cdn_export/health_checker.py`)

Monitors CDN export health and performance.

##### `hourly_health_check()`
Hourly health check of CDN export system.

**Checks:**
- Queue depth and age
- Recent failure rates
- CDN connectivity

##### `daily_full_scan()`
Daily comprehensive scan of all plans.

**Purpose:** Identify stale content or synchronization issues

##### `send_sync_failure_alert(sync_log_name)`
Send alert to system managers for critical failures.

#### URL Resolver (`memora/services/cdn_export/url_resolver.py`)

Resolves content URLs for CDN references.

##### `get_content_url(path)`
Generate full CDN URL for a content path.

**Returns:** Full CDN URL (e.g., `https://cdn.example.com/plans/PLAN-001/manifest.json`)

### Progress Engine Services

#### Bitmap Manager (`memora/services/progress_engine/bitmap_manager.py`)

Redis bitmap operations for lesson completion tracking.

##### `get_redis_key(player_id, subject_id)`
Generate Redis key for player-subject progress bitmap.

**Pattern:** `user_prog:{player_id}:{subject_id}`

##### `set_bit(bitmap_bytes, bit_index)`
Set a specific bit in the bitmap.

**Args:**
- `bitmap_bytes` (bytes): Current bitmap
- `bit_index` (int): Index of bit to set

**Returns:** Updated bitmap as bytes

##### `check_bit(bitmap_bytes, bit_index)`
Check if a specific bit is set in the bitmap.

**Returns:** `bool` - True if bit is set, False otherwise

##### `get_bitmap(player_id, subject_id)`
Get progress bitmap for a player-subject pair from Redis.

**Features:**
- Automatic cache warming from MariaDB on cache miss
- LRU caching for frequently accessed bitmaps

**Returns:** Bitmap as bytes (empty bytes if not found)

##### `update_bitmap(player_id, subject_id, bit_index)`
Update a lesson's completion status in the bitmap.

**Side Effects:**
- Marks key as dirty for sync to MariaDB

**Returns:** Updated bitmap as bytes

##### `mark_dirty(player_id, subject_id)`
Mark a player-subject progress key as dirty (pending sync to MariaDB).

##### `encode_bitmap_for_mariadb(bitmap_bytes)`
Encode bitmap bytes for storage in MariaDB (Base64).

**Returns:** Base64-encoded string

##### `decode_bitmap_from_mariadb(encoded)`
Decode bitmap from MariaDB Base64 string to bytes.

**Returns:** Bitmap as bytes (empty bytes if empty string)

##### `get_best_hearts_key(player_id, subject_id)`
Generate Redis key for best hearts data.

**Pattern:** `best_hearts:{player_id}:{subject_id}`

##### `get_best_hearts(player_id, subject_id)`
Get best hearts data from Redis.

**Returns:** Dictionary mapping lesson_id → best hearts (empty dict if not found)

##### `set_best_hearts(player_id, subject_id, best_hearts_data)`
Set best hearts data in Redis.

**Side Effects:** Marks key as dirty for sync

##### `update_best_hearts(player_id, subject_id, lesson_id, hearts)`
Update best hearts for a specific lesson in Redis.

**Returns:** Updated best_hearts_data dictionary

#### Structure Loader (`memora/services/progress_engine/structure_loader.py`)

Handles loading and caching of subject structure JSON files.

##### `get_subject_json_path(subject_id)`
Get file path for a subject's JSON structure.

**Default:** `/sites/{site}/public/memora_content/{subject_id}.json`

**Raises:** FileNotFoundError if JSON file doesn't exist

##### `load_subject_structure(subject_id)`
Load subject structure JSON from file with LRU caching.

**Cache:** 32 subjects by default (LRU eviction)

**Returns:** Dictionary containing subject structure

##### `clear_cache()`
Clear LRU cache for subject structures.

**Use Case:** When subject structure files are updated

##### `validate_structure(structure)`
Validate that subject structure has required fields.

**Required Fields:** `id`, `title`, `is_linear`, `tracks`

**Returns:** True if valid, raises ValueError otherwise

##### `get_lesson_bit_index(structure, lesson_id)`
Get the bit_index for a lesson from structure.

**Returns:** The bit_index for lesson

**Raises:** ValueError if lesson not found in structure

##### `count_total_lessons(structure)`
Count total number of lessons in subject structure.

**Returns:** Total number of lessons

##### `get_lesson_ids(structure)`
Get all lesson IDs from structure.

**Returns:** List of lesson IDs

#### Unlock Calculator (`memora/services/progress_engine/unlock_calculator.py`)

Computes unlock states (locked/unlocked/passed) for all nodes.

##### `compute_node_states(structure, bitmap, player_id=None, subject_id=None)`
Compute unlock states for all nodes in subject structure.

**Two-Pass Algorithm:**
1. Bottom-up: Compute child lesson states and container states
2. Top-down: Apply unlock rules based on parent is_linear flags

**Returns:** Structure with status and unlock_state populated for all nodes

**Node States:**
- `passed` - Lesson/Container fully completed
- `not_passed` - Lesson not yet completed
- `unlocked` - Available to play
- `locked` - Not yet available

##### `compute_container_status(node, children, structure)`
Compute container status based on children.

**Logic:** Container is 'passed' only if ALL children are 'passed'. Otherwise, 'unlocked'.

**Returns:** Container status: 'passed' or 'unlocked'

##### `flatten_nodes(structure, node_type=None)`
Flatten structure to list of nodes.

**Args:**
- `structure` (dict): The subject structure dictionary
- `node_type` (str, optional): Optional filter by node type

**Returns:** Flattened list of nodes

##### `find_node_by_id(structure, node_id)`
Find a node by ID in structure.

**Returns:** The node dictionary or None if not found

#### Progress Computer (`memora/services/progress_engine/progress_computer.py`)

Orchestrates computation of progress.

##### `compute_progress(subject_id)`
Compute full progress for a subject.

**Orchestration Flow:**
1. Load subject structure from JSON file
2. Get player bitmap from Redis (with MariaDB fallback)
3. Compute node states (passed/unlocked/locked)
4. Calculate completion percentage
5. Find next lesson suggestion
6. Get total XP earned

**Returns:**
```python
{
  "subject_id": "SUBJ-001",
  "root": {...},  # Root progress node (subject)
  "completion_percentage": 45.5,
  "total_xp_earned": 500,
  "suggested_next_lesson_id": "LESSON-010",
  "total_lessons": 100,
  "passed_lessons": 45
}
```

##### `_load_and_validate_structure(subject_id)`
Load and validate subject structure.

**Raises:** FileNotFoundError if subject JSON file doesn't exist

##### `_ensure_structure_has_children(structure)`
Ensure structure has 'children' key for traversal.

**Transformation:** Converts 'tracks' → 'children', 'units' → 'children', etc.

##### `_count_passed_lessons(structure)`
Count number of passed lessons in structure.

**Returns:** Number of passed lessons

##### `_calculate_completion_percentage(passed_lessons, total_lessons)`
Calculate completion percentage.

**Returns:** Completion percentage (0-100)

##### `_get_total_xp_earned(player_id, subject_id)`
Get total XP earned in subject from Memora Structure Progress document.

**Returns:** Total XP earned

##### `find_next_lesson(structure)`
Find next unlocked (not passed) lesson.

**Algorithm:** Traverses structure in tree order, returns first lesson that is 'unlocked'

**Returns:** Lesson ID or None if all lessons are passed

#### XP Calculator (`memora/services/progress_engine/xp_calculator.py`)

Calculates XP awards based on hearts and bonuses.

##### `calculate_xp(lesson_id, hearts, is_first_completion, best_hearts_data, base_xp)`
Calculate XP for lesson completion with bonuses.

**Formula:**
```
base_xp = 10 (or lesson.base_xp)
heart_multiplier = hearts * 2
total_xp = base_xp + heart_multiplier

Bonuses:
- First completion bonus: +5 XP
- Record-breaking bonus: +10 XP
```

**Returns:**
```python
{
  "xp_earned": 35,
  "base_xp": 10,
  "heart_bonus": 10,
  "first_completion_bonus": 5,
  "record_break_bonus": 10,
  "is_new_record": True,
  "best_hearts_data": {...}
}
```

#### Cache Warmer (`memora/services/progress_engine/cache_warmer.py`)

Warms Redis cache from MariaDB on cache miss.

##### `warm_on_cache_miss(player_id, subject_id)`
Warm bitmap cache from MariaDB on cache miss.

**Process:**
1. Load Memora Structure Progress document
2. Decode Base64 bitmap
3. Store in Redis
4. Update last_synced_at timestamp

**Returns:** Bitmap as bytes

##### `warm_best_hearts_on_cache_miss(player_id, subject_id)`
Warm best hearts cache from MariaDB on cache miss.

**Returns:** Best hearts data dictionary

#### Snapshot Syncer (`memora/services/progress_engine/snapshot_syncer.py`)

Synchronizes Redis dirty keys to MariaDB.

##### `sync_pending_bitmaps()`
Sync all dirty bitmap keys to MariaDB.

**Process:**
1. Get all dirty keys from Redis SET
2. Batch update Memora Structure Progress documents
3. Remove synced keys from dirty set

**Batch Size:** 100 documents per batch

**Performance:** <2min for 10k players

##### `sync_best_hearts_with_bitmap(player_id, subject_id, best_hearts_data)`
Sync best hearts data for a specific player-subject pair.

**Side Effects:** Updates Memora Structure Progress document

#### Migration (`memora/services/progress_engine/migration.py`)

Handles data migrations for progress engine.

##### `migrate_to_bitmap_structure()`
Migrate legacy progress tracking to bitmap-based system.

**Use Case:** One-time migration from old schema

---

## DocTypes

### Memora Player Profile (`memora/memora/doctype/memora_player_profile/`)

Central identity DocType linking Frappe User to player-specific educational context.

**Key Features:**
- 1:1 relationship with Frappe User (enforced by unique user field)
- Device authorization table with 2-device limit
- Auto-authorization of first device on profile creation
- Automatic Redis cache synchronization on device changes
- Auto-creation of Player Wallet on profile creation

**Fields:**
- `user` (Link): Frappe User
- `authorized_devices` (Table): Child table of Memora Authorized Device
  - `device_id` (Data): UUID v4
  - `device_name` (Data): Human-readable name
  - `added_on` (Datetime): Timestamp of addition

**Methods:**
- `validate_device_limit()` - Enforce max 2 devices
- `validate_unique_devices()` - Ensure unique device IDs
- `auto_authorize_first_device()` - Auto-authorize first device on creation
- `create_player_wallet()` - Create associated wallet
- `sync_device_cache()` - Sync to Redis on updates

### Memora Player Wallet (`memora/memora/doctype/memora_player_wallet/`)

Persistent storage for player XP and streak data.

**Key Features:**
- 1:1 relationship with Player Profile
- Non-negative constraints on XP and streak
- Automatic Redis cache population on creation
- Queued for batch sync on updates (15-minute intervals)
- Cache cleanup on deletion

**Fields:**
- `player` (Link): Memora Player Profile
- `total_xp` (Int): Cumulative XP earned (non-negative)
- `current_streak` (Int): Current consecutive day streak (non-negative)
- `last_success_date` (Date): Date of last lesson completion with hearts > 0
- `last_played_at` (Datetime): Timestamp of last player interaction

**Methods:**
- `validate_non_negative_xp()` - Enforce non-negative XP
- `validate_non_negative_streak()` - Reset to 0 if negative
- `validate_date_not_in_future()` - Ensure last_success_date not in future
- `populate_wallet_cache()` - Populate Redis cache on insert
- `cleanup_wallet_cache()` - Remove from Redis on delete

**Data Flow:**
- Write: Redis (immediate) → DB (15-min batch sync)
- Read: Redis (cache-first) → DB (fallback on cache miss)
- Sync: Pending wallet queue → Bulk SQL update (500-player chunks)

### Memora Authorized Device (`memora/memora/doctype/memora_authorized_device/`)

Child table for tracking authorized devices.

**Fields:**
- `device_id` (Data): UUID v4 device identifier
- `device_name` (Data): Human-readable device name
- `added_on` (Datetime): Timestamp of device addition

### Memora Structure Progress (`memora/memora/doctype/memora_structure_progress/`)

Tracks player progress through subject structure.

**Fields:**
- `player` (Link): Frappe User
- `subject` (Link): Memora Subject
- `progress_bitmap` (Long Text): Base64-encoded bitmap of completed lessons
- `total_xp_earned` (Int): Total XP earned in this subject
- `completion_percentage` (Float): Percentage of lessons completed (0-100)
- `last_synced_at` (Datetime): Last time bitmap was synced to MariaDB
- `best_hearts` (Long Text): JSON data of best hearts per lesson

### Content Hierarchy DocTypes

#### Memora Academic Plan (`memora/memora/doctype/memora_academic_plan/`)

Top-level container for educational content.

**Fields:**
- `title` (Data): Plan name
- `season` (Link): Memora Season
- `grade` (Link): Memora Grade
- `stream` (Link): Memora Stream
- `is_published` (Check): Publication status

#### Memora Subject (`memora/memora/doctype/memora_subject/`)

Subject container with tracks.

**Fields:**
- `title` (Data): Subject name
- `description` (Text): Subject description
- `image` (Attach): Subject image
- `color_code` (Data): Color for UI
- `is_published` (Check): Publication status
- `is_linear` (Check): Linear navigation mode

#### Memora Track (`memora/memora/doctype/memora_track/`)

Track container with units.

**Fields:**
- `parent_subject` (Link): Memora Subject
- `title` (Data): Track name
- `description` (Text): Track description
- `is_published` (Check): Publication status
- `is_linear` (Check): Linear navigation mode

#### Memora Unit (`memora/memora/doctype/memora_unit/`)

Unit container with topics.

**Fields:**
- `parent_track` (Link): Memora Track
- `title` (Data): Unit name
- `description` (Text): Unit description
- `is_published` (Check): Publication status

#### Memora Topic (`memora/memora/doctype/memora_topic/`)

Topic container with lessons.

**Fields:**
- `parent_unit` (Link): Memora Unit
- `title` (Data): Topic name
- `description` (Text): Topic description
- `is_published` (Check): Publication status

#### Memora Lesson (`memora/memora/doctype/memora_lesson/`)

Leaf node with lesson stages.

**Fields:**
- `parent_topic` (Link): Memora Topic
- `title` (Data): Lesson name
- `description` (Text): Lesson description
- `bit_index` (Int): Index in subject bitmap
- `base_xp` (Int): Base XP value
- `is_published` (Check): Publication status

#### Memora Lesson Stage (`memora/memora/doctype/memora_lesson_stage/`)

Child table with lesson stage configurations.

**Fields:**
- `parent` (Link): Memora Lesson
- `title` (Data): Stage title
- `type` (Data): Stage type (Video, Text, Quiz, etc.)
- `config` (Long Text): JSON configuration
- `idx` (Int): Sort order
- `weight` (Int): XP weight
- `target_time` (Int): Target completion time (seconds)
- `is_skippable` (Check): Can be skipped

#### Memora Plan Override (`memora/memora/doctype/memora_plan_override/`)

Plan-specific content overrides.

**Fields:**
- `parent` (Link): Memora Academic Plan
- `target_name` (Data): Content document name
- `action` (Select): Hide, Set Free, Set Sold Separately, Set Access Level, Set Linear
- `override_value` (Data): Override value

#### Memora Plan Subject (`memora/memora/doctype/memora_plan_subject/`)

Child table linking plans to subjects.

**Fields:**
- `parent` (Link): Memora Academic Plan
- `subject` (Link): Memora Subject

### CDN Settings DocTypes

#### CDN Settings (`memora/memora/doctype/cdn_settings/`)

Configuration for CDN export.

**Fields:**
- `enabled` (Check): Master switch
- `endpoint_url` (Data): S3/R2 endpoint
- `access_key` (Password): AWS/R2 access key
- `secret_key` (Password): AWS/R2 secret key
- `bucket_name` (Data): Bucket name
- `cdn_base_url` (Data): CDN base URL
- `cloudflare_zone_id` (Data): Cloudflare zone ID
- `cloudflare_api_token` (Password): Cloudflare API token
- `signed_url_expiry_hours` (Int): Signed URL expiry
- `batch_threshold` (Int): Immediate processing threshold
- `local_fallback_mode` (Check): Local storage fallback

#### CDN Sync Log (`memora/memora/doctype/cdn_sync_log/`)

Log of CDN sync operations.

**Fields:**
- `plan_id` (Data): Plan identifier
- `status` (Select): Queued, Processing, Success, Failed, Dead Letter
- `started_at` (Datetime): Start time
- `completed_at` (Datetime): Completion time
- `retry_count` (Int): Number of retries
- `next_retry_at` (Datetime): Next retry time
- `error_message` (Long Text): Error details
- `is_fallback` (Check): MariaDB fallback flag
- `files_uploaded` (Int): Number of files
- `sync_verified` (Check): Hash verification status

### Interaction Tracking DocTypes

#### Memora Interaction Log (`memora/memora/doctype/memora_interaction_log/`)

Logs all player interactions.

**Fields:**
- `player` (Link): Frappe User
- `interaction_type` (Data): Type of interaction (lesson_completion, login, logout)
- `reference_id` (Data): Related document ID
- `interaction_data` (JSON): Interaction details
- `created_at` (Datetime): Timestamp

---

## Utilities

### Redis Keys (`memora/utils/redis_keys.py`)

Redis key pattern constants for Player Core feature.

**Key Patterns:**
- `player:{user_id}:devices` - Authorized devices SET
- `active_session:{user_id}` - Active session STRING
- `wallet:{user_id}` - Wallet HASH
- `pending_wallet_sync` - Global pending queue SET
- `rate_limit:{user_id}:{function_name}` - Rate limit STRING with TTL
- `last_played_at_synced:{user_id}` - Last played throttle STRING with TTL

**Functions:**
- `get_player_devices_key(user_id)` - Get device key
- `get_active_session_key(user_id)` - Get session key
- `get_wallet_key(user_id)` - Get wallet key
- `get_rate_limit_key(user_id, function_name)` - Get rate limit key
- `get_pending_wallet_sync_key()` - Get pending sync queue key
- `get_last_played_at_synced_key(user_id)` - Get throttle key

### Diagnostics (`memora/utils/diagnostics.py`)

Diagnostic and validation utilities.

**Functions:**
- `validate_schema(doctype)` - Validate DocType schema against database
- `diagnose_query_failure(doctype)` - Identify failing SQL queries
- `get_table_info(doctype)` - Get table metadata
- `check_foreign_keys(doctype)` - Check foreign key constraints
- `validate_indexes(doctype)` - Check index configuration

---

## Hooks

### Document Events

All CDN Content Export document event handlers registered in `hooks.py`:

**Subject Content Hierarchy:**
- `Memora Subject`: on_update, on_trash, after_delete, on_restore

**Track Content Hierarchy:**
- `Memora Track`: on_update, on_trash, after_delete, on_restore

**Unit Content Hierarchy:**
- `Memora Unit`: on_update, on_trash, after_delete, on_restore

**Topic Content Hierarchy:**
- `Memora Topic`: on_update, on_trash, after_delete, on_restore

**Lesson Content (Leaf Node):**
- `Memora Lesson`: on_update, on_trash, after_delete, on_restore

**Lesson Stage Content:**
- `Memora Lesson Stage`: on_update, on_trash, after_delete, on_restore

**Plan Management:**
- `Memora Academic Plan`: on_update, on_trash, after_delete

**Plan Access Overrides:**
- `Memora Plan Override`: on_update, on_trash

### Scheduled Tasks

**Hourly:**
- `process_pending_plans()` - Process CDN export queue (max 10 plans per run)
- `hourly_health_check()` - CDN export health monitoring

**Daily:**
- `daily_full_scan()` - Comprehensive plan scan for synchronization issues

**Cron (`*/15 * * * *`):**
- `sync_pending_wallets()` - Wallet batch sync (every 15 minutes)

**All:**
- `sync_pending_bitmaps()` - Progress bitmap sync (all scheduler runs)

---

## Performance Targets

### Player Core
- Device/session verification: <2ms (Redis)
- XP display latency: <1s (cache-first)
- Session termination: <2s
- Batch sync: <5min for 50k players (90%+ DB write reduction)
- Scale: Support 10k concurrent students

### CDN Export
- JSON generation: <10s for typical plan (100 lessons)
- Upload to CDN: <30s for typical plan
- Cache purge: <5s for Cloudflare
- Queue processing: 50 plans/hour (default)
- Recovery time: <1h from dead-letter queue

### Progress Engine
- Progress computation: <100ms (cache hit)
- Bitmap operations: <2ms (Redis)
- Unlock calculation: <50ms (in-memory)
- Cache warm on miss: <200ms (MariaDB + Redis)
- Scale: Support 10k concurrent progress queries

---

## Error Handling

### CDN Export Retry Logic

**Exponential Backoff Schedule:**
1. 30 seconds delay
2. 1 minute delay
3. 2 minutes delay
4. 5 minutes delay
5. 15 minutes delay

**Dead Letter Queue:**
- After 5 failed retries, plan moves to dead-letter queue
- Requires manual intervention
- API endpoint: `/api/method/memora.api.cdn_admin.get_queue_status`

### Wallet Sync Error Handling

**Chunk-Level Errors:**
- Logged but don't crash scheduler
- Failed chunks re-added to pending queue

**Redis Failures:**
- Automatic fallback to MariaDB CDN Sync Log
- Queue continues processing
- Error logged for monitoring

---

## Security Features

### Device Authorization
- UUID v4 device IDs (client-generated)
- Max 2 devices per student
- Admin-only device management
- Redis-backed O(1) authorization checks

### Session Management
- Single active session enforcement
- Previous session invalidated on new login
- Persistent sessions (no TTL, explicit invalidation only)
- Session metadata for debugging

### Rate Limiting
- Per-user, per-endpoint limits
- Redis INCR with TTL for atomic counting
- X-RateLimit-* response headers
- Configurable limits via decorators

### Access Control
- Enrollment verification before progress access
- Plan-specific content overrides
- Hierarchical access level inheritance
- Public/authenticated/free_preview/paid levels

### Audit Logging
- All security events logged
- Device/session/wallet changes tracked
- Login/logout events recorded
- Rate limit violations logged

---

## Monitoring

### CDN Export Dashboard
- **Location:** Memora > CDN Export Status
- **Metrics:** Queue size, recent failures, dead-letter count
- **Logs:** Memora > CDN Sync Log

### Player Dashboard
- **Location:** Memora > Player Profiles / Player Wallets
- **Metrics:** Total players, device counts, XP distribution, streaks

### Error Logs
- **Location:** Frappe > Error Log
- **Key Logs:** "CDN Plan Rebuild Error", "Wallet Sync Critical Error", "Security Event"

---

## Development Notes

### Running Locally
```bash
cd /home/corex/aurevia-bench/apps/memora
# Install dependencies
pip install -r requirements.txt

# Run Frappe bench
bench start

# Run tests
pytest
```

### Redis Key Patterns
- Use `get_*_key()` utility functions from `redis_keys.py`
- Follow namespace format: `{type}:{identifier}:{subkey}`
- Use appropriate data types: SET, STRING, HASH

### CDN File Structure
```
/
├── plans/
│   ├── {plan_id}/
│   │   ├── manifest.json
│   │   ├── search_index.json
│   │   ├── search/
│   │   │   ├── {subject_id}.json
│   │   ├── {subject_id}_h.json (hierarchy)
│   │   └── {subject_id}_b.json (bitmap)
│   └── ...
└── lessons/
    └── {lesson_id}.json (shared)
```

### Atomic File Writes
1. Write to `{path}.tmp`
2. Calculate hash
3. Rename from `.tmp` to final path (atomic)
4. Update hash registry

### Bitmap Operations
- Use `set_bit()` and `check_bit()` utilities
- Always mark dirty after updates
- Warm cache on misses from MariaDB

---

## Troubleshooting

### CDN Export Issues
1. Check CDN Settings are configured
2. Verify Redis queue status: `frappe.cache().scard("cdn_export:pending_plans")`
3. Review CDN Sync Log for errors
4. Check dead-letter queue: `frappe.cache().hgetall("cdn_export:dead_letter")`

### Player Wallet Sync Issues
1. Verify Redis wallet data: `frappe.cache().hgetall("wallet:{user_id}")`
2. Check pending sync queue: `frappe.cache().smembers("pending_wallet_sync")`
3. Review Memora Player Wallet DocType
4. Check for negative values (validation should reset to 0)

### Progress Tracking Issues
1. Verify bitmap exists: `frappe.cache().get("user_prog:{player_id}:{subject_id}")`
2. Check subject JSON file exists locally
3. Validate bit_index assignments in subject structure
4. Review Memora Structure Progress document

### Session/Device Issues
1. Check device authorization: `frappe.cache().sismember("player:{user_id}:devices", device_id)`
2. Verify active session: `frappe.cache().get("active_session:{user_id}")`
3. Review authorized_devices table in Player Profile
4. Check security event logs for login failures

---

## Best Practices

### Performance
- Always read from cache first, fallback to DB
- Use bulk operations for batch updates
- Leverage Redis for fast counters and bitmaps
- Implement proper TTL for ephemeral data

### Reliability
- Use atomic operations (Redis SET, SADD)
- Implement exponential backoff for retries
- Queue failed operations for retry
- Log all errors with context

### Security
- Validate all user inputs
- Enforce device authorization on authenticated endpoints
- Use rate limiting on public APIs
- Log all security-relevant events

### Maintainability
- Use utility functions for common operations
- Document all retry schedules and thresholds
- Add schema validation for JSON generation
- Implement proper error handling with fallbacks

---

*Last Updated: 2026-01-27*
*Version: 1.0*
