# Feature Specification: CDN Content Export System

**Feature Branch**: `002-cdn-content-export`
**Created**: 2026-01-25
**Status**: Draft
**Input**: User description: "نظام إدارة محتوى الـ CDN - Static Content Generator for Memora Learning Platform"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Content Sync on Changes (Priority: P1)

As a content administrator, when I create, update, or delete educational content (subjects, units, lessons) in the Frappe system, the CDN should automatically receive the updated static JSON files without manual intervention, so that students always see the latest content.

**Why this priority**: Core value proposition - without automatic sync, manual exports would be required, defeating the purpose of the system and creating maintenance burden.

**Independent Test**: Can be fully tested by creating/modifying a lesson in Frappe and verifying the corresponding JSON file appears on the CDN storage with correct content within the batch processing window (5 minutes or 50 changes threshold).

**Acceptance Scenarios**:

1. **Given** a published lesson exists in Frappe, **When** an instructor updates the lesson title, **Then** the CDN JSON file is regenerated with the new title within the next batch cycle.
2. **Given** no pending changes exist, **When** an instructor creates a new unit with 3 lessons, **Then** all 4 affected JSON files (unit + 3 lessons) are generated in the next batch cycle.
3. **Given** multiple changes occur to 20 lessons in the same plan within 1 minute, **When** the batch processor runs, **Then** the plan is rebuilt only once (deduplication via Redis Set).

---

### User Story 2 - Plan-Specific Content Generation (Priority: P1)

As a curriculum designer, I need the exported content to respect plan-specific overrides and access configurations, so that different academic plans can show/hide content appropriately for their student audience.

**Why this priority**: Equal priority to P1 because plan context is fundamental to content export correctness - content varies by plan due to overrides.

**Independent Test**: Can be fully tested by creating two plans that share a subject but have different override settings, then verifying each plan's exported JSON only includes visible content for that plan.

**Acceptance Scenarios**:

1. **Given** Subject A is assigned to Plan X and Plan Y, **When** Plan X has an override hiding Unit 2, **Then** Plan X's subject JSON excludes Unit 2 while Plan Y's includes it.
2. **Given** a Subject is marked as paid, **When** the JSON is generated, **Then** all child units and lessons have `access_level: "paid"` unless marked as free preview.
3. **Given** a Unit is marked `is_free_preview: true` under a paid Subject, **When** JSON is generated, **Then** that Unit has `access_level: "free_preview"` despite parent being paid.

---

### User Story 3 - Content Deletion Handling (Priority: P2)

As a content administrator, when I trash or permanently delete content from Frappe (lessons, units, subjects, or entire plans), the corresponding CDN files should be cleaned up appropriately, so that deleted content doesn't persist on the CDN or appear in navigation.

**Why this priority**: Important for data integrity but happens less frequently than content updates; system remains functional without deletion handling initially.

**Independent Test**: Can be fully tested by trashing a lesson, then verifying the parent unit's JSON no longer references the trashed lesson and the lesson JSON is removed from CDN.

**Acceptance Scenarios**:

1. **Given** a Lesson exists and is referenced in a Unit JSON, **When** the Lesson is trashed in Frappe, **Then** the Unit JSON is regenerated without the lesson reference.
2. **Given** a trashed Lesson exists, **When** the Lesson is restored from trash, **Then** the system treats it as a new insert and regenerates affected files.
3. **Given** a Subject with files at `/plans/{plan_id}/subjects/{subject_id}.json`, **When** the Subject is permanently deleted, **Then** the JSON file is removed from CDN and the plan manifest is updated.
4. **Given** a Plan exists with a folder structure at `/plans/{plan_id}/`, **When** the Plan is permanently deleted, **Then** the entire plan folder is removed from CDN.

---

### User Story 4 - Access Control Metadata in JSON (Priority: P2)

As a frontend developer consuming the CDN content, I need each JSON file to contain access control metadata (`is_published`, `access_level`, `required_item`, `is_sold_separately`, `parent_item_required`), so that the frontend can render appropriate locked/unlocked states, purchase prompts, and DLC handling.

**Why this priority**: Critical for user experience but frontend can gracefully degrade without it initially; backend export is the foundation.

**Independent Test**: Can be fully tested by generating a JSON file for paid content and verifying the access metadata fields are present with correct values.

**Acceptance Scenarios**:

