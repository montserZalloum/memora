# Feature Specification: SRS High-Performance & Scalability Architecture

**Feature Branch**: `003-srs-scalability`
**Created**: 2026-01-19
**Status**: Draft
**Input**: User description: "Re-engineer the SRS (Spaced Repetition System) memory engine to handle 1B+ records with <100ms response time using in-memory caching for fast reads, database partitioning for storage, and asynchronous writes to prevent UI blocking."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Student Retrieves Due Review Questions (Priority: P1)

A student opens the review section to study questions that are due for review. The system retrieves their due questions instantly from memory, ensuring a seamless learning experience even when billions of review records exist across all users.

**Why this priority**: This is the core read operation that students perform multiple times daily. Fast retrieval directly impacts user experience and learning engagement. A slow or unresponsive system would cause students to abandon their study sessions.

**Independent Test**: Can be tested by having a student with 1000+ tracked questions request their due reviews, verifying results appear in under 100ms.

**Acceptance Scenarios**:

1. **Given** a student has 500 questions tracked in the current season with 50 due for review, **When** the student requests their review session, **Then** the system returns the due question IDs in under 100ms.
2. **Given** a student has no questions due for review, **When** the student requests their review session, **Then** the system returns an empty list within 100ms with a message indicating no reviews are due.
3. **Given** the system has 1 billion total memory records across all users, **When** any student requests their due reviews, **Then** system response time remains under 100ms.

---

### User Story 2 - Student Completes Review and Progress is Saved (Priority: P1)

After answering questions, a student's review progress is saved immediately from their perspective. The student sees instant confirmation while the actual database persistence happens in the background.

**Why this priority**: This is the core write operation paired with reading. Students must have confidence their progress is saved. Blocking the UI during database writes would create frustrating delays.

**Independent Test**: Can be tested by a student completing a review session of 20 questions, verifying instant UI confirmation and eventual database persistence.

**Acceptance Scenarios**:

1. **Given** a student has just answered a review question, **When** the system saves their progress, **Then** the student receives confirmation within 200ms.
2. **Given** a student submits review progress for 20 questions at once, **When** the batch is saved, **Then** confirmation returns within 500ms regardless of database load.
3. **Given** the background persistence queue has pending items, **When** a student submits new progress, **Then** the student's immediate experience is not affected by queue depth.
4. **Given** a student has submitted progress, **When** they immediately request their updated review schedule, **Then** the new review dates are reflected (from the fast cache layer).

---

### User Story 3 - Administrator Creates New Season with Automatic Infrastructure Setup (Priority: P2)

An administrator creates a new academic season in the system. The system automatically prepares the underlying infrastructure to handle that season's data efficiently, including separate storage partitions.

**Why this priority**: Season setup is infrequent but critical for system scalability. Without proper season-based data separation, the system cannot scale to billions of records.

**Independent Test**: Can be tested by creating a new season and verifying the infrastructure setup completes successfully, enabling data storage for that season.

**Acceptance Scenarios**:

1. **Given** an administrator is creating a new season "Season 2026", **When** the season is saved, **Then** a dedicated storage partition is automatically created for that season's memory data.
2. **Given** a season is created with caching enabled, **When** students begin tracking questions in that season, **Then** their data is properly synced to the fast-access cache layer.
3. **Given** a season already has its infrastructure created, **When** the administrator views the season, **Then** they can see the infrastructure status (partition created, caching enabled).

---

### User Story 4 - System Automatically Archives Old Season Data (Priority: P3)

The system automatically archives data from inactive seasons to maintain optimal performance. Archived data is moved to separate storage while remaining accessible if needed.

**Why this priority**: Archiving is a maintenance operation that prevents system degradation over time. While important for long-term health, it doesn't affect immediate user experience.

**Independent Test**: Can be tested by marking a season for auto-archive and verifying data migration occurs during the scheduled maintenance window.

**Acceptance Scenarios**:

1. **Given** a season is marked for auto-archive, **When** the nightly maintenance job runs, **Then** all memory tracker records for that season are moved to archive storage.
2. **Given** archived data exists for a past season, **When** an administrator queries historical statistics, **Then** the archived data can still be accessed (with potentially longer response times).
3. **Given** a season's data has been archived, **When** a student tries to access that season's reviews, **Then** they receive a clear message that the season has ended and data is archived.
4. **Given** archiving completes for a season, **When** the system checks cache storage, **Then** the cache entries for that season have been cleared to free memory.

---

### User Story 5 - Administrator Monitors Season Configuration (Priority: P3)

An administrator can view and modify season settings related to performance optimization, including enabling/disabling caching and auto-archive features.

**Why this priority**: Administrative control is important for system management but doesn't directly impact student learning experience.

**Independent Test**: Can be tested by toggling season settings and verifying the system behavior changes accordingly.

**Acceptance Scenarios**:

1. **Given** an administrator views an active season, **When** they check the season settings, **Then** they see options for: Is Active, Partition Created (read-only), Enable Caching, Auto Archive, and a "Rebuild Cache" action button.
2. **Given** caching is disabled for a season, **When** an administrator enables it, **Then** existing student data for that season begins syncing to the cache layer via lazy loading as students access the system.
3. **Given** an active season with students, **When** an administrator tries to enable auto-archive, **Then** the system warns that this will archive student data and requires confirmation.
4. **Given** an administrator wants to pre-warm the cache for a season, **When** they trigger "Rebuild Cache", **Then** a background job starts rebuilding all student cache entries with visible progress tracking and completion notification.

---

### Edge Cases

- What happens when a student's data is being written to the database and they request their review list simultaneously?
  - The fast cache layer always has the latest state, so reads return current data regardless of background write status.

- What happens if the fast cache layer is temporarily unavailable?
  - The system enters "Safe Mode": returns only top 5-10 most urgent reviews per student via lightweight indexed query, applies rate limiting to prevent database overload, notifies administrators, and displays a degraded mode indicator to users. This prevents cascading database failure under high concurrent load.

- What happens if the background write queue fails to persist data?
  - Failed writes are retried with exponential backoff. Critical failures are logged and alert administrators. The cache layer retains data until successful persistence.

- What happens when trying to create a partition for a season that already has one?
  - The system checks for existing partitions and skips creation, marking partition_created as true.

- What happens if a student has data across multiple seasons?
  - Each season's data is managed independently. When requesting reviews, only the active season's data is considered by default.

- What happens if the cache server restarts and loses all data?
  - The system uses lazy loading: when a student requests reviews and their cache entry is missing, the system fetches from the database and repopulates the cache transparently. Administrators can also trigger a full season rebuild proactively.

- What happens when caching is enabled for a season that already has student data?
  - Existing data is not immediately loaded. As students access their reviews, lazy loading populates the cache. Administrators can use the manual rebuild utility to pre-warm the cache for the entire season.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST retrieve due review questions for any student in under 100ms regardless of total record count.
- **FR-002**: System MUST store student review progress with instant user confirmation (under 500ms for batches up to 50 items).
- **FR-003**: System MUST persist all review progress to durable storage via background processing.
- **FR-004**: System MUST maintain data consistency between the fast cache layer and persistent storage.
- **FR-005**: System MUST support creating new seasons with automatic infrastructure setup.
- **FR-006**: System MUST partition memory tracker data by season to enable efficient querying and archiving.
- **FR-007**: System MUST allow administrators to enable/disable caching per season.
- **FR-008**: System MUST allow administrators to enable/disable auto-archive per season.
- **FR-009**: System MUST automatically archive old season data during scheduled maintenance windows when auto-archive is enabled.
- **FR-010**: System MUST clear cache entries for archived seasons to free memory resources.
- **FR-011**: System MUST preserve archived data in queryable (but potentially slower) archive storage for a minimum of 3 years.
- **FR-011a**: System MUST flag archived data older than 3 years as eligible for deletion; actual deletion requires explicit administrator approval.
- **FR-012**: System MUST track the following per student per question: player ID, season, question ID, next review date, stability score (0-4), last review date, and optional subject filter.
- **FR-013**: System MUST support filtering due reviews by subject within a season.
- **FR-014**: System MUST enter "Safe Mode" when cache layer is unavailable: (a) return only top N (5-10) most urgent reviews per student via lightweight indexed query, (b) apply rate limiting of maximum 500 requests/minute system-wide and 1 request per 30 seconds per user, (c) notify administrators immediately, (d) display degraded mode indicator to users, (e) queue excess requests with "please wait" message.
- **FR-015**: System MUST retry failed background persistence operations with appropriate backoff strategy.
- **FR-016**: System MUST automatically rehydrate cache entries on cache miss (lazy loading) by fetching the student's data from persistent storage and populating the cache transparently.
- **FR-017**: System MUST provide an administrative utility to trigger full cache rebuild for a specific season on demand, with progress tracking and completion notification.
- **FR-018**: System MUST run periodic reconciliation between cache and database, automatically correcting cache from database (source of truth), and alert administrators when discrepancy rate exceeds 0.1%.

