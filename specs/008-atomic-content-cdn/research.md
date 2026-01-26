# Research: Atomic JSON Content Generation & CDN Distribution

**Feature**: 008-atomic-content-cdn
**Date**: 2026-01-26
**Status**: Complete

## Executive Summary

The existing CDN export system (Feature 002) generates monolithic JSON files where each subject contains the complete hierarchy (tracks → units → topics → lessons → stages). Feature 008 requires refactoring to an atomic file structure for:
1. Sub-second loading (smaller files)
2. Shared lesson content across plans (deduplication)
3. Granular cache invalidation

This research documents the current implementation gaps and design decisions.

---

## Research Task 1: Current File Structure Analysis

### Current Implementation (Feature 002)

**File Structure:**
```
/sites/{site}/public/memora_content/
├── plans/
│   └── {plan_id}/
│       └── manifest.json       # Plan index
└── subjects/
    └── {subject_id}.json       # MONOLITHIC: Contains entire hierarchy
```

**Problems with Current Structure:**
1. `subjects/{subject_id}.json` contains ALL tracks, units, topics, lessons, and stages
2. File size grows linearly with content depth (~50KB+ for subjects with 100+ lessons)
3. Any lesson change requires regenerating the entire subject file
4. Lesson content is duplicated across plans (same lesson in different plans = multiple copies)
5. Cannot cache individual topics or lessons independently

### Required Structure (Feature 008)

**Target File Structure:**
```
/sites/{site}/public/memora_content/
├── plans/
│   └── {plan_id}/
│       ├── manifest.json           # Plan index (subjects list)
│       ├── {subject_id}_h.json     # Subject hierarchy (no lessons)
│       ├── {subject_id}_b.json     # Subject bitmap (progress engine)
│       └── {topic_id}.json         # Topic with lesson list
└── lessons/
    └── {lesson_id}.json            # Shared lesson content
```

**Decision**: Adopt the required structure. This enables:
- Independent caching of each content level
- Shared lesson files across all plans (deduplication)
- Faster regeneration (only affected files need updating)

---

## Research Task 2: Access Level Inheritance Algorithm

### Current Implementation

Location: `memora/services/cdn_export/access_calculator.py`

```python
def calculate_access_level(node, parent_access=None, plan_overrides=None):
    # Override check (Hide, Set Free, Set Sold Separately)
    # is_free_preview flag check
    # required_item check (→ paid)
    # is_public flag check
    # Parent inheritance
    # Default: authenticated
```

**Missing Override Actions (from spec FR-013, FR-014):**
- "Set Access Level" - Change access_level field directly
- "Set Linear" - Change is_linear field

### Current Override Actions in DocType

From `memora_plan_override.json`:
```json
"options": "Hide\nRename\nSet Free\nSet Sold Separately"
```

**Decision**: Add two new override actions:
1. `Set Access Level` - Uses `override_value` field for target level
2. `Set Linear` - Uses `override_value` field for boolean (0/1)

**Rationale**: Spec FR-013 requires ability to set access_level directly, FR-014 requires is_linear override.

---

## Research Task 3: Atomic Consistency Strategy

### Current Implementation

Location: `memora/services/cdn_export/batch_processor.py` → `_rebuild_plan()`

The current flow:
1. Generate all files for plan
2. Write to local storage
3. If CDN enabled, upload all files
4. Purge CDN cache

**Gap**: No atomic consistency guarantee between files. If generation fails mid-way, partial files may exist locally.

### Required Behavior (from spec FR-018)

"System MUST implement atomic consistency - no subject files uploaded until all related topic and lesson files are ready"

**Design Decision**: Two-phase commit approach:

1. **Phase 1: Generate All** - Write to staging directory with `.tmp` suffix
2. **Phase 2: Atomic Swap** - Rename all files atomically (or rollback on failure)

For CDN uploads:
1. Generate and validate all files locally
2. Upload all files to CDN with new version prefix
3. Update manifest last (manifest points to new version)
4. On failure: don't update manifest, old files remain valid

**Alternatives Considered:**
- Database transaction + file writes: Complex, Frappe ORM doesn't span file ops
- Redis atomic script: Overkill for file generation
- Simple overwrite: Rejected - violates atomic consistency requirement