1. **Given** a published free Unit, **When** JSON is generated, **Then** it contains `{"is_published": true, "access_level": "public"}`.
2. **Given** a paid Subject with ERPNext Item Code "COURSE-001", **When** JSON is generated, **Then** child content contains `{"access_level": "paid", "required_item": "COURSE-001"}`.
3. **Given** an unpublished draft Lesson, **When** JSON generation runs, **Then** the lesson is excluded from export (unpublished content not exported).
4. **Given** a Track marked as separately purchasable (DLC), **When** JSON is generated, **Then** it contains `{"is_sold_separately": true, "parent_item_required": false}`.
5. **Given** a Track that unlocks with the parent Subject purchase, **When** JSON is generated, **Then** it contains `{"is_sold_separately": false, "parent_item_required": true}`.

---

### User Story 5 - Search Index Generation (Priority: P2)

As a student, I need to search for lessons by name across my entire plan, so that I can quickly find specific content like "Limits" or "Derivatives" without browsing through all subjects and units.

**Why this priority**: Important for user experience and discoverability; without it students must navigate hierarchically which is slower.

**Independent Test**: Can be fully tested by generating a plan's search index and verifying it contains all lesson names with their IDs and parent references.

**Acceptance Scenarios**:

1. **Given** a Plan with 3 Subjects containing 50 total Lessons, **When** the batch processor runs, **Then** a `search_index.json` file is generated at `/plans/{plan_id}/search_index.json`.
2. **Given** the search index exists, **When** a new Lesson "النهايات" is added, **Then** the search index is regenerated to include the new lesson entry.
3. **Given** the search index contains an entry, **When** the corresponding Lesson is deleted, **Then** the entry is removed from the search index.
4. **Given** a Plan has more than 500 lessons, **When** search index is generated, **Then** the index is split by Subject into `/plans/{plan_id}/search/{subject_id}.json` files with a master index listing available shards.

---

### User Story 6 - Cache Invalidation on Updates (Priority: P2)

As a content administrator, when I fix an error in a question or lesson, I need students to see the correction immediately without waiting for browser/CDN cache to expire, so that incorrect content doesn't mislead students.

**Why this priority**: Critical for content accuracy but depends on core sync functionality being in place first.

**Independent Test**: Can be fully tested by updating a lesson, then verifying the CDN cache purge request is sent and the versioned URL changes.

**Acceptance Scenarios**:

1. **Given** a Lesson JSON exists on CDN with cache, **When** the lesson is updated, **Then** a cache purge request is sent to the CDN API.
2. **Given** the manifest file is requested, **When** the frontend loads it, **Then** the URL includes a version parameter (e.g., `manifest.json?v={timestamp}`).
3. **Given** a Subject is updated, **When** the new JSON is uploaded, **Then** the old cached version is invalidated within 60 seconds.

---

### User Story 7 - Monitoring and Error Visibility (Priority: P3)

As a system administrator, I need visibility into the CDN sync queue and any upload failures, so that I can identify and resolve issues before they affect students.

**Why this priority**: Operational tooling that supports system health but core functionality works without it.

**Independent Test**: Can be fully tested by triggering a CDN upload failure (invalid credentials) and verifying the error is logged and visible in Frappe.

**Acceptance Scenarios**:

1. **Given** 5 plans are queued for rebuild, **When** I view the admin dashboard, **Then** I see the count of pending rebuilds.
2. **Given** a CDN upload fails due to network error, **When** I view the error log, **Then** I see the plan ID, timestamp, and error details.
3. **Given** a batch job completes successfully, **When** I view the logs, **Then** I see a summary of files uploaded.

---

### Edge Cases

- What happens when a Subject is assigned to multiple Plans and deleted? All affected plans must have their manifests updated.
- How does system handle circular references or orphaned content? Content without a valid plan association is skipped with a warning log.
- What happens if CDN upload fails mid-batch? Completed uploads remain; failed items are re-queued for next batch with exponential backoff (max 3 retries).
- What happens when Redis is unavailable? Changes are logged to a fallback table in MariaDB and processed when Redis recovers.
- What happens if a JSON file exceeds reasonable size? Files are built in memory buffer first; if buffer exceeds 10MB, a warning is logged and the file is split or flagged for manual review.
- What happens if two Workers try to build the same Plan simultaneously? Redis locking prevents concurrent builds; second worker skips to next plan.
- What happens if a Lesson Stage is updated? Dependency mapping ensures parent Lesson, Unit, and Subject files are all regenerated bottom-up.
- What happens when content is trashed vs. permanently deleted? Trashed content triggers CDN removal; restoration triggers insert flow.
- What if search index grows too large (2000+ lessons)? Index is sharded by Subject to keep individual files under 100KB.

## Requirements *(mandatory)*

### Functional Requirements

**Change Tracking & Batching**

