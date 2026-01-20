# Memora API Package

This package reorganizes the monolithic `api.py` file (1897 lines) into a modular package structure with domain-specific modules.

## Purpose

The reorganization improves code navigation and maintainability while preserving all existing functionality with zero breaking changes.

## Module Organization

### Core Files

- **`__init__.py`** - Public API gateway that re-exports all `@frappe.whitelist()` functions to maintain backward compatibility
- **`utils.py`** - Shared utility functions used across multiple domain modules

### Domain Modules

Each domain module contains logically related API functions:

| Module | Purpose | Public Functions |
|---------|-----------|-----------------|
| `subjects.py` | Subjects & Tracks domain | `get_subjects()`, `get_my_subjects()`, `get_game_tracks()` |
| `map_engine.py` | Map Engine domain | `get_map_data()`, `get_topic_details()` | `get_track_details`|
| `sessions.py` | Session & Gameplay domain | `submit_session()`, `get_lesson_details()` |
| `srs.py` | SRS/Memory algorithms + Admin endpoints | `get_cache_status()`, `rebuild_season_cache()`, `archive_season()`, `get_archive_status()`, `delete_eligible_archived_records()` |
| `reviews.py` | Review Session domain | `get_review_session()`, `submit_review_session()` |
| `profile.py` | Profile domain | `get_player_profile()`, `get_full_profile_stats()` |
| `quests.py` | Daily Quests domain | `get_daily_quests()` |
| `leaderboard.py` | Leaderboard domain | `get_leaderboard()` |
| `onboarding.py` | Onboarding domain | `get_academic_masters()`, `set_academic_profile()` |
| `store.py` | Store domain | `get_store_items()`, `request_purchase()` |

## SRS Scalability Features

The SRS (Spaced Repetition System) module has been enhanced with high-performance caching and scalability features to support millions of student records with sub-100ms response times.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Application                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Layer (reviews.py)                      │
│  - get_review_session()      - submit_review_session()       │
└────────┬────────────────────────────────┬───────────────────┘
         │                                │
         ▼                                ▼