### Key Entities

- **Player Memory Tracker**: Represents a student's memory state for a specific question within a season. Contains: player reference, season reference, question ID, next review date, stability score, last review date, and optional subject reference. This is the high-volume entity expected to reach billions of records.

- **Archived Memory Tracker**: Historical copy of Player Memory Tracker for inactive seasons. Contains all fields from Player Memory Tracker plus the archive timestamp. Used for historical reporting and compliance. Retention period: 3 years minimum; eligible for deletion with admin approval after retention period.

- **Game Subscription Season**: Represents an academic or subscription period. Contains: name, is_active flag, partition_created status, enable_redis flag, and auto_archive flag. Controls system behavior for data segregation and lifecycle management.

- **Cache Entry (Conceptual)**: Represents a student's review schedule in the fast-access layer. Key format: srs:{user_id}:{season_id}. Contains question IDs sorted by next review timestamp for O(log n) retrieval of due items.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Students can retrieve their due review questions in under 100ms, measured at the 99th percentile, regardless of total system record count.
- **SC-002**: System supports 1 billion total memory tracker records while maintaining response time targets.
- **SC-003**: Students receive save confirmation within 500ms for review sessions up to 50 questions.
- **SC-004**: Background persistence completes within 5 minutes for 99% of submitted review data.
- **SC-005**: New season infrastructure setup completes within 30 seconds of season creation.
- **SC-006**: Nightly archive job processes 10 million records per hour without impacting active user performance.
- **SC-007**: System maintains 99.9% data consistency between cache and persistent storage; periodic reconciliation auto-corrects discrepancies using database as source of truth; administrators alerted if discrepancy rate exceeds 0.1%.
- **SC-008**: Cache layer memory usage scales linearly with active users, not total historical records.
- **SC-009**: System handles 10,000 concurrent students requesting reviews simultaneously without degradation.
- **SC-010**: Zero data loss for submitted review progress, even during system failures (verified via audit logs).

## Clarifications

### Session 2026-01-19

- Q: How should the system behave when cache layer fails with 10,000+ concurrent users? → A: Safe Mode with Limited Data - System enters degraded mode returning only top N most urgent reviews per student via lightweight indexed query, with rate limiting on concurrent requests.
- Q: How should the system handle cache data loss (server restart) or enabling caching on existing season? → A: Hybrid Auto + Manual - Automatic background rehydration on cache miss detection (lazy loading) plus manual full-season rebuild utility for administrators.
- Q: What rate limiting threshold should apply during Safe Mode? → A: Moderate - Maximum 500 database requests per minute system-wide, with per-user limit of 1 request per 30 seconds.
- Q: How should the system handle cache-database discrepancies during reconciliation? → A: Auto-correct with alerts - Automatically correct cache from database (source of truth), alert administrators if discrepancy rate exceeds 0.1%.
- Q: How long should archived season data be retained? → A: 3 years - Archived data retained for 3 years (typical academic cycle), then eligible for deletion with administrator approval.

## Assumptions

- Students primarily interact with one active season at a time.
- The system already has a User/Player entity that can be referenced.
- The Game Subscription Season DocType exists and can be extended with new fields.
- The Game Stage (question) entity exists and provides question content.
- Infrastructure for scheduled background jobs exists in the platform.
- Platform supports connection to an in-memory data store for caching.
- Database supports table partitioning by list values.
