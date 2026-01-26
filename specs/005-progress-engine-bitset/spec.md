# Feature Specification: Progress Tracking and Smart Unlocking Engine (Bitset Edition)

**Feature Branch**: `005-progress-engine-bitset`
**Created**: 2026-01-25
**Last Updated**: 2026-01-26 (v1.1)
**Status**: Updated
**Version**: 1.1
**Input**: User description: "PRD for Memora Structure Progress Engine - a high-performance progress tracking engine using Redis Bitmaps for lesson completion state and unlock logic supporting 100K concurrent users"

## v1.1 Updates (2026-01-26)

This version incorporates five critical enhancements to improve system performance, game balance, and data integrity:

1. **Lazy Cache Warming (FR-023, FR-025, FR-026)**: Bitmaps are loaded on-demand from MariaDB instead of bulk-loading at server startup, preventing database overload during restarts
2. **JSON Integrity Filter (FR-027, FR-028)**: Unpublished and deleted lessons are automatically excluded from the JSON structure generation
3. **Bit Index Protection (FR-029, FR-030)**: Each lesson's bit_index is strictly scoped to its Subject ID; moving lessons triggers automatic progress reset
4. **Persistence of Success (FR-031)**: Once a lesson is passed (bit=1), it cannot be reset to 0 through normal gameplay, protecting student achievements
5. **Two-Tier Reward Policy (FR-021 through FR-024)**: Uses Redis SETBIT return value to distinguish first-time completions (full XP) from replays (fixed 10 XP bonus)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete a Lesson and Track Progress (Priority: P1)

As a student using the Memora learning platform, I want my lesson completion to be instantly recorded and reflected in my progress, so that I can see my advancement through the course material without delays.

**Why this priority**: This is the core write operation of the entire system. Without reliable lesson completion tracking, no other feature can function. This represents the primary value delivery mechanism.

**Independent Test**: Can be fully tested by completing a lesson and verifying the progress state updates immediately. Delivers value by giving students instant feedback on their learning progress.

**Acceptance Scenarios**:

1. **Given** a student has remaining hearts (> 0), **When** they successfully complete a lesson, **Then** the lesson is marked as "Passed" and the completion is persisted immediately
2. **Given** a student completes a lesson for the first time, **When** the system records the completion, **Then** XP rewards are calculated as Base XP + (Hearts * 10) and added to the student's profile
3. **Given** a student has zero hearts remaining, **When** they attempt to complete a lesson, **Then** the system rejects the completion and informs them they need more hearts
4. **Given** the primary storage is unavailable, **When** a student completes a lesson, **Then** the system falls back to secondary storage without data loss

---

### User Story 2 - View Progress with Unlock States (Priority: P1)

As a student, I want to see my complete progress through a subject including which lessons, topics, units, and tracks are passed, unlocked, or locked, so that I can understand what content is available to me and plan my learning path.

**Why this priority**: This is the core read operation that students use constantly to navigate the platform. The unlock logic (linear vs non-linear) is central to the gamified learning experience.

**Independent Test**: Can be tested by requesting progress for a subject and verifying accurate status for all nodes (lessons and containers). Delivers value by showing students their learning journey.

**Acceptance Scenarios**:

1. **Given** a student requests their progress for a subject, **When** the system processes the request, **Then** it returns the status (Passed/Unlocked/Locked) for every node (lessons, topics, units, tracks) in under 20 milliseconds
2. **Given** a subject has linear progression rules, **When** a student views progress, **Then** only the next sequential lesson after passed lessons is marked as Unlocked
3. **Given** a subject has non-linear progression rules, **When** a parent node is unlocked, **Then** all child lessons are immediately marked as Unlocked
4. **Given** a topic contains 5 lessons, **When** 4 lessons are passed, **Then** the topic shows as "In Progress" or "Unlocked", not "Passed"
5. **Given** a topic contains 5 lessons, **When** all 5 lessons are passed, **Then** the topic shows as "Passed"
6. **Given** the primary storage is unavailable, **When** a student requests progress, **Then** the system retrieves data from persistent storage seamlessly

