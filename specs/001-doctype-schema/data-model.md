# Data Model: Memora DocType Schema

**Feature**: 001-doctype-schema
**Date**: 2026-01-24
**Total DocTypes**: 19 (14 parent + 5 child tables)

## Overview

```
Educational Content Hierarchy:
Subject → Track → Unit → Topic → Lesson → Lesson Stage (child)

Academic Planning:
Season + Stream → Academic Plan → Plan Subject (child) + Plan Override (child)

Commerce:
Item (ERPNext) → Product Grant → Grant Component (child)

Player System:
User (Frappe) → Player Profile → Player Device (child)
                             → Player Wallet
                             → Memory State (FSRS)
                             → Interaction Log
                             → Subscription Transaction
```

---

## Entity Definitions

### Educational Content DocTypes

#### 1. Memora Subject

**Purpose**: Top-level educational category (Math, Physics, Chemistry)

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | Yes | Yes | - | Also used as ID (autoname: field:title) |
| color_code | Data | No | No | No | - | Hex color for UI branding |
| is_published | Check | No | No | No | 0 | Standard mixin |
| is_free_preview | Check | No | No | No | 0 | Standard mixin |
| sort_order | Int | No | Yes | No | 0 | Standard mixin |
| image | Attach Image | No | No | No | - | Standard mixin |
| description | Small Text | No | No | No | - | Standard mixin |

**Autoname**: `field:title`
**Permissions**: System Manager (full), Content Manager (read/write/create)

---

#### 2. Memora Track

**Purpose**: Sub-category within a Subject (can be sold separately)

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | No | No | - | Display name |
| parent_subject | Link (Memora Subject) | Yes | Yes | No | - | FK to Subject |
| is_sold_separately | Check | No | No | No | 0 | Commerce flag |
| is_published | Check | No | No | No | 0 | Standard mixin |
| is_free_preview | Check | No | No | No | 0 | Standard mixin |
| sort_order | Int | No | Yes | No | 0 | Standard mixin |
| image | Attach Image | No | No | No | - | Standard mixin |
| description | Small Text | No | No | No | - | Standard mixin |

**Autoname**: Default (hash) - allows duplicate titles across subjects
**Permissions**: System Manager (full), Content Manager (read/write/create)

---

#### 3. Memora Unit

**Purpose**: Learning module within a Track (awards badge on completion)

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | No | No | - | Display name |
| parent_track | Link (Memora Track) | Yes | Yes | No | - | FK to Track |
| badge_image | Attach Image | No | No | No | - | Completion badge |
| is_published | Check | No | No | No | 0 | Standard mixin |
| is_free_preview | Check | No | No | No | 0 | Standard mixin |
| sort_order | Int | No | Yes | No | 0 | Standard mixin |
| image | Attach Image | No | No | No | - | Standard mixin |
| description | Small Text | No | No | No | - | Standard mixin |

**Autoname**: Default (hash)
**Permissions**: System Manager (full), Content Manager (read/write/create)

---

#### 4. Memora Topic

**Purpose**: Specific topic within a Unit (groups related lessons)

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | No | No | - | Display name |
| parent_unit | Link (Memora Unit) | Yes | Yes | No | - | FK to Unit |
| is_published | Check | No | No | No | 0 | Standard mixin |
| is_free_preview | Check | No | No | No | 0 | Standard mixin |
| sort_order | Int | No | Yes | No | 0 | Standard mixin |
| image | Attach Image | No | No | No | - | Standard mixin |
| description | Small Text | No | No | No | - | Standard mixin |

**Autoname**: Default (hash)
**Permissions**: System Manager (full), Content Manager (read/write/create)

---

#### 5. Memora Lesson

**Purpose**: Individual learning item containing multiple stages

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | No | No | - | Display name |
| parent_topic | Link (Memora Topic) | Yes | Yes | No | - | FK to Topic |
| stages | Table (Memora Lesson Stage) | No | No | No | - | Child table |
| is_published | Check | No | No | No | 0 | Standard mixin |
| is_free_preview | Check | No | No | No | 0 | Standard mixin |
| sort_order | Int | No | Yes | No | 0 | Standard mixin |
| image | Attach Image | No | No | No | - | Standard mixin |
| description | Small Text | No | No | No | - | Standard mixin |

