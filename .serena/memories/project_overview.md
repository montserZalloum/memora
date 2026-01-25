# Memora Project Overview

## Project Purpose

Memora is a gamification learning platform built on the Frappe framework. It provides an educational content management system with features like:
- Academic Plans with hierarchical content structure (Subjects → Tracks → Units → Topics → Lessons)
- Player profiles, wallets, and subscription management
- Interaction logging and memory state tracking
- CDN content export system for static JSON generation

## Tech Stack

- **Framework**: Frappe v14/v15 (Python-based ERP framework)
- **Language**: Python 3.10+
- **Database**: MariaDB
- **Cache/Queue**: Redis (via frappe.cache)
- **CDN**: AWS S3 or Cloudflare R2 (via boto3)
- **Background Jobs**: RQ (Redis Queue)
- **Frontend**: JavaScript/Vue.js
- **Testing**: pytest with frappe test harness

## Code Style & Conventions

### Python Code Style
- **Indentation**: Tabs (not spaces)
- **Line Length**: 110 characters (ruff)
- **Quotes**: Double quotes for strings
- **Type Hints**: Uses `frappe.types.DF` for typing
- **Docstrings**: Required for all methods and classes
- **Naming**:
  - Classes: PascalCase (e.g., `MemoraSubject`, `CDNSettings`)
  - Methods: snake_case (e.g., `validate_endpoint_url`, `mark_as_success`)
  - Variables: snake_case
  - Constants: UPPER_SNAKE_CASE

### DocType Structure
Each DocType follows the pattern:
```
memora/memora/doctype/{doctype_name}/
├── __init__.py
├── {doctype_name}.json    # Schema definition
├── {doctype_name}.py      # Controller class
├── {doctype_name}.js      # Client-side logic (if needed)
└── test_{doctype_name}.py # Unit tests
```

### DocType Controller Pattern
```python
# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class DocTypeName(Document):
    def validate(self):
        """Validate document before save."""
        pass
    
    def before_save(self):
        """Set defaults before saving."""
        pass
```

### JSON Schema Format
DocType JSON files use Frappe's schema format with:
- `field_order`: List of field names in display order
- `fields`: Array of field definitions
- `search_index: 1` on Link fields used for filtering
- `reqd: 1` for required fields

## Project Structure

```
memora/
├── memora/
│   ├── doctype/              # All DocTypes
│   │   ├── cdn_settings/     # CDN configuration (NEW)
│   │   ├── cdn_sync_log/     # Sync audit log (NEW)
│   │   ├── memora_subject/   # Content hierarchy
│   │   ├── memora_track/
│   │   ├── memora_unit/
│   │   ├── memora_topic/
│   │   ├── memora_lesson/
│   │   ├── memora_academic_plan/
│   │   ├── memora_plan_override/
│   │   ├── memora_player_profile/
│   │   └── ...
│   └── hooks.py              # Frappe hooks (doc_events, scheduler_events)
├── services/
│   └── cdn_export/           # CDN export service (NEW)
│       ├── change_tracker.py      # Redis queue management
│       ├── dependency_resolver.py # Bottom-up rebuild logic
│       ├── json_generator.py      # Content to JSON conversion
│       ├── access_calculator.py  # Access level inheritance
│       ├── search_indexer.py     # Search index generation
│       ├── cdn_uploader.py        # S3/R2 upload + cache purge
│       └── batch_processor.py     # Main orchestration
├── api/
│   └── cdn_admin.py          # Dashboard API endpoints (NEW)
├── tests/
│   ├── unit/cdn_export/      # Unit tests
│   ├── integration/          # Integration tests
│   └── contract/             # Contract tests
├── specs/                    # Feature specifications (speckit methodology)
│   └── 002-cdn-content-export/
├── docs/                     # Documentation
└── .specify/                 # Speckit methodology files
    ├── memory/
    │   └── constitution.md   # Core principles
    ├── scripts/              # Helper scripts
    └── templates/            # Document templates
```

## Content Hierarchy