- **FR-001**: System MUST register affected Plan IDs in a Redis Set (`pending_cdn_rebuild`) when Insert, Update, Trash, Restore, or Permanent Delete occurs on monitored DocTypes.
- **FR-002**: System MUST process the rebuild queue every 5 minutes OR when 50 plans accumulate (whichever comes first).
- **FR-003**: System MUST deduplicate plan rebuilds - multiple changes to the same plan within a batch window result in one rebuild.
- **FR-004**: System MUST provide a fallback mechanism to MariaDB when Redis is unavailable.

**Dependency Mapping (Bottom-Up Rebuild)**

- **FR-005**: System MUST implement a dependency tree for change propagation:
  - Lesson Stage change -> queues parent Lesson ID
  - Lesson change -> queues parent Unit IDs
  - Unit change -> queues parent Subject IDs
  - Subject change -> queues parent Plan IDs
- **FR-006**: System MUST rebuild files bottom-up (Lesson -> Unit -> Subject -> Manifest) to ensure parent files contain updated child references.

**Content Generation**

- **FR-007**: System MUST generate JSON files based on Plan context, applying `Memora Plan Override` rules to hide/show content per plan.
- **FR-008**: System MUST calculate and inject access control fields into every JSON file (see Access Matrix below).
- **FR-009**: System MUST implement access inheritance: paid parent makes children paid; `is_free_preview` flag on child overrides parent lock.
- **FR-010**: System MUST only export published content where `is_published` checkbox is checked (draft/unpublished content is excluded).
- **FR-011**: System MUST build JSON files completely in a memory buffer before uploading to ensure atomicity.

**Search Index**

- **FR-012**: System MUST generate a search index for each Plan containing lightweight entries: `{lesson_name, subject_name, lesson_id, unit_id, subject_id}`.
- **FR-013**: System MUST regenerate the search index when any Lesson is added, modified, or deleted within the Plan.
- **FR-014**: System MUST shard search index by Subject when total lessons exceed 500, creating:
  - Master index at `/plans/{plan_id}/search_index.json` listing available shards
  - Subject shards at `/plans/{plan_id}/search/{subject_id}.json`

**CDN Path Structure**

- **FR-015**: System MUST organize files following the path schema:
  - Plan manifest: `/plans/{plan_id}/manifest.json`
  - Subject details: `/plans/{plan_id}/subjects/{subject_id}.json`
  - Unit content: `/units/{unit_id}.json`
  - Lesson content: `/lessons/{lesson_id}.json`
  - Search index: `/plans/{plan_id}/search_index.json` (or sharded structure)

**Cache Busting & Versioning**

- **FR-016**: System MUST include a version parameter (timestamp or hash) in manifest URLs to prevent stale cache hits.
- **FR-017**: System MUST send cache purge requests to the CDN API when files are updated (Cloudflare Purge API or equivalent).
- **FR-018**: System MUST invalidate CDN cache within 60 seconds of file update.

**Lifecycle Management (Trash vs. Delete)**

- **FR-019**: System MUST handle Frappe Trash (soft delete) by:
  - Removing the trashed item from parent JSON references
  - Removing the item's own JSON file from CDN
  - NOT permanently deleting data until permanent delete is triggered
- **FR-020**: System MUST handle Frappe Restore (untrash) by treating it as a new insert, regenerating affected files.
- **FR-021**: System MUST handle Permanent Delete by:
  - Removing all CDN files associated with the deleted item
  - Updating all parent references
- **FR-022**: System MUST delete the entire plan folder when a Plan is permanently deleted.
- **FR-023**: System MUST overwrite existing CDN files at the same path for updates (no versioned URLs for file paths).

**Concurrency Control**

- **FR-024**: System MUST acquire a Redis lock for a Plan ID before building its files.
- **FR-025**: System MUST skip to the next Plan if the current one is already locked by another worker.
- **FR-026**: System MUST release the lock after build completes (success or failure) with a maximum lock TTL of 5 minutes.

**Monitoring**

- **FR-027**: System MUST provide a dashboard showing count of pending rebuilds in the queue.
- **FR-028**: System MUST log CDN upload errors with plan ID, timestamp, and error details.
- **FR-029**: System MUST retry failed uploads up to 3 times with exponential backoff; after exhaustion, move the Plan ID to a dead-letter queue for manual investigation.

**Security**

- **FR-030**: System MUST support generating signed URLs for sensitive content (video links) with a 4-hour expiration window.
- **FR-031**: System MUST ensure CDN configuration prevents directory listing.

### Monitored DocTypes

The system tracks changes on these DocTypes:

- **Academic Plans**: `Memora Academic Plan`, `Memora Plan Subject`
- **Content Structure**: `Memora Subject`, `Memora Track`, `Memora Unit`, `Memora Topic`
- **Lesson Content**: `Memora Lesson`, `Memora Lesson Stage`
- **Overrides**: `Memora Plan Override`

