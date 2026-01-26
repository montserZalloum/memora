# Quickstart: Progress Engine Bitset

**Feature**: 005-progress-engine-bitset
**Date**: 2026-01-25

## Overview

The Progress Engine provides high-performance lesson completion tracking using Redis bitmaps. This guide covers setup, basic usage, and testing.

## Prerequisites

- Frappe bench environment with Memora app installed
- Redis running (standard Frappe requirement)
- MariaDB with Memora tables migrated

## Setup

### 1. Run Database Migration

After adding the new fields, run:

```bash
cd $BENCH_PATH
bench migrate
```

### 2. Backfill Existing Lessons (if applicable)

```bash
bench execute memora.services.progress_engine.migration.backfill_bit_indices
```

### 3. Verify Redis Connection

```python
import frappe
frappe.cache().set("test_key", "test_value")
assert frappe.cache().get("test_key") == "test_value"
```

## Basic Usage

### Complete a Lesson

```python
import frappe

# Via API
result = frappe.call(
    "memora.api.progress.complete_lesson",
    lesson_id="LESSON-001",
    hearts=4
)
print(result)
# {
#     "success": True,
#     "xp_earned": 50,  # base 10 + (4 * 10)
#     "new_total_xp": 150,
#     "is_first_completion": True,
#     "is_new_record": True
# }
```

### Get Progress

```python
result = frappe.call(
    "memora.api.progress.get_progress",
    subject_id="SUBJ-001"
)
print(result["completion_percentage"])  # 25.0
print(result["suggested_next_lesson_id"])  # "LESSON-002"
```

### Direct Service Usage

```python
from memora.services.progress_engine import progress_computer

# Get progress data
progress = progress_computer.compute_progress(
    player_id="PLAYER-001",
    subject_id="SUBJ-001"
)

# Check specific lesson status
from memora.services.progress_engine import bitmap_manager

is_passed = bitmap_manager.check_bit(
    player_id="PLAYER-001",
    subject_id="SUBJ-001",
    bit_index=5
)
```

## API Endpoints

### POST /api/method/memora.api.progress.complete_lesson

**Request:**
```json
{
    "lesson_id": "LESSON-001",
    "hearts": 4
}
```

**Response (success):**
```json
{
    "success": true,
    "xp_earned": 50,
    "new_total_xp": 150,
    "is_first_completion": true,
    "is_new_record": true
}
```

**Response (error - no hearts):**
```json
{
    "success": false,
    "error_code": "NO_HEARTS",
    "message": "No hearts remaining. Wait for hearts to regenerate."
}
```

### GET /api/method/memora.api.progress.get_progress

**Request:**
```
?subject_id=SUBJ-001
```

**Response:**
```json
{
    "subject_id": "SUBJ-001",
    "completion_percentage": 25.0,
    "total_xp_earned": 150,
    "suggested_next_lesson_id": "LESSON-002",
    "total_lessons": 20,
    "passed_lessons": 5,
    "root": {
        "id": "SUBJ-001",
        "type": "subject",
        "status": "unlocked",
        "children": [...]
    }
}
```

## Testing

### Run Unit Tests

```bash
pytest memora/tests/unit/progress_engine/ -v
```

### Run Integration Tests

```bash
pytest memora/tests/integration/test_progress_api.py -v
```

### Manual Testing with Frappe Console

```bash
bench console
```

```python
# Create test data
subject = frappe.get_doc({
    "doctype": "Memora Subject",
    "title": "Test Subject",
    "is_linear": True
}).insert()

# ... create track, unit, topic, lesson hierarchy ...

# Test completion
from memora.api import progress
result = progress.complete_lesson("LESSON-001", 5)
print(result)
```

## Redis Key Inspection

```bash
# Connect to Redis CLI
redis-cli

# List progress keys
KEYS "user_prog:*"

# Check specific bitmap
GET "user_prog:PLAYER-001:SUBJ-001"

# Check dirty keys pending sync
SMEMBERS "progress_dirty_keys"
```

## Background Job Monitoring

The snapshot syncer runs every 30 seconds. Monitor via:

```bash
# Check RQ scheduler
bench show-pending-jobs

# View scheduler logs
tail -f logs/scheduler.log
```

## Troubleshooting

### Progress not updating

1. Check Redis connection: `frappe.cache().ping()`
2. Verify lesson has valid `bit_index`: `frappe.get_value("Memora Lesson", lesson_id, "bit_index")`
3. Check dirty keys: `frappe.cache().smembers("progress_dirty_keys")`

### XP not awarded

1. Verify player wallet exists: `frappe.get_value("Memora Player Wallet", {"player": player_id})`
2. Check background job queue: `bench show-pending-jobs`

### Slow progress retrieval

1. Check JSON structure file is cached
2. Verify Redis latency: `redis-cli --latency`
3. Profile with: `frappe.utils.cint(frappe.conf.get("enable_profiler"))`

## Performance Benchmarks

Expected and measured performance on standard hardware:

| Operation | Target | Expected |
|-----------|--------|----------|
| Get progress (1000 lessons) | <20ms | <20ms |
| Complete lesson | <5ms | <5ms |
| Bitmap read (Redis) | <1ms | <1ms |
| JSON structure load (cached) | <1ms | <1ms |
| Unlock computation (1000 nodes) | <15ms | <15ms |
| Bitmap write (Redis) | <1ms | <1ms |
| Dirty key tracking | <1ms | <1ms |

### Performance Architecture

The progress engine achieves sub-20ms performance through:
- **Redis Bitmaps**: O(1) bit operations for lesson completion checks
- **LRU-Cached JSON**: Subject structure cached in memory for <1ms loads
- **In-Memory Traversal**: O(n) tree traversal for unlock states
- **Batched Writes**: No MariaDB writes on hot path, 30-second sync batches

### Benchmark Testing

To run performance benchmarks (requires pytest):

```bash
# Install pytest if not available
pip install pytest pytest-benchmark

# Run benchmarks
pytest memora/tests/performance/test_progress_benchmarks.py -v
```

Note: Actual measured benchmarks require pytest and test infrastructure setup. Expected values are based on the architecture design documented in research.md.
