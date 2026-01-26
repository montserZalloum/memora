# Feature Specification: Progress Tracking and Smart Unlocking Engine (Bitset Edition)

**Feature Branch**: `005-progress-engine-bitset`
**Created**: 2026-01-25
**Status**: Draft
**Input**: User description: "PRD for Memora Structure Progress Engine - a high-performance progress tracking engine using Redis Bitmaps for lesson completion state and unlock logic supporting 100K concurrent users"

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

### User Story 4 - Replay Lesson for Record-Breaking Bonus (Priority: P2)

As a student, I want to replay a lesson I've already passed to improve my score, and earn bonus XP if I perform better than my previous best, so that I'm motivated to master content without exploiting the XP system.

**Why this priority**: This creates a meaningful "mastery loop" that encourages skill improvement rather than simple completion grinding.

**Independent Test**: Can be tested by replaying a passed lesson with more hearts and verifying only the differential bonus XP is awarded.

**Acceptance Scenarios**:

1. **Given** a student replays a lesson they previously passed with 2 hearts, **When** they complete it again with 2 or fewer hearts, **Then** no additional XP is awarded
2. **Given** a student replays a lesson they previously passed with 2 hearts, **When** they complete it with 4 hearts, **Then** they receive bonus XP of (4-2) * 10 = 20 XP
3. **Given** a student replays a lesson, **When** they achieve a new record, **Then** their new hearts score is stored for future comparisons
4. **Given** a student replays a lesson, **When** they complete it, **Then** the Base XP is never awarded again (only first completion)

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

---

### User Story 8 - System Recovery After Failure (Priority: P3)

As a system administrator, I want the progress data to be recoverable from persistent storage if the fast cache fails, so that students never lose their progress.

**Why this priority**: Data durability is essential but this scenario (cache failure) is rare. The system should degrade gracefully but this is not the primary path.

**Independent Test**: Can be tested by simulating cache unavailability and verifying progress data is correctly restored from persistent storage.

**Acceptance Scenarios**:

1. **Given** the fast cache becomes unavailable, **When** a student requests progress, **Then** the system loads data from persistent storage and serves the request
2. **Given** the cache was unavailable and is restored, **When** the system recovers, **Then** it rebuilds the cache from persistent snapshots
3. **Given** both cache and snapshot exist, **When** they have conflicting data, **Then** the most recent write takes precedence

---

### Edge Cases

- What happens when a student completes the same lesson multiple times? (XP: Base awarded only once; Hearts bonus only if new record achieved)
- How does the system handle concurrent completion requests for the same lesson by the same student? (Idempotent operation - second request is a no-op for completion state, but may award bonus XP if higher hearts)
- What happens when a subject has zero lessons? (Return empty progress with 100% completion, null suggested_next_lesson_id)
- How does the system handle extremely large subjects (1000+ lessons)? (Must still respond within 20ms)
- What happens if persistent storage write fails after cache update? (Queue for retry, log the discrepancy)
- How does the system handle a student accessing a subject they're not enrolled in? (Return error indicating no access)
- What happens if all lessons are passed? (Container shows Passed, suggested_next_lesson_id is null)
- How are container states calculated when children have mixed states? (Container is Passed only if ALL children are Passed; otherwise Unlocked if accessible, Locked if not)
- What if the system crashes within the 30-second snapshot window? (Up to 30 seconds of completions may need to be re-done; acceptable tradeoff for performance)

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
- **FR-021**: System MUST store the highest hearts score achieved per lesson for each student to enable record-breaking bonus calculations
- **FR-022**: System MUST award bonus XP = (new_hearts - previous_best_hearts) * 10 when a student replays a passed lesson and achieves a higher hearts score

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

## Clarifications

### Session 2026-01-25

- Q: Where is the `is_linear` unlock rule stored/retrieved from? → A: `is_linear` is stored in the pre-generated JSON structure file per container node
- Q: What is the maximum hearts value at lesson completion? → A: Maximum 5 hearts (balanced, standard gamification)
- Q: What is the snapshot sync frequency to persistent storage? → A: Batched every 30 seconds (aggregate pending updates)

## Assumptions

- Students are authenticated and their identity is known before any progress operations
- The subject structure (hierarchy, lessons, unlock rules including `is_linear` per container node) is pre-generated and available as a structured JSON file
- Hearts/lives system already exists and can be queried for remaining count
- XP wallet/profile system exists and can accept XP additions
- Interaction logging system exists and can receive completion events
- Background job processing infrastructure exists for async operations
- Subjects have a reasonable upper bound of lessons (designed for up to 1000, but no hard limit enforced)
- Base XP value is configured per lesson or subject (not specified in this feature)
