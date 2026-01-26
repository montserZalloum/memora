# Feature Specification: Atomic JSON Content Generation & CDN Distribution

**Feature Branch**: `008-atomic-content-cdn`
**Created**: 2026-01-26
**Status**: Draft
**Input**: PRD for static JSON file generation system with access control inheritance and plan-specific overrides

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Student Loads Subject Content (Priority: P1)

A student opens the learning app and selects their academic plan. The system provides a fast-loading manifest of available subjects, each showing access status (free, preview, or paid) and navigation to subject hierarchy.

**Why this priority**: This is the primary entry point for all students. Without fast content loading, the entire learning experience fails. Sub-second loading enables engagement and reduces dropout.

**Independent Test**: Can be fully tested by fetching manifest.json for a plan and verifying it contains all expected subjects with correct access levels and navigation URLs.

**Acceptance Scenarios**:

1. **Given** a student with plan "PLAN-2024", **When** they open the app, **Then** the manifest loads within 1 second showing all their available subjects
2. **Given** a manifest with 10 subjects, **When** loaded, **Then** each subject displays title, image, color, access level, and navigation URL
3. **Given** a student's plan has been updated with new subjects, **When** they refresh, **Then** they see the updated content (via version-based cache busting)

---

### User Story 2 - Student Navigates Subject Hierarchy (Priority: P1)

A student selects a subject and browses through Tracks -> Units -> Topics. The hierarchy reflects their plan's customizations including hidden content, modified access levels, and linear/non-linear navigation modes.

**Why this priority**: Navigation is core to the learning experience. Students must find and access lessons through the content tree efficiently.

**Independent Test**: Can be fully tested by fetching subject hierarchy JSON and verifying structure matches expected tracks/units/topics with correct access inheritance and override application.

**Acceptance Scenarios**:

1. **Given** subject "Mathematics" with 3 tracks, **When** student views hierarchy, **Then** they see all non-hidden tracks with their units and topics
2. **Given** a unit marked as "free_preview" in a paid subject, **When** viewing hierarchy, **Then** that unit and all its children show as "free_preview"
3. **Given** a topic hidden via plan override, **When** viewing hierarchy, **Then** that topic does not appear in the JSON
4. **Given** a subject with is_linear=true, **When** viewing hierarchy, **Then** the navigation enforces sequential access

---

### User Story 3 - Student Accesses Topic Lessons (Priority: P1)

A student selects a topic and sees the list of lessons within it. Each lesson shows its title, completion tracking bit_index, and direct URL to lesson content.

**Why this priority**: Lessons are the atomic learning units. Students must efficiently discover and access individual lessons within a topic.

**Independent Test**: Can be fully tested by fetching topic JSON and verifying lesson list matches expected content with correct bit indices for progress tracking.

**Acceptance Scenarios**:

1. **Given** topic "Exponent Rules" with 15 lessons, **When** student views topic, **Then** they see all non-hidden lessons with titles and URLs
2. **Given** a lesson with bit_index 45, **When** viewing topic JSON, **Then** the bit_index is included for progress engine integration
3. **Given** lessons hidden via plan override, **When** viewing topic, **Then** hidden lessons are excluded from the list

---

### User Story 4 - Student Plays Lesson Content (Priority: P1)

A student opens a lesson and receives the raw lesson content including all stages (MCQ, video, etc.) with their weights, target times, and skippability settings.

**Why this priority**: Lesson playback is the core value delivery. Without accessible lesson content, no learning occurs.

**Independent Test**: Can be fully tested by fetching lesson JSON and verifying all stages are present with required metadata.

**Acceptance Scenarios**:

1. **Given** lesson "Introduction" with 5 stages, **When** student opens lesson, **Then** all stages load with type, weight, target_time, is_skippable, and data
2. **Given** a stage of type "MCQ", **When** viewing stage data, **Then** question, options, and answer fields are present
3. **Given** lesson content is shared across plans, **When** fetching, **Then** all plans reference the same lesson file (no duplication)

---

### User Story 5 - Content Admin Triggers Regeneration (Priority: P2)

A content administrator saves changes to subjects, lessons, plans, or overrides. The system automatically queues affected plans for JSON regeneration and distributes updated files.

**Why this priority**: Content updates must propagate to students. Without regeneration triggers, content becomes stale.

**Independent Test**: Can be fully tested by modifying a subject and verifying the affected plan(s) are queued for regeneration with correct file outputs.

**Acceptance Scenarios**:

1. **Given** admin saves a lesson change, **When** saved, **Then** all plans containing that lesson are added to regeneration queue
2. **Given** admin adds a plan override, **When** saved, **Then** only the affected plan is queued for regeneration
3. **Given** regeneration completes, **When** student loads content, **Then** they receive updated files with new version timestamp

---

### User Story 6 - System Enforces Access Control (Priority: P2)

The system generates JSON files with pre-computed access levels. Students can only see content available in their plan's JSON. Paid content requires valid grants in the student's wallet.

**Why this priority**: Access control ensures monetization and content security. Without it, paid content could be accessed freely.

**Independent Test**: Can be fully tested by comparing JSON outputs for different plans and verifying access_level fields differ according to override rules.

**Acceptance Scenarios**:

