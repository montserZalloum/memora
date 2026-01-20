# Data Model: SRS High-Performance & Scalability Architecture

**Feature Branch**: `003-srs-scalability`
**Date**: 2026-01-19

## Entity Overview

```
┌─────────────────────────────────┐
│   Game Subscription Season      │
│   (extended with cache fields)  │
└────────────────┬────────────────┘
                 │ 1:N
                 ▼
┌─────────────────────────────────┐
│   Player Memory Tracker         │◄──────┐
│   (partitioned by season)       │       │
└────────────────┬────────────────┘       │
                 │ archive                │ lazy load
                 ▼                        │
┌─────────────────────────────────┐       │
│   Archived Memory Tracker       │       │
│   (cold storage)                │       │
└─────────────────────────────────┘       │
                                          │
┌─────────────────────────────────┐       │
│   Redis Cache (ZSET)            │───────┘
│   srs:{user}:{season}           │
└─────────────────────────────────┘
```

## Entities

### 1. Game Subscription Season (MODIFIED)

**DocType**: `Game Subscription Season`
**Location**: `memora/memora/doctype/game_subscription_season/`

#### Existing Fields (unchanged)
| Field | Type | Description |
|-------|------|-------------|
| `season_name` | Data | Unique season identifier (e.g., "SEASON-2026") |
| `start_date` | Date | Season start date |
| `end_date` | Date | Season end date |
| `is_active` | Check | Whether season is currently active |

#### New Fields
| Field | Type | Default | Hidden | Description |
|-------|------|---------|--------|-------------|
| `partition_created` | Check | 0 | Yes | Has DB partition been created for this season |
| `enable_redis` | Check | 1 | No | Enable Redis caching for this season |
| `auto_archive` | Check | 0 | No | Enable automatic archiving when season ends |

#### Validation Rules
- `season_name` must be unique and match pattern `^SEASON-\d{4}(-\w+)?$`
- `end_date` must be >= `start_date`
- `auto_archive` cannot be enabled while `is_active` is true (warning dialog)

#### Hooks
| Event | Action |
|-------|--------|
| `after_insert` | Create DB partition for new season |
| `on_update` (enable_redis changed) | Trigger cache rebuild if enabled |
| `on_update` (auto_archive enabled) | Show confirmation if is_active |

---

### 2. Player Memory Tracker (MODIFIED)

**DocType**: `Player Memory Tracker`
**Location**: `memora/memora/doctype/player_memory_tracker/`

#### Existing Fields (unchanged)
| Field | Type | Index | Description |
|-------|------|-------|-------------|
| `player` | Link (User) | Yes | Student user reference |
| `subject` | Link (Game Subject) | No | Optional subject filter |
| `topic` | Link (Game Topic) | No | Optional topic filter |
| `question_id` | Data | Yes | UUID of the question |
| `stability` | Float | No | SRS stability score (0-4) |
| `next_review_date` | Datetime | No | Calculated next review time |
| `last_review_date` | Datetime | No | Last review timestamp |

#### Modified Fields
| Field | Type | Index | Change | Description |
|-------|------|-------|--------|-------------|
| `season` | Link (Game Subscription Season) | Yes | **Now Required** | Partition key - cannot be NULL |

#### Database Schema Changes
```sql
-- Make season NOT NULL (migration required)
ALTER TABLE `tabPlayer Memory Tracker`
MODIFY COLUMN `season` VARCHAR(140) NOT NULL;

-- Apply LIST partitioning
ALTER TABLE `tabPlayer Memory Tracker`
PARTITION BY LIST COLUMNS(season) (
    PARTITION p_default VALUES IN (''),
    PARTITION p_season_initial VALUES IN ('SEASON-2025')
);
```

#### Compound Indexes (for Safe Mode queries)
```sql
-- Composite index for Safe Mode fallback queries
CREATE INDEX idx_pmt_player_season_review
ON `tabPlayer Memory Tracker` (player, season, next_review_date);
```

---

### 3. Archived Memory Tracker (NEW)

**DocType**: `Archived Memory Tracker`
**Location**: `memora/memora/doctype/archived_memory_tracker/`

#### Fields
| Field | Type | Index | Read Only | Description |
|-------|------|-------|-----------|-------------|
| `player` | Link (User) | Yes | Yes | Student user reference |
| `season` | Link (Game Subscription Season) | Yes | Yes | Original season |
| `question_id` | Data | No | Yes | UUID of the question |
| `stability` | Float | No | Yes | Final stability score |
| `next_review_date` | Datetime | No | Yes | Last calculated review date |
| `last_review_date` | Datetime | No | Yes | Last review timestamp |
| `subject` | Link (Game Subject) | No | Yes | Optional subject filter |
| `topic` | Link (Game Topic) | No | Yes | Optional topic filter |
| `archived_at` | Datetime | Yes | Yes | When record was archived |
| `eligible_for_deletion` | Check | No | No | 3+ years old, can be deleted |

#### Validation Rules
- All fields except `eligible_for_deletion` are read-only
- `eligible_for_deletion` can only be set by system (scheduled job)

#### Database Notes
- No partitioning (cold storage, less frequently accessed)
- Consider InnoDB compression for storage efficiency
- Index on `archived_at` for retention queries