---

## Research Task 4: Lesson Sharing Across Plans

### Current Behavior

Lessons are embedded in subject JSON, regenerated per-plan. If "Math Lesson 1" exists in Plan A and Plan B, it's duplicated in both plan's subject files.

### Required Behavior (spec FR-006)

"System MUST generate `{lesson_id}.json` for each lesson containing stages array"

Lessons should be shared:
- Location: `/lessons/{lesson_id}.json`
- Plan-agnostic (no plan_id in path)
- Access control: Applied at topic level, lesson content is public (gated by topic access)

**Design Decision**:
- Lesson files contain only content (stages, metadata)
- Access level is NOT in lesson file (inherited from topic)
- Topic files include `lesson_url` pointing to shared lesson

**Change Impact**:
- `generate_lesson_json()` must NOT include access block
- Topic JSON includes lesson list with access info
- Lesson change → only regenerate lesson file, not subject hierarchy

---

## Research Task 5: Bitmap File Structure

### Current Implementation

The progress engine (Feature 005) uses `bit_index` values stored on lessons. The current subject JSON includes bit_index inline with lessons.

### Required Structure (spec FR-004)

"System MUST generate `{subject_id}_b.json` (bitmap) for each subject containing progress engine bit mappings"

**Design Decision**: Bitmap file structure:

```json
{
  "subject_id": "SUBJ-001",
  "version": 1706270400,
  "total_lessons": 150,
  "mappings": {
    "LESSON-001": { "bit_index": 0, "topic_id": "TOPIC-001" },
    "LESSON-002": { "bit_index": 1, "topic_id": "TOPIC-001" },
    ...
  }
}
```

**Rationale**:
- Separates bitmap data from navigation hierarchy
- Progress engine can load bitmap file without parsing full hierarchy
- Enables independent caching of bitmap vs hierarchy

---

## Research Task 6: Change Tracking Granularity

### Current Implementation

Location: `memora/services/cdn_export/change_tracker.py`

Hooks exist for all content types:
- `on_subject_update`, `on_track_update`, `on_unit_update`, `on_topic_update`, `on_lesson_update`

All hooks call `add_plan_to_queue(plan_id)` which queues a FULL plan rebuild.

### Required Granularity

With atomic files, we can be smarter:
- Lesson change → Only regenerate that lesson file
- Topic change → Regenerate topic file + update subject hierarchy/bitmap
- Unit/Track/Subject change → Regenerate hierarchy files

**Design Decision**: Keep full plan rebuild for now, optimize later.

**Rationale**:
- Atomic files already reduce per-file generation cost
- Dependency tracking adds complexity
- Can optimize with granular tracking in future iteration

---

## Research Task 7: Version/Cache Busting Strategy

### Current Implementation

Manifest includes `version` field (Unix timestamp) for cache busting.

### Required Behavior (spec FR-019)

"System MUST include version timestamp in manifest.json for cache busting"

**Design Decision**: Extend versioning to all file types:

1. **Manifest**: `version` = generation timestamp (as today)
2. **Hierarchy files**: Include `version` field
3. **Topic files**: Include `version` field
4. **Lesson files**: Include `version` field (shared across plans)

Client behavior:
- Check manifest version → if changed, re-fetch hierarchy files
- Hierarchy points to topic URLs with version query param
- Topic points to lesson URLs with version query param

---

## Summary of Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| File structure | Atomic (5 file types) | Spec requirement, enables granular caching |
| New override actions | Set Access Level, Set Linear | Spec FR-013, FR-014 |
| Atomic consistency | Two-phase commit (staging → swap) | Spec FR-018, prevents partial updates |
| Lesson sharing | `/lessons/{id}.json` (plan-agnostic) | Deduplication, spec FR-006 |
| Bitmap file | Separate `{subject_id}_b.json` | Progress engine optimization |
| Change tracking | Full plan rebuild (initial) | Simplicity, can optimize later |
| Versioning | Timestamp in all files | Cache busting at all levels |

---

## Next Steps

1. Create data-model.md with detailed file schemas
2. Create JSON Schema contracts in `/contracts/`
3. Create quickstart.md for developer onboarding
4. Ready for /speckit.tasks to generate implementation tasks