---

### User Story 3 - Continue Learning with Next-Up Suggestion (Priority: P1)

As a student, I want to tap "Continue Learning" and be taken directly to my next lesson, so that I don't waste time navigating through the course structure.

**Why this priority**: This is a critical UX feature that dramatically reduces friction. Students expect one-tap access to resume their learning journey.

**Independent Test**: Can be tested by verifying the progress API returns a valid next lesson ID and the UI can navigate directly to it.

**Acceptance Scenarios**:

1. **Given** a student has partially completed a subject, **When** they request their progress, **Then** the response includes a `suggested_next_lesson_id` pointing to the first Unlocked (not Passed) lesson in tree order
2. **Given** a student has completed all lessons in a subject, **When** they request progress, **Then** `suggested_next_lesson_id` is null or indicates completion
3. **Given** a student is starting a new subject, **When** they request progress, **Then** `suggested_next_lesson_id` points to the first lesson

---

### User Story 4 - Replay Lesson for Review (Priority: P2)

As a student, I want to replay lessons I've already passed to review content and earn a small bonus, so that I can reinforce my learning without exploiting the XP system.

**Why this priority**: This creates a meaningful review mechanism that encourages mastery while maintaining game balance through a modest fixed reward.

**Independent Test**: Can be tested by replaying a passed lesson and verifying a fixed 10 XP reward is awarded regardless of performance.

**Acceptance Scenarios**:

1. **Given** a student completes a lesson for the first time with any hearts count > 0, **When** the system records completion, **Then** they receive the full reward: Base XP + (Remaining Hearts * 10) and the lesson bit is set to 1
2. **Given** a student replays a lesson they previously passed (bit already = 1), **When** they complete it successfully with any hearts count > 0, **Then** they receive a fixed review bonus of 10 XP only
3. **Given** a student replays a passed lesson, **When** they fail (Hearts = 0), **Then** no XP is awarded and the bit remains 1 (success is permanent)
4. **Given** a student replays a passed lesson, **When** they complete it successfully, **Then** the lesson remains marked as "Passed" (green) in the progress UI

---

### User Story 5 - Lesson Reordering Without Progress Loss (Priority: P2)

As an instructor, I want to reorder lessons within a subject without affecting students' existing progress, so that I can improve the course structure without resetting anyone's achievements.

**Why this priority**: Course content often needs restructuring based on feedback. Preserving student progress during these changes is essential for user trust and retention.

**Independent Test**: Can be tested by reordering lessons in a subject and verifying all student progress remains intact. Delivers value by allowing course improvements without negative impact on students.

**Acceptance Scenarios**:

1. **Given** lessons have been reordered in a subject, **When** a student views their progress, **Then** all previously passed lessons remain marked as passed
2. **Given** a lesson's display position changes, **When** the system checks completion status, **Then** it uses the immutable lesson identifier rather than the display order
3. **Given** lessons are reordered, **When** unlock logic is evaluated, **Then** the new visual order is respected for determining sequential unlocks

---

### User Story 6 - Lesson Deletion Handling (Priority: P2)

As an instructor, I want to delete outdated lessons without breaking the progress tracking system, so that I can keep course content current and relevant.

**Why this priority**: Content maintenance is a regular operational need. The system must gracefully handle deleted content without errors or data corruption.

**Independent Test**: Can be tested by deleting a lesson and verifying the system continues to function correctly for all progress operations.

**Acceptance Scenarios**:

1. **Given** a lesson is deleted from a subject, **When** a student views their progress, **Then** the deleted lesson does not appear in the progress response
2. **Given** a lesson was completed before being deleted, **When** XP totals are calculated, **Then** the earned XP remains in the student's profile
3. **Given** a deleted lesson was in the middle of a linear sequence, **When** progress is displayed, **Then** the unlock logic correctly handles the gap

---

### User Story 7 - New Lesson Addition (Priority: P2)

As an instructor, I want to add new lessons to an existing subject, so that I can expand course content without conflicts with existing progress data.

**Why this priority**: Courses grow and evolve. New lessons must integrate cleanly with the existing progress tracking system.

