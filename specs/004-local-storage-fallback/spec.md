# Feature Specification: Local Content Staging & Fallback Engine

**Feature Branch**: `004-local-storage-fallback`
**Created**: 2026-01-25
**Status**: Draft
**Input**: User description: "نظام التخزين المحلي والتبديل الاحتياطي - Local Content Staging & Fallback Engine"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Local Backup of Generated Content (Priority: P1)

As a system administrator, I want every generated JSON file to be saved to the local server disk first, so that I have a backup copy of the content in case the CDN upload fails.

**Why this priority**: This is the foundation of the entire feature. Without reliable local storage, the fallback mechanism cannot function, and data loss becomes a risk during CDN outages.

**Independent Test**: Can be tested by generating a JSON file and verifying it exists at the expected local path with correct content, regardless of CDN status.

**Acceptance Scenarios**:

1. **Given** a content item (Plan, Subject, Unit) is created or updated, **When** the JSON generation process completes, **Then** the JSON file is saved to the local storage path `/sites/{site_name}/public/memora_content/` with the correct structure.

2. **Given** the CDN upload fails due to network issues, **When** the JSON file has been generated, **Then** the local copy remains intact and accessible.

3. **Given** a JSON file is being written to local storage, **When** another request attempts to read the same file, **Then** the reader either gets the complete previous version or waits until the new version is fully written (atomic write).

---

### User Story 2 - Instant URL Fallback to Local Server (Priority: P1)

As a frontend developer, I want the system to automatically return URLs pointing to the local server when CDN is disabled in settings, so that the application continues to function without interruption.

**Why this priority**: This ensures business continuity. Students must be able to access learning content even when CDN is unavailable, making this equally critical as local storage.

**Independent Test**: Can be tested by toggling the CDN enable setting and verifying that API responses return the appropriate URL prefix (CDN base URL when enabled, local domain when disabled).

**Acceptance Scenarios**:

1. **Given** CDN is enabled in settings and CDN is healthy, **When** the system generates a content URL, **Then** the URL uses the CDN base URL prefix.

2. **Given** CDN is disabled in settings, **When** the system generates a content URL, **Then** the URL uses the local domain with `/files/memora_content/` path.

3. **Given** CDN was enabled and is now disabled, **When** the API is called within 1 second of the change, **Then** all returned URLs point to the local server.

---

### User Story 3 - CDN Synchronization from Local Source (Priority: P2)

As a backend developer, I want the CDN upload process to use locally stored files as the source, so that there is 100% data consistency between the local server and what students access via CDN.

**Why this priority**: While important for data integrity, this can be implemented after the core local storage and fallback mechanisms are in place.

**Independent Test**: Can be tested by generating content locally, triggering CDN sync, and comparing file hashes between local storage and CDN.

**Acceptance Scenarios**:

1. **Given** a JSON file exists in local storage, **When** the CDN sync process runs, **Then** the file uploaded to CDN is byte-for-byte identical to the local file.

2. **Given** a file exists on CDN but not locally, **When** a sync verification runs, **Then** the system flags this as an inconsistency.

---

### User Story 4 - Content Health Monitoring (Priority: P2)

As a system administrator, I want a periodic health check that verifies local files exist and match database records, so that I can detect and fix data integrity issues proactively.

**Why this priority**: Important for operational reliability but not blocking core functionality. Can be implemented after main features are stable.

**Independent Test**: Can be tested by running the health check and verifying it correctly reports missing files or mismatches.

**Acceptance Scenarios**:

1. **Given** database records exist for content items, **When** the health check runs, **Then** it verifies each expected local file exists.

2. **Given** a local file is missing, **When** the health check completes, **Then** the system logs a warning and optionally triggers regeneration.

3. **Given** low disk space (below 10%), **When** the system attempts to generate new content, **Then** an alert is sent to administrators and generation is paused.

---

### User Story 5 - Automatic Cleanup on Content Deletion (Priority: P3)

As a backend developer, I want local files to be automatically deleted when their corresponding content is deleted from the backend, so that storage is not wasted on orphaned files.

**Why this priority**: Important for storage hygiene but not critical for core functionality. The system works without this, just with unnecessary files taking up space.

**Independent Test**: Can be tested by deleting a content item and verifying the corresponding local file is removed.

**Acceptance Scenarios**:

1. **Given** a Plan, Subject, or Unit is deleted from the backend, **When** the deletion is committed, **Then** the corresponding local JSON file is deleted immediately.

2. **Given** a parent item (Plan) is deleted, **When** the deletion is committed, **Then** all child files (manifest, subjects) in that plan's directory are also deleted.

---

### Edge Cases