**Autoname**: Default (hash)
**Permissions**: System Manager (full), Content Manager (read/write/create)

---

#### 6. Memora Lesson Stage (Child Table)

**Purpose**: Atomic content piece within a lesson

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | No | No | - | Stage title |
| type | Select | Yes | No | No | - | Video/Question/Text/Interactive |
| config | JSON | No | No | No | - | Stage-specific configuration |

**Type Options**: `\nVideo\nQuestion\nText\nInteractive`
**Is Table**: Yes (istable: 1)

---

### Planning & Products DocTypes

#### 7. Memora Season

**Purpose**: Academic period (e.g., "Gen-2007", "Fall-2026")

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | Yes | Yes | - | Also used as ID (autoname: field:title) |
| is_published | Check | No | No | No | 0 | Visibility flag |
| start_date | Date | No | No | No | - | Period start |
| end_date | Date | No | No | No | - | Period end |

**Autoname**: `field:title`
**Permissions**: System Manager (full), Academic Planner (read/write/create)

---

#### 8. Memora Stream

**Purpose**: Educational track type (Scientific, Literary, Industrial)

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | Yes | Yes | - | Also used as ID (autoname: field:title) |

**Autoname**: `field:title`
**Permissions**: System Manager (full), Academic Planner (read/write/create)

---

#### 9. Memora Academic Plan

**Purpose**: Combines Season + Stream + Subjects with visibility overrides

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| title | Data | Yes | No | No | - | Plan display name |
| season | Link (Memora Season) | Yes | Yes | No | - | FK to Season |
| stream | Link (Memora Stream) | Yes | Yes | No | - | FK to Stream |
| subjects | Table (Memora Plan Subject) | No | No | No | - | Included subjects |
| overrides | Table (Memora Plan Override) | No | No | No | - | Visibility overrides |

**Autoname**: Default (hash)
**Permissions**: System Manager (full), Academic Planner (read/write/create)

---

#### 10. Memora Plan Subject (Child Table)

**Purpose**: Subject inclusion in an Academic Plan

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| subject | Link (Memora Subject) | Yes | No | No | - | FK to Subject |
| sort_order | Int | No | No | No | 0 | Display order |

**Is Table**: Yes (istable: 1)

---

#### 11. Memora Plan Override (Child Table)

**Purpose**: Visibility/behavior override for specific content within a plan

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| target_doctype | Link (DocType) | Yes | No | No | - | Which DocType (Track/Unit/Topic/Lesson) |
| target_name | Dynamic Link | Yes | No | No | - | Specific record (options: target_doctype) |
| action | Select | Yes | No | No | - | Hide/Rename/Set Free/Set Sold Separately |
| override_value | Data | No | No | No | - | Optional value for action |

**Action Options**: `\nHide\nRename\nSet Free\nSet Sold Separately`
**Is Table**: Yes (istable: 1)

**Note**: target_doctype should be filtered to show only: Memora Track, Memora Unit, Memora Topic, Memora Lesson

---

#### 12. Memora Product Grant

**Purpose**: Links ERPNext Item to Academic Plan for access control

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| item_code | Link (Item) | Yes | Yes | No | - | FK to ERPNext Item |
| academic_plan | Link (Memora Academic Plan) | Yes | Yes | No | - | FK to Academic Plan |
| grant_type | Select | Yes | No | No | - | Full Plan Access / Specific Components |
| unlocked_components | Table (Memora Grant Component) | No | No | No | - | If grant_type = Specific Components |

**Grant Type Options**: `\nFull Plan Access\nSpecific Components`
**Autoname**: Default (hash)
**Permissions**: System Manager (full), Sales Manager (read/write/create)

---

#### 13. Memora Grant Component (Child Table)

**Purpose**: Specific content items unlocked by a Product Grant

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| target_doctype | Link (DocType) | Yes | No | No | - | Which DocType (Subject/Track/Unit/Topic/Lesson) |
| target_name | Dynamic Link | Yes | No | No | - | Specific record (options: target_doctype) |

**Is Table**: Yes (istable: 1)

**Note**: target_doctype should be filtered to show only: Memora Subject, Memora Track, Memora Unit, Memora Topic, Memora Lesson

