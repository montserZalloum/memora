# memora Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-19

## Active Technologies
- Python 3.10+ (Frappe Framework v15+) + Frappe Framework, Redis (already configured at redis://127.0.0.1:13000), MariaDB/MySQL (003-srs-scalability)
- MariaDB with LIST partitioning by season; Redis Sorted Sets for hot data (003-srs-scalability)

- Python 3.11+ (Frappe Framework) + Frappe Framework, frappe.whitelist decorator (002-api-reorganization)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+ (Frappe Framework): Follow standard conventions

## Recent Changes
- 003-srs-scalability: Added Python 3.10+ (Frappe Framework v15+) + Frappe Framework, Redis (already configured at redis://127.0.0.1:13000), MariaDB/MySQL

- 002-api-reorganization: Added Python 3.11+ (Frappe Framework) + Frappe Framework, frappe.whitelist decorator

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