**Independent Test**: Can be tested by adding a new lesson to a subject with existing student progress and verifying no conflicts occur.

**Acceptance Scenarios**:

1. **Given** a new lesson is added to a subject, **When** the lesson is created, **Then** it receives a unique identifier that doesn't conflict with any existing or previously deleted lessons
2. **Given** a new lesson is added, **When** students view their progress, **Then** the new lesson appears with the correct initial state based on unlock rules
3. **Given** a new lesson is added and only appears in JSON when is_published = True, **When** the JSON structure is regenerated, **Then** students only see published lessons in their progress

---

### User Story 8 - System Recovery After Failure (Priority: P3)

As a system administrator, I want the progress data to be recoverable from persistent storage if the fast cache fails, so that students never lose their progress.

**Why this priority**: Data durability is essential but this scenario (cache failure) is rare. The system should degrade gracefully but this is not the primary path.

**Independent Test**: Can be tested by simulating cache unavailability and verifying progress data is correctly restored from persistent storage.

**Acceptance Scenarios**:

1. **Given** the fast cache becomes unavailable, **When** a student requests progress, **Then** the system loads data from persistent storage and serves the request
2. **Given** the cache was unavailable and is restored, **When** the system recovers, **Then** it rebuilds the cache from persistent snapshots on-demand as students access their progress
3. **Given** both cache and snapshot exist, **When** they have conflicting data, **Then** the most recent write takes precedence

---

### User Story 9 - Lazy Cache Warming After System Restart (Priority: P3)

As a system administrator, I want the system to start quickly without loading all student progress into memory, so that service restarts don't cause extended downtime or database overload.

**Why this priority**: This is an operational efficiency feature that improves system resilience and reduces startup time, but it's not a user-facing feature.

**Independent Test**: Can be tested by restarting Redis and verifying that progress data is loaded incrementally as students make requests, rather than all at once.

**Acceptance Scenarios**:

1. **Given** Redis cache is empty (after restart), **When** a student requests their progress for the first time, **Then** the system loads their bitmap from MariaDB, caches it in Redis with a TTL, and returns the progress within 100ms
2. **Given** a bitmap is already cached in Redis, **When** a student requests progress, **Then** the system retrieves it from Redis without touching MariaDB (cache hit)
3. **Given** a cached bitmap has expired (TTL elapsed), **When** a student requests progress, **Then** the system reloads it from MariaDB and resets the TTL
4. **Given** 100,000 students access the system simultaneously after a restart, **When** the system warms the cache, **Then** MariaDB query load is distributed over time rather than spiking at startup

---

### Edge Cases

