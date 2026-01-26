# Data Model: Player Core

**Feature**: 007-player-core | **Date**: 2026-01-26
**Purpose**: Detailed entity schemas, relationships, and validation rules

## Entity Relationship Diagram

```
┌─────────────────────────────────┐
│         Frappe User             │
│  (existing core DocType)        │
│                                 │
│  - name (email)                 │
│  - full_name                    │
│  - enabled                      │
└─────────────┬───────────────────┘
              │ 1:1
              │
              ▼
┌─────────────────────────────────┐
│   Memora Player Profile         │
│                                 │
│  - name (auto)                  │
│  - user (Link)                  │
│  - grade (Link)                 │
│  - stream (Link)                │
│  - season (Link)                │
│  - academic_plan (Link)         │
│  - photo (Attach Image)         │
│  - authorized_devices (Table)   │
└─────────────┬───────────────────┘
              │ 1:many
              │
              ▼
┌─────────────────────────────────┐
│  Memora Authorized Device       │
│      (Child Table)              │
│                                 │
│  - device_id (UUID)             │
│  - device_name (string)         │
│  - added_on (datetime)          │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│   Memora Player Profile         │
└─────────────┬───────────────────┘
              │ 1:1
              │
              ▼
┌─────────────────────────────────┐
│   Memora Player Wallet          │
│                                 │
│  - name (auto)                  │
│  - player (Link)                │
│  - total_xp (int)               │
│  - current_streak (int)         │
│  - last_success_date (date)     │
│  - last_played_at (datetime)    │
└─────────────────────────────────┘
```

## Entities

### 1. Memora Player Profile

**Purpose**: Central identity DocType linking Frappe User to player-specific educational context and device authorizations.

#### Fields

| Field Name | Field Type | Options/Link | Required | Unique | Default | Validation |
|------------|-----------|--------------|----------|---------|---------|------------|
| `name` | Data | - | Yes (auto) | Yes | Auto-generated | Frappe naming series |
| `user` | Link | User | Yes | Yes | - | Must exist in User table |
| `grade` | Link | Memora Grade | Yes | No | - | Must exist |
| `stream` | Link | Memora Stream | No | No | - | Must exist if set |
| `season` | Link | Memora Season | Yes | No | - | Must exist |
| `academic_plan` | Link | Memora Academic Plan | Yes | No | - | Must exist |
| `photo` | Attach Image | - | No | No | - | Valid image file |
| `authorized_devices` | Table | Memora Authorized Device | No | No | `[]` | Max 2 rows (FR-005b) |

#### Validation Rules

```python
def validate(self):
    """
    FR-005b: Enforce maximum 2 authorized devices
    FR-005a: Auto-authorize first device on creation
    """
    # Device limit check
    if len(self.authorized_devices) > 2:
        frappe.throw(_("Maximum 2 authorized devices allowed per student"))

    # Ensure unique device IDs within this profile
    device_ids = [d.device_id for d in self.authorized_devices]
    if len(device_ids) != len(set(device_ids)):
        frappe.throw(_("Duplicate device IDs are not allowed"))

    # Auto-authorize first device on new profile creation
    if self.is_new() and not self.authorized_devices:
        first_device_id = frappe.local.get("device_id")
        if first_device_id:
            self.append("authorized_devices", {
                "device_id": first_device_id,
                "device_name": "First Device (Auto-authorized)",
                "added_on": frappe.utils.now()
            })
```

#### Lifecycle Hooks

```python
def after_insert(self):
    """
    FR-018: Create wallet with zero XP on profile creation
    FR-022a: Initialize streak at 0
    """
    wallet = frappe.new_doc("Memora Player Wallet")
    wallet.player = self.name
    wallet.total_xp = 0
    wallet.current_streak = 0
    wallet.last_success_date = None
    wallet.last_played_at = None
    wallet.insert(ignore_permissions=True)

    # Populate Redis cache with device list
    redis_client = frappe.cache()
    device_key = f"player:{self.user}:devices"
    for device in self.authorized_devices:
        redis_client.sadd(device_key, device.device_id)

def on_update(self):
    """Sync device changes to Redis cache"""
    redis_client = frappe.cache()
    device_key = f"player:{self.user}:devices"

    # Clear old cache
    redis_client.delete(device_key)

    # Rebuild from current state
    for device in self.authorized_devices:
        redis_client.sadd(device_key, device.device_id)

    # If device removed, invalidate any active sessions from that device
    # (session_id is not device-specific, so invalidate all sessions)
    session_key = f"active_session:{self.user}"
    redis_client.delete(session_key)
```

#### Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Student | ✅ (own) | ❌ | ❌ | ❌ |
| System Manager | ✅ | ✅ | ✅ | ✅ |
| Teacher | ✅ | ❌ | ❌ | ❌ |

#### State Transitions

N/A (no workflow states)

---

### 2. Memora Authorized Device (Child Table)

**Purpose**: Store device authorization records with timestamp tracking.

#### Fields

| Field Name | Field Type | Required | Unique | Default | Validation |
|------------|-----------|----------|---------|---------|------------|
| `device_id` | Data (UUID) | Yes | Yes (global) | - | Valid UUID v4 format |
| `device_name` | Data | Yes | No | - | Max 100 chars |
| `added_on` | Datetime | Yes | No | `Now` | Read-only after insert |

#### Validation Rules

```python
def validate(self):
    """FR-006: Validate device ID format and name"""
    import uuid

    # Validate UUID format
    try:
        uuid.UUID(self.device_id, version=4)
    except ValueError:
        frappe.throw(_("Invalid device ID format. Must be UUID v4."))

    # Ensure device_name is meaningful
    if not self.device_name or len(self.device_name.strip()) < 3:
        frappe.throw(_("Device name must be at least 3 characters"))

    # Set added_on timestamp if new
    if not self.added_on:
        self.added_on = frappe.utils.now()
```

#### Notes
- **Global uniqueness**: One device ID cannot be authorized for multiple students (prevents device sharing)
- **Immutable timestamp**: `added_on` cannot be changed after creation (audit trail)

---

### 3. Memora Player Wallet

**Purpose**: Store persistent XP and streak data; synchronized from Redis cache via batch job.

#### Fields

| Field Name | Field Type | Options/Link | Required | Unique | Default | Validation |
|------------|-----------|--------------|----------|---------|---------|------------|
| `name` | Data | - | Yes (auto) | Yes | Auto-generated | Frappe naming |
| `player` | Link | Memora Player Profile | Yes | Yes | - | Must exist |
| `total_xp` | Int | - | Yes | No | `0` | Non-negative |
| `current_streak` | Int | - | Yes | No | `0` | Non-negative |
| `last_success_date` | Date | - | No | No | `None` | Valid date or null |
| `last_played_at` | Datetime | - | No | No | `None` | Valid datetime or null |

#### Validation Rules

```python
def validate(self):
    """
    FR-018: Ensure non-negative XP
    FR-022a: Ensure non-negative streak
    """
    if self.total_xp < 0:
        frappe.throw(_("Total XP cannot be negative"))

    if self.current_streak < 0:
        self.current_streak = 0  # Auto-correct instead of error

    # Validate last_success_date is not in future
    if self.last_success_date:
        from datetime import date
        if date.fromisoformat(self.last_success_date) > date.today():
            frappe.throw(_("Last success date cannot be in the future"))
```

#### Lifecycle Hooks

```python
def after_insert(self):
    """Populate Redis cache on wallet creation"""
    redis_client = frappe.cache()
    wallet_key = f"wallet:{self.player}"

    wallet_data = {
        "total_xp": self.total_xp,
        "current_streak": self.current_streak,
        "last_success_date": self.last_success_date or "",
        "last_played_at": self.last_played_at or ""
    }

    redis_client.hset(wallet_key, mapping=wallet_data)

def on_trash(self):
    """Clean up Redis cache on wallet deletion"""
    redis_client = frappe.cache()
    wallet_key = f"wallet:{self.player}"
    redis_client.delete(wallet_key)

    # Remove from pending sync queue
    redis_client.srem("pending_wallet_sync", self.player)
```

#### Permissions

| Role | Read | Write | Create | Delete |
|------|------|-------|--------|--------|
| Student | ✅ (own) | ❌ | ❌ | ❌ |
| System Manager | ✅ | ✅ | ✅ | ✅ |
| Teacher | ✅ | ❌ | ❌ | ❌ |

