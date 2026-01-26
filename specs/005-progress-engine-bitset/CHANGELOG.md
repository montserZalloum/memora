# Changelog: Progress Engine (Bitset Edition)

## v1.1 (2026-01-26)

### Major Enhancements

#### 1. Lazy Cache Warming Strategy
- **Problem**: Loading all student bitmaps at server startup caused database overload and slow restarts
- **Solution**: Implemented on-demand loading with TTL-based cache expiration
- **Requirements**: FR-023, FR-025, FR-026
- **User Story**: US9
- **Success Criteria**: SC-013

#### 2. JSON Integrity Filter
- **Problem**: Unpublished or deleted lessons appeared in progress views if they had bit_index values
- **Solution**: JSON generator automatically excludes is_published=False and is_deleted=True lessons
- **Requirements**: FR-027, FR-028
- **Success Criteria**: SC-014

#### 3. Bit Index Protection
- **Problem**: Bit index conflicts when lessons moved between subjects
- **Solution**: Bit index scoped to Subject ID; moving lessons resets progress
- **Requirements**: FR-029, FR-030

#### 4. Persistence of Success
- **Problem**: Student progress could be lost if replay attempts failed
- **Solution**: Once bit=1, it never resets to 0 through gameplay
- **Requirements**: FR-031
- **Success Criteria**: SC-012

#### 5. Two-Tier Reward Policy
- **Problem**: Previous "record-breaking" system was complex and allowed XP exploitation
- **Solution**: Redis SETBIT return value distinguishes first-time vs replay
  - First completion: Base_XP + (Hearts * 10)
  - Replay: Fixed 10 XP
- **Requirements**: FR-021, FR-022, FR-023, FR-024, FR-032
- **User Story**: US4 (updated)
- **Success Criteria**: SC-011

### Documentation Updates

- Added 10 new functional requirements (FR-023 through FR-032)
- Updated User Story 4 to reflect two-tier reward policy
- Added User Story 9 for lazy cache warming
- Expanded edge cases to cover new scenarios
- Added 4 new success criteria (SC-011 through SC-014)
- Added clarification session 2026-01-26
- Updated assumptions to include Redis SETBIT behavior and TTL configuration

### Removed Features

- **Record-breaking XP bonus system**: Replaced with simpler fixed replay reward
- **Hearts score tracking per lesson**: No longer needed with fixed replay rewards
- Old FR-021, FR-022 replaced with new reward policy requirements

## v1.0 (2026-01-25)

Initial specification with core features:
- Redis bitmap-based progress tracking
- Linear and non-linear unlock logic
- Container state computation
- Next-lesson suggestion
- XP reward system
- Lesson reordering support
- System recovery mechanisms