- What happens when a student completes the same lesson multiple times? (First completion: Base XP + Hearts * 10; Subsequent completions: Fixed 10 XP; Bit remains 1)
- How does the system handle concurrent completion requests for the same lesson by the same student? (Idempotent operation using Redis SETBIT return value; duplicate requests get replay reward)
- What happens when a subject has zero lessons? (Return empty progress with 100% completion, null suggested_next_lesson_id)
- How does the system handle extremely large subjects (1000+ lessons)? (Must still respond within 20ms)
- What happens if persistent storage write fails after cache update? (Queue for retry, log the discrepancy)
- How does the system handle a student accessing a subject they're not enrolled in? (Return error indicating no access)
- What happens if all lessons are passed? (Container shows Passed, suggested_next_lesson_id is null)
- How are container states calculated when children have mixed states? (Container is Passed only if ALL children are Passed; otherwise Unlocked if accessible, Locked if not)
- What if the system crashes within the 30-second snapshot window? (Up to 30 seconds of completions may need to be re-done; acceptable tradeoff for performance)
- What happens when a lesson is moved from one subject to another? (Old bit_index is cleared, new bit_index assigned in target subject, student progress considered reset for that lesson)
- What happens when Redis restarts and cache is empty? (Lazy loading: bitmaps loaded from MariaDB on first request per student-subject, then cached with TTL)
- What happens when a student replays a passed lesson but loses (Hearts = 0)? (No XP awarded, bit stays 1, attempt logged, student can retry)
- How does the JSON generator handle unpublished or deleted lessons? (Excluded from JSON structure file even if they have bit_index values; progress engine ignores missing lessons)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST record lesson completion state as a binary pass/fail value
- **FR-002**: System MUST assign each lesson a unique, immutable identifier within its subject upon creation
- **FR-003**: System MUST increment the subject's identifier counter when assigning new lesson identifiers
- **FR-004**: System MUST verify the student has remaining hearts (> 0) before accepting lesson completion
- **FR-005**: System MUST calculate first-completion XP rewards using the formula: XP = Base + (Hearts * 10), where Hearts ranges from 0 to 5 (maximum)
- **FR-006**: System MUST persist completion state to fast storage immediately upon lesson completion
- **FR-007**: System MUST asynchronously update persistent storage snapshots in batches every 30 seconds, aggregating all pending completion events
- **FR-008**: System MUST compute progress status (Passed/Unlocked/Locked) for ALL nodes in the hierarchy (Lessons, Topics, Units, Tracks) in memory based on the lesson bitmap
- **FR-009**: System MUST apply linear unlock rules: next lesson unlocks only when previous lesson is passed
- **FR-010**: System MUST apply non-linear unlock rules: all children unlock when parent node becomes unlocked
- **FR-011**: System MUST support mixed linear and non-linear rules within the same subject hierarchy
- **FR-012**: System MUST preserve lesson completion status when lessons are reordered
- **FR-013**: System MUST exclude deleted lessons from progress responses without errors
- **FR-014**: System MUST prevent identifier reuse when new lessons are added
- **FR-015**: System MUST restore progress data from persistent storage when fast storage is unavailable
- **FR-016**: System MUST log all lesson completion events for audit purposes
- **FR-017**: System MUST calculate and return completion percentage for each subject
- **FR-018**: System MUST add earned XP to the student's profile wallet asynchronously
- **FR-019**: System MUST determine and return `suggested_next_lesson_id` in every progress response - the first lesson in tree order that is Unlocked but not Passed
- **FR-020**: System MUST mark a container (Topic/Unit/Track) as Passed ONLY when ALL of its descendant lessons have Passed status (all corresponding bits = 1)
- **FR-021**: System MUST use Redis SETBIT command to atomically set a lesson bit to 1 and retrieve the previous value (0 or 1) in a single operation
- **FR-022**: System MUST award full XP (Base_XP + Remaining_Hearts * 10) when SETBIT returns previous value = 0 (first-time completion)
- **FR-023**: System MUST award fixed 10 XP when SETBIT returns previous value = 1 (replay completion)
- **FR-024**: System MUST NOT modify the Redis bitmap when a student fails a lesson (Hearts = 0), regardless of whether the lesson was previously passed
- **FR-025**: System MUST implement lazy cache warming by loading bitmaps from MariaDB into Redis only when requested (cache miss scenario)
- **FR-026**: System MUST set a TTL (Time To Live) on Redis bitmap keys to prevent indefinite memory growth
- **FR-027**: System MUST exclude lessons with is_published = False from the generated JSON structure file
- **FR-028**: System MUST exclude lessons with is_deleted = True (trashed) from the generated JSON structure file
- **FR-029**: System MUST ensure each lesson's bit_index is scoped to its parent Subject ID and never shared across subjects
- **FR-030**: System MUST clear a lesson's old bit_index and assign a new one if the lesson is moved to a different subject (progress reset for that lesson)
- **FR-031**: System MUST treat success state (bit = 1) as permanent and irreversible through normal gameplay operations
- **FR-032**: System MUST log all replay attempts, including failures, to the Interaction Log for analytics

### Key Entities

- **Memora Subject**: A course/subject containing lessons organized in a hierarchical structure. Maintains a counter for assigning unique lesson identifiers. Has a progression mode (linear/non-linear) that can vary by level.

- **Memora Lesson**: An individual learning unit within a subject. Has an immutable identifier for progress tracking, a display order for presentation, and belongs to a topic within the subject hierarchy.

