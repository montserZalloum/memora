# Quick Start Guide: Player Core Development

**Feature**: 007-player-core | **For**: Developers implementing or extending Player Core
**Prerequisites**: Frappe Framework v14/v15, Redis, MariaDB, Python 3.10+

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Running Tests](#running-tests)
3. [Creating DocTypes](#creating-doctypes)
4. [Implementing Services](#implementing-services)
5. [Testing Endpoints](#testing-endpoints)
6. [Common Workflows](#common-workflows)
7. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### 1. Prerequisites Check

```bash
# Verify Frappe bench
bench --version
# Expected: 5.x.x

# Verify Redis is running
redis-cli ping
# Expected: PONG

# Verify Python version
python3 --version
# Expected: Python 3.10.x or 3.11.x

# Check MariaDB
mysql --version
# Expected: MariaDB 10.x
```

### 2. Clone and Install Memora App

```bash
# Navigate to frappe-bench
cd ~/frappe-bench

# Get app if not already installed
bench get-app memora https://github.com/your-org/memora.git

# Install app to site
bench --site your-site.local install-app memora

# Verify installation
bench --site your-site.local list-apps
# Should include 'memora'
```

### 3. Enable Developer Mode

```bash
# Edit site_config.json
nano sites/your-site.local/site_config.json

# Add:
{
  "developer_mode": 1,
  "disable_website_cache": 1
}

# Restart bench
bench restart
```

### 4. Redis Configuration

Frappe automatically configures Redis. Verify via:

```python
# In bench console
bench --site your-site.local console

# Test Redis connection
import frappe
redis_client = frappe.cache()
redis_client.ping()
# Expected: True
```

---

## Running Tests

### Unit Tests

```bash
# Run all Player Core tests
bench --site your-site.local run-tests --app memora --module memora.tests.unit

# Run specific test file
bench --site your-site.local run-tests --app memora --module memora.tests.unit.test_device_auth

# Run single test function
bench --site your-site.local run-tests --app memora --module memora.tests.unit.test_device_auth --test test_device_authorization_check
```

### Integration Tests

```bash
# Run integration tests
bench --site your-site.local run-tests --app memora --module memora.tests.integration.test_player_flows

# Run with coverage
bench --site your-site.local run-tests --app memora --module memora.tests --coverage
```

### Test Data Setup

```python
# In test files, use Frappe's test framework
import frappe
from frappe.tests.utils import FrappeTestCase

class TestPlayerCore(FrappeTestCase):
    def setUp(self):
        # Create test user
        self.test_user = frappe.get_doc({
            "doctype": "User",
            "email": "test.student@example.com",
            "first_name": "Test",
            "last_name": "Student",
            "enabled": 1
        }).insert(ignore_permissions=True)

        # Create test player profile
        self.test_profile = frappe.get_doc({
            "doctype": "Memora Player Profile",
            "user": self.test_user.name,
            "grade": "Grade 10",
            "season": "2025-2026",
            "academic_plan": "Default Plan"
        }).insert(ignore_permissions=True)

    def tearDown(self):
        # Cleanup
        frappe.delete_doc("Memora Player Profile", self.test_profile.name, force=1)
        frappe.delete_doc("User", self.test_user.name, force=1)
```

---

## Creating DocTypes

### Via Desk (Recommended for First-Time)

1. Navigate to http://your-site.local/app/doctype
2. Click "New DocType"
3. Fill in fields per `data-model.md`
4. Save
5. Export to JSON:

```bash
bench --site your-site.local export-doc "DocType" "Memora Player Profile"
# Creates file: memora/memora/doctype/memora_player_profile/memora_player_profile.json
```

### Via Code (For Automation)

```python
# Example: Create Memora Player Wallet DocType
{
  "name": "Memora Player Wallet",
  "module": "Memora",
  "autoname": "format:WALLET-{player}",
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
    }
    # ... more fields
  ],
  "permissions": [
    {
      "role": "Student",
      "read": 1
    },
    {
      "role": "System Manager",
      "read": 1,
      "write": 1
    }
  ]
}
```

### Running Migrations

```bash
# After creating/modifying DocTypes
bench --site your-site.local migrate

# Check migration status
bench --site your-site.local migrate --help
```

---

## Implementing Services

### Service Structure

```
memora/services/
├── device_auth.py        # Device authorization logic
├── session_manager.py    # Session management
├── wallet_engine.py      # XP/Streak calculations
└── wallet_sync.py        # Batch sync background job
```

### Example: Device Authorization Service

```python
# memora/services/device_auth.py

import frappe
import uuid

def is_device_authorized(user_id, device_id):
    """
    FR-010: Check device authorization in <2ms (Redis)

    Args:
        user_id (str): Frappe User.name
        device_id (str): UUID v4 device identifier

    Returns:
        bool: True if device is authorized
    """
    redis_client = frappe.cache()
    device_key = f"player:{user_id}:devices"

    # O(1) membership check
    return redis_client.sismember(device_key, device_id)

def add_authorized_device(player_profile, device_id, device_name):
    """
    FR-009: Admin-only device addition
    FR-005b: Enforce 2-device limit

    Args:
        player_profile (str): Player Profile DocType name
        device_id (str): UUID v4
        device_name (str): Human-readable name

    Raises:
        frappe.ValidationError: If device limit exceeded
    """
    # Validate UUID format
    try:
        uuid.UUID(device_id, version=4)
    except ValueError:
        frappe.throw("Invalid device ID format. Must be UUID v4.")

    # Load profile
    profile = frappe.get_doc("Memora Player Profile", player_profile)

    # Check limit
    if len(profile.authorized_devices) >= 2:
        frappe.throw("Maximum 2 authorized devices allowed per student")

    # Add device
    profile.append("authorized_devices", {
        "device_id": device_id,
        "device_name": device_name,
        "added_on": frappe.utils.now()
    })

    profile.save(ignore_permissions=True)

    # Update Redis cache
    redis_client = frappe.cache()
    redis_client.sadd(f"player:{profile.user}:devices", device_id)

    return profile
```

### Example: Wallet Engine Service

```python
# memora/services/wallet_engine.py

import frappe
from datetime import datetime, date

def update_streak(user_id, hearts_earned):
    """
    FR-022 through FR-028: Streak calculation logic

    Args:
        user_id (str): Frappe User.name
        hearts_earned (int): Hearts from lesson (must be > 0 for streak update)

    Returns:
        dict: Streak update result
    """
    if hearts_earned <= 0:
        return {"streak_action": "no_update", "reason": "hearts <= 0"}

    redis_client = frappe.cache()
    wallet_key = f"wallet:{user_id}"

    # Get current wallet state
    wallet = redis_client.hgetall(wallet_key)
    current_streak = int(wallet.get("current_streak", 0))
    last_success_date = wallet.get("last_success_date")

    # Server time (UTC)
    today = date.today()
    today_str = today.isoformat()

    # Streak logic (FR-028)
    if not last_success_date:
        # First lesson ever (FR-022b)
        new_streak = 1
        action = "first_completion"
    elif last_success_date == today_str:
        # Same day - no change (FR-025)
        new_streak = current_streak
        action = "maintained"
    elif is_consecutive_day(last_success_date, today):
        # Next day - increment (FR-023)
        new_streak = current_streak + 1
        action = "incremented"
    else:
        # Gap > 1 day - reset (FR-024)
        new_streak = 1
        action = "reset"

    # Update Redis
    redis_client.hset(wallet_key, mapping={
        "current_streak": new_streak,
        "last_success_date": today_str
    })

    # Queue for DB sync (FR-034)
    redis_client.sadd("pending_wallet_sync", user_id)

    return {
        "old_streak": current_streak,
        "new_streak": new_streak,
        "streak_action": action,
        "last_success_date": today_str
    }

def is_consecutive_day(last_date_str, today):
    """Check if today is exactly 1 day after last_date"""
    last_date = date.fromisoformat(last_date_str)
    return (today - last_date).days == 1
```

---

## Testing Endpoints

### Using cURL

```bash
# Login
curl -X POST http://your-site.local/api/method/memora.api.player.login \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "usr": "student@example.com",
    "pwd": "password123"
  }'
# Capture 'sid' cookie from Set-Cookie header

# Get wallet
curl http://your-site.local/api/method/memora.api.player.get_wallet \
  -H "Cookie: sid=YOUR_SESSION_ID" \
  -H "X-Device-ID: 550e8400-e29b-41d4-a716-446655440000"

# Complete lesson
curl -X POST http://your-site.local/api/method/memora.api.player.complete_lesson \
  -H "Cookie: sid=YOUR_SESSION_ID" \
  -H "X-Device-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{
    "lesson_id": "LESSON-12345",
    "hearts_earned": 2
  }'
```

### Using Postman/Insomnia

1. Import OpenAPI specs from `/contracts/` directory
2. Set environment variables:
   - `BASE_URL`: http://your-site.local
   - `DEVICE_ID`: Generate UUID v4 at https://www.uuidgenerator.net/
3. Authenticate via `POST /login` and capture `sid` cookie
4. Use cookie in subsequent requests

### Using Frappe Console

```python
bench --site your-site.local console

# Test device authorization
from memora.services.device_auth import is_device_authorized
is_device_authorized("student@example.com", "550e8400-e29b-41d4-a716-446655440000")

# Test wallet read
from memora.services.wallet_engine import get_wallet
wallet = get_wallet("student@example.com")
print(wallet)

# Test streak update
from memora.services.wallet_engine import update_streak
result = update_streak("student@example.com", hearts_earned=2)
print(result)
```

---

## Common Workflows

### Workflow 1: New Student Onboarding

```python
# 1. Create Frappe User (via Frappe Desk or API)
user = frappe.get_doc({
    "doctype": "User",
    "email": "newstudent@example.com",
    "first_name": "New",
    "last_name": "Student"
}).insert()

# 2. Create Player Profile (auto-creates wallet via after_insert hook)
from memora.services.device_auth import create_player_profile

profile = create_player_profile(
    user_id=user.name,
    grade="Grade 10",
    season="2025-2026",
    academic_plan="Science Track",
    first_device_id="550e8400-e29b-41d4-a716-446655440000",  # Auto-authorized
    first_device_name="Student's iPhone"
)

# 3. Verify wallet created
wallet = frappe.get_doc("Memora Player Wallet", {"player": profile.name})
assert wallet.total_xp == 0
assert wallet.current_streak == 0
```

### Workflow 2: Device Authorization Flow

```python
# Student attempts login from new device (unauthorized)
device_id = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

# Check if authorized
from memora.services.device_auth import is_device_authorized
authorized = is_device_authorized("student@example.com", device_id)
# Returns: False

# Student contacts admin
# Admin authorizes device
from memora.services.device_auth import add_authorized_device
add_authorized_device(
    player_profile="PLAYER-00001",
    device_id=device_id,
    device_name="Student's iPad"
)

# Student can now log in
authorized = is_device_authorized("student@example.com", device_id)
# Returns: True
```

### Workflow 3: Batch Wallet Sync

```bash
# Trigger batch sync manually (normally runs every 15 minutes)
bench --site your-site.local console

from memora.services.wallet_sync import sync_pending_wallets
result = sync_pending_wallets()
print(result)
# {"synced": 150, "duration": 2.5}
```

---

## Troubleshooting

### Issue: Redis Connection Error

**Symptom**: `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379`

**Solution**:
```bash
# Check Redis status
sudo systemctl status redis

# Start Redis if stopped
sudo systemctl start redis

# Verify Frappe can connect
bench --site your-site.local console
import frappe
frappe.cache().ping()  # Should return True
```

### Issue: Device Not Found in Cache

**Symptom**: `is_device_authorized()` returns False for valid device

**Solution**:
```python
# Rebuild device cache from DB
bench --site your-site.local console

from memora.services.device_auth import rebuild_device_cache
rebuild_device_cache()  # Repopulates Redis from all Player Profiles
```

### Issue: Streak Not Incrementing

**Symptom**: Completing lessons doesn't update streak

**Debugging**:
```python
bench --site your-site.local console

# Check wallet state in Redis
redis_client = frappe.cache()
wallet = redis_client.hgetall("wallet:student@example.com")
print(wallet)

# Verify last_success_date
from datetime import date
today = date.today().isoformat()
print(f"Today: {today}")
print(f"Last Success: {wallet.get('last_success_date')}")

# Manual streak update for testing
from memora.services.wallet_engine import update_streak
result = update_streak("student@example.com", hearts_earned=2)
print(result)
```

### Issue: Session Invalidated Unexpectedly

**Symptom**: Student gets kicked out mid-session

**Debugging**:
```python
bench --site your-site.local console

# Check active session
redis_client = frappe.cache()
active_session = redis_client.get("active_session:student@example.com")
print(f"Active Session: {active_session}")

# Check current user's session
import frappe
current_session = frappe.session.sid
print(f"Current Session: {current_session}")

# If mismatch, another login occurred
if active_session != current_session:
    print("Session replaced by login from another device")
```

### Issue: Batch Sync Not Running

**Symptom**: Wallet data not syncing to MariaDB after 15 minutes

**Solution**:
```bash
# Check scheduler status
bench --site your-site.local doctor

# Verify hooks.py scheduler config
cat memora/hooks.py | grep -A 5 "scheduler_events"

# Manually trigger scheduler
bench --site your-site.local enable-scheduler
bench restart

# Check scheduler logs
tail -f sites/your-site.local/logs/scheduler.log
```

---

## Next Steps

1. **Read**: [research.md](./research.md) for technical decisions and rationale
2. **Review**: [data-model.md](./data-model.md) for entity schemas
3. **Explore**: [contracts/](./contracts/) for API specifications
4. **Implement**: Start with `device_auth.py` service (lowest risk, no dependencies)
5. **Test**: Write unit tests before implementation (TDD approach)

---

## Useful Commands Reference

```bash
# Development
bench --site your-site.local console              # Python REPL with Frappe context
bench --site your-site.local migrate              # Run database migrations
bench --site your-site.local clear-cache          # Clear Redis cache
bench restart                                     # Restart Gunicorn/Werkzeug

# Testing
bench run-tests --app memora                      # Run all tests
bench run-tests --app memora --coverage           # With coverage report
bench run-tests --app memora --profile            # Profile test performance

# Redis
redis-cli                                         # Redis CLI
redis-cli KEYS "player:*"                         # List all player keys
redis-cli HGETALL "wallet:student@example.com"    # Get wallet data
redis-cli SMEMBERS "pending_wallet_sync"          # Check sync queue

# Database
bench --site your-site.local mariadb              # MySQL/MariaDB CLI
```

---

**Need Help?**
- Documentation: [spec.md](./spec.md)
- Architecture: [plan.md](./plan.md)
- Team Contact: dev-team@memora.example.com
