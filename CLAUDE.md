# memora Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-26

## Active Technologies
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, Redis (frappe.cache), boto3 (S3/R2), RQ (background jobs) (002-cdn-content-export)
- MariaDB (source data), Redis (queue/locks), S3/Cloudflare R2 (CDN target) (002-cdn-content-export)
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, boto3 (existing), shutil/os (stdlib for file ops) (004-local-storage-fallback)
- Local filesystem (`/sites/{site_name}/public/memora_content/`), MariaDB (existing), S3/R2 (existing CDN) (004-local-storage-fallback)
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, redis-py (via frappe.cache), RQ (background jobs) (005-progress-engine-bitset)
- MariaDB (persistent snapshots), Redis (fast bitmap storage), Local JSON files (subject structure) (005-progress-engine-bitset)
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, MariaDB (database), Redis (cache/queue), frappe.db ORM (006-json-generation-debug)
- MariaDB for DocTypes (Memora Academic Plan, Subject, Track, Unit, Topic, Lesson), Local filesystem for JSON files (`/sites/{site}/public/memora_content/`) (006-json-generation-debug)
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, redis-py (via frappe.cache), RQ (background jobs) (007-player-core)
- MariaDB (persistent DocTypes), Redis (session/wallet cache, device lists) (007-player-core)
- Python 3.10+ (Frappe Framework) + Frappe Framework (v14/v15), ERPNext (for Item/Invoice links) (001-doctype-schema)
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, redis-py (via frappe.cache), RQ (background jobs), boto3 (S3/R2 CDN) (008-atomic-content-cdn)
- MariaDB (DocTypes), Redis (queue/locks), Local filesystem (`/sites/{site}/public/memora_content/`), S3/Cloudflare R2 (CDN target) (008-atomic-content-cdn)

## MCP Usage & Code Search
- **Always prioritize Serena MCP tools** for any codebase exploration, symbol searching, or code retrieval tasks.
- Before reading a whole file or using `grep`, use Serena's semantic tools to find relevant code parts.
- Specifically, use:
  - `find_symbol`: To locate definitions of classes, functions, or variables.
  - `find_referencing_symbols`: To find where a symbol is used.
  - `find_file`: To locate files by path or name.
  - `read_memory` / `list_memories`: To get project context from Serena's index.
- Only fall back to standard `read_file` or `ls` if Serena cannot find the information or if you need to read a very specific, small utility file.
- **Reason:** Using Serena saves tokens and provides better semantic accuracy.

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.10+ (Frappe Framework): Follow standard conventions

## Recent Changes
- 008-atomic-content-cdn: Added Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, redis-py (via frappe.cache), RQ (background jobs), boto3 (S3/R2 CDN)
- 007-player-core: Added Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, redis-py (via frappe.cache), RQ (background jobs)
  - DocTypes: Memora Player Profile, Memora Player Wallet, Memora Authorized Device (child table)
  - Services: device_auth.py, session_manager.py, wallet_engine.py, wallet_sync.py
  - API: player.py (11 endpoints for auth, sessions, wallet, devices)
  - Redis Patterns: player:{user}:devices (SET), active_session:{user} (STRING), wallet:{user} (HASH), pending_wallet_sync (SET)
  - Migration: v007_player_core_create_profiles.py (creates profiles for existing users)
- 006-json-generation-debug: Added Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, MariaDB (database), Redis (cache/queue), frappe.db ORM

<!-- MANUAL ADDITIONS START -->

## AI Workflow
- Use **Serena MCP** for all code search and symbol navigation.

## Feature: Player Core (007)

### Overview
Secure student identity system with device authorization, single-session enforcement, and high-performance rewards engine (XP & Streak). Prevents account sharing through hardware-locked device authorization and single active session enforcement.

### DocTypes
- **Memora Player Profile**: Central identity hub linking User to educational context with authorized_devices table (max 2 devices)
- **Memora Player Wallet**: Persistent XP/streak storage synchronized from Redis via 15-min batch job
- **Memora Authorized Device**: Child table storing device records with timestamps

### API Endpoints
- POST `/api/method/memora.api.player/login` - Student login with device auth (first device auto-authorized)
- GET `/api/method/memora.api.player/check_device_authorization` - Check device status
- POST `/api/method/memora.api.player/register_device` (admin) - Add authorized device
- POST `/api/method/memora.api.player/remove_device` (admin) - Remove device
- GET `/api/method/memora.api.player/validate_session` - Validate active session
- POST `/api/method/memora.api.player/logout` - Invalidate session
- POST `/api/method/memora.api.player/complete_lesson` - Complete lesson (update XP/streak)
- GET `/api/method/memora.api.player/get_wallet` - Get wallet data (cache-first)
- POST `/api/method/memora.api.player/add_xp` - Award XP
- POST `/api/method/memora.api.player/trigger_wallet_sync` (admin) - Manual batch sync

### Services
- `device_auth.py`: Device authorization (O(1) Redis checks)
- `session_manager.py`: Single-session enforcement (atomic Redis SET)
- `wallet_engine.py`: XP/streak calculations with cache-first reads
- `wallet_sync.py`: 15-min batch sync (500-player chunks, SQL CASE updates)

### Key Features
- Device authorization: Client-generated UUID v4 in X-Device-ID header, max 2 devices per student
- Single session: Redis-based lock, previous session invalidated on new login (<2s)
- Streak tracking: Date-based logic with server UTC time, resets to 1 (not 0) on gap
- XP accumulation: Immediate Redis update, queued for 15-min batch sync to DB
- Rate limiting: Redis INCR with TTL, X-RateLimit-* response headers
- Security audit: All device/session events logged

### Performance Targets
- Device/session verification: <2ms (Redis)
- XP display latency: <1s (cache-first)
- Session termination: <2s
- Batch sync: <5min for 50k players (90%+ DB write reduction)
- Scale: Support 10k concurrent students

<!-- MANUAL ADDITIONS END -->
