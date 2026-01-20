# Research: SRS High-Performance & Scalability Architecture

**Feature Branch**: `003-srs-scalability`
**Date**: 2026-01-19
**Status**: Complete

## Research Topics

### 1. Redis Sorted Sets for SRS Scheduling

**Decision**: Use Redis Sorted Sets (ZSET) with `next_review_timestamp` as score

**Rationale**:
- O(log n) complexity for ZADD (insert/update) and ZRANGEBYSCORE (range query)
- Native support for time-based ordering without additional indexing
- Memory-efficient: ~70 bytes per member for typical key sizes
- Atomic operations prevent race conditions during concurrent updates

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| Redis Lists | O(n) for sorted retrieval; would require client-side sorting |
| Redis Hashes | No native sorting; would need separate index structure |
| Database-only (indexed) | 1B records makes index maintenance prohibitive; WHERE clauses degrade at scale |
| Memcached | No sorted data structures; less feature-rich than Redis |

**Implementation Pattern**:
```python
# Key format: srs:{user_email}:{season_name}
# Score: Unix timestamp (float) of next_review_date
# Member: question_id (string)

# Add/Update
ZADD srs:user@email.com:SEASON-2026 NX 1737380000 "Q-UUID-123"

# Get due items (score <= now)
ZRANGEBYSCORE srs:user@email.com:SEASON-2026 -inf {current_timestamp} LIMIT 0 20
```

### 2. MariaDB Table Partitioning Strategy

**Decision**: LIST COLUMNS partitioning by `season` field

**Rationale**:
- Season-based partitioning aligns with business lifecycle (academic years)
- Partition pruning: queries for active season only scan relevant partition
- Easy archival: entire partitions can be dropped or migrated
- MariaDB supports up to 8192 partitions (sufficient for decades of seasons)

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| RANGE by date | Queries would need date ranges; season is more intuitive |
| HASH partitioning | Even distribution but no partition pruning for season queries |
| No partitioning (indexes only) | 1B rows makes index maintenance and full scans problematic |
| Separate tables per season | Application complexity; loses referential integrity |

**Implementation Pattern**:
```sql
ALTER TABLE `tabPlayer Memory Tracker`
PARTITION BY LIST COLUMNS(season) (
    PARTITION p_default VALUES IN (''),
    PARTITION p_season_2025 VALUES IN ('SEASON-2025'),
    PARTITION p_season_2026 VALUES IN ('SEASON-2026')
);

-- Add partition for new season (in hooks)
ALTER TABLE `tabPlayer Memory Tracker`
ADD PARTITION (PARTITION p_season_2027 VALUES IN ('SEASON-2027'));
```

**Frappe Compatibility Note**: Frappe doesn't natively support partitioning. Implementation requires:
1. Patch script to execute raw SQL after DocType migration
2. Hook on Season creation to add new partitions
3. Ensure `season` field is never NULL (required for LIST partitioning)

### 3. Frappe Background Jobs for Async Writes

**Decision**: Use `frappe.enqueue()` with dedicated queue for SRS persistence

**Rationale**:
- Native Frappe integration; no additional infrastructure
- RQ (Redis Queue) backed; already configured in environment
- Supports job priorities, retries, and failure handling
- Idempotent job design prevents duplicate writes

**Alternatives Considered**:
| Alternative | Why Rejected |
|-------------|--------------|
| Celery | Additional infrastructure; Frappe already uses RQ |
| Direct async (asyncio) | Frappe is synchronous; would require major refactoring |
| Message queue (RabbitMQ, Kafka) | Overkill for this use case; operational overhead |
| Synchronous writes | Blocks user response; unacceptable latency |

**Implementation Pattern**:
```python
# In api/reviews.py
def submit_review_session(responses):
    # Step 1: Update Redis immediately
    redis_manager.update_reviews(user, season, responses)

    # Step 2: Queue DB persistence
    frappe.enqueue(
        "memora.services.srs_persistence.persist_review_batch",
        queue="srs_write",  # Dedicated queue
        job_name=f"srs_persist_{user}_{frappe.utils.now()}",
        responses=responses,
        user=user,
        season=season,
        is_async=True,
        retry=3
    )

    # Step 3: Return immediately
    return {"status": "success", "message": "Progress saved"}
```