#### Indexes

```sql
-- Performance optimization for batch sync queries
CREATE INDEX idx_player_wallet_player ON `tabMemora Player Wallet`(player);

-- Quick lookups for admin dashboards
CREATE INDEX idx_player_wallet_streak ON `tabMemora Player Wallet`(current_streak DESC);
CREATE INDEX idx_player_wallet_xp ON `tabMemora Player Wallet`(total_xp DESC);
```

---

## Redis Cache Structures

**Purpose**: High-speed read/write for session, device, and wallet operations.

### 1. Authorized Devices

**Key Pattern**: `player:{user_id}:devices`
**Type**: SET
**TTL**: None (persistent)

**Example**:
```
Key: player:student@example.com:devices
Value: {
    "550e8400-e29b-41d4-a716-446655440000",
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
}
```

**Operations**:
- **Add device**: `SADD player:{user_id}:devices {device_id}`
- **Check authorization**: `SISMEMBER player:{user_id}:devices {device_id}` (O(1))
- **List devices**: `SMEMBERS player:{user_id}:devices`
- **Remove device**: `SREM player:{user_id}:devices {device_id}`

---

### 2. Active Session

**Key Pattern**: `active_session:{user_id}`
**Type**: STRING
**TTL**: None (persistent sessions per clarification)

**Example**:
```
Key: active_session:student@example.com
Value: "abc123xyz789sessiontoken"
```

**Operations**:
- **Create/replace session**: `SET active_session:{user_id} {session_id}`
- **Validate session**: `GET active_session:{user_id}` → compare with current session
- **Invalidate session**: `DEL active_session:{user_id}`

---

### 3. Wallet State

**Key Pattern**: `wallet:{user_id}`
**Type**: HASH
**TTL**: None (persistent)

**Example**:
```
Key: wallet:student@example.com
Fields: {
    "total_xp": "1250",
    "current_streak": "7",
    "last_success_date": "2026-01-26",
    "last_played_at": "2026-01-26T14:32:15"
}
```

**Operations**:
- **Increment XP**: `HINCRBY wallet:{user_id} total_xp {amount}`
- **Update streak**: `HSET wallet:{user_id} current_streak {new_value}`
- **Read full wallet**: `HGETALL wallet:{user_id}`
- **Read single field**: `HGET wallet:{user_id} total_xp`

---

### 4. Pending Sync Queue

**Key Pattern**: `pending_wallet_sync`
**Type**: SET (global, not per-user)
**TTL**: None

**Example**:
```
Key: pending_wallet_sync
Value: {
    "student1@example.com",
    "student2@example.com",
    "student3@example.com"
}
```

**Operations**:
- **Queue for sync**: `SADD pending_wallet_sync {user_id}`
- **Get all pending**: `SMEMBERS pending_wallet_sync`
- **Remove after sync**: `SREM pending_wallet_sync {user_id}`
- **Batch pop**: `SPOP pending_wallet_sync {count}`

---

## Data Relationships

### Primary Relationships

1. **User → Player Profile** (1:1)
   - **Constraint**: One Frappe User can have only one Player Profile
   - **Cascade**: Delete User → Delete Profile (via Frappe link cascade)

2. **Player Profile → Authorized Devices** (1:many, max 2)
   - **Constraint**: Max 2 devices per profile (enforced in validate)
   - **Cascade**: Delete Profile → Delete Devices (child table cascade)

3. **Player Profile → Wallet** (1:1)
   - **Constraint**: One Profile has exactly one Wallet
   - **Cascade**: Delete Profile → Delete Wallet (via Frappe link cascade)

### Referential Integrity

- **Foreign Keys**: Frappe enforces Link field integrity automatically
- **Orphan Prevention**: Cannot delete referenced User, Grade, Stream, Season, or Academic Plan
- **Cascade Rules**: Defined in DocType JSON schema

---

## Data Volume Estimates

### Per-Student Footprint

**MariaDB**:
- Player Profile: ~500 bytes (including 2 devices)
- Player Wallet: ~200 bytes
- **Total per student**: ~700 bytes

