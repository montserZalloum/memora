<!--
Sync Impact Report:
Version: 0.0.0 → 1.0.0
Change Type: Initial Constitution Creation
Modified Principles: N/A (Initial creation)
Added Sections:
  - Core Principles (Academic, Backend Sovereignty, Security)
  - Quality Standards (Mandatory Logic Tests)
  - Development Workflow
  - Governance
Templates Status:
  ✅ plan-template.md - Constitution Check section ready
  ✅ spec-template.md - Aligns with user-centric requirements
  ✅ tasks-template.md - Updated to reflect logic-testing requirements
-->

# Memora Constitution

## Core Principles

### I. Academic-First Architecture (The Brain)
The system is built around the **Game Academic Plan**. A user MUST never see content irrelevant to their defined `Grade` and `Stream`.
**Rules:**
- Content visibility is governed SOLELY by `Game Academic Plan`, never by hardcoding subjects to grades.
- The concept of "Partial Content" (Specific Units for specific Streams) is a first-class citizen and must be supported in all content APIs.
- Migration scripts are mandatory when changing the Academic Structure (Grades/Streams).

### II. Backend Sovereignty (Headless Logic)
The React App is a "Dumb Renderer". All critical business logic resides in the Frappe Backend (`api.py`).
**Rules:**
- **SRS Logic:** Calculation of `stability`, `next_review`, and `xp` happens ONLY in Python.
- **Access Control:** The Frontend UI validation is visual only. The Backend API MUST re-validate access permissions (Subscription/Season) on every critical call.
- **Store Logic:** Filtering purchased/pending items happens on the server to prevent data leakage.

### III. Lock-First Security (The Freemium Model)
Content is considered **LOCKED** by default unless an explicit "Key" is found.
**Rules:**
- **The Hierarchy of Keys (OR Logic):**
    1. Unit/Topic is `is_free_preview`.
    2. User has an `Active` Subscription linked to a valid `Season`.
    3. Subject AND Track are explicitly marked `is_paid = 0`.
- If a Subject is Paid, all its contents are locked, regardless of the Track status (unless the Track is explicitly free).

### IV. Data Integrity & Stable Identity
We prioritize long-term data stability over ease of editing to protect User Progress.
**Rules:**
- **ID Injection:** We do NOT use array indexes for SRS tracking. Every question inside a JSON stage must have a unique UUID (`id`) injected before saving.
- **Self-Healing:** The system must handle "Orphaned Data" (deleted lessons/questions) gracefully by cleaning up `Player Memory Tracker` records silently during runtime.

### V. Performance & Scalability
Memora must remain responsive under concurrent load from students during exam seasons.
**Rules:**
- **Payload Efficiency:** `get_map_data` must NOT return the full lesson body (JSON stages). It only returns structure and status.
- **Lazy Loading:** For `Topic-Based` units, lesson details are fetched only on demand (`get_topic_details`).
- **Atomic Transactions:** Session submissions must handle XP, SRS, and Leaderboard updates within a single DB transaction.

## Quality Standards

### Testing Philosophy
- **Core Logic Tests are MANDATORY:**
  - Subscription/Access Control Logic (`api.py`).
  - SRS Algorithm & Scheduling.
  - Academic Plan Filtering.
  - Purchase Workflows.
- **UI/Component Tests are OPTIONAL:**
  - Unless checking for complex interaction flows (e.g., Onboarding).
- **Golden Rule:** If it touches Money or Grades, it must be tested.

### Documentation Requirements
- All API endpoints MUST document expected inputs, outputs, and error codes.
- Database schema changes MUST be reflected in the "Data Dictionary" documentation.

## Development Workflow

### Branch Strategy
- Feature branches: `feat/###-description`.
- Hotfixes: `hotfix/description`.
- PRs must link to a Spec or Issue.

### Commit Standards
- Conventional Commits: `type(scope): description`.
- Types: `feat`, `fix`, `refactor`, `test`, `perf`, `chore`.

### Deployment Gates
- Pre-commit hooks (ruff, eslint) MUST pass.
- **Schema Migration:** Schema changes (DocType JSONs) are the source of truth. Manual DB changes in production are prohibited.
- Critical Logic changes require a passing Test Suite run before merge.

## Governance

### Amendment Process
1. Propose amendment via PR.
2. Require approval from the **System Architect**.
3. Update version and Sync Impact Report.

### Conflict Resolution
- This Constitution supersedes all other documentation or verbal agreements.
- When in doubt, favor **Data Integrity** over **Feature Velocity**.

**Version**: 1.0.0 | **Ratified**: 2026-01-19 | **Last Amended**: 2026-01-19