### 4. Safe Mode Implementation (Cache Failure Fallback)

**Decision**: Degraded service with rate limiting and limited data retrieval

**Rationale**:
- Maintains partial service availability during outages
- Prevents database cascade failure from sudden load spike
- Configurable limits allow tuning based on infrastructure capacity
- User feedback (degraded mode indicator) sets expectations

**Implementation Pattern**:
```python
# In api/utils.py
class SafeModeManager:
    GLOBAL_LIMIT = 500  # requests per minute
    USER_LIMIT_SECONDS = 30  # 1 request per 30 seconds per user

    @staticmethod
    def is_safe_mode_active():
        # Check Redis connectivity
        try:
            frappe.cache().ping()
            return False
        except:
            return True

    @staticmethod
    def check_rate_limit(user):
        # Use frappe.cache for rate limit counters (separate from SRS cache)
        key = f"safe_mode_rate:{user}"
        last_request = frappe.cache().get(key)
        if last_request and (now() - last_request) < USER_LIMIT_SECONDS:
            return False  # Rate limited
        frappe.cache().set(key, now(), expires_in=USER_LIMIT_SECONDS)
        return True

# In api/reviews.py - Safe Mode query
def get_reviews_safe_mode(user, season, limit=10):
    """Lightweight indexed query for degraded mode"""
    return frappe.db.sql("""
        SELECT question_id, next_review_date, stability
        FROM `tabPlayer Memory Tracker`
        WHERE player = %s AND season = %s
        AND next_review_date <= NOW()
        ORDER BY next_review_date ASC
        LIMIT %s
    """, (user, season, limit), as_dict=True)
```

### 5. Cache Rehydration Strategy

**Decision**: Hybrid lazy loading + manual rebuild utility

**Rationale**:
- Lazy loading handles organic cache misses without admin intervention
- Manual rebuild provides proactive cache warming for planned events
- Progress tracking gives visibility during long-running rebuilds
- Batch processing prevents memory spikes during large rebuilds

**Implementation Pattern**:
```python
# Lazy loading (in SRSRedisManager)
def get_due_items(self, user, season, limit=20):
    key = self._make_key(user, season)
    items = self.redis.zrangebyscore(key, "-inf", time.time(), start=0, num=limit)

    if not items:
        # Cache miss - attempt rehydration
        items = self._rehydrate_user_cache(user, season)
        if items:
            return items[:limit]
    return items

def _rehydrate_user_cache(self, user, season):
    """Lazy load from DB on cache miss"""
    records = frappe.get_all("Player Memory Tracker",
        filters={"player": user, "season": season},
        fields=["question_id", "next_review_date"])

    if records:
        pipe = self.redis.pipeline()
        key = self._make_key(user, season)
        for r in records:
            score = r.next_review_date.timestamp()
            pipe.zadd(key, {r.question_id: score})
        pipe.execute()
    return [r.question_id for r in records if r.next_review_date <= now()]

# Manual rebuild (admin utility)
def rebuild_season_cache(season_name):
    """Background job for full season cache rebuild"""
    total = frappe.db.count("Player Memory Tracker", {"season": season_name})
    processed = 0
    batch_size = 1000

    # Process in batches
    for offset in range(0, total, batch_size):
        records = frappe.db.sql("""
            SELECT player, question_id, next_review_date
            FROM `tabPlayer Memory Tracker`
            WHERE season = %s
            LIMIT %s OFFSET %s
        """, (season_name, batch_size, offset), as_dict=True)

        # Group by player
        by_player = defaultdict(list)
        for r in records:
            by_player[r.player].append(r)

        # Batch insert to Redis
        pipe = redis.pipeline()
        for player, items in by_player.items():
            key = f"srs:{player}:{season_name}"
            for item in items:
                pipe.zadd(key, {item.question_id: item.next_review_date.timestamp()})
        pipe.execute()

        processed += len(records)
        frappe.publish_progress(processed * 100 / total,
            title=f"Rebuilding cache for {season_name}")
```

### 6. Reconciliation Service Design

**Decision**: Scheduled job with sampling-based consistency check

**Rationale**:
- Full reconciliation of 1B records is impractical; sampling provides statistical confidence
- DB is source of truth; cache corrections are one-directional
- Alert threshold (0.1%) catches systemic issues without noise from transient differences
- Daily schedule balances detection speed with system load

