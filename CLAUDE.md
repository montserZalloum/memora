# memora Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-24

## Active Technologies
- Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, Redis (frappe.cache), boto3 (S3/R2), RQ (background jobs) (002-cdn-content-export)
- MariaDB (source data), Redis (queue/locks), S3/Cloudflare R2 (CDN target) (002-cdn-content-export)

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
- 002-cdn-content-export: Added Python 3.10+ (Frappe Framework v14/v15) + Frappe Framework, Redis (frappe.cache), boto3 (S3/R2), RQ (background jobs)

<!-- MANUAL ADDITIONS START -->
## AI Workflow
- Use **Serena MCP** for all code search and symbol navigation.
<!-- MANUAL ADDITIONS END -->
