# Memora Backend Core Constitution

## Core Principles

### I. Read/Write Segregation (The Generator Pattern)
**Write Model (Frappe) ≠ Read Model (JSON/Redis).** The database is treated as a "Content Studio" for admins. Runtime data delivery MUST NOT depend on heavy hierarchical SQL joins. Complex content structures (Plans, Overrides, Trees) must be compiled into static JSON payloads or cached Redis structures via background jobs ("The Generator").

### II. High-Velocity Data Segregation
**Transactional DB is for State, not Logs.** Write-intensive data (Interaction Logs, Stream Events) MUST NEVER block the main operational database (MariaDB). High-velocity writes must go through an ingestion layer (Redis Streams/Queues) before being batched into the database or offloaded to specialized storage (ClickHouse/Logs).

### III. Content-Commerce Decoupling
**Content is unaware of Price.** `Subject`, `Track`, and `Unit` DocTypes MUST remain pure content containers. They cannot contain pricing, currency, or sales logic. Access is determined exclusively via the `Product Grant` mapping layer. Hard-linking items directly to content nodes is strictly prohibited.

### IV. Logic Verification (TDD for Business Rules)
**Complex Logic requires 100% Coverage.** The "Plan Override System" and "Access Resolution Algorithm" are the core risks. No code related to content merging or permission calculation is merged without comprehensive unit tests covering edge cases (e.g., conflicting overrides, orphan nodes, nested visibility).

### V. Performance-First Schema Design
**Denormalization over Joins.** For high-traffic APIs, pre-calculated fields (Snapshots) and JSON storage (e.g., `Lesson Stage Config`) are preferred over deep Child Table nesting. Database Indexes MUST be explicitly defined for all Filter/Join columns identified in the PRD (Parents, Player IDs, Dates).

## Technical Constraints & Standards

### Database & Indexing
1.  **Strict Indexing:** No PR involving a new `Link` field or `Select` field used for filtering is accepted without an accompanying database index.
2.  **JSON Usage:** Use `JSON` fields for polymorphic content (like Lesson Stages) to avoid table explosion, but NEVER query inside JSON fields using SQL.
3.  **Partitioning:** Tables expected to exceed 10M rows (Logs, Memory States) must be designed with partitioning keys (e.g., Hash on PlayerID) from Day 1.

### API & Concurrency
1.  **Idempotency:** All state-changing APIs (Submit Answer, Purchase) must accept an `idempotency_key` to prevent duplicate processing.
2.  **Rate Limiting:** Public APIs must have strict Redis-backed rate limits to prevent "Thundering Herd" scenarios.
3.  **Optimistic UI Support:** APIs must return success immediately after queuing async jobs (e.g., XP calculation), enabling non-blocking UI.

## Development Workflow & Quality Gates

### Code Review Standards
1.  **The "Slow Query" Check:** Any code introducing a recursive function or a loop performing DB queries (N+1 problem) will be rejected immediately.
2.  **Migration Safety:** Schema changes must not lock tables for extended periods. Large data migrations must be implemented as background background jobs.
3.  **Constitution Compliance:** Every PR description must explicitly state which Core Principles are touched and how they are upheld.

## Governance

This Constitution supersedes all other coding standards or convenience patterns provided by the framework. Amendments require a written architectural proposal (RFC) and approval from the Lead Architect.

**Version**: 1.0.0 | **Ratified**: 2024-01-24 | **Last Amended**: 2024-01-24