**Implementation Pattern**:
```python
# Scheduled job (daily)
def reconcile_cache_with_database():
    """Sample-based reconciliation - runs daily"""
    sample_size = 10000
    discrepancies = 0

    # Random sample of active records
    records = frappe.db.sql("""
        SELECT player, season, question_id, next_review_date
        FROM `tabPlayer Memory Tracker`
        WHERE season IN (SELECT name FROM `tabGame Subscription Season` WHERE is_active = 1)
        ORDER BY RAND()
        LIMIT %s
    """, (sample_size,), as_dict=True)

    for record in records:
        key = f"srs:{record.player}:{record.season}"
        cached_score = redis.zscore(key, record.question_id)
        db_score = record.next_review_date.timestamp()

        if cached_score is None or abs(cached_score - db_score) > 1:  # 1 second tolerance
            discrepancies += 1
            # Auto-correct
            redis.zadd(key, {record.question_id: db_score})

    discrepancy_rate = discrepancies / sample_size

    if discrepancy_rate > 0.001:  # 0.1% threshold
        frappe.sendmail(
            recipients=get_system_admins(),
            subject="SRS Cache Discrepancy Alert",
            message=f"Discrepancy rate: {discrepancy_rate:.2%} ({discrepancies}/{sample_size})"
        )

    frappe.log_error(f"Reconciliation complete: {discrepancy_rate:.2%} discrepancies",
        "SRS Reconciliation")
```

### 7. Archiving Service Design

**Decision**: Partition-based bulk move with cache cleanup

**Rationale**:
- Moving entire partitions is O(1) in terms of row count
- Separate archive table allows different storage engine or compression
- Cache cleanup via pattern deletion frees Redis memory
- Admin approval gate prevents accidental data loss

**Implementation Pattern**:
```python
# Nightly job (checks for auto_archive seasons)
def process_auto_archive():
    """Archive seasons marked for auto-archive"""
    seasons = frappe.get_all("Game Subscription Season",
        filters={"auto_archive": 1, "is_active": 0},
        fields=["name"])

    for season in seasons:
        archive_season(season.name)

def archive_season(season_name):
    """Move season data to archive table and cleanup"""
    # Step 1: Copy to archive table
    frappe.db.sql("""
        INSERT INTO `tabArchived Memory Tracker`
        (name, player, season, question_id, stability, next_review_date,
         last_review_date, subject, archived_at)
        SELECT
            name, player, season, question_id, stability, next_review_date,
            last_review_date, subject, NOW()
        FROM `tabPlayer Memory Tracker`
        WHERE season = %s
    """, (season_name,))

    # Step 2: Delete from active table
    frappe.db.sql("""
        DELETE FROM `tabPlayer Memory Tracker`
        WHERE season = %s
    """, (season_name,))

    # Step 3: Cleanup Redis (pattern delete)
    # Note: SCAN is used to avoid blocking
    cursor = 0
    pattern = f"srs:*:{season_name}"
    while True:
        cursor, keys = redis.scan(cursor, match=pattern, count=1000)
        if keys:
            redis.delete(*keys)
        if cursor == 0:
            break

    # Step 4: Update season status
    frappe.db.set_value("Game Subscription Season", season_name,
        "partition_created", 0)  # Mark for potential partition drop

    frappe.db.commit()
```

## Dependencies and Risks

### Dependencies
| Dependency | Status | Mitigation |
|------------|--------|------------|
| Redis server | Configured (127.0.0.1:13000) | Safe Mode fallback |
| MariaDB partitioning support | Available in MariaDB 10.1+ | Verify version in deployment |
| Frappe RQ workers | Configured | Ensure workers assigned to srs_write queue |

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Redis memory exhaustion | Medium | High | Monitor memory; implement TTL for inactive users |
| Partition limit reached | Low | Medium | 8192 partitions = decades of seasons |
| Background job backlog | Medium | Medium | Dedicated queue; monitor queue depth |
| Reconciliation performance | Low | Low | Sampling approach limits load |

## Conclusion

All technical decisions have been made and documented. No NEEDS CLARIFICATION items remain. The implementation can proceed to Phase 1 (data modeling and API contracts).
