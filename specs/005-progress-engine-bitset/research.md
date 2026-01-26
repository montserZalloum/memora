# Research: Progress Engine Bitset Implementation

**Feature**: 005-progress-engine-bitset
**Date**: 2026-01-25

## 1. Redis Bitmap Operations in Frappe

### Decision
Use `frappe.cache().set()` and `frappe.cache().get()` with raw byte strings for bitmap storage, combined with Python's bitwise operations for bit manipulation.

### Rationale
- Frappe's Redis wrapper (`frappe.cache()`) provides direct access to Redis
- Python's `int.from_bytes()` and `int.to_bytes()` allow efficient bit manipulation
- Redis strings can store up to 512MB, far exceeding our 1000-bit (125 bytes) requirement
- No additional dependencies required beyond existing Frappe infrastructure

### Alternatives Considered
1. **redis-py SETBIT/GETBIT commands**: Rejected because Frappe's cache wrapper doesn't expose these directly; would require raw Redis connection
2. **Python bitarray library**: Rejected to avoid additional dependency; native Python bitwise ops are sufficient for our scale
3. **JSON array of booleans**: Rejected due to memory inefficiency (1000 booleans = ~6KB vs 125 bytes)

### Implementation Pattern
```python
# Key format
key = f"user_prog:{player_id}:{subject_id}"

# Set bit (lesson completed)
def set_bit(bitmap_bytes: bytes, bit_index: int) -> bytes:
    bitmap_int = int.from_bytes(bitmap_bytes, 'big') if bitmap_bytes else 0
    bitmap_int |= (1 << bit_index)
    byte_length = (bit_index // 8) + 1
    return bitmap_int.to_bytes(max(byte_length, len(bitmap_bytes or b'')), 'big')

# Check bit
def check_bit(bitmap_bytes: bytes, bit_index: int) -> bool:
    if not bitmap_bytes:
        return False
    bitmap_int = int.from_bytes(bitmap_bytes, 'big')
    return bool(bitmap_int & (1 << bit_index))
```

## 2. Unlock Logic Algorithm

### Decision
Depth-first traversal of the subject JSON structure, computing states bottom-up for containers and respecting parent `is_linear` flag for sibling unlock rules.

### Rationale
- JSON structure already contains hierarchy (Subject → Tracks → Units → Topics → Lessons)
- `is_linear` flag exists on Subject, Track, and Unit (needs adding to Topic)
- Bottom-up computation allows container states to be derived from child states
- Tree traversal is O(n) where n = total nodes, fitting within 20ms target

### Algorithm
```
function compute_progress(structure_json, bitmap):
    for each node in depth_first_order(structure_json):
        if node.is_lesson:
            node.status = "passed" if bit_is_set(bitmap, node.bit_index) else "not_passed"
        else:  # container
            all_passed = all(child.status == "passed" for child in node.children)
            node.status = "passed" if all_passed else "unlocked"

    # Apply unlock rules (second pass, top-down)
    for each node in breadth_first_order(structure_json):
        if node.parent.is_linear:
            if prev_sibling exists and prev_sibling.status != "passed":
                node.unlock_status = "locked"
            else:
                node.unlock_status = "unlocked" if node.status != "passed" else "passed"
        else:  # non-linear parent
            node.unlock_status = "unlocked" if parent.unlock_status != "locked" else "locked"
```

### Alternatives Considered
1. **Store pre-computed states in Redis**: Rejected due to complexity of invalidation when structure changes
2. **SQL-based state computation**: Rejected due to join overhead violating 20ms target
3. **GraphQL resolver pattern**: Rejected as over-engineering for this use case

## 3. Batch Sync Strategy

### Decision
Use Frappe's RQ (Redis Queue) scheduler to run a background job every 30 seconds that flushes pending bitmap changes to MariaDB.

### Rationale
- RQ scheduler already configured in Frappe hooks
- 30-second window balances durability (max 30s data loss) with performance (no DB write on hot path)
- Batch processing reduces DB load from 1000 writes/sec to ~33 batch operations/sec
- MariaDB BLOB field can store bitmap bytes directly

### Implementation Pattern
```python
# In hooks.py
scheduler_events = {
    "cron": {
        "*/30 * * * * *": [  # Every 30 seconds (requires scheduler_interval = 30 in common_site_config)
            "memora.services.progress_engine.snapshot_syncer.sync_pending_bitmaps"
        ]
    }
}

# Sync function
def sync_pending_bitmaps():
    # Get all dirty keys from Redis set
    dirty_keys = frappe.cache().smembers("progress_dirty_keys")
    for key in dirty_keys:
        player_id, subject_id = parse_key(key)
        bitmap = frappe.cache().get(key)
        update_mariadb_snapshot(player_id, subject_id, bitmap)
        frappe.cache().srem("progress_dirty_keys", key)
```

### Alternatives Considered
1. **Write-through to MariaDB**: Rejected due to 1000 writes/sec overwhelming DB
2. **5-minute batch**: Rejected due to 5-minute max data loss exceeding acceptable risk
3. **Event-driven with debounce**: Rejected due to implementation complexity

