# Quickstart: Atomic JSON Content Generation & CDN Distribution

**Feature**: 008-atomic-content-cdn
**Branch**: `008-atomic-content-cdn`

## Overview

This feature refactors the CDN export system from monolithic to atomic JSON files, enabling:
- Sub-second content loading
- Shared lesson files across plans
- Granular cache invalidation

## Prerequisites

1. Feature 002 (CDN Content Export) is implemented
2. Feature 005 (Progress Engine Bitset) is implemented (for bit_index values)
3. Frappe bench environment with memora app installed

## Development Setup

```bash
# Switch to feature branch
git checkout 008-atomic-content-cdn

# Ensure dependencies are installed
cd $BENCH_PATH
bench update --requirements

# Run migrations (for new override actions)
bench migrate
```

## File Structure

```
/sites/{site}/public/memora_content/
├── plans/{plan_id}/
│   ├── manifest.json           # Plan entry point
│   ├── {subject_id}_h.json     # Subject hierarchy
│   ├── {subject_id}_b.json     # Subject bitmap
│   └── {topic_id}.json         # Topic lessons
└── lessons/{lesson_id}.json    # Shared lessons
```

## Key Changes from Feature 002

| Aspect | Before (002) | After (008) |
|--------|--------------|-------------|
| Subject file | `subjects/{id}.json` (full hierarchy) | `{id}_h.json` + `{id}_b.json` (split) |
| Lessons | Embedded in subject | Separate topic + lesson files |
| Lesson sharing | Duplicated per plan | Shared `/lessons/{id}.json` |
| Override actions | Hide, Rename, Set Free, Set Sold Separately | + Set Access Level, Set Linear |

## API Usage

### Triggering Regeneration

```python
# Trigger plan rebuild (unchanged from 002)
from memora.services.cdn_export.batch_processor import trigger_plan_rebuild

trigger_plan_rebuild("PLAN-GRADE12-2024")
```

### Accessing Generated Files

```python
# Get local base path
from memora.services.cdn_export.local_storage import get_local_base_path

base_path = get_local_base_path()
# /sites/{site}/public/memora_content/

# File paths for plan PLAN-001 and subject SUBJ-MATH:
manifest = f"{base_path}/plans/PLAN-001/manifest.json"
hierarchy = f"{base_path}/plans/PLAN-001/SUBJ-MATH_h.json"
bitmap = f"{base_path}/plans/PLAN-001/SUBJ-MATH_b.json"
topic = f"{base_path}/plans/PLAN-001/TOPIC-001.json"
lesson = f"{base_path}/lessons/LESSON-001.json"
```

## Testing

### Run Unit Tests

```bash
# Test access calculator (with new override actions)
pytest memora/tests/unit/cdn_export/test_access_calculator.py -v

# Test JSON generators
pytest memora/tests/unit/cdn_export/test_json_generator.py -v

# Test atomic consistency
pytest memora/tests/unit/cdn_export/test_atomic_consistency.py -v
```

### Manual Testing

```python
# In Frappe console: bench console

import frappe
from memora.services.cdn_export.batch_processor import trigger_plan_rebuild

# Trigger rebuild
trigger_plan_rebuild("PLAN-001")

# Check generated files
import os
import json

base = frappe.get_site_path("public", "memora_content")

# Read manifest
with open(f"{base}/plans/PLAN-001/manifest.json") as f:
    manifest = json.load(f)
    print(f"Subjects: {len(manifest['subjects'])}")

# Read first subject hierarchy
subject_id = manifest["subjects"][0]["id"]
with open(f"{base}/plans/PLAN-001/{subject_id}_h.json") as f:
    hierarchy = json.load(f)
    print(f"Tracks: {len(hierarchy['tracks'])}")
```

## Plan Overrides

### New Override Actions

```python
# Add "Set Access Level" override
frappe.get_doc({
    "doctype": "Memora Academic Plan",
    "name": "PLAN-001"
}).append("overrides", {
    "target_doctype": "Memora Unit",
    "target_name": "UNIT-001",
    "action": "Set Access Level",
    "override_value": "free_preview"  # public|authenticated|paid|free_preview
}).save()

# Add "Set Linear" override
frappe.get_doc({
    "doctype": "Memora Academic Plan",
    "name": "PLAN-001"
}).append("overrides", {
    "target_doctype": "Memora Topic",
    "target_name": "TOPIC-001",
    "action": "Set Linear",
    "override_value": "0"  # 0 = non-linear, 1 = linear
}).save()
```

## JSON Schema Validation

```python
# Validate generated files against schemas
from memora.services.cdn_export.batch_processor import validate_all_json_files

results = validate_all_json_files(files_data)
if not results["valid"]:
    print(f"Validation errors: {results['errors']}")
```

## Common Issues

### Issue: Old subject.json files still exist

**Solution**: Run cleanup to remove legacy files:
```bash
bench execute memora.services.cdn_export.migration.cleanup_legacy_files
```

### Issue: Lesson file not found

**Cause**: Lesson may be hidden by plan override
**Solution**: Check plan overrides for the lesson's parent topic/unit

### Issue: Bitmap bit_index is -1

**Cause**: Lesson missing bit_index assignment
**Solution**: Run progress engine migration:
```bash
bench execute memora.services.progress_engine.migration.assign_bit_indices
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Content Change                           │
│    (Subject/Track/Unit/Topic/Lesson/Override saved)         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  change_tracker.py                          │
│         Hooks detect change → Queue plan to Redis           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  batch_processor.py                         │
│         Process queue → Generate atomic files               │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  manifest   │  │  hierarchy  │  │   bitmap    │
│    .json    │  │   _h.json   │  │   _b.json   │
└─────────────┘  └─────────────┘  └─────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   topic .json       │
              │  (per topic)        │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   lesson .json      │
              │  (shared, no plan)  │
              └─────────────────────┘
```

## Related Documentation

- [spec.md](./spec.md) - Feature specification with user stories
- [plan.md](./plan.md) - Implementation plan
- [research.md](./research.md) - Research findings and decisions
- [data-model.md](./data-model.md) - Detailed data schemas
- [contracts/](./contracts/) - JSON Schema definitions
