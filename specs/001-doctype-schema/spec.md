# Feature Specification: Memora DocType Schema Creation

**Feature Branch**: `001-doctype-schema`
**Created**: 2026-01-24
**Status**: Draft
**Input**: User description: "Create scripts to create DocTypes using after_migrate hook for Memora custom app with complete data schema including educational content hierarchy, player profiles, FSRS spaced repetition engine, and commerce system"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Administrator Deploys Memora App (Priority: P1)

An administrator installs or updates the Memora custom app on a Frappe/ERPNext site. Upon running `bench migrate`, all required DocTypes are automatically created or updated without manual intervention.

**Why this priority**: This is the foundational story - without the automatic schema creation, no other functionality can exist. The after_migrate hook ensures consistent deployment across all environments.

**Independent Test**: Can be fully tested by running `bench migrate` on a fresh site and verifying all 19 DocTypes exist with correct fields and indexes.

**Acceptance Scenarios**:

1. **Given** a Frappe site without Memora DocTypes, **When** the administrator runs `bench migrate` after installing Memora, **Then** all 19 DocTypes are created with correct field definitions
2. **Given** an existing site with older Memora DocTypes, **When** the administrator runs `bench migrate` after updating the app, **Then** DocTypes are updated without data loss
3. **Given** all DocTypes already exist and match the schema, **When** the administrator runs `bench migrate`, **Then** the migration completes without errors or unnecessary modifications

---

### User Story 2 - Content Manager Creates Educational Hierarchy (Priority: P2)

A content manager uses Frappe Desk to create educational content following the hierarchical structure: Subject > Track > Unit > Topic > Lesson > Lesson Stages.

**Why this priority**: The educational content hierarchy is the core data structure. Without it, no learning content can be organized.

**Independent Test**: Can be tested by navigating to Frappe Desk, creating a Subject, then a Track linked to that Subject, continuing down the hierarchy to Lesson Stages.

**Acceptance Scenarios**:

1. **Given** a logged-in content manager, **When** they create a new Memora Subject with title and color_code, **Then** the subject is saved with ID matching the title (e.g., "Math") and all standard mixin fields
2. **Given** an existing Subject, **When** they create a Track linked to that Subject, **Then** the Track is saved with a hash-based ID and parent_subject as an indexed link field
3. **Given** a Lesson, **When** they add Lesson Stages with type (Video/Question/Text/Interactive) and JSON config, **Then** the stages are saved as child table records

---

### User Story 3 - Academic Planner Configures Plans and Products (Priority: P2)

An academic planner creates academic plans that combine seasons, streams, and subjects with optional overrides for specific content visibility.

**Why this priority**: Academic plans connect raw content to purchasable products and student access control. This is essential for monetization.

**Independent Test**: Can be tested by creating a Season, Stream, then an Academic Plan linking them with included subjects and override rules.

**Acceptance Scenarios**:

1. **Given** existing Season and Stream records, **When** a planner creates an Academic Plan with subjects, **Then** the plan is saved with indexed links to season and stream
2. **Given** an Academic Plan, **When** a planner adds an override to hide a specific Track, **Then** the override is stored with target_doctype, target_name (dynamic link), and action
3. **Given** an ERPNext Item, **When** a planner creates a Product Grant linking item to academic plan, **Then** the grant specifies what content is unlocked upon purchase

---

### User Story 4 - System Tracks Player Progress with FSRS (Priority: P2)

The system maintains player profiles with wallet data and uses the FSRS (Free Spaced Repetition Scheduler) algorithm to schedule question reviews based on memory state.

**Why this priority**: Player profiles and the FSRS engine are core to the gamified learning experience. The memory state indexing is critical for performance at scale.

**Independent Test**: Can be tested by creating a Player Profile linked to a User, then verifying Memory State records can be created with FSRS fields and that next_review is indexed.

**Acceptance Scenarios**:

1. **Given** a Frappe User, **When** a Player Profile is created for them, **Then** the profile is saved with unique indexed link to User and includes devices child table
2. **Given** a Player Profile, **When** a Memory State record is created for a question, **Then** it includes stability, difficulty, next_review (indexed), and state fields
3. **Given** thousands of Memory State records, **When** querying for due reviews, **Then** the indexed next_review field ensures fast retrieval

---

### User Story 5 - System Logs Interactions and Processes Transactions (Priority: P3)

The system records all student question interactions as write-only logs and processes subscription transactions through multiple payment methods.

**Why this priority**: Logging and commerce are supporting systems. They require the content and player infrastructure to be in place first.

**Independent Test**: Can be tested by creating Interaction Logs and Subscription Transactions, verifying proper field structure and indexing.

**Acceptance Scenarios**:

1. **Given** a player answering a question, **When** an Interaction Log is created, **Then** it captures player, academic_plan, question_id, answer data, correctness, and time_taken with appropriate indexes
2. **Given** a player purchasing access, **When** a Subscription Transaction is created, **Then** it uses naming_series SUB-TX-.YYYY.- (e.g., SUB-TX-2026-00001), captures payment details, and links to Product Grant

---

### Edge Cases

- What happens when a DocType already exists with different field definitions? The migration should update fields without data loss.
- How does the system handle circular references in dynamic links? Validation should prevent invalid target_doctype/target_name combinations.
- What happens if the User linked to a Player Profile is deleted? The link should be preserved as-is (Frappe default behavior) with application-level handling.
- How does the system handle duplicate device_id in Player Devices? The device_id should be unique per player (enforced at application level).
- What happens when creating a Subject with a duplicate title? Should fail with unique constraint error (autoname: field:title).

## Clarifications

### Session 2026-01-24

- Q: Migration error handling strategy? → A: Atomic rollback - fail entire migration if any DocType fails
- Q: Memory State lifecycle ownership? → A: Application layer - schema stores state; calling code manages transitions
- Q: Observability requirements for migration? → A: Structured logs - log each DocType creation/update with timestamps
- Q: Interaction Log retention policy? → A: Out of scope - logs accumulate; archival is a separate future feature
- Q: Question ID field type? → A: UUID/hash - opaque identifier managed by application layer

## Requirements *(mandatory)*

### Functional Requirements

#### Schema Creation (after_migrate hook)

- **FR-001**: System MUST create all 19 DocTypes automatically when `bench migrate` runs
- **FR-002**: System MUST be idempotent - running migrate multiple times produces the same result
- **FR-003**: System MUST create child table DocTypes before their parent DocTypes reference them
- **FR-004**: System MUST apply database indexes as specified in the indexing strategy
- **FR-004a**: System MUST use atomic rollback on migration errors - if any DocType creation fails, the entire migration fails and no partial schema changes persist
- **FR-004b**: System MUST produce structured logs for each DocType creation/update operation, including timestamps and operation type (created/updated/unchanged)

#### Educational Content DocTypes

- **FR-005**: System MUST create `Memora Subject` with autoname: field:title, title, color_code, and all standard mixin fields
- **FR-006**: System MUST create `Memora Track` with default naming (hash), indexed parent_subject link and is_sold_separately flag
- **FR-007**: System MUST create `Memora Unit` with default naming (hash), indexed parent_track link and badge_image field
- **FR-008**: System MUST create `Memora Topic` with default naming (hash), indexed parent_unit link
- **FR-009**: System MUST create `Memora Lesson` with default naming (hash), indexed parent_topic link and stages table field
- **FR-010**: System MUST create `Memora Lesson Stage` child table with title, type (Select: Video/Question/Text/Interactive), and config (JSON)

#### Standard Mixin Fields

- **FR-011**: System MUST add is_published (Check), is_free_preview (Check), sort_order (Int, indexed), image (Attach Image), and description (Small Text) to Subject, Track, Unit, Topic, and Lesson DocTypes

