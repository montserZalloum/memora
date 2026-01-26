# Research & Technical Decisions: Player Core

**Feature**: 007-player-core | **Date**: 2026-01-26
**Purpose**: Document technical research, decisions, rationale, and alternatives for Player Core implementation

## Table of Contents

1. [Device Identification Strategy](#device-identification-strategy)
2. [Session Management Architecture](#session-management-architecture)
3. [Redis Data Structures for Caching](#redis-data-structures-for-caching)
4. [Batch Synchronization Pattern](#batch-synchronization-pattern)
5. [Streak Calculation Logic](#streak-calculation-logic)
6. [Cache Failure Recovery](#cache-failure-recovery)
7. [DocType Schema Design](#doctype-schema-design)
8. [API Security & Rate Limiting](#api-security--rate-limiting)

---

## Device Identification Strategy

### Decision
Use **client-generated UUID v4** transmitted in custom HTTP header `X-Device-ID` for device identification.

### Rationale
- **UUID v4** provides sufficient entropy (2^122 unique values) to prevent collisions across millions of devices
- **Client-generated** enables first-device auto-authorization during account creation without server-side device fingerprinting
- **Custom header** separates device identity from user authentication (session token), enabling independent validation
- **Frappe-compatible** works with existing Frappe authentication without modifications

### Implementation Details
```python
# Client sends on every request:
Headers: {
    "Authorization": "token xxx:yyy",
    "X-Device-ID": "550e8400-e29b-41d4-a716-446655440000"
}

# Server validation flow:
1. Extract device_id from X-Device-ID header
2. Query Redis Set: SADD player:{user_id}:devices
3. If device_id not in set, reject (403 Forbidden)
4. If in set, proceed with request
```

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| **Server-side fingerprinting** (User-Agent + IP + Canvas) | Unreliable (VPNs, browser updates, privacy tools invalidate fingerprints); violates GDPR/privacy principles; complex to implement reliably |
| **MAC address** | Not accessible from browser; security risk if transmitted; privacy violation |
| **Device registration tokens** (OAuth device flow) | Overcomplicated for educational platform; requires additional OAuth server; poor UX for students |
| **Session cookies only** | Cannot distinguish between devices; fails device authorization requirement |

### Related Frappe Patterns
- Frappe uses similar approach for API key auth: `frappe.get_request_header()`
- Compatible with existing `@frappe.whitelist()` decorator

---

## Session Management Architecture

### Decision
Implement **Redis-based single-session lock** using key pattern `active_session:{user_id}` storing latest session ID with timestamp.

### Rationale
- **Sub-2ms latency**: Redis GET operation meets <2ms session verification requirement
- **Atomic operations**: Redis SETNX/GETSET provide race-condition-free session updates
- **Persistent sessions**: No TTL on session keys (explicit invalidation only)
- **Simple conflict resolution**: Last login wins (latest SETNX overwrites previous session_id)

### Implementation Details
```python
# Session creation flow:
def create_session(user_id, device_id):
    session_id = generate_session_token()  # Frappe's built-in
    redis_key = f"active_session:{user_id}"

    # Atomic session replacement
    old_session = redis_client.getset(redis_key, session_id)

    # Log previous session for debugging
    if old_session and old_session != session_id:
        log_session_replacement(user_id, old_session, session_id)

    # Store session metadata
    redis_client.hset(f"session:{session_id}", mapping={
        "user_id": user_id,
        "device_id": device_id,
        "created_at": now()
    })

    return session_id

# Session validation (on every API request):
def validate_session(user_id, current_session_id):
    active_session = redis_client.get(f"active_session:{user_id}")

    if active_session != current_session_id:
        raise SessionInvalidated("Another device has logged in")

    # Session is valid
    return True
```

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| **Database session table** | Too slow (50-100ms query latency); cannot meet <2ms requirement; excessive DB load for 10k concurrent users |
| **JWT with short expiry** | Cannot enforce single-session (tokens are stateless); requires complex token revocation system |
| **WebSocket heartbeat** | Requires maintaining persistent connections; complex infrastructure; doesn't work for API-only clients |
| **Frappe's built-in session** (sid cookie) | Already in use; need additional layer for single-session enforcement; doesn't invalidate on conflict |

### Edge Case Handling
- **Simultaneous logins**: GETSET is atomic; both clients get session token, but only latest is valid
- **Session invalidation on device removal**: Admin action triggers `DEL active_session:{user_id}` + `DEL session:{session_id}`
- **Cache failure**: Fallback to "allow all sessions" mode with warning logged; restore from DB on recovery

---

## Redis Data Structures for Caching

### Decision
Use **four Redis data structures** optimized for different access patterns:

1. **Authorized Devices**: `SET player:{user_id}:devices` → `{device_id1, device_id2}`
2. **Active Session**: `STRING active_session:{user_id}` → `{session_id}`
3. **Wallet State**: `HASH wallet:{user_id}` → `{total_xp, current_streak, last_success_date, last_played_at}`
4. **Pending Sync Queue**: `SET pending_wallet_sync` → `{user_id1, user_id2, ...}`

### Rationale

#### 1. Authorized Devices (SET)
- **O(1) membership check** via `SISMEMBER` (meets <2ms requirement)
- **Max 2 elements** per set (device limit) keeps memory footprint minimal
- **Natural deduplication** (SET semantics prevent duplicate device IDs)

#### 2. Active Session (STRING)
- **Simplest structure** for single value storage
- **Atomic GET/SET** operations prevent race conditions
- **No expiration** (persistent sessions per clarification)

#### 3. Wallet State (HASH)
- **Atomic field updates** via `HINCRBY` for XP increments
- **Partial reads** via `HGET total_xp` (don't need full wallet every time)
- **Single key** per player reduces key namespace pollution
- **Type safety** (integer fields for counters, string for dates)

#### 4. Pending Sync Queue (SET)
- **Automatic deduplication** (multiple XP updates = one sync entry)
- **O(1) addition** via `SADD` during XP update
- **Bulk retrieval** via `SMEMBERS` during batch job
- **Atomic removal** via `SPOP` prevents duplicate syncing

### Implementation Details
```python
# Device authorization check:
def is_device_authorized(user_id, device_id):
    return redis_client.sismember(f"player:{user_id}:devices", device_id)

# XP increment:
def add_xp(user_id, xp_amount):
    wallet_key = f"wallet:{user_id}"
    redis_client.hincrby(wallet_key, "total_xp", xp_amount)
    redis_client.sadd("pending_wallet_sync", user_id)  # Queue for sync

# Wallet read (cache-first):
def get_wallet(user_id):
    wallet_data = redis_client.hgetall(f"wallet:{user_id}")
    if not wallet_data:
        # Cache miss - load from DB and populate cache
        wallet_data = load_wallet_from_db(user_id)
        redis_client.hset(f"wallet:{user_id}", mapping=wallet_data)
    return wallet_data
```

### Memory Estimation
```
Per player:
- Devices SET: ~100 bytes (2 UUIDs @ 36 chars each)
- Session STRING: ~50 bytes (session_id)
- Wallet HASH: ~200 bytes (4 fields with metadata)
Total per player: ~350 bytes

10,000 concurrent players: 3.5 MB
50,000 total active players: 17.5 MB (easily fits in Redis)
```

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| **Single HASH for all player data** | Too large; cannot partially update; slow HGETALL for all fields |
| **LIST for device history** | Need fast membership check, not ordering; SET is O(1), LIST is O(N) |
| **ZSET for wallet with scores** | Overcomplicated; don't need ordering/ranking; HASH is simpler |
| **Redis Streams for sync queue** | Overkill for simple set of pending IDs; SET is lighter weight |

---

## Batch Synchronization Pattern

### Decision
Implement **15-minute scheduled job** using **RQ (Redis Queue)** with **chunked bulk updates** (500 players per chunk).

### Rationale
- **RQ integration**: Already used in Frappe ecosystem (002-cdn-content-export, 005-progress-engine-bitset)
- **Scheduled execution**: Frappe's `scheduler_events` hook provides reliable 15-min intervals
- **Chunking**: Prevents long-running transactions; allows progress tracking; limits memory usage
- **Idempotent**: Can safely retry failed chunks without duplication

### Implementation Details
```python
# hooks.py registration:
scheduler_events = {
    "cron": {
        "*/15 * * * *": [  # Every 15 minutes
            "memora.services.wallet_sync.sync_pending_wallets"
        ]
    }
}

# Batch sync job:
def sync_pending_wallets():
    # Get all pending user IDs
    pending_users = redis_client.smembers("pending_wallet_sync")

    if not pending_users:
        return {"synced": 0, "duration": 0}

    # Process in chunks of 500
    chunks = chunk_list(list(pending_users), 500)
    synced_count = 0

    for chunk in chunks:
        # Bulk read from Redis
        wallet_data = {}
        for user_id in chunk:
            wallet_data[user_id] = redis_client.hgetall(f"wallet:{user_id}")

        # Bulk update to MariaDB
        frappe.db.bulk_update({
            "doctype": "Memora Player Wallet",
            "updates": [
                {
                    "name": f"wallet_{user_id}",
                    "total_xp": data["total_xp"],
                    "current_streak": data["current_streak"],
                    "last_success_date": data["last_success_date"],
                    "last_played_at": data["last_played_at"]
                }
                for user_id, data in wallet_data.items()
            ]
        })

        # Remove from pending queue (atomic)
        redis_client.srem("pending_wallet_sync", *chunk)
        synced_count += len(chunk)

    frappe.db.commit()
    return {"synced": synced_count, "duration": time.time() - start}
```

### Performance Estimation
```
50,000 pending updates:
- 100 chunks @ 500 players each
- ~30ms per chunk (bulk update)
- Total: ~3 seconds (well under 5-minute requirement)
```

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| **Real-time DB writes** | 90%+ reduction requirement; 10k concurrent users = 10k writes/sec unsustainable |
| **Event-driven sync** (on every 10th XP update) | Unpredictable; violates 15-minute lag guarantee; complex logic |
| **Celery** | Additional dependency; RQ already in use and sufficient |
| **Frappe's `enqueue_doc`** | Too granular; need batch processing not individual doc queues |

---

## Streak Calculation Logic

### Decision
Implement **date-based streak logic** using **server time (UTC)** with three states: increment, maintain, reset.

### Rationale
- **Server time authority**: Prevents client clock manipulation (security requirement FR-027)
- **Date-only comparison**: Ignores time-of-day; streak persists across midnight
- **Simple state machine**: No complex time window calculations
- **UTC standardization**: Consistent across time zones

### Implementation Details
```python
def update_streak(user_id, lesson_hearts):
    if lesson_hearts <= 0:
        return  # No streak update for failed lessons

    # Get current wallet state from cache
    wallet = redis_client.hgetall(f"wallet:{user_id}")
    current_streak = int(wallet.get("current_streak", 0))
    last_success_date = wallet.get("last_success_date")  # "YYYY-MM-DD" format

    # Server time (UTC)
    today = datetime.utcnow().date()
    today_str = today.isoformat()

    # Streak logic (FR-028)
    if not last_success_date:
        # First lesson ever (FR-022b)
        new_streak = 1
    elif last_success_date == today_str:
        # Same day - no change (FR-025)
        new_streak = current_streak
    elif is_consecutive_day(last_success_date, today):
        # Next day - increment (FR-023)
        new_streak = current_streak + 1
    else:
        # Gap > 1 day - reset (FR-024)
        new_streak = 1

    # Update cache (atomic)
    redis_client.hset(f"wallet:{user_id}", mapping={
        "current_streak": new_streak,
        "last_success_date": today_str
    })

    # Queue for DB sync
    redis_client.sadd("pending_wallet_sync", user_id)

def is_consecutive_day(last_date_str, today):
    last_date = datetime.fromisoformat(last_date_str).date()
    return (today - last_date).days == 1
```

### Edge Cases Handled
- **First lesson**: Streak 0 → 1 (clarification answer)
- **Midnight boundary**: Date changes at 00:00 UTC; consistent for all users
- **Multiple lessons same day**: Only first lesson updates streak (FR-025)
- **Long gap**: Automatically resets to 1, not 0 (per FR-024)

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| **Client-reported time** | Easily gamed; violates security requirement |
| **24-hour rolling window** | Complex; doesn't align with human understanding of "daily" |
| **Time zone per student** | Inconsistent; enables gaming by changing time zones; complex to implement |
| **Streak resets to 0 on gap** | Clarification specified reset to 1 for UX (immediate re-engagement) |

---

## Cache Failure Recovery

### Decision
Implement **graceful degradation with AOF persistence** and **automatic cache repopulation** on recovery.

### Rationale
- **AOF (Append-Only File)**: Redis persistence mode for durability (FR-038)
- **Graceful degradation**: System continues with DB reads (slower but functional)
- **Automatic recovery**: No manual intervention required (SC-015)
- **Accepted lag**: 15-minute staleness acceptable (FR-039)

### Implementation Details
```python
# Cache read with fallback:
def get_wallet_safe(user_id):
    try:
        # Try cache first (FR-019a)
        wallet_data = redis_client.hgetall(f"wallet:{user_id}")
        if wallet_data:
            return wallet_data
    except redis.ConnectionError:
        frappe.log_error("Redis unavailable - using DB fallback")

    # Fallback to DB (may be up to 15 min stale)
    wallet_doc = frappe.get_doc("Memora Player Wallet", f"wallet_{user_id}")
    wallet_data = {
        "total_xp": wallet_doc.total_xp,
        "current_streak": wallet_doc.current_streak,
        "last_success_date": wallet_doc.last_success_date,
        "last_played_at": wallet_doc.last_played_at
    }

    # Try to repopulate cache
    try:
        redis_client.hset(f"wallet:{user_id}", mapping=wallet_data)
    except redis.ConnectionError:
        pass  # Will retry on next request

    return wallet_data

# Session validation fallback:
def validate_session_safe(user_id, session_id):
    try:
        return validate_session(user_id, session_id)
    except redis.ConnectionError:
        # CRITICAL: Cannot enforce single-session without Redis
        # Allow through with warning
        frappe.log_error("Redis down - single-session enforcement disabled")
        return True  # Fail open for availability
```

### Recovery Strategy
1. **Redis restart**: AOF file replays all writes; full data restoration
2. **Data corruption**: Fall back to DB; trigger full cache rebuild job
3. **Network partition**: Temporary; retry with exponential backoff

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| **RDB snapshots only** | Point-in-time; loses data between snapshots; AOF is more durable |
| **Fail closed on cache miss** | Poor availability; violates 99.9% uptime requirement |
| **Dual-write to cache and DB** | Eliminates batching benefit; defeats performance goals |
| **Redis Cluster** | Overcomplicated for 50k players; single Redis instance sufficient |

---

## DocType Schema Design

### Decision
Create **three DocTypes** with **child table relationship** following Frappe's ORM patterns.

### DocType 1: Memora Player Profile

**Purpose**: Central identity hub linking Frappe User to player-specific data

```json
{
  "name": "Memora Player Profile",
  "fields": [
    {
      "fieldname": "user",
      "label": "User",
      "fieldtype": "Link",
      "options": "User",
      "reqd": 1,
      "unique": 1
    },
    {
      "fieldname": "grade",
      "label": "Grade",
      "fieldtype": "Link",
      "options": "Memora Grade",
      "reqd": 1
    },
    {
      "fieldname": "stream",
      "label": "Stream",
      "fieldtype": "Link",
      "options": "Memora Stream"
    },
    {
      "fieldname": "season",
      "label": "Season",
      "fieldtype": "Link",
      "options": "Memora Season",
      "reqd": 1
    },
    {
      "fieldname": "academic_plan",
      "label": "Academic Plan",
      "fieldtype": "Link",
      "options": "Memora Academic Plan",
      "reqd": 1
    },
    {
      "fieldname": "photo",
      "label": "Photo",
      "fieldtype": "Attach Image"
    },
    {
      "fieldname": "authorized_devices",
      "label": "Authorized Devices",
      "fieldtype": "Table",
      "options": "Memora Authorized Device"
    }
  ],
  "permissions": [
    {
      "role": "Student",
      "read": 1,
      "write": 0
    },
    {
      "role": "System Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "delete": 1
    }
  ]
}
```

### DocType 2: Memora Authorized Device (Child Table)

**Purpose**: Store device authorization records (max 2 per profile)

```json
{
  "name": "Memora Authorized Device",
  "istable": 1,
  "fields": [
    {
      "fieldname": "device_id",
      "label": "Device ID",
      "fieldtype": "Data",
      "reqd": 1,
      "unique": 1
    },
    {
      "fieldname": "device_name",
      "label": "Device Name",
      "fieldtype": "Data",
      "reqd": 1
    },
    {
      "fieldname": "added_on",
      "label": "Added On",
      "fieldtype": "Datetime",
      "default": "Now",
      "read_only": 1
    }
  ]
}
```

### DocType 3: Memora Player Wallet

**Purpose**: Persistent storage for XP and streak data

```json
{
  "name": "Memora Player Wallet",
  "fields": [
    {
      "fieldname": "player",
      "label": "Player",
      "fieldtype": "Link",
      "options": "Memora Player Profile",
      "reqd": 1,
      "unique": 1
    },
    {
      "fieldname": "total_xp",
      "label": "Total XP",
      "fieldtype": "Int",
      "default": "0",
      "non_negative": 1
    },
    {
      "fieldname": "current_streak",
      "label": "Current Streak",
      "fieldtype": "Int",
      "default": "0",
      "non_negative": 1
    },
    {
      "fieldname": "last_success_date",
      "label": "Last Success Date",
      "fieldtype": "Date"
    },
    {
      "fieldname": "last_played_at",
      "label": "Last Played At",
      "fieldtype": "Datetime"
    }
  ],
  "permissions": [
    {
      "role": "Student",
      "read": 1,
      "write": 0
    },
    {
      "role": "System Manager",
      "read": 1,
      "write": 1
    }
  ]
}
```

### Validation Hooks

```python
# In memora_player_profile.py:
def validate(self):
    # FR-005b: Enforce 2-device limit
    if len(self.authorized_devices) > 2:
        frappe.throw("Maximum 2 authorized devices allowed per student")

    # FR-005a: Auto-authorize first device on creation
    if self.is_new() and not self.authorized_devices:
        # Device ID will be passed in context during account creation
        first_device_id = frappe.local.device_id
        if first_device_id:
            self.append("authorized_devices", {
                "device_id": first_device_id,
                "device_name": "First Device (Auto-authorized)"
            })

# In memora_player_wallet.py:
def validate(self):
    # Ensure streak doesn't go negative
    if self.current_streak < 0:
        self.current_streak = 0
```

### Rationale for Schema Choices
- **1:1 User-Profile relationship**: Prevents duplicate player profiles per user
- **Child Table for devices**: Frappe's native 1:many pattern; enforces parent-child lifecycle
- **Separate Wallet DocType**: Allows independent caching/syncing without affecting profile reads
- **Non-negative constraints**: Data integrity at schema level
- **Read-only timestamps**: Prevent tampering

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| **Single "Player" DocType with all fields** | Too large; frequent wallet updates would lock profile reads |
| **JSON field for devices** | Loses Frappe's table UI; no validation; harder to query |
| **Separate Device DocType (not child)** | Overcomplicated; parent-child is Frappe best practice for 1:many |
| **Wallet as custom fields on User** | Frappe User is core doctype; extending risks upgrade conflicts |

---

## API Security & Rate Limiting

### Decision
Implement **Frappe's built-in auth** with **custom device validation middleware** and **Redis-based rate limiting**.

### Rationale
- **Frappe auth**: Already implemented (`@frappe.whitelist(allow_guest=False)`)
- **Device middleware**: Custom check after auth, before business logic
- **Rate limiting**: Redis INCR with TTL prevents abuse

### Implementation Details

```python
# Decorator for device-authorized endpoints:
def require_authorized_device(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = frappe.session.user
        device_id = frappe.get_request_header("X-Device-ID")

        if not device_id:
            frappe.throw("Device ID required", frappe.MissingDeviceError)

        # FR-010: Device check in <2ms (Redis)
        if not is_device_authorized(user_id, device_id):
            frappe.throw("Unauthorized device. Contact administrator.",
                        frappe.PermissionError)

        # FR-016: Session validation in <2ms
        session_id = frappe.session.sid
        if not validate_session(user_id, session_id):
            frappe.throw("Session invalidated on another device",
                        frappe.SessionExpired)

        return fn(*args, **kwargs)
    return wrapper

# Rate limiting:
def rate_limit(max_requests=100, window_seconds=60):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = frappe.session.user
            key = f"rate_limit:{user_id}:{fn.__name__}"

            # Increment counter
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, window_seconds)

            if count > max_requests:
                frappe.throw(f"Rate limit exceeded: {max_requests} requests per {window_seconds}s")

            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Example endpoint:
@frappe.whitelist(allow_guest=False)
@require_authorized_device
@rate_limit(max_requests=10, window_seconds=60)
def complete_lesson(lesson_id, hearts_earned):
    # Business logic here
    pass
```

### Rate Limiting Strategy

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `complete_lesson` | 10/min | Prevent rapid-fire fake completions |
| `get_wallet` | 60/min | Allow frequent UI refreshes |
| `login` | 5/min | Prevent brute force |
| `register_device` | 3/hour | Device changes are rare |

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|--------------|
| **JWT tokens** | Stateless; cannot revoke on session conflict; incompatible with Frappe |
| **OAuth 2.0** | Overcomplicated; Frappe has built-in auth |
| **Database-based rate limiting** | Too slow; Redis INCR is O(1) and fast |
| **Nginx rate limiting** | Applies to IP, not user; doesn't handle per-user logic |

---

## Summary of Key Decisions

| Decision Area | Choice | Primary Justification |
|---------------|--------|----------------------|
| **Device ID** | Client-generated UUID v4 in header | Enables first-device auto-auth; sufficient entropy |
| **Session Management** | Redis single-session lock | Sub-2ms latency; atomic operations |
| **Caching Strategy** | 4 Redis structures (SET/STRING/HASH) | Optimized for access patterns; minimal memory |
| **Batch Sync** | RQ 15-min scheduled job, 500-player chunks | Existing infrastructure; meets performance goals |
| **Streak Logic** | Date-based with server UTC time | Prevents manipulation; simple state machine |
| **Cache Recovery** | AOF persistence + graceful degradation | Durability + availability balance |
| **Schema** | 3 DocTypes (Profile, Wallet, Device child) | Frappe best practices; separation of concerns |
| **API Security** | Frappe auth + device middleware + Redis rate limit | Layered security; leverages existing infra |

---

## Next Steps (Phase 1)

1. ✅ Research complete
2. ⏭️ Generate `data-model.md` (detailed entity schemas)
3. ⏭️ Create API contracts in `/contracts/` (OpenAPI specs)
4. ⏭️ Write `quickstart.md` (developer onboarding guide)
5. ⏭️ Update CLAUDE.md with new technologies

**Estimated Research Duration**: 2 hours
**Confidence Level**: High (leveraging proven Frappe patterns + Redis best practices)
