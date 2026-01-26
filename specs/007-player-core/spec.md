# Feature Specification: Player Core - Identity, Security & Rewards

**Feature Branch**: `007-player-core`
**Created**: 2026-01-26
**Status**: Draft
**Input**: User description: "وثيقة متطلبات المنتج (PRD): نواة اللاعب، الأمان، والمكافآت - Establishing secure student digital identity preventing account sharing and multi-session access, with high-performance rewards engine (XP & Streak) using caching and batching to minimize database pressure."

## Clarifications

### Session 2026-01-26

- Q: When a new student account is created, how should their first device be authorized? → A: First device auto-authorized on account creation; subsequent devices require admin approval
- Q: What is the maximum number of devices that can be authorized for a single student? → A: 2 devices
- Q: How long should an active session remain valid before requiring re-authentication? → A: Persistent unless session conflict
- Q: What should the streak value be for a new student who has not yet completed their first lesson? → A: Streak starts at 0; becomes 1 after first successful lesson completion
- Q: When a student views their wallet and there's a discrepancy between cached data (newer) and database data (older due to pending sync), which should be displayed? → A: Always display cache data (most recent, may be ahead of database by up to 15 minutes)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure Single-Device Authentication (Priority: P1)

A student logs into the Memora platform from their registered device and gets immediate access to their learning content. If they attempt to log in from an unauthorized device, the system blocks access and prompts them to contact administration for device authorization.

**Why this priority**: Core security requirement that prevents account sharing and unauthorized access. Without this, all other features cannot function securely.

**Independent Test**: Can be fully tested by attempting login from both authorized and unauthorized devices, and delivers the foundational security layer for the entire platform.

**Acceptance Scenarios**:

1. **Given** a new student account is being created, **When** they complete registration and first login on their device, **Then** that device is automatically authorized and they gain immediate access to the platform
2. **Given** a student has a registered authorized device, **When** they log in using valid credentials from that device, **Then** they gain immediate access to the platform
3. **Given** a student attempts login from an unregistered device (not their first device), **When** they submit valid credentials, **Then** access is denied with a message directing them to contact administration for device authorization
4. **Given** a student has multiple authorized devices, **When** they log in from any of these devices, **Then** access is granted without issues
5. **Given** an administrator authorizes a new device for a student, **When** the device information is added, **Then** the student can log in from that device successfully

---

### User Story 2 - Single Active Session Enforcement (Priority: P1)

A student logs into the platform on their tablet and begins studying. Later, they log in from their phone (both are authorized devices). The system automatically logs them out from the tablet and maintains only the phone session. When they return to the tablet, they must log in again.

**Why this priority**: Critical for preventing account sharing between students. Even with authorized devices, simultaneous sessions enable sharing, undermining the learning integrity and analytics.

**Independent Test**: Can be fully tested by logging in from two different authorized devices sequentially and verifying that only the most recent session remains active.

**Acceptance Scenarios**:

1. **Given** a student is logged in on Device A, **When** they log in from Device B (both authorized), **Then** Device A session is terminated and only Device B session remains active
2. **Given** a student's session was terminated due to login from another device, **When** they attempt any action on the terminated device, **Then** they are prompted to log in again
3. **Given** a student is actively using the platform on one device, **When** another login occurs from a different device, **Then** the transition happens within 2 seconds
4. **Given** a student has been logged out due to session replacement, **When** they log back in on the original device, **Then** their learning progress is preserved from their last successful save

---

### User Story 3 - Daily Learning Streak Tracking (Priority: P2)

A new student starts with a streak of 0. When they complete their first lesson successfully (earning at least one heart), their streak becomes 1. On subsequent days, the streak increments if they studied yesterday, or resets to 1 if they missed a day. The streak motivates consistent daily engagement with learning content.

**Why this priority**: Key engagement feature that drives retention and consistent learning habits. Depends on successful authentication (P1) but delivers significant user value independently.

**Independent Test**: Can be fully tested by completing lessons on consecutive days and non-consecutive days, verifying streak logic operates correctly.

**Acceptance Scenarios**:

1. **Given** a new student with streak = 0 and no completed lessons, **When** they successfully complete their first lesson with hearts > 0, **Then** their streak becomes 1
2. **Given** a student completed a lesson yesterday with hearts > 0, **When** they successfully complete a lesson today, **Then** their streak increments by 1
3. **Given** a student has not completed any lesson for more than one day, **When** they successfully complete a lesson today, **Then** their streak resets to 1
4. **Given** a student completes multiple lessons in the same day, **When** each lesson is completed, **Then** the streak increments only once per day
5. **Given** a student successfully completes a lesson, **When** the completion is recorded, **Then** the last_success_date is updated to today's server time