#### Planning & Products DocTypes

- **FR-012**: System MUST create `Memora Season` with autoname: field:title, title, is_published, start_date, and end_date
- **FR-013**: System MUST create `Memora Stream` with autoname: field:title, title field
- **FR-014**: System MUST create `Memora Academic Plan` with default naming, title, indexed season link, indexed stream link, subjects table, and overrides table
- **FR-015**: System MUST create `Memora Plan Subject` child table with subject link and sort_order
- **FR-016**: System MUST create `Memora Plan Override` child table with target_doctype (Link to DocType with filter), target_name (Dynamic Link referencing target_doctype), action (Select: Hide/Rename/Set Free/Set Sold Separately), and override_value
- **FR-017**: System MUST create `Memora Product Grant` with default naming, indexed item_code link to Item, indexed academic_plan link, grant_type (Select: Full Plan Access/Specific Components), and unlocked_components table
- **FR-018**: System MUST create `Memora Grant Component` child table with target_doctype (Link to DocType with filter) and target_name (Dynamic Link referencing target_doctype)

#### Player Profile DocTypes

- **FR-019**: System MUST create `Memora Player Profile` with default naming, unique indexed user link, display_name, avatar, indexed current_plan link, and devices table
- **FR-020**: System MUST create `Memora Player Device` child table with device_id, device_name, and is_trusted
- **FR-021**: System MUST create `Memora Player Wallet` with default naming, unique indexed player link, total_xp, current_streak, and last_played_at

#### Engine & Logs DocTypes

- **FR-022**: System MUST create `Memora Interaction Log` with default naming, indexed player link, indexed academic_plan link, indexed question_id, student_answer, correct_answer, is_correct, time_taken, and timestamp
- **FR-023**: System MUST create `Memora Memory State` with default naming, indexed player link, indexed question_id, stability (Float), difficulty (Float), indexed next_review (Datetime), and state (Select: New/Learning/Review/Relearning)

#### Commerce DocTypes

- **FR-024**: System MUST create `Memora Subscription Transaction` with autoname: naming_series:, naming_series field with default SUB-TX-.YYYY.-, indexed player link, transaction_type (Select: Purchase/Renewal/Upgrade), payment_method (Select: Payment Gateway/Manual-Admin/Voucher), status (Select: Pending Approval/Completed/Failed/Cancelled), transaction_id, amount (Currency), receipt_image, indexed related_grant link, and read-only erpnext_invoice link

### Key Entities

- **Memora Subject**: Top-level educational category (Math, Physics). Contains color branding and standard content controls. ID = title.
- **Memora Track**: Sub-category within a Subject. Can be sold separately from parent subject. ID = hash (supports duplicate titles).
- **Memora Unit**: Learning module within a Track. Awards badge upon completion. ID = hash.
- **Memora Topic**: Specific topic within a Unit. Groups related lessons. ID = hash.
- **Memora Lesson**: Individual learning item containing multiple stages. ID = hash.
- **Memora Lesson Stage**: Atomic content piece (Video/Question/Text/Interactive) with JSON configuration.
- **Memora Season**: Academic period (e.g., "Gen-2007") with date bounds. ID = title.
- **Memora Stream**: Educational track type (Scientific/Literary/Industrial). ID = title.
- **Memora Academic Plan**: Combines Season + Stream + Subjects with visibility overrides. ID = hash.
- **Memora Product Grant**: Links ERPNext Item to Academic Plan for access control. ID = hash.
- **Memora Player Profile**: Game identity separate from Frappe User. Tracks plan and devices. ID = hash.
- **Memora Player Wallet**: High-velocity XP and streak data for gamification. ID = hash.
- **Memora Interaction Log**: Write-only audit trail of all question attempts. ID = hash. The question_id field is an opaque UUID/hash string managed by application layer.
- **Memora Memory State**: FSRS algorithm state per player-question pair. Critical for spaced repetition scheduling. ID = hash. State transitions (New→Learning→Review→Relearning) are managed by application layer; schema only stores current state value.
- **Memora Subscription Transaction**: Payment records linking purchases to product grants. ID = naming_series (e.g., SUB-TX-2026-00001).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 19 DocTypes are created successfully after a single `bench migrate` execution on a fresh site
- **SC-002**: Running `bench migrate` on an existing site with all DocTypes completes in under 30 seconds without errors
- **SC-003**: Content managers can create complete content hierarchy (Subject through Lesson Stage) using Frappe Desk without errors
- **SC-004**: System supports 100,000 Memory State records with next_review queries returning results in under 100ms (due to proper indexing)
- **SC-005**: All indexed fields specified in the indexing strategy have database indexes created
- **SC-006**: Child table relationships are properly established - deleting a parent cascades to children appropriately
- **SC-007**: Dynamic Link fields in Override and Grant Component tables properly resolve to their target DocTypes with navigation arrows visible in Desk
- **SC-008**: Subject, Season, and Stream DocTypes use title as ID (human-readable constants)
- **SC-009**: Subscription Transaction DocTypes use naming series format SUB-TX-YYYY-##### for sequential IDs

