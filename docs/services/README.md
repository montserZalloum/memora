# Memora Services Documentation

Complete reference for all Memora business logic services.

## Table of Contents

- [Overview](#overview)
- [Service Architecture](#service-architecture)
- [SRS Services](#srs-services)
  - [SRS Redis Manager](#srs-redis-manager)
  - [SRS Persistence](#srs-persistence)
  - [SRS Archiver](#srs-archiver)
  - [SRS Reconciliation](#srs-reconciliation)
- [Infrastructure Services](#infrastructure-services)
  - [Partition Manager](#partition-manager)
- [Service Best Practices](#service-best-practices)

## Overview

Services in Memora encapsulate business logic separate from API endpoints and DocTypes. They handle complex operations like SRS algorithms, caching, archival, and data persistence.

### Service Layer Benefits

- **Separation of Concerns**: Business logic isolated from API layer
- **Reusability**: Services can be called from multiple endpoints
- **Testability**: Easier to unit test in isolation
- **Maintainability**: Clear boundaries and responsibilities

### File Structure

```
memora/services/
├── __init__.py
├── srs_redis_manager.py      # Redis operations for SRS
├── srs_persistence.py        # Async database persistence
├── srs_archiver.py           # Season archival
├── srs_reconciliation.py     # Cache consistency
└── partition_manager.py      # Database partitioning
```

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                               │
│  (reviews.py, sessions.py, srs.py, etc.)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer                             │
│  ┌──────────────┬──────────────┬──────────────┐         │
│  │  Redis       │  Persistence  │   Archiver   │         │
│  │  Manager     │   Service     │              │         │
│  └──────────────┴──────────────┴──────────────┘         │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐         ┌──────────────┐
│     Redis     │         │  PostgreSQL  │
│    (Cache)    │         │  (Database)  │
└───────────────┘         └──────────────┘
```

## SRS Services

### SRS Redis Manager

**Module**: [`memora/services/srs_redis_manager.py`](../../memora/services/srs_redis_manager.py)

**Purpose**: Manages Redis Sorted Sets for SRS scheduling using high-performance ZSET operations.

#### Key Concepts

- **Key Format**: `srs:{user_email}:{season_name}`
- **Score**: Unix timestamp of `next_review_date`
- **Member**: Question ID (string)
- **TTL**: 30 days for automatic cleanup of inactive users

#### Class: SRSRedisManager

```python
class SRSRedisManager:
    """Manages Redis Sorted Sets for SRS scheduling"""
    
    DEFAULT_TTL = 30 * 24 * 60 * 60  # 30 days
    DEFAULT_REDIS_URL = "redis://localhost:13000"
```

#### Methods

##### `is_available() -> bool`

Check if Redis is responsive.

**Returns**: `True` if Redis is available, `False` otherwise

**Example**:
```python
manager = SRSRedisManager()
if manager.is_available():
    # Use Redis
    pass
else:
    # Fall back to database
    pass
```

---

##### `add_item(user, season, question_id, next_review_ts, ttl=None) -> bool`

Add or update a question's review schedule in Redis.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `question_id` (str): UUID of question
- `next_review_ts` (float): Unix timestamp of next review date
- `ttl` (int, optional): Time-to-live in seconds

**Returns**: `True` if successful, `False` otherwise

**Example**:
```python
manager = SRSRedisManager()
manager.add_item(
    user="user@example.com",
    season="2024-2025",
    question_id="q-123",
    next_review_ts=time.time() + 86400  # 1 day from now
)
```

---

##### `get_due_items(user, season, limit=20) -> List[str]`

Get question IDs due for review.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `limit` (int): Maximum number of items to return

**Returns**: List of question IDs due for review

**Example**:
```python
due_questions = manager.get_due_items(
    user="user@example.com",
    season="2024-2025",
    limit=15
)
```

---

##### `get_due_items_with_rehydration(user, season, limit=20) -> Tuple[List[str], bool]`

Get due items with automatic cache rehydration on miss.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `limit` (int): Maximum number of items to return

**Returns**: Tuple of (due_items, was_rehydrated)

**Example**:
```python
items, was_rehydrated = manager.get_due_items_with_rehydration(
    user="user@example.com",
    season="2024-2025",
    limit=15
)
if was_rehydrated:
    # Cache was loaded from database
    pass
```

---

##### `add_batch(user, season, items, ttl=None) -> bool`

Add multiple items to review schedule in a single operation.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `items` (Dict[str, float]): Dictionary mapping question_id -> next_review_ts
- `ttl` (int, optional): Time-to-live in seconds

**Returns**: `True` if successful, `False` otherwise

**Example**:
```python
items = {
    "q-123": time.time() + 86400,
    "q-124": time.time() + 172800,
    "q-125": time.time() + 259200
}
manager.add_batch(
    user="user@example.com",
    season="2024-2025",
    items=items
)
```

---

##### `remove_item(user, season, question_id) -> bool`

Remove a question from review schedule.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name
- `question_id` (str): UUID of question

**Returns**: `True` if successful, `False` otherwise

---

##### `clear_user_cache(user, season) -> bool`

Clear all review schedule data for a user-season pair.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name

**Returns**: `True` if successful, `False` otherwise

---

##### `get_cache_stats(user, season) -> Dict`

Get statistics about a user's cache.

**Parameters**:
- `user` (str): User email or ID
- `season` (str): Season name

**Returns**: Dictionary with statistics:
- `total_items`: Total items in cache
- `due_items`: Number of due items
- `memory_usage_bytes`: Memory used by key

---

#### Module Functions

##### `rebuild_season_cache(season_name, batch_size=1000) -> Dict`

Rebuild Redis cache for an entire season with progress tracking.

**Parameters**:
- `season_name` (str): Name of season to rebuild cache for
- `batch_size` (int): Number of records to process per batch

**Returns**: Dictionary with rebuild results:
- `total_records`: Total records processed
- `total_users`: Number of unique users
- `total_keys`: Number of Redis keys created
- `status`: "completed" or "failed"

**Optimization**: Uses Keyset Pagination (Seek Method) for O(1) performance regardless of table size.

**Example**:
```python
result = rebuild_season_cache("2024-2025", batch_size=1000)
print(f"Processed {result['total_records']} records")
```

---

### SRS Persistence

**Module**: [`memora/services/srs_persistence.py`](../../memora/services/srs_persistence.py)

**Purpose**: Handles asynchronous database persistence for SRS review responses with retry logic and audit logging.

#### Key Features

- **Async Persistence**: Background job processing
- **Retry Logic**: Exponential backoff with max retries
- **Audit Logging**: Logs all persistence operations
- **Idempotent Design**: Prevents duplicate writes
- **Race Condition Handling**: Uses DB constraints

#### Class: SRSPersistenceService

```python
class SRSPersistenceService:
    """Service for asynchronous SRS data persistence"""
    
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1  # seconds
    RETRY_DELAY_MAX = 60  # seconds
    IDEMPOTENCY_WINDOW = 300  # 5 minutes
```

#### Methods

##### `persist_review_batch(responses, user, season, retry_count=0) -> Dict`

Persist a batch of review responses to database.

**Parameters**:
- `responses` (List[Dict]): List of review responses
  - `question_id` (str): Question ID
  - `new_stability` (float): New stability level
  - `new_next_review_date` (datetime): Next review date
  - `subject` (str, optional): Subject
  - `topic` (str, optional): Topic
- `user` (str): User email or ID
- `season` (str): Season name
- `retry_count` (int): Current retry attempt

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `processed_count`: Number of records processed
- `failed_count`: Number of records failed
- `errors`: List of error messages

**Example**:
```python
service = SRSPersistenceService()
responses = [
    {
        "question_id": "q-123",
        "new_stability": 2.5,
        "new_next_review_date": datetime(2026, 1, 21),
        "subject": "mathematics",
        "topic": "algebra"
    }
]
result = service.persist_review_batch(
    responses=responses,
    user="user@example.com",
    season="2024-2025"
)
```

**Process**:
1. Try to INSERT new record
2. If duplicate (race condition), UPDATE existing record
3. Check idempotency window (5 minutes)
4. Commit transaction
5. Log audit on errors or retries

---

##### `persist_single_review(response, user, season) -> bool`

Convenience method for single-item persistence.

**Parameters**:
- `response` (Dict): Single review response
- `user` (str): User email or ID
- `season` (str): Season name

**Returns**: `True` if successful, `False` otherwise

---

##### `get_persistence_status(job_id) -> Optional[Dict]`

Get status of a persistence background job.

**Parameters**:
- `job_id` (str): Background job ID

**Returns**: Job status dictionary or `None`

---

### SRS Archiver

**Module**: [`memora/services/srs_archiver.py`](../../memora/services/srs_archiver.py)

**Purpose**: Manages archiving of old season data to cold storage.

#### Key Features

- **Transactional Operations**: Ensures data integrity
- **Bulk SQL Operations**: High-performance copy/delete
- **Cache Cleanup**: Clears Redis for archived seasons
- **Retention Policy**: 3-year retention before deletion
- **Auto-Archive**: Scheduled archival of eligible seasons

#### Class: SRSArchiver

```python
class SRSArchiver:
    """Manages archiving of old season data"""
    
    RETENTION_DAYS = 3 * 365  # 3 years
```

#### Methods

##### `archive_season(season_name) -> Dict`

Archive all memory tracker records for a season.

**Parameters**:
- `season_name` (str): Name of season to archive

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `archived_count`: Number of records archived
- `season`: Season name
- `error`: Error message if failed

**Process**:
1. Validate season exists and is not active
2. Start database transaction
3. Bulk copy records to `Archived Memory Tracker`
4. Bulk delete from `Player Memory Tracker`
5. Commit transaction
6. Clear Redis cache for season

**Example**:
```python
archiver = SRSArchiver()
result = archiver.archive_season("2023-2024")
if result["success"]:
    print(f"Archived {result['archived_count']} records")
```

---

##### `process_auto_archive() -> Dict`

Process auto-archive for eligible seasons.

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `archived_seasons`: Number of seasons archived
- `failed_seasons`: List of failed seasons

**Eligibility**:
- Season has `auto_archive` flag set
- Season is not active
- Season end date has passed

---

##### `flag_eligible_for_deletion() -> Dict`

Flag archived records eligible for deletion (3+ years old).

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `flagged_count`: Number of records flagged
- `cutoff_date`: Date threshold used

**Process**:
1. Calculate cutoff date (3 years ago)
2. Bulk update `eligible_for_deletion` flag
3. Return count of affected records

---

##### `get_archive_status(season_name) -> Dict`

Get archive status for a season.

**Parameters**:
- `season_name` (str): Season name

**Returns**: Dictionary with:
- `season`: Season name
- `is_active`: Whether season is active
- `auto_archive`: Whether auto-archive is enabled
- `end_date`: Season end date
- `active_records`: Count of active records
- `archived_records`: Count of archived records
- `eligible_for_deletion`: Count of records marked for deletion
- `total_records`: Total records (active + archived)

---

##### `delete_eligible_records(season_name=None, confirm=False) -> Dict`

Delete archived records marked for deletion.

**Parameters**:
- `season_name` (str, optional): Filter by season
- `confirm` (bool): Must be `True` to confirm deletion

**Returns**: Dictionary with:
- `success`: Whether operation succeeded
- `deleted_count`: Number of records deleted
- `error`: Error message if failed

**Safety**: Requires explicit confirmation to prevent accidental deletion.

---

### SRS Reconciliation

**Module**: [`memora/services/srs_reconciliation.py`](../../memora/services/srs_reconciliation.py)

**Purpose**: Ensures cache consistency between Redis and PostgreSQL.

#### Key Features

- **Cache Consistency**: Detects and fixes discrepancies
- **Automatic Correction**: Auto-corrects common issues
- **Audit Logging**: Logs all reconciliation actions
- **Scheduled Execution**: Runs daily via background job

#### Typical Use Cases

1. **Cache Miss**: Redis empty but database has records
2. **Stale Cache**: Redis has outdated data
3. **Orphaned Records**: Database records without cache entries
4. **Ghost Records**: Cache entries without database records

#### Reconciliation Process

```
1. Fetch all records from database for user-season
2. Fetch all records from Redis cache
3. Compare and identify discrepancies:
   - Missing in Redis → Add to cache
   - Missing in database → Remove from cache
   - Timestamp mismatch → Update cache
4. Log all corrections
5. Return summary
```

---

## Infrastructure Services

### Partition Manager

**Module**: [`memora/services/partition_manager.py`](../../memora/services/partition_manager.py)

**Purpose**: Manages database partitioning for performance optimization.

#### Key Concepts

- **Partitioning Type**: LIST COLUMNS
- **Partition Key**: `season` field
- **Automatic Creation**: New partitions created for new seasons
- **Query Optimization**: Queries filtered by season use partition pruning

#### Benefits

- **Performance**: Queries only scan relevant partitions
- **Maintenance**: Can archive/drop old partitions
- **Scalability**: Supports millions of records efficiently

#### Typical Operations

##### Create Partition

```python
from memora.services.partition_manager import create_partition

create_partition("2024-2025")
```

##### Drop Partition

```python
from memora.services.partition_manager import drop_partition

drop_partition("2020-2021")
```

##### List Partitions

```python
from memora.services.partition_manager import list_partitions

partitions = list_partitions("Player Memory Tracker")
```

---

## Service Best Practices

### 1. Error Handling

Always wrap service operations in try-except blocks:

```python
try:
    result = service.method()
except Exception as e:
    frappe.log_error(str(e), "ServiceName.method")
    return {"success": False, "error": str(e)}
```

### 2. Transaction Management

Use database transactions for multi-step operations:

```python
frappe.db.begin()
try:
    # Operation 1
    # Operation 2
    frappe.db.commit()
except Exception as e:
    frappe.db.rollback()
    raise
```

### 3. Batch Operations

Use batch operations for better performance:

```python
# Good: Batch insert
items = {"q-1": ts1, "q-2": ts2, "q-3": ts3}
redis_manager.add_batch(user, season, items)

# Avoid: Individual inserts
for question_id, ts in items.items():
    redis_manager.add_item(user, season, question_id, ts)
```

### 4. Logging

Log errors and important events:

```python
frappe.log_error(
    f"Failed to persist {len(responses)} records: {str(e)}",
    "SRSPersistenceService.persist_review_batch"
)
```

### 5. Idempotency

Design services to be idempotent:

```python
# Check if already processed
if already_processed(job_id):
    return {"status": "already_processed"}

# Process
result = process_job(job_id)
```

### 6. Retry Logic

Implement exponential backoff for retries:

```python
if retry_count < MAX_RETRIES:
    delay = min(RETRY_DELAY_BASE * (2 ** retry_count), RETRY_DELAY_MAX)
    time.sleep(delay)
    # Retry
```

### 7. Cache Invalidation

Invalidate cache when data changes:

```python
# Update database
update_record(record_id)

# Clear cache
redis_manager.clear_user_cache(user, season)
```

### 8. Performance Monitoring

Track service performance:

```python
import time

start = time.time()
result = service.method()
duration = time.time() - start

if duration > 1.0:
    frappe.logger().warning(f"Slow operation: {duration:.2f}s")
```

---

## Testing Services

### Unit Testing

```python
def test_redis_manager_add_item():
    manager = SRSRedisManager()
    result = manager.add_item(
        user="test@example.com",
        season="2024-2025",
        question_id="q-123",
        next_review_ts=time.time() + 86400
    )
    assert result == True
```

### Integration Testing

```python
def test_persistence_with_redis():
    # Add to Redis
    redis_manager.add_item(...)
    
    # Persist to database
    persistence_service.persist_review_batch(...)
    
    # Verify database
    record = frappe.get_doc("Player Memory Tracker", filters={...})
    assert record is not None
```

---

## Scheduled Jobs

Services can be registered as scheduled jobs in [`memora/hooks.py`](../../memora/hooks.py):

```python
scheduler_events = {
    "daily": [
        "memora.services.srs_archiver.process_auto_archive",
        "memora.services.srs_reconciliation.reconcile_cache_with_database"
    ],
    "weekly": [
        "memora.services.srs_archiver.flag_eligible_for_deletion"
    ]
}
```

---

**Last Updated**: 2026-01-20