---

### User Story 4 - Experience Points Accumulation (Priority: P2)

A student earns experience points (XP) for various learning activities. Their total XP accumulates over time and is visible in their wallet, providing a sense of progression and achievement throughout their learning journey.

**Why this priority**: Core engagement mechanic that rewards learning effort. Independent of security features but depends on authenticated sessions to attribute XP correctly.

**Independent Test**: Can be fully tested by performing XP-earning activities and verifying the wallet total updates correctly.

**Acceptance Scenarios**:

1. **Given** a student completes an activity that awards XP, **When** the activity is successfully completed, **Then** their total XP increases by the awarded amount
2. **Given** a student has earned XP from multiple activities, **When** they view their wallet, **Then** the total XP reflects the cumulative sum of all earned points
3. **Given** a student's XP update is pending synchronization, **When** they check their wallet, **Then** they see their current XP total including pending updates
4. **Given** a student performs multiple XP-earning activities rapidly, **When** all activities complete, **Then** the final XP total is accurate without data loss

---

### User Story 5 - Activity Timestamp Tracking (Priority: P3)

The system tracks when students last interacted with the platform to provide insights into engagement patterns. This timestamp updates with each meaningful interaction but avoids excessive database writes through intelligent throttling.

**Why this priority**: Analytics and engagement monitoring feature. Provides value for administrators and product teams but is not user-facing or critical to core functionality.

**Independent Test**: Can be fully tested by performing platform interactions and verifying timestamp updates occur appropriately without excessive database load.

**Acceptance Scenarios**:

1. **Given** a student performs any platform interaction, **When** the interaction occurs, **Then** the system records the activity timestamp internally
2. **Given** a student has multiple interactions within a short time window, **When** these interactions occur, **Then** database writes are minimized through throttling
3. **Given** sufficient time has passed since the last database write, **When** the next interaction occurs, **Then** the timestamp is persisted to long-term storage
4. **Given** an administrator views student engagement data, **When** they access the last_played_at field, **Then** it reflects recent activity within acceptable precision (15-minute granularity)

---

### Edge Cases

- What happens when a student's device is lost or stolen and needs to be removed from authorized devices? (Admin-only capability ensures security)
- What happens when a student attempts to authorize a third device when already at the 2-device limit? (System rejects the request; admin must first remove an existing device before adding a new one)
- How does the system handle clock manipulation attempts on client devices? (Server-time authority prevents gaming the streak system)
- What happens when the caching layer (Redis) becomes unavailable? (System falls back to persistent storage with AOF recovery ensuring data integrity)
- How does the system prevent streak increment more than once per day? (Date comparison using server time ensures single daily increment)
- What happens when a student logs in exactly at midnight? (Server timezone determines day boundaries consistently)
- What is the streak value displayed to a brand new student before completing any lessons? (Streak displays as 0 until first successful lesson completion)
- How are pending wallet updates handled during system maintenance? (Batch sync job processes pending updates upon service restoration)
- What happens when two login attempts occur simultaneously from different devices? (Latest session wins with consistent Redis-based session management)
- How does the system handle network interruptions during XP updates? (Updates are queued in Redis and batch-synced to ensure no data loss)
- What happens if a student's device is compromised and they remain logged in indefinitely? (Persistent sessions combined with device authorization provide security; admin can deauthorize the device to force logout)
- How are sessions invalidated when an admin removes an authorized device? (Session invalidation occurs immediately; next API request from that device is rejected)
- What happens when a student views their wallet while updates are pending sync to database? (Cache data is always displayed as authoritative; student sees most recent progress even if database is up to 15 minutes behind)
- What happens if cache and database show different XP/streak values? (Cache value is always used for display; database discrepancy will be resolved at next batch sync)

## Requirements *(mandatory)*

### Functional Requirements

**Identity & Profile Management**

- **FR-001**: System MUST maintain a unique player profile for each student with 1:1 relationship to system user account
- **FR-002**: Player profile MUST store student's current grade, stream, season, and active academic plan
- **FR-003**: System MUST support profile photo attachment for student identification
- **FR-004**: Player profile MUST persist across sessions and device changes

**Device Authorization**