┌──────────────────────┐      ┌──────────────────────────────┐
│   Redis Cache Layer  │      │   PostgreSQL Database        │
│   (SRSRedisManager)  │      │   (Player Memory Tracker)    │
│                      │      │                              │
│  - <100ms reads     │      │  - Partitioned by season     │
│  - ZADD/ZRANGE ops  │      │  - Composite indexes         │
│  - Safe Mode fallback│     │  - Async persistence         │
└──────────┬───────────┘      └──────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│              Background Services                            │
│  - SRSArchiver (season archival)                            │
│  - SRSReconciliation (cache consistency)                     │
│  - SRSPersistence (async DB writes)                         │
└─────────────────────────────────────────────────────────────┘
```

### Enhanced API Endpoints

#### Student-Facing Endpoints (reviews.py)

**`get_review_session(subject=None, topic_id=None)`**
- **Performance**: <100ms response time via Redis cache
- **Features**:
  - Redis cache for instant due question retrieval
  - Safe Mode fallback with rate limiting (500 req/min global, 1 req/30s per user)
  - Lazy loading on cache miss
  - Subject and topic filtering support
  - Returns `is_degraded` flag to indicate Safe Mode status
- **Response**:
  ```json
  {
    "questions": [...],
    "is_degraded": false,
    "season": "2024-2025"
  }
  ```

**`submit_review_session(session_data)`**
- **Performance**: <500ms confirmation with async persistence
- **Features**:
  - Synchronous Redis update for instant confirmation
  - Asynchronous database persistence via background job
  - Returns `persistence_job_id` for tracking
  - Audit logging for all submitted reviews
- **Response**:
  ```json
  {
    "xp_earned": 120,
    "remaining_items": 45,
    "persistence_job_id": "job_12345"
  }
  ```

#### Admin Endpoints (srs.py)

**`get_cache_status()`**
- **Purpose**: Monitor Redis cache health and statistics
- **Returns**:
  ```json
  {
    "redis_connected": true,
    "is_safe_mode": false,
    "memory_used_mb": 245.67,
    "total_keys": 125000,
    "keys_by_season": {
      "2024-2025": 85000,
      "2023-2024": 40000
    }
  }
  ```
- **Permissions**: System Manager

**`rebuild_season_cache(season_name)`**
- **Purpose**: Trigger full cache rebuild for a season
- **Features**:
  - Runs as background job with progress tracking
  - Estimated record count provided
  - Requires System Manager role
- **Returns**:
  ```json
  {
    "status": "started",
    "job_id": "cache_rebuild_2024-2025_2024-01-20",
    "estimated_records": 85000
  }
  ```
- **Permissions**: System Manager

**`archive_season(season_name, confirm=False)`**
- **Purpose**: Archive season data to cold storage
- **Features**:
  - Requires explicit confirmation (`confirm=True`)
  - Copies records to Archived Memory Tracker
  - Deletes original records from active table
  - Clears Redis cache for archived season
  - Validates season is not active before archiving
- **Returns**:
  ```json
  {
    "success": true,
    "archived_count": 45000,
    "message": "Season archived successfully"
  }
  ```
- **Permissions**: System Manager

**`get_archive_status(season_name)`**
- **Purpose**: Get archive status for a season
- **Returns**:
  ```json
  {
    "active_records": 0,
    "archived_records": 45000,
    "eligible_for_deletion": 12000,
    "archived_at": "2024-01-15T10:30:00"
  }
  ```
- **Permissions**: Read access to Game Subscription Season

**`delete_eligible_archived_records(season_name=None, confirm=False)`**
- **Purpose**: Delete archived records marked for deletion
- **Features**:
  - Only deletes records older than 3 years
  - Requires explicit confirmation
  - Optional season filter
- **Returns**:
  ```json
  {
    "success": true,
    "deleted_count": 12000,
    "message": "Deleted 12,000 eligible records"
  }
  ```
- **Permissions**: System Manager

### Key Performance Features

1. **Redis Caching**
   - Sorted sets for due question scheduling (ZADD/ZRANGE)
   - Sub-100ms read response times
   - Automatic rehydration on cache miss
   - Memory-efficient storage with TTL

2. **Safe Mode**
   - Automatic fallback to database when Redis unavailable
   - Rate limiting to prevent database overload
   - Limited result sets (15 items max)
   - Indexed queries for performance

3. **Async Persistence**
   - Instant confirmation (<500ms) for review submissions
   - Background job queue for database writes
   - Retry logic with exponential backoff
   - Audit logging for compliance

4. **Database Partitioning**
   - LIST COLUMNS partitioning by season
   - Automatic partition creation for new seasons
   - Composite indexes for Safe Mode queries
   - Efficient archival and cleanup

5. **Cache Management**
   - Manual cache rebuild via admin endpoint
   - Daily reconciliation for consistency
   - Automatic cache cleanup on archival
   - Progress tracking for rebuild jobs

### Background Jobs

The following background jobs are registered in `memora/hooks.py`:

| Job | Frequency | Purpose |
|-----|-----------|---------|
| `process_auto_archive` | Daily | Automatically archive seasons marked for auto-archive |
| `flag_eligible_for_deletion` | Weekly | Flag archived records older than 3 years for deletion |
| `reconcile_cache_with_database` | Daily | Check cache consistency and auto-correct discrepancies |

### Data Flow Examples

**Retrieving Due Reviews (Normal Mode)**:
```
1. Client calls get_review_session()
2. API checks Redis connectivity
3. Redis returns due items via ZRANGEBYSCORE (<100ms)
4. API fetches full records from DB (indexed query)
5. Returns quiz cards to client
```

**Retrieving Due Reviews (Safe Mode)**:
```
1. Client calls get_review_session()
2. API detects Redis unavailable
3. API checks rate limits
4. API executes indexed DB query with LIMIT 15
5. Returns quiz cards with is_degraded=true
```

**Submitting Review Session**:
```
1. Client calls submit_review_session()
2. API updates Redis synchronously (ZADD)
3. API enqueues background job for DB persistence
4. API returns confirmation with job_id (<500ms)
5. Background job persists to DB with retry logic
```

### Service Layer Architecture

The implementation follows a clean service layer architecture:

```
memora/
├── api/
│   ├── reviews.py          # Student-facing endpoints
│   ├── srs.py              # Admin endpoints + SRS algorithms
│   └── utils.py            # SafeModeManager, rate limiting
└── services/
    ├── srs_redis_manager.py    # Redis operations
    ├── srs_persistence.py      # Async DB persistence
    ├── srs_archiver.py         # Season archival
    ├── srs_reconciliation.py   # Cache consistency
    └── partition_manager.py   # Database partitioning