**Tracked Events**: `on_update`, `after_insert`, `on_trash`, `after_delete`, `on_restore` (where applicable)

### Key Entities

- **Change Registry**: Temporary record of affected Plan IDs awaiting rebuild (stored in Redis Set)
- **Dependency Map**: Mapping from child DocType changes to parent IDs that require rebuild
- **CDN Build Job**: Background task that processes a plan, generates JSON files, and uploads to CDN
- **CDN Sync Log**: Audit record of sync operations including successes, failures, and retries
- **Dead-Letter Queue**: Separate queue for Plan IDs that failed after 3 retry attempts, awaiting manual investigation
- **Search Index Entry**: Lightweight record of lesson metadata for client-side search
- **Access Matrix**: Computed access state for each content item (see below)

### JSON Access Matrix

Every exported JSON file MUST contain these access control fields:

| Field                  | Type    | Description                                                                 |
| ---------------------- | ------- | --------------------------------------------------------------------------- |
| `is_published`         | Boolean | Whether content is visible to users                                         |
| `access_level`         | Enum    | One of: `"public"`, `"authenticated"`, `"paid"`, `"free_preview"`           |
| `required_item`        | String  | ERPNext Item Code (only present if `access_level` is `"paid"`)              |
| `is_sold_separately`   | Boolean | Whether this Track/Unit can be purchased independently (DLC pattern)        |
| `parent_item_required` | Boolean | Whether purchasing the parent Subject unlocks this content                  |

**Access Level Logic**:
- `public`: Available to everyone including anonymous users (explicitly marked as public)
- `authenticated`: Requires user login but no purchase (non-paid content under a non-public parent)
- `paid`: Requires purchase of `required_item`
- `free_preview`: Marked as free sample despite parent being paid

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Content changes are reflected on CDN within 10 minutes of modification (batch window + upload time).
- **SC-002**: System handles 1000 content changes per hour without queue backlog accumulation.
- **SC-003**: 99.5% of CDN uploads succeed on first attempt under normal network conditions.
- **SC-004**: Failed uploads are retried and succeed within 30 minutes or escalate to error log.
- **SC-005**: Plan manifests correctly reflect current content state with 100% accuracy (no stale references to deleted or trashed content).
- **SC-006**: Access control fields are present and correct in 100% of generated JSON files.
- **SC-007**: System administrators can identify sync issues within 5 minutes via dashboard/logs.
- **SC-008**: Deleting a Plan removes all associated CDN content within the next batch cycle.
- **SC-009**: Cache invalidation completes within 60 seconds of file update.
- **SC-010**: Search index returns accurate results for 100% of published lessons in a plan.
- **SC-011**: No concurrent build conflicts occur (zero duplicate uploads for same plan in same batch).
- **SC-012**: Individual search index shard files remain under 100KB.

## Assumptions

- Redis is the primary queue mechanism; MariaDB fallback handles Redis downtime gracefully.
- CDN storage (S3/Cloudflare R2) credentials are configured in Frappe site settings.
- CDN API credentials (for cache purge) are configured in Frappe site settings.
- The `is_published` checkbox exists on all content DocTypes (Subject, Track, Unit, Topic, Lesson) to control export eligibility.
- The `is_free_preview` flag exists on Unit and Topic DocTypes for access override.
- The `is_sold_separately` and `parent_item_required` flags exist on Track DocType for DLC handling.
- ERPNext Item integration provides `required_item` codes for paid content.
- Frappe background job workers (RQ) are available for batch processing.
- Network connectivity to CDN is generally reliable; transient failures are expected and handled via retry.
- Frappe's document lifecycle hooks (`on_trash`, `after_delete`, `on_restore`) are available and fire reliably.

## Out of Scope

- Real-time streaming updates (WebSocket) - batch processing only.
- Content versioning or rollback capabilities.
- Multi-CDN failover or geographic distribution.
- Content transformation (image resizing, video transcoding) - raw metadata only.
- Student-facing APIs - this system produces static files consumed by frontend directly from CDN.
- Full-text search indexing - search index contains titles only, not content body.
- Handling trashed items differently than deleted (both result in CDN removal; distinction is Frappe-internal).

## Clarifications

### Session 2026-01-25

- Q: What is the expiration duration for signed URLs (video links)? → A: 4 hours (balances session length with security)
- Q: What happens after 3 retry failures for CDN uploads? → A: Move to dead-letter queue for manual investigation
- Q: What triggers the "authenticated" access level? → A: Non-paid content under a non-public parent requires login
- Q: Which field determines published status? → A: `is_published` checkbox on each content DocType