- **FR-005**: System MUST maintain a list of authorized devices for each student with unique device identifiers
- **FR-005a**: System MUST automatically authorize the first device used during account creation without requiring admin approval
- **FR-005b**: System MUST enforce a maximum limit of 2 authorized devices per student
- **FR-006**: Each authorized device record MUST capture device ID (UUID), device name, and authorization timestamp
- **FR-007**: System MUST reject login attempts from devices not in the authorized list (excluding first device during account creation)
- **FR-008**: System MUST provide clear feedback when login is denied due to unauthorized device
- **FR-009**: Only administrators MUST be able to add or remove authorized devices from student profiles (after initial device is established)
- **FR-009a**: System MUST prevent administrators from adding a third device unless an existing device is first removed
- **FR-010**: Device authorization checks MUST complete within 2 milliseconds using cached device lists

**Session Management**

- **FR-011**: System MUST enforce single active session per student at any given time
- **FR-011a**: Sessions MUST remain valid indefinitely (persistent) until explicitly invalidated by session conflict, logout, or device deauthorization
- **FR-011b**: System MUST NOT implement time-based session expiration or inactivity timeouts
- **FR-012**: When a student logs in from a new device, system MUST invalidate previous active session
- **FR-013**: Invalidated sessions MUST terminate within the next API request (immediate kick-out)
- **FR-014**: Session validation MUST occur on every authenticated API request
- **FR-015**: Session tokens MUST be stored in fast-access cache with user identifier mapping
- **FR-016**: Session state verification MUST complete within 2 milliseconds per request

**Wallet & Points System**

- **FR-017**: System MUST maintain a wallet for each player tracking total experience points (XP)
- **FR-018**: Wallet MUST initialize with zero XP for new players
- **FR-019**: XP updates MUST be reflected immediately in the student's view
- **FR-019a**: System MUST always display wallet data from cache as the authoritative source for current state
- **FR-019b**: System MUST NOT display database wallet values when cache data is available, even if database is more recently synchronized
- **FR-020**: XP calculations MUST be accurate with no data loss during rapid activity
- **FR-021**: System MUST support concurrent XP updates for multiple students without conflicts

**Streak Tracking**

- **FR-022**: System MUST track current streak count for each student (consecutive days with successful lesson completion)
- **FR-022a**: Streak MUST initialize at 0 for new students who have not completed any lessons
- **FR-022b**: Streak MUST change from 0 to 1 upon first successful lesson completion with hearts > 0
- **FR-022c**: System MUST display streak data from cache as the authoritative current value
- **FR-023**: Streak MUST increment by 1 when student completes lesson with hearts > 0 on consecutive days
- **FR-024**: Streak MUST reset to 1 when student completes lesson after missing one or more days
- **FR-025**: Streak MUST NOT increment more than once per calendar day regardless of lesson count
- **FR-026**: System MUST record last successful lesson completion date for streak calculation
- **FR-027**: All streak calculations MUST use server time to prevent client-side manipulation
- **FR-028**: Streak determination logic MUST be: same day = no change, next day = increment, gap > 1 day = reset to 1

**Activity Tracking**

- **FR-029**: System MUST record timestamp of last student interaction (last_played_at)
- **FR-030**: Activity timestamps MUST update with each authenticated API request
- **FR-031**: Database writes for activity timestamps MUST be throttled to occur no more frequently than every 15 minutes per student
- **FR-032**: Activity timestamp cache MUST update immediately even when database write is throttled

**Performance & Data Synchronization**

- **FR-033**: XP and streak updates MUST be written to fast cache immediately upon activity completion
- **FR-034**: System MUST maintain a queue of player IDs with pending wallet synchronization
- **FR-035**: Background synchronization job MUST run every 15 minutes to sync cached wallet data to persistent storage
- **FR-036**: Batch updates to persistent storage MUST process in chunks of 500 players maximum
- **FR-037**: System MUST reduce wallet database write operations by at least 90% through batching strategy

**Data Resilience**

- **FR-038**: Cache layer MUST enable append-only file (AOF) persistence for data recovery
- **FR-039**: In case of complete cache failure, persistent storage MUST serve as source of truth (accepting up to 15-minute data lag)
- **FR-040**: System MUST recover gracefully from cache failures without data corruption
- **FR-041**: All time-sensitive calculations MUST use authoritative server time

### Key Entities

- **Player Profile**: Represents a student's identity within the platform, linking to their system user account. Contains educational context (grade, stream, season, academic plan) and authorized devices for security enforcement. Serves as the central identity hub for all player-related features.

