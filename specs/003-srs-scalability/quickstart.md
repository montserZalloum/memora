# Quickstart: SRS High-Performance & Scalability

**Feature Branch**: `003-srs-scalability`
**Date**: 2026-01-19

## Prerequisites

Before implementing this feature, ensure:

1. **Redis is running** (already configured in environment)
   ```bash
   # Verify Redis connectivity
   redis-cli -p 13000 ping
   # Expected: PONG
   ```

2. **MariaDB version supports partitioning**
   ```bash
   # Check MariaDB version (requires 10.1+)
   mysql -e "SELECT VERSION();"
   ```

3. **Frappe workers are configured**
   ```bash
   # Verify RQ workers
   bench doctor
   ```

## Implementation Order

### Phase 1: Infrastructure Setup

```
1. DocType Updates
   ├── Game Subscription Season (add fields)
   ├── Archived Memory Tracker (create new)
   └── Player Memory Tracker (make season required)

2. Database Migration
   ├── Run bench migrate
   ├── Execute partitioning patch
   └── Create composite index
```

### Phase 2: Core Services

```
1. SRSRedisManager class
   ├── Connection handling
   ├── ZADD/ZRANGEBYSCORE operations
   └── Cache miss handling (lazy load)

2. API Integration
   ├── Modify get_review_session
   └── Modify submit_review_session
```

### Phase 3: Resilience Features

```
1. Safe Mode implementation
   ├── Cache health check
   ├── Rate limiter
   └── Fallback query

2. Background Jobs
   ├── Async persistence
   ├── Reconciliation
   └── Archiving
```

## Key Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `memora/services/__init__.py` | CREATE | Services package init |
| `memora/services/srs_redis_manager.py` | CREATE | Redis cache wrapper |
| `memora/services/srs_reconciliation.py` | CREATE | Reconciliation service |
| `memora/services/srs_archiver.py` | CREATE | Archiving service |
| `memora/api/reviews.py` | MODIFY | Integrate Redis |
| `memora/api/srs.py` | MODIFY | Add admin endpoints |
| `memora/api/utils.py` | MODIFY | Add Safe Mode utils |
| `memora/hooks.py` | MODIFY | Add scheduled jobs |
| `memora/patches/v1_0/setup_partitioning.py` | CREATE | DB partition setup |

## Code Snippets

### SRSRedisManager Basic Structure

```python
# memora/services/srs_redis_manager.py
import frappe
import redis
import time
from typing import List, Optional

class SRSRedisManager:
    """Manages Redis Sorted Sets for SRS scheduling"""

    def __init__(self):
        self.redis = self._get_redis_connection()

    def _get_redis_connection(self):
        """Get Redis connection from Frappe config"""
        redis_url = frappe.conf.get("redis_cache", "redis://localhost:13000")
        return redis.from_url(redis_url)

    def _make_key(self, user: str, season: str) -> str:
        return f"srs:{user}:{season}"

    def add_item(self, user: str, season: str, question_id: str, next_review_ts: float):
        """Add or update a question's review schedule"""
        key = self._make_key(user, season)
        self.redis.zadd(key, {question_id: next_review_ts})

    def get_due_items(self, user: str, season: str, limit: int = 20) -> List[str]:
        """Get question IDs due for review"""
        key = self._make_key(user, season)
        now = time.time()
        return self.redis.zrangebyscore(key, "-inf", now, start=0, num=limit)

    def remove_item(self, user: str, season: str, question_id: str):
        """Remove a question from the schedule"""
        key = self._make_key(user, season)
        self.redis.zrem(key, question_id)

    def is_available(self) -> bool:
        """Check if Redis is available"""
        try:
            self.redis.ping()
            return True
        except:
            return False
```

### Safe Mode Check Pattern

```python
# In memora/api/reviews.py
from memora.services.srs_redis_manager import SRSRedisManager

@frappe.whitelist()
def get_review_session(subject=None, limit=20):
    user = frappe.session.user
    season = get_active_season()

    redis_manager = SRSRedisManager()

    if redis_manager.is_available():
        # Normal mode - use Redis
        question_ids = redis_manager.get_due_items(user, season, limit)
        is_degraded = False
    else:
        # Safe Mode - rate limited DB query
        if not check_rate_limit(user):
            frappe.throw("Please wait 30 seconds", exc=RateLimitExceeded)

        question_ids = get_reviews_safe_mode(user, season, limit=10)
        is_degraded = True

    # Fetch question details...
    return {
        "questions": questions,
        "is_degraded": is_degraded,
        "season": season
    }
```

### Async Write Pattern

```python
# In memora/api/reviews.py
@frappe.whitelist()
def submit_review_session(responses):
    user = frappe.session.user
    season = get_active_season()

    # Step 1: Update Redis immediately
    redis_manager = SRSRedisManager()
    for response in responses:
        new_schedule = calculate_next_review(response)
        redis_manager.add_item(user, season, response["question_id"], new_schedule)

    # Step 2: Queue DB persistence
    job = frappe.enqueue(
        "memora.services.srs_persistence.persist_review_batch",
        queue="srs_write",
        responses=responses,
        user=user,
        season=season
    )

    # Step 3: Return immediately
    return {
        "status": "success",
        "processed": len(responses),
        "persistence_job_id": job.id
    }
```

### Scheduled Jobs in hooks.py

```python
# Add to memora/hooks.py
scheduler_events = {
    "daily": [
        "memora.services.srs_reconciliation.reconcile_cache_with_database",
        "memora.services.srs_archiver.process_auto_archive"
    ],
    "cron": {
        # Run retention check weekly
        "0 2 * * 0": [
            "memora.services.srs_archiver.flag_eligible_for_deletion"
        ]
    }
}
```

## Testing Checklist

- [ ] Redis connection works
- [ ] ZADD/ZRANGEBYSCORE operations work
- [ ] Cache miss triggers lazy loading
- [ ] Safe Mode activates when Redis down
- [ ] Rate limiting works in Safe Mode
- [ ] Async persistence completes successfully
- [ ] Reconciliation detects and corrects discrepancies
- [ ] Archiving moves data correctly
- [ ] Cache rebuild utility works
- [ ] Partition creation hook works

## Monitoring Points

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| get_review_session p99 | <100ms | >200ms |
| submit_review_session p99 | <500ms | >1000ms |
| Redis memory usage | Linear with users | >80% capacity |
| Reconciliation discrepancy rate | <0.1% | >0.1% |
| Background job queue depth | <1000 | >5000 |
| Safe Mode activations | 0 | Any |

## Common Issues

### Redis Connection Failed
```python
# Check common_site_config.json has correct redis_cache URL
frappe.conf.get("redis_cache")
```

### Partition Creation Failed
```sql
-- Check if table has data with NULL season
SELECT COUNT(*) FROM `tabPlayer Memory Tracker` WHERE season IS NULL;

-- Fix by assigning default season before partitioning
UPDATE `tabPlayer Memory Tracker` SET season = 'SEASON-DEFAULT' WHERE season IS NULL;
```

### Background Jobs Not Processing
```bash
# Ensure workers are running
bench worker --queue srs_write

# Check RQ dashboard
bench rq-dashboard
```