```
Memora Academic Plan
├── subjects (Table: Memora Plan Subject)
│   └── subject → Memora Subject
│       └── Memora Track (parent_subject)
│           └── Memora Unit (parent_track)
│               └── Memora Topic (parent_unit)
│                   └── Memora Lesson (parent_topic)
│                       └── stages (Table: Memora Lesson Stage)
└── overrides (Table: Memora Plan Override)
    ├── target_doctype
    ├── target_name
    └── action (Hide, Rename, Set Free, Set Sold Separately)
```

## Core Principles (Constitution)

### I. Read/Write Segregation (The Generator Pattern)
Write Model (Frappe) ≠ Read Model (JSON/Redis). Complex content structures must be compiled into static JSON payloads or cached Redis structures via background jobs.

### II. High-Velocity Data Segregation
Transactional DB is for State, not Logs. Write-intensive data (Interaction Logs, Stream Events) must go through an ingestion layer (Redis Streams/Queues).

### III. Content-Commerce Decoupling
Content is unaware of Price. Subject, Track, and Unit DocTypes must remain pure content containers. Access is determined via Product Grant mapping layer.

### IV. Logic Verification (TDD for Business Rules)
Complex Logic requires 100% Coverage. The "Plan Override System" and "Access Resolution Algorithm" need comprehensive unit tests.

### V. Performance-First Schema Design
Denormalization over Joins. Pre-calculated fields (Snapshots) and JSON storage preferred over deep Child Table nesting. Database Indexes MUST be explicitly defined for all Filter/Join columns.

## Key Commands

### Development Setup
```bash
# Install app in bench
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app memora

# Enable pre-commit hooks
cd apps/memora
pre-commit install
```

### Code Quality
```bash
# Run pre-commit checks (linting, formatting)
pre-commit run --all-files

# Run ruff linter
ruff check memora/

# Run ruff formatter
ruff format memora/
```

### Frappe Commands
```bash
# Run database migrations
bench migrate

# Start development server
bench start

# Run tests
bench run-tests

# Create new DocType
bench new-doctype "DocTypeName" --module "Memora"
```

### Testing
```bash
# Run unit tests
pytest memora/tests/unit/

# Run integration tests
pytest memora/tests/integration/

# Run specific test file
pytest memora/tests/unit/cdn_export/test_access_calculator.py
```

## Dependencies

### Core Dependencies
- `frappe~=15.0.0` (managed by bench)
- `boto3>=1.26.0` (AWS SDK for CDN operations)

### Dev Dependencies
- `ruff` (Python linter and formatter)
- `eslint` (JavaScript linter)
- `prettier` (JavaScript formatter)
- `pyupgrade` (Python syntax upgrader)

## Speckit Methodology

The project uses the speckit methodology for feature development:
1. **Research**: Understand requirements and existing patterns
2. **Plan**: Create implementation plan with constitution check
3. **Data Model**: Define schema and data structures
4. **Tasks**: Break down into actionable tasks with dependencies
5. **Implementation**: Follow TDD principles for complex logic
6. **Validation**: Test against acceptance criteria

Each feature has a spec in `specs/{feature-id}/` with:
- `spec.md` - User stories and acceptance criteria
- `plan.md` - Implementation plan and architecture
- `research.md` - Research findings
- `data-model.md` - Schema definitions
- `tasks.md` - Actionable task list
- `contracts/` - JSON schemas for validation
- `checklists/` - Requirements checklists

## Current Feature: CDN Content Export (002-cdn-content-export)

Building an automated static JSON generation system that exports educational content from Frappe/MariaDB to CDN (S3/Cloudflare R2). This implements the "Generator Pattern" from the constitution.

**Status**: Phase 2 (Foundational) - Adding required fields to existing DocTypes
- T009: Add `is_public` field to Memora Subject
- T010: Add `required_item` field to Memora Subject
- T011: Add `required_item` field to Memora Track
- T012: Add `parent_item_required` field to Memora Track

These fields are required for access control and content-commerce decoupling (Constitution Principle III).
