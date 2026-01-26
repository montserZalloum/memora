# memora Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-24

## Active Technologies
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, Redis (frappe.cache), boto3 (S3/R2), RQ (background jobs) (002-cdn-content-export)
- MariaDB (source data), Redis (queue/locks), S3/Cloudflare R2 (CDN target) (002-cdn-content-export)
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, boto3 (existing), shutil/os (stdlib for file ops) (004-local-storage-fallback)
- Local filesystem (`/sites/{site_name}/public/memora_content/`), MariaDB (existing), S3/R2 (existing CDN) (004-local-storage-fallback)
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, redis-py (via frappe.cache), RQ (background jobs) (005-progress-engine-bitset)
- MariaDB (persistent snapshots), Redis (fast bitmap storage), Local JSON files (subject structure) (005-progress-engine-bitset)
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, MariaDB (database), Redis (cache/queue), frappe.db ORM (006-json-generation-debug)
- MariaDB for DocTypes (Memora Academic Plan, Subject, Track, Unit, Topic, Lesson), Local filesystem for JSON files (`/sites/{site}/public/memora_content/`) (006-json-generation-debug)

- Python 3.10+ (Frappe Framework) + Frappe Framework (v14/v15), ERPNext (for Item/Invoice links) (001-doctype-schema)

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
- 006-json-generation-debug: Added Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, MariaDB (database), Redis (cache/queue), frappe.db ORM
- 005-progress-engine-bitset: Added Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, redis-py (via frappe.cache), RQ (background jobs)
- 004-local-storage-fallback: Added Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, boto3 (existing), shutil/os (stdlib for file ops)

<!-- MANUAL ADDITIONS START -->
## AI Workflow
- Use **Serena MCP** for all code search and symbol navigation.
<!-- MANUAL ADDITIONS END -->