- **Disk Full**: When disk space falls below 10%, the system alerts administrators and pauses JSON generation to prevent corrupted writes.
- **Permission Denied**: If the frappe user lacks write permissions on the public directory, the system logs a clear error and fails gracefully without crashing.
- **Concurrent Writes**: When multiple processes attempt to write the same file simultaneously, atomic write operations ensure only one complete version exists (last writer wins).
- **File Overwrite**: When regenerating content, the previous version is renamed to `.prev` (e.g., `manifest.json.prev`) before the new file is written - providing single-version rollback capability.
- **Network Partition**: If CDN becomes unreachable mid-sync, locally stored files remain the source of truth and sync retries using exponential backoff (30s, 1m, 2m, 5m, max 15m between retries).
- **Retry Exhaustion**: When CDN upload retries are exhausted (after ~1 hour of failures), the system marks the sync as failed in the sync log, alerts administrators via system notification and email, and queues the item for manual retry.
- **Settings Change Race**: If CDN settings change while a URL is being generated, the URL reflects the setting value at the time of generation start.

## Requirements *(mandatory)*

### Functional Requirements

#### Local Storage Management

- **FR-001**: System MUST create and maintain the directory structure `/sites/{site_name}/public/memora_content/` with subdirectories matching CDN path structure.
- **FR-002**: System MUST write JSON files atomically by first writing to a temporary location then moving to the final path.
- **FR-003**: System MUST delete local JSON files immediately when corresponding content items (Plan, Subject, Unit) are deleted from the database.
- **FR-004**: System MUST retain the previous version of a file by renaming it with `.prev` suffix before writing a new version, enabling single-version rollback.
- **FR-005**: System MUST store files with paths matching CDN structure:
  - `plans/{plan_id}/manifest.json`
  - `plans/{plan_id}/subjects/{subject_id}.json`
  - `units/{unit_id}.json`

#### URL Resolver

- **FR-006**: System MUST provide a global function `get_content_url(path)` that returns the appropriate full URL based on CDN settings.
- **FR-007**: When CDN is enabled (`CDN Settings.enabled == True`), `get_content_url(path)` MUST return `{CDN_Base_URL}/{path}`.
- **FR-008**: When CDN is disabled (`CDN Settings.enabled == False`), `get_content_url(path)` MUST return `{Local_Domain}/files/memora_content/{path}`.
- **FR-009**: All generated JSON files (manifests, content files) MUST use `get_content_url()` for building internal links to related files.

#### System Settings

- **FR-010**: System MUST provide `Enable CDN` toggle field in Memora/CDN settings.
- **FR-011**: System MUST provide `Local Fallback Mode` field in Memora/CDN settings for explicit fallback control.
- **FR-012**: Settings changes MUST take effect immediately without requiring server restart.

#### Health Check & Monitoring

- **FR-013**: System MUST monitor available disk space and alert administrators when it falls below 10% via Frappe system notification and email to users with System Manager role.
- **FR-014**: System MUST pause content generation operations when disk space is critically low.
- **FR-015**: System MUST provide a health check function that verifies local files exist for all database content records, running hourly during business hours with a comprehensive daily scan overnight.
- **FR-016**: System MUST log all file operation failures with sufficient detail for debugging.
- **FR-017**: System MUST mark CDN uploads as failed after retry exhaustion (~1 hour), alert administrators, and provide a mechanism for manual retry.

### Key Entities

- **Local Content File**: A JSON file stored on the local server filesystem, representing serialized content data. Key attributes: path, content hash, last modified timestamp, corresponding database record ID.
- **CDN Settings**: Configuration controlling CDN behavior. Key attributes: enabled flag, CDN base URL, local fallback mode, local domain.
- **Content URL**: A resolved URL pointing to content, either on CDN or local server. Determined dynamically based on CDN settings at resolution time.
- **Health Check Report**: Result of filesystem validation. Key attributes: checked timestamp, missing files list, orphaned files list, disk space status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Local file generation completes within 500ms after content processing finishes.
- **SC-002**: URL resolver returns correct URL prefix (local or CDN) within 1 second of CDN settings change.
- **SC-003**: 100% data match between local files and CDN-uploaded files (verified by hash comparison).
- **SC-004**: Local server (via web server) can serve 1000 concurrent requests for static files during fallback mode.
- **SC-005**: Zero data loss during CDN outages - all generated content remains accessible via local server.
- **SC-006**: Health check identifies 100% of missing or orphaned files within its scan scope.
- **SC-007**: System sends disk space alerts within 1 minute of crossing the 10% threshold.

## Clarifications

### Session 2026-01-25

- Q: How frequently should the content health check run? → A: Hourly during business hours, daily full scan overnight
- Q: What retry strategy should be used when CDN upload fails? → A: Exponential backoff (30s, 1m, 2m, 5m, max 15m between retries)
- Q: Should the system retain previous file versions when content is regenerated? → A: Keep last version only (rename to `.prev` before overwrite)
- Q: How should disk space alerts be delivered to administrators? → A: Frappe system notification + email to System Managers
- Q: What should happen when CDN upload retries are exhausted? → A: Mark as failed in sync log, alert admins, queue for manual retry

## Assumptions

- The web server (Nginx or similar) is already configured to serve static files from the Frappe public directory.
- The frappe user has write permissions on the `/sites/{site_name}/public/` directory.
- CDN settings DocType already exists or will be created as part of this feature.
- The existing JSON generation pipeline can be modified to write to local storage first.
- Network latency between the server and CDN is not a factor in the 500ms local write requirement.