- **Memora Structure Progress**: The progress record linking a student to a subject. Stores the completion bitmap snapshot, total XP earned, completion percentage, and per-lesson best hearts scores. One record per student-subject-academic plan combination.

- **Memora Player Profile**: The student's profile containing their hearts (lives), XP wallet, and overall statistics.

- **Academic Plan**: The enrollment structure connecting students to subjects, defining what content they can access.

- **Interaction Log**: Audit trail of all student actions including lesson completions, XP awards, and significant events.

- **Container Nodes (Topic/Unit/Track)**: Hierarchical grouping nodes that contain lessons or other containers. Their status is computed dynamically based on their descendant lessons' completion states.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Progress retrieval responds within 20 milliseconds for subjects with up to 1000 lessons
- **SC-002**: System supports 100,000 concurrent users without performance degradation
- **SC-003**: System handles 1000 progress update operations per second without backlog
- **SC-004**: Memory usage for storing one student's progress in a 1000-lesson subject is under 150 bytes (bitmap only; best-hearts storage is separate)
- **SC-005**: Student progress is never lost, even during system failures (99.99% data durability)
- **SC-006**: Lesson reordering operations do not affect any student's completion status
- **SC-007**: XP awards are correctly calculated and applied within 5 seconds of lesson completion
- **SC-008**: Progress retrieval from backup storage completes within 100 milliseconds when primary storage is unavailable
- **SC-009**: Container (Topic/Unit/Track) statuses are accurately computed in every progress response
- **SC-010**: `suggested_next_lesson_id` correctly identifies the next lesson 100% of the time
- **SC-011**: First-time lesson completions always award full XP (Base + Hearts * 10); replay completions always award fixed 10 XP
- **SC-012**: Students never lose progress on passed lessons, even after failed replay attempts
- **SC-013**: Cache warming after Redis restart completes within 50 milliseconds per student-subject on first request
- **SC-014**: Unpublished and deleted lessons never appear in student progress views, regardless of bitmap state

## Clarifications

### Session 2026-01-25

- Q: Where is the `is_linear` unlock rule stored/retrieved from? → A: `is_linear` is stored in the pre-generated JSON structure file per container node
- Q: What is the maximum hearts value at lesson completion? → A: Maximum 5 hearts (balanced, standard gamification)
- Q: What is the snapshot sync frequency to persistent storage? → A: Batched every 30 seconds (aggregate pending updates)

### Session 2026-01-26

- Q: How are first-time vs replay completions distinguished? → A: Redis SETBIT returns the previous bit value (0 = first time, 1 = replay)
- Q: What is the replay reward amount? → A: Fixed 10 XP for any successful replay, regardless of hearts remaining
- Q: What happens to the bitmap when a student fails a replay? → A: Bitmap is not modified; bit stays 1 (success is permanent)
- Q: When are bitmaps loaded into Redis? → A: Lazy loading on first request per student-subject (cache miss) from MariaDB, with TTL set
- Q: How are unpublished/deleted lessons handled? → A: Excluded from JSON structure generation; invisible to progress engine and students

## Assumptions

- Students are authenticated and their identity is known before any progress operations
- The subject structure (hierarchy, lessons, unlock rules including `is_linear` per container node) is pre-generated and available as a structured JSON file
- Hearts/lives system already exists and can be queried for remaining count
- XP wallet/profile system exists and can accept XP additions
- Interaction logging system exists and can receive completion events
- Background job processing infrastructure exists for async operations
- Subjects have a reasonable upper bound of lessons (designed for up to 1000, but no hard limit enforced)
- Base XP value is configured per lesson or subject (not specified in this feature)
- Redis SETBIT operation is atomic and returns the previous bit value reliably
- TTL values for Redis keys are configured appropriately (recommendation: 7-30 days based on user activity patterns)
- JSON structure regeneration happens automatically when lessons are added, deleted, or have status changes (is_published, is_deleted)
- Moving lessons between subjects is a rare administrative operation and requires manual intervention or explicit system support
- MariaDB serves as the source of truth for all bitmap data; Redis is a performance cache layer