---

### Player Profile DocTypes

#### 14. Memora Player Profile

**Purpose**: Game identity separate from Frappe User

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| user | Link (User) | Yes | Yes | Yes | - | FK to Frappe User (unique) |
| display_name | Data | No | No | No | - | Public display name |
| avatar | Attach Image | No | No | No | - | Profile picture |
| current_plan | Link (Memora Academic Plan) | No | Yes | No | - | Active academic plan |
| devices | Table (Memora Player Device) | No | No | No | - | Registered devices |

**Autoname**: Default (hash)
**Permissions**: System Manager (full), Player (own records only)

---

#### 15. Memora Player Device (Child Table)

**Purpose**: Device registration for player

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| device_id | Data | Yes | No | No | - | Unique device identifier |
| device_name | Data | No | No | No | - | Human-readable name |
| is_trusted | Check | No | No | No | 0 | Trust flag for auto-login |

**Is Table**: Yes (istable: 1)

---

#### 16. Memora Player Wallet

**Purpose**: High-velocity XP and streak data for gamification

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| player | Link (Memora Player Profile) | Yes | Yes | Yes | - | FK to Player (unique) |
| total_xp | Int | No | No | No | 0 | Total experience points |
| current_streak | Int | No | No | No | 0 | Current daily streak |
| last_played_at | Datetime | No | No | No | - | Last activity timestamp |

**Autoname**: Default (hash)
**Permissions**: System Manager (full)

---

### Engine & Logs DocTypes

#### 17. Memora Interaction Log

**Purpose**: Write-only audit trail of all question attempts

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| player | Link (Memora Player Profile) | Yes | Yes | No | - | FK to Player |
| academic_plan | Link (Memora Academic Plan) | Yes | Yes | No | - | FK to Plan |
| question_id | Data | Yes | Yes | No | - | Opaque UUID/hash identifier |
| student_answer | Data | No | No | No | - | What student answered |
| correct_answer | Data | No | No | No | - | Expected answer |
| is_correct | Check | No | No | No | 0 | Answer correctness |
| time_taken | Int | No | No | No | - | Seconds to answer |
| timestamp | Datetime | No | No | No | Now | When interaction occurred |

**Autoname**: Default (hash)
**Permissions**: System Manager (read only - write via API)

**Note**: This is a write-only log. Deletion should be restricted.

---

#### 18. Memora Memory State

**Purpose**: FSRS algorithm state per player-question pair

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| player | Link (Memora Player Profile) | Yes | Yes | No | - | FK to Player |
| question_id | Data | Yes | Yes | No | - | Opaque UUID/hash identifier |
| stability | Float | No | No | No | - | FSRS stability parameter |
| difficulty | Float | No | No | No | - | FSRS difficulty parameter |
| next_review | Datetime | No | Yes | No | - | **Critical index** for scheduling |
| state | Select | No | No | No | New | FSRS state machine |

**State Options**: `\nNew\nLearning\nReview\nRelearning`
**Autoname**: Default (hash)
**Permissions**: System Manager (full)

**Performance Note**: The `next_review` index is critical for FSRS scheduling queries. Must support 100,000+ records with <100ms query time.

---

### Commerce DocTypes

#### 19. Memora Subscription Transaction

**Purpose**: Payment records linking purchases to product grants

| Field | Type | Required | Indexed | Unique | Default | Notes |
|-------|------|----------|---------|--------|---------|-------|
| naming_series | Select | Yes | No | No | SUB-TX-.YYYY.- | Naming series field |
| player | Link (Memora Player Profile) | Yes | Yes | No | - | FK to Player |
| transaction_type | Select | Yes | No | No | - | Purchase/Renewal/Upgrade |
| payment_method | Select | Yes | No | No | - | Payment Gateway/Manual-Admin/Voucher |
| status | Select | Yes | No | No | Pending Approval | Transaction status |
| transaction_id | Data | No | No | No | - | External payment ID |
| amount | Currency | No | No | No | - | Transaction amount |
| receipt_image | Attach Image | No | No | No | - | Payment receipt |
| related_grant | Link (Memora Product Grant) | No | Yes | No | - | FK to Product Grant |
| erpnext_invoice | Link (Sales Invoice) | No | No | No | - | FK to ERPNext invoice (read-only) |