- **Authorized Device**: Represents a specific device permitted to access a student's account. Identified by unique UUID with human-readable name and authorization timestamp. Relationship: Multiple authorized devices can belong to one player profile (1:many).

- **Player Wallet**: Represents a student's achievement metrics and engagement status. Tracks cumulative experience points (initializes at 0), current learning streak (initializes at 0, becomes 1 after first successful lesson), last success date for streak calculation, and last activity timestamp. Relationship: One wallet per player profile (1:1).

- **Wallet Synchronization Queue**: Represents pending updates awaiting batch synchronization from cache to persistent storage. Contains player identifiers whose wallet data has changed in cache but not yet written to database. Enables performance optimization through batching.

## Success Criteria *(mandatory)*

### Measurable Outcomes

**Security & Access Control**

- **SC-001**: Device and session verification completes in under 2 milliseconds for 100% of authenticated requests
- **SC-002**: Account sharing is prevented with 100% effectiveness through device authorization and single-session enforcement
- **SC-003**: Unauthorized device login attempts are blocked with 0% false positives (authorized devices never incorrectly denied)
- **SC-004**: Session termination upon secondary login occurs within 2 seconds for 95% of cases

**Engagement & Rewards**

- **SC-005**: Streak calculations are 100% accurate with no duplicate increments within the same calendar day
- **SC-006**: XP updates are reflected in student view within 1 second of activity completion
- **SC-007**: Zero XP data loss occurs during concurrent rapid activities across all students
- **SC-008**: Student engagement visibility (last activity timestamp) is accurate within 15-minute precision

**Performance & Scalability**

- **SC-009**: Database write operations for wallet updates are reduced by over 90% compared to real-time writes
- **SC-010**: System supports 10,000 concurrent active students without performance degradation
- **SC-011**: Batch synchronization jobs complete within 5 minutes for up to 50,000 pending player updates
- **SC-012**: Cache recovery time after failure is under 2 minutes with no permanent data loss

**Reliability & Data Integrity**

- **SC-013**: System maintains 99.9% uptime for authentication and session management
- **SC-014**: Data consistency between cache and persistent storage is maintained with maximum 15-minute lag under normal operation
- **SC-015**: Recovery from cache failures occurs automatically with zero manual intervention required
- **SC-016**: Time manipulation attempts on client devices have 0% success rate in gaming streaks or timestamps

## Assumptions

- Students use a maximum of 2 devices (e.g., mobile and tablet/computer) for platform access
- First device is automatically authorized during account creation to enable immediate platform access
- Device authorization for the second device is an infrequent operation handled through administrative support channels
- Two-device limit is sufficient for legitimate student use while preventing widespread account sharing
- Persistent sessions (no time-based expiration) provide optimal user experience while device authorization layer ensures security
- Students maintain physical control of their authorized devices, minimizing risk of unauthorized access via persistent sessions
- Students value streak tracking as a motivational tool for consistent daily engagement
- XP-earning activities occur frequently enough that batching provides significant performance benefit
- 15-minute granularity for last activity timestamp is acceptable for engagement analytics
- Cache is the authoritative source for current wallet state (XP, streak); database serves as durable backup
- Students expect to see immediate progress updates; cache-first display strategy ensures real-time feedback
- Server infrastructure includes Redis or compatible caching layer with AOF persistence capability
- Database supports efficient bulk update operations for batch synchronization
- Session tokens are managed securely through existing authentication infrastructure
- Network connectivity is generally reliable with occasional brief interruptions
- Student time zones may vary but server time provides consistent reference for streak calculations

## Dependencies

- Existing user authentication system providing user accounts and login mechanism
- Grade, Stream, Season, and Academic Plan entities must exist in the platform
- Lesson completion system that can trigger XP and streak updates
- Device identification capability (UUID generation and transmission from client applications)
- Background job scheduler for periodic batch synchronization tasks
- Administrative interface for device authorization management
- Caching infrastructure (Redis or equivalent) with AOF persistence enabled

## Out of Scope

- Social features between students (leaderboards, friend connections, sharing)
- Detailed XP award calculation logic (how much XP per activity type)
- Redemption or spending of accumulated XP
- Advanced streak recovery mechanisms (freeze days, streak insurance)
- Multi-platform device fingerprinting beyond basic UUID
- Automated suspicious activity detection and account flagging
- Parent/guardian access to student progress and wallet
- Historical analytics and trend reporting for administrators
- Migration of existing student data to new wallet system
- Gamification features beyond basic XP and streaks (badges, achievements, levels)