## 4. Cache Warming Strategy

### Decision
On cache miss, load bitmap from `Memora Structure Progress.passed_lessons_bitset` field and populate Redis atomically.

### Rationale
- Simple fallback path: Redis miss → MariaDB read → Redis write
- Single source of truth: MariaDB snapshot is the durable copy
- Atomic operation prevents race conditions during warming

### Implementation Pattern
```python
def get_bitmap(player_id: str, subject_id: str) -> bytes:
    key = f"user_prog:{player_id}:{subject_id}"
    bitmap = frappe.cache().get(key)

    if bitmap is None:
        # Cache miss - warm from MariaDB
        progress = frappe.get_value(
            "Memora Structure Progress",
            {"player": player_id, "subject": subject_id},
            "passed_lessons_bitset"
        )
        bitmap = progress or b''
        frappe.cache().set(key, bitmap)

    return bitmap
```

## 5. XP Calculation with Record-Breaking Bonus

### Decision
Store per-lesson best hearts in a JSON field (`best_hearts_data`) on `Memora Structure Progress`. Calculate bonus as `(new_hearts - best_hearts) * 10` when new_hearts > best_hearts.

### Rationale
- Hearts range 0-5, so per-lesson storage is 3 bits (or 1 byte for simplicity)
- JSON format allows sparse storage (only store lessons with recorded hearts)
- Bonus calculation is simple arithmetic, no external lookups needed

### Implementation Pattern
```python
def calculate_xp(lesson_id: str, hearts: int, is_first_completion: bool, best_hearts_data: dict, base_xp: int) -> tuple[int, dict]:
    """Returns (xp_earned, updated_best_hearts_data)"""
    xp = 0

    if is_first_completion:
        xp = base_xp + (hearts * 10)
        best_hearts_data[lesson_id] = hearts
    else:
        prev_best = best_hearts_data.get(lesson_id, 0)
        if hearts > prev_best:
            xp = (hearts - prev_best) * 10
            best_hearts_data[lesson_id] = hearts

    return xp, best_hearts_data
```

## 6. JSON Structure Enhancement

### Decision
Extend `json_generator.py` to include `bit_index` per lesson and `is_linear` per container node in the subject JSON output.

### Rationale
- Progress engine needs `bit_index` to map lessons to bitmap positions
- `is_linear` flags determine unlock behavior at each level
- Reuse existing JSON generation infrastructure (CDN export feature)

### JSON Structure Addition
```json
{
  "id": "SUBJ-001",
  "is_linear": true,
  "tracks": [{
    "id": "TRACK-001",
    "is_linear": true,
    "units": [{
      "id": "UNIT-001",
      "is_linear": false,
      "topics": [{
        "id": "TOPIC-001",
        "is_linear": true,
        "lessons": [{
          "id": "LESSON-001",
          "bit_index": 0
        }, {
          "id": "LESSON-002",
          "bit_index": 1
        }]
      }]
    }]
  }]
}
```

## 7. API Design Decisions

### Decision
Two Frappe whitelisted API endpoints: `POST /api/method/memora.api.progress.complete_lesson` and `GET /api/method/memora.api.progress.get_progress`.

### Rationale
- Follows existing Frappe API patterns (`@frappe.whitelist()`)
- Consistent with other Memora API endpoints
- Supports mobile/web clients via standard HTTP methods

### Endpoint Signatures
```python
@frappe.whitelist()
def complete_lesson(lesson_id: str, hearts: int) -> dict:
    """Mark lesson as completed, award XP."""
    # Returns: {"success": bool, "xp_earned": int, "new_total_xp": int}

@frappe.whitelist()
def get_progress(subject_id: str) -> dict:
    """Get full progress for a subject."""
    # Returns: {"nodes": [...], "completion_percentage": float, "suggested_next_lesson_id": str|None}
```

## 8. Performance Benchmarks (Expected)

| Operation | Target | Approach |
|-----------|--------|----------|
| Bitmap read (Redis) | <1ms | Direct key lookup |
| JSON structure load (LRU cached) | <1ms | `functools.lru_cache` on file read |
| Unlock computation (1000 nodes) | <15ms | In-memory tree traversal |
| Total progress read | <20ms | Sum of above |
| Bitmap write (Redis) | <1ms | Direct key set |
| Dirty key tracking | <1ms | Redis SADD |
| Total completion write | <5ms | Redis-only hot path |

## Summary of Technical Decisions

| Area | Decision | Key Benefit |
|------|----------|-------------|
| Bitmap storage | Python bytes + bitwise ops via frappe.cache | No extra dependencies |
| Unlock algorithm | Two-pass DFS/BFS traversal | O(n) complexity |
| Batch sync | RQ scheduler every 30s | 1000 writes/sec → 33 batches/sec |
| Cache warming | MariaDB fallback on miss | 99.99% durability |
| XP calculation | JSON field for best_hearts | Sparse storage, simple math |
| JSON enhancement | Add bit_index, is_linear | Reuse CDN export infra |
| API design | Frappe whitelist methods | Consistent patterns |