## Implementation Notes

### Naming & Autoname Strategy

| DocType | Autoname | Rationale |
|---------|----------|-----------|
| Memora Subject | `field:title` | Human-readable IDs (e.g., "Math", "Physics") act as constants |
| Memora Season | `field:title` | Human-readable IDs (e.g., "Gen-2007") |
| Memora Stream | `field:title` | Human-readable IDs (e.g., "Scientific", "Literary") |
| Memora Subscription Transaction | `naming_series:` | Sequential IDs with year (SUB-TX-2026-00001) |
| All others | Default (hash) | Supports duplicate titles (e.g., "Introduction" in multiple Units) |

### Dynamic Link Configuration (Critical for Frappe Desk UI)

For Dynamic Link fields to work correctly in Frappe Desk (with the arrow icon for navigation):

1. **target_doctype field**: MUST be type `Link` pointing to `DocType` (not Select type)
   - Apply a filter in code to restrict options to valid DocTypes only (e.g., Track, Unit, Topic, Lesson for Plan Override)
   - Select type would work functionally but won't show the navigation arrow icon

2. **target_name field**: MUST be type `Dynamic Link` with `options` property set to the name of the target_doctype field
   - Example: If target_doctype field is named `target_doctype`, then target_name's options = `target_doctype`

3. **Filter Implementation**: Use `get_query` in the form's client script or set link filters in DocType JSON to restrict the DocType link field to show only the allowed DocTypes

### Indexing Strategy

Database indexes MUST be enabled for:
1. **Content Hierarchy**: parent_subject, parent_track, parent_unit, parent_topic
2. **Player Data**: player field in Logs, Wallet, and Transaction tables
3. **FSRS Algorithm**: next_review in Memory State (most critical index)
4. **Plans**: season, stream, academic_plan fields
5. **Commerce**: item_code in Product Grant

## Assumptions

- The Memora app is properly installed in the Frappe bench apps directory
- ERPNext is installed (required for Item and Sales Invoice links in commerce DocTypes)
- Frappe version supports all field types used (JSON, Dynamic Link, Attach Image, etc.)
- Database (MariaDB/PostgreSQL) supports the required index types
- The after_migrate hook mechanism is available in the installed Frappe version

## Out of Scope

- API endpoints for content delivery
- Frontend/mobile app integration
- FSRS algorithm implementation (only the data structure)
- Payment gateway integration (only transaction record structure)
- User permission rules and role-based access
- Data migration from existing systems
- Backup and restore procedures
- Interaction Log retention/archival strategy (logs accumulate indefinitely; archival is a separate future feature)