1. **Given** a paid subject with no overrides, **When** JSON generated, **Then** all children inherit access_level "paid"
2. **Given** a unit marked is_free_preview in a paid subject, **When** JSON generated, **Then** that unit and children have access_level "free_preview"
3. **Given** plan override sets unit to "paid", **When** JSON generated, **Then** override takes precedence over base content settings
4. **Given** student without required_item grant, **When** they attempt access, **Then** frontend shows purchase prompt

---

### Edge Cases

- What happens when a plan has no subjects assigned? (Return empty subjects array in manifest)
- How does system handle circular references in content hierarchy? (Prevent via validation on save)
- What happens when a topic has zero non-hidden lessons? (Exclude topic from hierarchy if all lessons hidden)
- How does system handle concurrent regeneration requests for same plan? (Queue deduplication via Redis SET)
- What happens when CDN upload fails mid-batch? (Atomic consistency - rollback partial uploads, retry)
- What happens when lesson content is deleted but still referenced? (Validation prevents deletion of referenced content)

## Requirements *(mandatory)*

### Functional Requirements

**File Structure & Storage**

- **FR-001**: System MUST generate hierarchical JSON files in the structure: `/public/memora_content/plans/{plan_id}/` for plan-specific files and `/public/memora_content/lessons/` for shared lesson content
- **FR-002**: System MUST generate `manifest.json` for each plan containing plan_id, title, version timestamp, and subjects array
- **FR-003**: System MUST generate `{subject_id}_h.json` (hierarchy) for each subject containing tracks -> units -> topics structure
- **FR-004**: System MUST generate `{subject_id}_b.json` (bitmap) for each subject containing progress engine bit mappings
- **FR-005**: System MUST generate `{topic_id}.json` for each topic containing lesson list with bit_index references
- **FR-006**: System MUST generate `{lesson_id}.json` for each lesson containing stages array with type, weight, target_time, is_skippable, and data

**Access Level Inheritance**

- **FR-007**: System MUST implement inheritance rule: paid subject -> all children inherit "paid" by default
- **FR-008**: System MUST implement free_preview piercing: if any node has is_free_preview=true, it and all descendants become "free_preview"
- **FR-009**: System MUST implement sold_separately tracks: tracks with is_sold_separately=true become independent "paid" islands
- **FR-010**: System MUST support four access levels: "public", "authenticated", "free_preview", "paid"
- **FR-011**: System MUST include required_item field for paid content linking to purchasable products

**Plan Overrides**

- **FR-012**: System MUST apply "Hide" override by completely removing the node from JSON output
- **FR-013**: System MUST apply "Set Access Level" override to change access_level field
- **FR-014**: System MUST apply "Set Linear" override to change is_linear field
- **FR-015**: System MUST apply overrides AFTER computing base inheritance (overrides take precedence)

**Generation Pipeline**

- **FR-016**: System MUST trigger regeneration when Subject, Lesson, Academic Plan, or Override documents are saved
- **FR-017**: System MUST queue affected plans to `pending_cdn_plans` in Redis for processing
- **FR-018**: System MUST implement atomic consistency - no subject files uploaded until all related topic and lesson files are ready
- **FR-019**: System MUST include version timestamp in manifest.json for cache busting

**Performance & Security**

- **FR-020**: System MUST generate plan-specific JSON so students cannot access content outside their plan
- **FR-021**: System MUST support local staging before CDN upload
- **FR-022**: System MUST use relative URLs in JSON for content navigation

### Key Entities

- **Academic Plan**: Represents a cohort/curriculum (e.g., "Grade 12 Science 2024"). Contains list of subjects and plan-level overrides.
- **Subject**: Top-level content container with is_paid flag, contains tracks. Linked to purchasable Item.
- **Track**: Organizational grouping within subject, can be sold_separately.
- **Unit**: Learning module within track, can have is_free_preview flag.
- **Topic**: Collection of lessons within unit, can have is_free_preview flag.
- **Lesson**: Atomic learning unit with stages, shared across plans. Contains bit_index for progress tracking.
- **Stage**: Individual learning activity (MCQ, video, etc.) within a lesson.
- **Plan Override**: Per-plan customization rule (hide, set_access, set_linear) for any content node.
- **Manifest**: Plan-level index file listing available subjects with access metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Students can load manifest and navigate to any lesson within 1 second (sub-second loading)
- **SC-002**: System supports thousands of lessons per plan without file size degradation (hierarchical structure keeps individual files small)
- **SC-003**: Content updates propagate to all affected plans within the regeneration batch window
- **SC-004**: 100% of access control rules are enforced through pre-computed JSON (no runtime permission checks needed for content visibility)
- **SC-005**: Zero data leakage - students cannot access content not present in their plan's JSON files
- **SC-006**: System maintains atomic consistency - partial updates never visible to students
- **SC-007**: 95% reduction in backend permission calculation load (access levels pre-baked into JSON)

## Assumptions

- Frappe Framework's existing DocType structure for Subject, Track, Unit, Topic, Lesson, and Academic Plan is already in place
- Redis infrastructure exists for queue management (from existing features)
- Local storage fallback from feature 004 is available for JSON file staging
- CDN export infrastructure from feature 002 is available for distribution
- Progress engine bitset from feature 005 provides bit_index values for lessons
- Student wallet/grants system exists for checking paid content access (from Player Core feature 007)