**Naming Series**: `SUB-TX-.YYYY.-` (e.g., SUB-TX-2026-00001)
**Transaction Type Options**: `\nPurchase\nRenewal\nUpgrade`
**Payment Method Options**: `\nPayment Gateway\nManual-Admin\nVoucher`
**Status Options**: `\nPending Approval\nCompleted\nFailed\nCancelled`
**Autoname**: `naming_series:`
**Permissions**: System Manager (full), Sales Manager (read/write/create)

---

## Relationships Diagram

```
                        ┌─────────────────┐
                        │  Memora Subject │
                        │  (autoname:title)│
                        └────────┬────────┘
                                 │ 1:N
                        ┌────────▼────────┐
                        │  Memora Track   │
                        │  (hash ID)      │
                        └────────┬────────┘
                                 │ 1:N
                        ┌────────▼────────┐
                        │   Memora Unit   │
                        │  (hash ID)      │
                        └────────┬────────┘
                                 │ 1:N
                        ┌────────▼────────┐
                        │  Memora Topic   │
                        │  (hash ID)      │
                        └────────┬────────┘
                                 │ 1:N
                        ┌────────▼────────┐
                        │  Memora Lesson  │───┬─► Memora Lesson Stage (child)
                        │  (hash ID)      │   │
                        └─────────────────┘   │
                                              │
┌──────────────┐    ┌───────────────┐         │
│Memora Season │◄───┤Memora Academic├─────────┼─► Memora Plan Subject (child)
│(autoname:title)│  │    Plan       │         │
└──────────────┘    │  (hash ID)    ├─────────┼─► Memora Plan Override (child)
                    └───────┬───────┘         │
┌──────────────┐            │                 │
│Memora Stream │◄───────────┘                 │
│(autoname:title)│                            │
└──────────────┘                              │
                                              │
┌──────────────────┐     ┌──────────────────┐ │
│ Item (ERPNext)   │◄────┤Memora Product    ├─┴─► Memora Grant Component (child)
└──────────────────┘     │     Grant        │
                         │  (hash ID)       │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
┌──────────────┐         │Memora Subscription│
│User (Frappe) │◄────────┤   Transaction    │
└──────┬───────┘         │  (naming_series) │
       │                 └──────────────────┘
       │ 1:1
┌──────▼────────────┐
│Memora Player      │──► Memora Player Device (child)
│    Profile        │
│  (hash ID)        │
└──────┬────────────┘
       │ 1:1
┌──────▼────────────┐
│Memora Player      │
│    Wallet         │
│  (hash ID)        │
└───────────────────┘

┌───────────────────┐     ┌───────────────────┐
│Memora Interaction │     │Memora Memory      │
│      Log          │     │     State         │
│  (hash ID)        │     │  (hash ID)        │
└───────────────────┘     └───────────────────┘
```

---

## Index Summary

| DocType | Indexed Fields | Critical | Rationale |
|---------|----------------|----------|-----------|
| Memora Track | parent_subject, sort_order | No | Hierarchy queries |
| Memora Unit | parent_track, sort_order | No | Hierarchy queries |
| Memora Topic | parent_unit, sort_order | No | Hierarchy queries |
| Memora Lesson | parent_topic, sort_order | No | Hierarchy queries |
| Memora Academic Plan | season, stream | No | Plan filtering |
| Memora Player Profile | user, current_plan | No | User lookup |
| Memora Player Wallet | player | No | Player lookup |
| Memora Interaction Log | player, academic_plan, question_id | No | Query performance |
| Memora Memory State | player, question_id, **next_review** | **Yes** | FSRS scheduling |
| Memora Product Grant | item_code, academic_plan | No | Commerce queries |
| Memora Subscription Transaction | player, related_grant | No | Transaction lookup |

---

## State Transitions

### Memory State (FSRS)

```
New → Learning → Review ⟷ Relearning
                   ↓
               (continues)

Managed by application layer, not schema constraints.
```

### Subscription Transaction Status

```
Pending Approval → Completed
                → Failed
                → Cancelled

Managed by application layer workflows.
```