```

## Import Patterns

### Public API Usage (Backward Compatible)

```python
# Old way (still works)
from memora.api import get_subjects, get_map_data

# New way (also works)
from memora.api import get_subjects, get_map_data
```

### Internal Module Imports

```python
# Import from utils (shared utilities)
from .utils import get_user_active_subscriptions, check_subscription_access

# Import from other domain modules (allowed dependencies)
from .srs import process_srs_batch
from .leaderboard import update_subject_progression

# Import from sibling packages
from ..ai_engine import get_ai_distractors
```

## Dependency Graph

```
                    ┌─────────────┐
                    │  __init__   │
                    └──────┬──────┘
                           │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
    │ subjects │        │map_engine│        │sessions │
    └────┬────┘        └────┬────┘        └────┬────┘
         │                     │                     │
         │                     │                  ┌───▼────┐
         │                     │                  │  srs    │
         │                     │                  └───┬────┘
         │                     │                      │
         │                  ┌───▼────┐      ┌───▼────┐
         │                  │ reviews │      │profile  │
         │                  └───┬────┘      └───┬────┘
         │                      │                  │
         │                      │              ┌───▼────┐
         │                      │              │ quests  │
         │                      │              └───┬────┘
         │                      │                  │
         │                  ┌───▼────┐      ┌───▼────┐
         │                  │leaderbd│      │onboard│
         │                  └───┬────┘      └───┬────┘
         │                      │                  │
         └──────────────────────┴──────────────────┴───▼────┐
                                                        │ store  │
                                                        └────────┘
```

## Key Rules

1. **All domain modules can import from `utils.py`**
2. **Domain modules should NOT import from other domain modules** (except for allowed dependencies)
3. **`__init__.py` imports from all domain modules** and re-exports public functions
4. **Allowed cross-module imports:**
   - `sessions.py` can import from `srs.py` and `leaderboard.py`
   - `reviews.py` can import from `srs.py` and `leaderboard.py`

## Module Size Guidelines

Each module file should not exceed 400 lines of code to maintain readability.

## Migration Notes

- The original `memora/api.py` file (1897 lines) can be deprecated after successful migration
- All existing tests should pass without modification (or with only import path updates)
- All API endpoints maintain their existing documentation in `specs/002-api-reorganization/contracts/api-openapi.yaml`

## Testing

To verify the reorganization works correctly:

1. Run existing test suite: `pytest memora/tests/`
2. Manually test all 15 API endpoints
3. Verify backward compatibility: test that code importing from `memora.api` still works
4. Test subscription access control across all modules
5. Test SRS memory tracking after session submission and review completion

## Success Criteria

- ✅ Developers can locate any API endpoint's source code within 30 seconds by navigating to the appropriate domain module
- ✅ 100% of existing API endpoints return identical responses before and after reorganization
- ✅ No duplicate function definitions exist across the reorganized module files
- ✅ Each module file contains no more than 400 lines of code
- ✅ All existing automated tests pass without modification (or with only import path updates)
- ✅ New developers can understand the API organization from file/folder names alone without reading documentation