---

### 4. Redis Cache Structure (Conceptual)

**Not a DocType** - In-memory cache layer

#### Key Structure
```
Key:    srs:{user_email}:{season_name}
Type:   Sorted Set (ZSET)
Score:  Unix timestamp (float) of next_review_date
Member: question_id (string)
TTL:    None (managed by archival process)
```

#### Examples
```redis
# User with 3 questions scheduled
srs:student@example.com:SEASON-2026
  Score: 1737380000  Member: "Q-UUID-001"  (Jan 20, 2026)
  Score: 1737466400  Member: "Q-UUID-002"  (Jan 21, 2026)
  Score: 1737552800  Member: "Q-UUID-003"  (Jan 22, 2026)
```

#### Operations
| Operation | Command | Use Case |
|-----------|---------|----------|
| Add/Update | `ZADD key score member` | After review session |
| Get due | `ZRANGEBYSCORE key -inf {now} LIMIT 0 N` | Get review session |
| Remove | `ZREM key member` | After question deleted |
| Count due | `ZCOUNT key -inf {now}` | Dashboard stats |
| Get all | `ZRANGE key 0 -1 WITHSCORES` | Rehydration verification |

---

## State Transitions

### Season Lifecycle

```
                    ┌──────────────┐
                    │   Created    │
                    │ is_active=0  │
                    │ partition=0  │
                    └──────┬───────┘
                           │ after_insert hook
                           ▼
                    ┌──────────────┐
                    │   Ready      │
                    │ is_active=0  │
                    │ partition=1  │
                    └──────┬───────┘
                           │ admin activates
                           ▼
                    ┌──────────────┐
         ┌─────────│   Active     │─────────┐
         │         │ is_active=1  │         │
         │         │ enable_redis │         │
         │         └──────────────┘         │
         │                                  │
    auto_archive=0                    auto_archive=1
         │                                  │
         ▼                                  ▼
  ┌──────────────┐                  ┌──────────────┐
  │   Inactive   │                  │   Archived   │
  │ is_active=0  │                  │ is_active=0  │
  │ data remains │                  │ data moved   │
  └──────────────┘                  │ cache cleared│
                                    └──────────────┘
```

### Memory Tracker Record Lifecycle

```
┌─────────────────┐
│  New Question   │
│  stability=0    │
│  Redis: ZADD    │
│  DB: INSERT     │
└────────┬────────┘
         │ student reviews
         ▼
┌─────────────────┐
│   Learning      │◄───────┐
│  stability=1-2  │        │
│  Redis: ZADD    │        │ poor recall
│  DB: UPDATE     │        │
└────────┬────────┘        │
         │ good recall     │
         ▼                 │
┌─────────────────┐        │
│    Mature       │────────┘
│  stability=3-4  │
│  Redis: ZADD    │
│  DB: UPDATE     │
└────────┬────────┘
         │ season ends + auto_archive
         ▼
┌─────────────────┐
│   Archived      │
│  Redis: ZREM    │
│  DB: MOVE       │
└─────────────────┘
```

---

## Relationships

### Entity Relationship Summary

| From | To | Type | Foreign Key |
|------|-----|------|-------------|
| Player Memory Tracker | User | N:1 | `player` |
| Player Memory Tracker | Game Subscription Season | N:1 | `season` |
| Player Memory Tracker | Game Subject | N:1 | `subject` (optional) |
| Player Memory Tracker | Game Topic | N:1 | `topic` (optional) |
| Archived Memory Tracker | User | N:1 | `player` |
| Archived Memory Tracker | Game Subscription Season | N:1 | `season` |

### Cache-Database Relationship

```
┌─────────────────────────────────────────────────────────┐
│                    Read Flow                            │
│                                                         │
│  Request ──► Redis ZRANGEBYSCORE                        │
│                    │                                    │
│               Cache Hit? ──► Yes ──► Return IDs         │
│                    │                                    │
│                   No (miss)                             │
│                    │                                    │
│                    ▼                                    │
│              DB SELECT ──► Populate Redis ──► Return    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    Write Flow                           │
│                                                         │
│  Request ──► Redis ZADD (sync) ──► Return 200 OK        │
│                    │                                    │
│                    ▼                                    │
│           frappe.enqueue()                              │
│                    │                                    │
│                    ▼                                    │
│           Background Worker                             │
│                    │                                    │
│                    ▼                                    │
│           DB INSERT/UPDATE                              │
└─────────────────────────────────────────────────────────┘
```

---

## Migration Notes

### Phase 1: Schema Updates
1. Add new fields to `Game Subscription Season` DocType JSON
2. Create `Archived Memory Tracker` DocType
3. Run `bench migrate`

### Phase 2: Data Migration (Patch)
1. Set `season` to current active season for existing records with NULL
2. Apply partitioning via raw SQL
3. Create initial partitions for existing seasons

### Phase 3: Index Creation
1. Add composite index for Safe Mode queries
2. Verify index usage with EXPLAIN

### Rollback Plan
1. Remove partitioning: `ALTER TABLE ... REMOVE PARTITIONING`
2. Revert DocType changes
3. Redis data can be flushed (DB is source of truth)