**Redis**:
- Devices SET: ~100 bytes
- Session STRING: ~50 bytes
- Wallet HASH: ~200 bytes
- **Total per student**: ~350 bytes

### Scale Projections

| Scale | Students | MariaDB | Redis | Notes |
|-------|----------|---------|-------|-------|
| **Small** | 1,000 | 700 KB | 350 KB | Single school |
| **Medium** | 10,000 | 7 MB | 3.5 MB | Multiple schools |
| **Large** | 50,000 | 35 MB | 17.5 MB | District-level |
| **Extra Large** | 100,000 | 70 MB | 35 MB | National platform |

**Conclusion**: Data footprint is minimal; no sharding/partitioning needed for foreseeable scale.

---

## Migration Plan

### Phase 1: Schema Creation

```sql
-- Run via Frappe bench migrate
bench migrate
```

Creates DocTypes and tables automatically.

### Phase 2: Existing Data Migration (if applicable)

```python
# If migrating existing users to player profiles
def migrate_users_to_players():
    users = frappe.get_all("User", filters={"user_type": "Student"})

    for user in users:
        # Check if player profile already exists
        if frappe.db.exists("Memora Player Profile", {"user": user.name}):
            continue

        # Create player profile (wallet created via after_insert hook)
        profile = frappe.new_doc("Memora Player Profile")
        profile.user = user.name
        profile.grade = get_user_grade(user.name)  # Custom logic
        profile.season = get_current_season()
        profile.academic_plan = get_default_plan(profile.grade)
        # No devices on migration (students must log in to auto-authorize)
        profile.insert(ignore_permissions=True)

    frappe.db.commit()
```

### Phase 3: Cache Warm-up

```python
def warm_up_redis_cache():
    """Populate Redis with existing player data"""
    wallets = frappe.get_all("Memora Player Wallet", fields=["*"])
    redis_client = frappe.cache()

    for wallet in wallets:
        # Populate wallet cache
        redis_client.hset(f"wallet:{wallet.player}", mapping={
            "total_xp": wallet.total_xp,
            "current_streak": wallet.current_streak,
            "last_success_date": wallet.last_success_date or "",
            "last_played_at": wallet.last_played_at or ""
        })

        # Populate device cache
        profile = frappe.get_doc("Memora Player Profile", wallet.player)
        for device in profile.authorized_devices:
            redis_client.sadd(f"player:{profile.user}:devices", device.device_id)
```

---

## Data Consistency Rules

### Cache-DB Sync Strategy

**Cache is Source of Truth for Current State** (per clarification):
- **Read Path**: Always read from Redis first (FR-019a)
- **Write Path**: Write to Redis immediately, queue for DB sync (FR-033, FR-034)
- **Accepted Lag**: Up to 15 minutes between cache and DB (FR-039)

### Conflict Resolution

1. **Cache Unavailable**: Fallback to DB read (may be stale)
2. **DB Unavailable**: Continue with cache (data loss risk if Redis also fails)
3. **Mismatch on Sync**: Cache overwrites DB (cache is authoritative)

### Data Integrity Checks

```python
def verify_wallet_consistency(user_id):
    """Compare Redis and DB; flag discrepancies"""
    redis_wallet = redis_client.hgetall(f"wallet:{user_id}")
    db_wallet = frappe.get_doc("Memora Player Wallet", {"player": user_id})

    discrepancies = {}
    if int(redis_wallet["total_xp"]) != db_wallet.total_xp:
        discrepancies["total_xp"] = {
            "redis": redis_wallet["total_xp"],
            "db": db_wallet.total_xp
        }

    if discrepancies:
        # Log for monitoring
        frappe.log_error(f"Wallet mismatch for {user_id}: {discrepancies}")

    return discrepancies
```

---

## Summary

- **3 DocTypes**: Player Profile, Authorized Device (child), Player Wallet
- **4 Redis structures**: Devices SET, Session STRING, Wallet HASH, Sync Queue SET
- **1:1 relationships**: User→Profile, Profile→Wallet
- **1:many (max 2)**: Profile→Devices
- **Cache-first strategy**: Redis is authoritative for current state
- **Batch sync**: 15-minute interval reduces DB writes by 90%+
- **Minimal footprint**: <100 MB for 100k students
