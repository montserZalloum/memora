# Feature Specification: Memora Application Documentation

**Feature Branch**: `001-memora-docs`
**Created**: 2026-01-19
**Status**: Draft
**Input**: User description: "Analyze the entire Memora application and produce complete documentation including business overview, flows, architecture, doctypes, APIs, database models, validation rules, and diagrams."

---

## 1. Business Overview and App Purpose

### 1.1 What is Memora?

Memora is a **Gamified Learning Management System (LMS)** built on the Frappe/ERPNext framework. It transforms traditional education into an engaging, game-like experience by combining:

- **Spaced Repetition System (SRS)**: Scientific memory retention algorithms that optimize when students review material
- **Gamification**: XP points, levels, streaks, leaderboards, and daily quests to motivate learners
- **Academic Planning**: Flexible curriculum mapping based on grade, academic stream (specialization), and academic year
- **Subscription Economy**: Multi-tiered access control with manual payment approval workflow

### 1.2 Target Users

| User Type | Description |
|-----------|-------------|
| **Students** | Primary users who learn through interactive lessons and review sessions |
| **Administrators** | Manage content, approve purchases, configure academic plans |
| **Content Creators** | Build lessons with interactive stages (Reveal, Matching, Quiz, etc.) |

### 1.3 Core Value Proposition

1. **Personalized Learning Paths**: Students see only subjects and units relevant to their academic context (grade + stream)
2. **Memory Optimization**: SRS ensures students review information at scientifically optimal intervals
3. **Engagement Loop**: Gamification mechanics (XP, streaks, quests) drive daily engagement
4. **Flexible Monetization**: Supports both free previews and paid content with season-based subscriptions

---

## 2. Full Business Flows (Step-by-Step)

### 2.1 Student Onboarding Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    STUDENT ONBOARDING FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User Registration (Frappe Auth)                             │
│         │                                                        │
│         ▼                                                        │
│  2. API: get_academic_masters()                                 │
│     ├── Returns: Grades with allowed streams                    │
│     └── Returns: Active subscription season                     │
│         │                                                        │
│         ▼                                                        │
│  3. Student Selects Grade & Stream (if applicable)              │
│         │                                                        │
│         ▼                                                        │
│  4. API: set_academic_profile(grade, stream)                    │
│     ├── Validates stream is allowed for grade                   │
│     ├── Creates/Updates Player Profile                          │
│     └── Links to active season                                  │
│         │                                                        │
│         ▼                                                        │
│  5. Profile Complete → Redirect to Subject Map                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Content Discovery Flow (Learning Map)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTENT DISCOVERY FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. API: get_subjects() or get_my_subjects()                    │
│     ├── Reads Player Profile (grade, stream, academic_year)    │
│     ├── Finds matching Academic Plan                            │
│     └── Returns subjects with display_name overrides            │
│         │                                                        │
│         ▼                                                        │
│  2. Student Selects Subject                                     │
│         │                                                        │
│         ▼                                                        │
│  3. API: get_map_data(subject)                                  │
│     ├── Loads Unit hierarchy from plan                          │
│     ├── BRANCH: Unit.structure_type                             │
│     │   ├── "Lesson Based" → Load lessons directly (eager)      │
│     │   └── "Topic Based" → Load topics only (lazy)             │
│     ├── Calculates lock states (financial + progression)        │
│     └── Returns hierarchical map structure                      │
│         │                                                        │
│         ▼                                                        │
│  4. Student Clicks Topic (if Topic Based)                       │
│         │                                                        │
│         ▼                                                        │
│  5. API: get_topic_details(topic_id)                            │
│     ├── Loads lessons for that topic                            │
│     ├── Applies financial access check                          │
│     └── Applies linear progression check (if is_linear=true)    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Gameplay Session Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     GAMEPLAY SESSION FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Student selects available lesson                            │
│         │                                                        │
│         ▼                                                        │
│  2. API: get_lesson_details(lesson_id)                          │
│     ├── Returns lesson metadata                                  │
│     └── Returns stages array with configs (JSON)                │
│         │                                                        │
│         ▼                                                        │
│  3. Frontend renders interactive stages:                        │
│     ├── Reveal: Show sentence, highlight key words              │
│     ├── Matching: Connect pairs (left ↔ right)                  │
│     ├── Fill Blank: Complete the sentence                       │
│     ├── Sentence Builder: Arrange words in order                │
│     └── Quiz: Multiple choice questions                         │
│         │                                                        │
│         ▼                                                        │
│  4. Student completes lesson → Frontend collects:               │
│     ├── session_meta: {lesson_id, timestamps}                   │
│     ├── gamification_results: {xp_earned, score}                │
│     └── interactions: [{question_id, is_correct, duration}]     │
│         │                                                        │
│         ▼                                                        │
│  5. API: submit_session(session_meta, results, interactions)    │
│     ├── Creates Gameplay Session record                          │
│     ├── Updates Player Profile (total_xp += earned)             │
│     ├── Updates Player Subject Score (leaderboard)              │
│     └── Calls process_srs_batch() → Updates Memory Trackers     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 Spaced Repetition Review Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SRS REVIEW SESSION FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Student opens Review section                                │
│         │                                                        │
│         ▼                                                        │
│  2. API: get_review_session(subject?, topic_id?)                │
│     ├── Mode A: General Review (subject or all)                 │
│     │   └── Fetches items where next_review_date <= NOW()       │
│     ├── Mode B: Topic Focus (topic_id provided)                 │
│     │   ├── Dynamic sizing: 10% of items, min=10, max=30        │
│     │   └── Priority: stability=1 > overdue > not seen today    │
│     ├── Converts stages to quiz format:                         │
│     │   ├── Reveal → Fill-the-blank quiz                        │
│     │   └── Matching → Synonym quiz                             │
│     ├── AI distractor generation (or local fallback)            │
│     └── Cleans corrupt tracker entries (self-healing)           │
│         │                                                        │
│         ▼                                                        │
│  3. Student answers quiz cards (timed, with combo streak)       │
│         │                                                        │
│         ▼                                                        │
│  4. API: submit_review_session(session_data)                    │
│     ├── Updates SRS stability for each item:                    │
│     │   ├── Correct + Fast (<2s): stability += 2 (cap at 4)     │
│     │   ├── Correct + Normal (2-6s): stability += 1             │
│     │   ├── Correct + Slow (>6s): stability unchanged           │
│     │   └── Wrong: stability = 1 (reset)                        │
│     ├── Calculates next_review_date based on new stability:     │
│     │   ├── Stability 1: +1 day                                 │
│     │   ├── Stability 2: +3 days                                │
│     │   ├── Stability 3: +7 days                                │
│     │   └── Stability 4: +14 days                               │
│     ├── Records session with XP (decreasing for repeats)        │
│     └── Returns remaining_items (Netflix Effect prompt)         │
│         │                                                        │
│         ▼                                                        │
│  5. If remaining_items > 0: Show "Continue Review?" prompt      │
│     If remaining_items = 0: Show completion celebration         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 Purchase and Subscription Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   PURCHASE & SUBSCRIPTION FLOW                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. API: get_store_items()                                      │
│     ├── Filters items by student's grade and stream             │
│     ├── Hides already-owned content                             │
│     └── Hides pending purchase requests                         │
│         │                                                        │
│         ▼                                                        │
│  2. Student selects item and pays externally (manual process)   │
│         │                                                        │
│         ▼                                                        │
│  3. API: request_purchase(item_id, transaction_id?)             │
│     ├── Creates Game Purchase Request (status: Pending)         │
│     └── Prevents duplicate pending requests                     │
│         │                                                        │
│         ▼                                                        │
│  4. Admin reviews payment proof                                 │
│         │                                                        │
│         ▼                                                        │
│  5. Admin approves → System creates Game Player Subscription    │
│     ├── Links to current active season                          │
│     ├── Populates access_items from bundle contents             │
│     └── Sets status to 'Active'                                 │
│         │                                                        │
│         ▼                                                        │
│  6. Access Check (on each content request)                      │
│     ├── get_user_active_subscriptions(user)                     │
│     │   └── Validates season.end_date >= TODAY                  │
│     └── check_subscription_access(subs, subject, track)         │
│         ├── Global Access → unlock all                          │
│         ├── Subject Access → unlock that subject                │
│         └── Track Access → unlock that specific track           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. System Architecture

### 3.1 Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend Framework** | Frappe (ERPNext ecosystem) |
| **Backend Language** | Python 3.10+ |
| **Database** | MariaDB/MySQL with InnoDB |
| **Frontend** | JavaScript (Vue.js/React bundled) |
| **AI Integration** | External HTTP service at localhost:5177/ai (stub) |
| **API Protocol** | Frappe REST + RPC (@frappe.whitelist) |

### 3.2 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │   Web Frontend  │    │  Mobile App     │                     │
│  │  (Vue.js/React) │    │  (Future)       │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                      │                               │
│           ▼                      ▼                               │
│  ┌─────────────────────────────────────────┐                    │
│  │        Frappe REST API Layer            │                    │
│  │   (api.py - @frappe.whitelist())        │                    │
│  └────────────────────┬────────────────────┘                    │
└───────────────────────┼─────────────────────────────────────────┘
                        │
┌───────────────────────┼─────────────────────────────────────────┐
│                       ▼                                          │
│              APPLICATION LAYER                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    api.py (1,897 lines)                 │    │
│  │  ┌──────────────┬──────────────┬──────────────────┐     │    │
│  │  │ Content APIs │ Gameplay APIs│ Economy APIs     │     │    │
│  │  │ get_subjects │ submit_sess. │ get_store_items  │     │    │
│  │  │ get_map_data │ get_review   │ request_purchase │     │    │
│  │  │ get_lesson   │ submit_revw  │ get_leaderboard  │     │    │
│  │  └──────────────┴──────────────┴──────────────────┘     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                        │                                         │
│  ┌─────────────────────┴───────────────────────────────────┐    │
│  │                    Helper Modules                        │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │    │
│  │  │ ai_engine.py │  │   setup.py   │  │  hooks.py    │   │    │
│  │  │ Distractors  │  │ After-migrate│  │ App config   │   │    │
│  │  │ (stub/AI)    │  │ SRS setup    │  │ JS hooks     │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────┼─────────────────────────────────────────┐
│                       ▼                                          │
│                 DATA LAYER                                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              DocTypes (26 Total)                         │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │ Academic Infrastructure (5)                      │    │    │
│  │  │ Game Academic Grade, Stream, Season, Plan, etc.  │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │ Content Hierarchy (5)                            │    │    │
│  │  │ Game Subject, Track, Unit, Topic, Lesson         │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │ Player Data (4)                                  │    │    │
│  │  │ Player Profile, Memory Tracker, Subject Score    │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │ Economy & Store (5)                              │    │    │
│  │  │ Sales Item, Subscription, Purchase Request       │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │ Child Tables (7)                                 │    │    │
│  │  │ Stage, Plan Subject, Bundle Content, Access...   │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                        │                                         │
│                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              MariaDB/MySQL Database                      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. All DocTypes and Features

### 4.1 Academic Infrastructure (5 DocTypes)

#### 4.1.1 Game Academic Grade

**Purpose**: Defines academic levels (e.g., Grade 10, Tawjihi)

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `grade_name` | Data | Display name shown in onboarding | - |
| `valid_streams` | Table | Allowed specializations for this grade | → Game Grade Valid Stream |

**Business Logic**: Used during onboarding to filter which streams (specializations) a student can choose based on their grade.

---

#### 4.1.2 Game Academic Stream

**Purpose**: Defines academic specializations (Scientific, Literary, Industrial, etc.)

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `stream_name` | Data | Identifier/display name | - |

**Business Logic**: Streams may have different subject sets in the academic plan.

---

#### 4.1.3 Game Subscription Season

**Purpose**: Defines time-bound periods for subscriptions (e.g., "Tawjihi 2025")

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `start_date` | Date | Season start | - |
| `end_date` | Date | Season end - **controls subscription validity** | - |
| `is_active` | Check | Marks the current default season for new students | - |

**Critical Business Rule**: Subscription validity is NOT based on purchase date. When `Season.end_date` passes, ALL linked subscriptions expire instantly.

---

#### 4.1.4 Game Academic Plan

**Purpose**: Maps (Grade + Stream + Year) to a specific curriculum

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `grade` | Link | Target grade | → Game Academic Grade |
| `stream` | Link | Target stream (optional) | → Game Academic Stream |
| `year` | Data | Academic year (e.g., "2025") | - |
| `subjects` | Table | Curriculum subjects | → Game Plan Subject |

**Unique Constraint**: (grade, stream, year) combination must be unique.

---

#### 4.1.5 Game Plan Subject (Child Table)

**Purpose**: Defines which subjects and units appear in an academic plan

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `subject` | Link | The subject to include | → Game Subject |
| `display_name` | Data | Override name (e.g., show "Math" instead of "Advanced Mathematics") | - |
| `selection_type` | Select | "All Units" or "Specific Unit" | - |
| `specific_unit` | Link | Only show this unit (when selection_type = Specific) | → Game Unit |
| `is_mandatory` | Check | Marks required subjects | - |

---

### 4.2 Content Hierarchy (5 DocTypes)

#### 4.2.1 Game Subject

**Purpose**: Top-level content container (e.g., Mathematics, Physics)

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `title` | Data | Subject name | - |
| `icon` | Data | Icon identifier for UI | - |
| `is_published` | Check | Visibility control | - |
| `is_paid` | Check | **Master lock** - if true, all content requires subscription | - |

**Access Logic**: If `is_paid = false`, the entire subject is free for everyone regardless of subscription status.

---

#### 4.2.2 Game Learning Track

**Purpose**: Parallel paths within a subject (Standard, Intensive, Foundation)

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `track_name` | Data | Track identifier | - |
| `subject` | Link | Parent subject | → Game Subject |
| `is_default` | Check | Shows first in track selection | - |
| `unlock_level` | Int | Minimum player level to access | - |
| `is_paid` | Check | Requires payment (can differ from subject) | - |
| `is_sold_separately` | Check | If true, standard subscription doesn't unlock this track | - |

**Business Logic**: A track with `is_sold_separately = true` is a premium product requiring its own subscription.

---

#### 4.2.3 Game Unit

**Purpose**: Chapters/Modules containing topics or lessons

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `title` | Data | Unit name | - |
| `subject` | Link | Parent subject | → Game Subject |
| `learning_track` | Link | Associated track | → Game Learning Track |
| `structure_type` | Select | **"Topic Based"** (clusters) or **"Lesson Based"** (path) | - |
| `is_linear_topics` | Check | Enforce sequential topic completion | - |
| `is_free_preview` | Check | Override all payment locks (marketing teaser) | - |

**Critical Business Logic**:
- `structure_type` determines map rendering style
- `Topic Based`: Shows topics as clusters (lazy load lessons)
- `Lesson Based`: Shows lessons directly as a linear path

---

#### 4.2.4 Game Topic

**Purpose**: Groups lessons under a themed cluster (only for Topic Based units)

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `title` | Data | Topic name | - |
| `unit` | Link | Parent unit | → Game Unit |
| `description` | Small Text | Topic description | - |
| `is_linear` | Check | Enforce sequential lesson completion within topic | - |
| `is_free_preview` | Check | Make this specific topic free | - |

---

#### 4.2.5 Game Lesson

**Purpose**: The playable learning unit containing interactive stages

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `title` | Data | Lesson name | - |
| `unit` | Link | Parent unit | → Game Unit |
| `topic` | Link | Parent topic (null for Lesson Based units) | → Game Topic |
| `xp_reward` | Int | XP earned on completion | - |
| `is_published` | Check | Visibility control | - |
| `stages` | Table | Interactive content | → Game Stage |

**Validation Rule**: If `Unit.structure_type = "Topic Based"`, lesson MUST have a topic. If `structure_type = "Lesson Based"`, topic MUST be null (auto-cleaned).

---

#### 4.2.6 Game Stage (Child Table)

**Purpose**: Individual interactive game elements within a lesson

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `title` | Data | Stage identifier | - |
| `type` | Select | Stage type | - |
| `config` | JSON | Stage-specific configuration | - |

**Stage Types**:

| Type | Config Structure | Purpose |
|------|-----------------|---------|
| **Reveal** | `{sentence, highlights: [{word, translation}]}` | Show text with highlighted vocabulary |
| **Matching** | `{pairs: [{left, right}]}` | Connect related terms |
| **Fill Blank** | `{sentence, blanks: [{word, position}]}` | Complete sentences |
| **Sentence Builder** | `{words: [], correct_order: []}` | Arrange words correctly |
| **Quiz** | `{question, correct_answer, options: []}` | Multiple choice |

---

### 4.3 Player Data & Progression (4 DocTypes)

#### 4.3.1 Player Profile

**Purpose**: Master record for each student

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `user` | Link | Frappe User account | → User |
| `total_xp` | Int | Global XP across all subjects | - |
| `gems_balance` | Int | Virtual currency (future use) | - |
| `current_grade` | Link | Student's academic level | → Game Academic Grade |
| `current_stream` | Link | Student's specialization | → Game Academic Stream |
| `academic_year` | Data | Links to season (e.g., "2025") | - |
| `devices` | Table | Registered devices | → Game Player Device |

---

#### 4.3.2 Player Memory Tracker

**Purpose**: SRS tracking - one record per (player, question) combination

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `player` | Link | Owner | → User |
| `question_id` | Data | Stage reference (format: "STAGE-ID:index") | - |
| `subject` | Link | Subject for filtering | → Game Subject |
| `topic` | Link | Topic for focus mode filtering | → Game Topic |
| `stability` | Int | Memory strength (1-4) | - |
| `last_review_date` | Datetime | When last reviewed | - |
| `next_review_date` | Datetime | When to show again | - |
| `season` | Link | Scoped to academic season | → Game Subscription Season |

**Stability Levels**:
- **1 (New/Failing)**: Review tomorrow
- **2 (Learning)**: Review in 3 days
- **3 (Intermediate)**: Review in 7 days
- **4 (Mastered)**: Review in 14 days

---

#### 4.3.3 Player Subject Score

**Purpose**: Per-subject progression for leaderboards

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `player` | Link | Owner | → User |
| `subject` | Link | Subject | → Game Subject |
| `total_xp` | Int | XP earned in this subject | - |
| `level` | Int | Calculated level | - |
| `season` | Link | Scoped to season | → Game Subscription Season |

**Naming Convention**: `SUB-SCR-{user}-{subject}`

---

#### 4.3.4 Gameplay Session

**Purpose**: Audit log of all completed lessons/reviews

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `player` | Link | Who played | → User |
| `lesson` | Link/Data | Which lesson (or "مراجعة الذاكرة" for reviews) | → Game Lesson |
| `xp_earned` | Int | XP from this session | - |
| `score` | Int | Performance score | - |
| `raw_data` | JSON | Complete interaction log | - |

---

### 4.4 Economy & Store (5 DocTypes)

#### 4.4.1 Game Sales Item

**Purpose**: Products displayed in the store

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `item_name` | Data | Display name | - |
| `description` | Text | Marketing text | - |
| `price` | Currency | Original price | - |
| `discounted_price` | Currency | Sale price | - |
| `image` | Attach Image | Product image | - |
| `sku` | Data | Stock keeping unit | - |
| `linked_season` | Link | Subscription period | → Game Subscription Season |
| `target_grade` | Link | Only show to this grade | → Game Academic Grade |
| `target_streams` | Table | Only show to these streams | → Game Item Target Stream |
| `bundle_contents` | Table | What's included | → Game Bundle Content |

---

#### 4.4.2 Game Bundle Content (Child Table)

**Purpose**: Defines what a sales item unlocks

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `content_type` | Select | "Subject" or "Track" | - |
| `subject` | Link | If type is Subject | → Game Subject |
| `track` | Link | If type is Track | → Game Learning Track |

---

#### 4.4.3 Game Player Subscription

**Purpose**: Active subscription records

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `player` | Link | Owner | → Player Profile |
| `type` | Select | "Global Access" (all content) or "Specific" | - |
| `linked_season` | Link | Validity period | → Game Subscription Season |
| `access_items` | Table | What's unlocked | → Game Subscription Access |
| `status` | Select | Active/Expired/Cancelled | - |

---

#### 4.4.4 Game Subscription Access (Child Table)

**Purpose**: Specific items unlocked by a subscription

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `type` | Select | "Subject" or "Track" | - |
| `subject` | Link | If type is Subject | → Game Subject |
| `track` | Link | If type is Track | → Game Learning Track |

---

#### 4.4.5 Game Purchase Request

**Purpose**: Payment approval queue (manual workflow)

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `user` | Link | Requester | → User |
| `sales_item` | Link | What they're buying | → Game Sales Item |
| `status` | Select | Draft/Pending/Approved/Rejected | - |
| `price` | Currency | Amount | - |
| `transaction_id` | Data | External payment reference | - |

**Workflow**: Pending → Admin reviews → Approved → System creates Subscription

---

### 4.5 Utility DocTypes (2 DocTypes)

#### 4.5.1 Game AI Question Cache

**Purpose**: Cache AI-generated distractors to reduce API calls

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `content_hash` | Data | MD5(question_type:correct_answer:context) | - |
| `question_type` | Data | "reveal" or "matching" | - |
| `original_text` | Data | The correct answer | - |
| `ai_response` | JSON | Cached distractor options | - |

---

#### 4.5.2 Game Content Builder Item

**Purpose**: Helper for content creation UI

| Field | Type | Purpose | Relations |
|-------|------|---------|-----------|
| `item_config` | JSON | Builder state | - |

---

## 5. API Endpoints and Data Flow

### 5.1 Content APIs

| Endpoint | Method | Parameters | Returns | Purpose |
|----------|--------|------------|---------|---------|
| `get_subjects()` | GET | - | `[{name, title, icon, is_paid}]` | Subjects for user's academic plan |
| `get_my_subjects()` | GET | - | `[{id, name, icon, display_name, is_mandatory}]` | Enhanced subject list with metadata |
| `get_game_tracks(subject)` | GET | subject_id | `[{name, track_name, is_default, unlock_level}]` | Learning tracks for a subject |
| `get_map_data(subject?)` | GET | optional subject_id | Hierarchical map structure | Smart content map with dual mode support |
| `get_lesson_details(lesson_id)` | GET | lesson_id | `{name, title, xp_reward, stages: [...]}` | Full lesson with stage configs |
| `get_topic_details(topic_id)` | GET | topic_id | `{topic_id, title, description, lessons: [...]}` | Topic lessons with lock states |

### 5.2 Gameplay APIs

| Endpoint | Method | Parameters | Returns | Purpose |
|----------|--------|------------|---------|---------|
| `submit_session(meta, results, interactions)` | POST | session data | `{status: "success"}` | Record lesson completion |
| `get_review_session(subject?, topic_id?)` | GET | optional filters | `[{id, type, question, correct_answer, options}]` | Intelligent review session |
| `submit_review_session(session_data)` | POST | answers, meta | `{status, xp_earned, remaining_items}` | Save review, update SRS |

### 5.3 Profile & Stats APIs

| Endpoint | Method | Parameters | Returns | Purpose |
|----------|--------|------------|---------|---------|
| `get_player_profile()` | GET | - | `{xp, gems, current_grade, current_stream}` | Basic profile data |
| `get_full_profile_stats(subject?)` | GET | optional subject | `{level, streak, mastery, weeklyActivity}` | Comprehensive stats |
| `get_daily_quests(subject?)` | GET | optional subject | `[{id, type, title, progress, target, status}]` | Daily challenges |
| `get_leaderboard(subject?, period?)` | GET | optional filters | `{leaderboard: [...], userRank: {...}}` | Rankings |

### 5.4 Onboarding APIs

| Endpoint | Method | Parameters | Returns | Purpose |
|----------|--------|------------|---------|---------|
| `get_academic_masters()` | GET | - | `{grades, streams, current_season}` | Onboarding data |
| `set_academic_profile(grade, stream?)` | POST | grade, optional stream | `{status}` | Save student's academic context |

### 5.5 Store APIs

| Endpoint | Method | Parameters | Returns | Purpose |
|----------|--------|------------|---------|---------|
| `get_store_items()` | GET | - | `[{name, item_name, price, ...}]` | Filtered products |
| `request_purchase(item_id, transaction_id?)` | POST | item_id, optional ref | `{status, message}` | Create purchase request |

---

## 6. Database Models: Tables and Fields

### 6.1 Entity Relationship Diagram (Text-Based)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ENTITY RELATIONSHIP DIAGRAM                         │
└─────────────────────────────────────────────────────────────────────────────┘

                              ACADEMIC INFRASTRUCTURE
                              ─────────────────────────

    ┌──────────────────┐         ┌──────────────────┐
    │ Game Academic    │         │ Game Academic    │
    │ Grade            │         │ Stream           │
    ├──────────────────┤         ├──────────────────┤
    │ PK: name         │────┐    │ PK: name         │
    │ grade_name       │    │    │ stream_name      │
    └──────────────────┘    │    └──────────────────┘
             │              │             │
             │              │             │
             ▼              ▼             │
    ┌────────────────────────────────┐   │
    │ Game Grade Valid Stream (Child)│◄──┘
    ├────────────────────────────────┤
    │ parent → Grade                 │
    │ stream → Stream                │
    └────────────────────────────────┘
             │
             │
             ▼
    ┌──────────────────────────────────────────────────────┐
    │ Game Academic Plan                                    │
    ├──────────────────────────────────────────────────────┤
    │ PK: name                                              │
    │ FK: grade → Game Academic Grade                       │
    │ FK: stream → Game Academic Stream                     │
    │ year: Data                                            │
    │ UNIQUE: (grade, stream, year)                        │
    └──────────────────────────────────────────────────────┘
             │
             │ has many
             ▼
    ┌──────────────────────────────────────────────────────┐
    │ Game Plan Subject (Child)                             │
    ├──────────────────────────────────────────────────────┤
    │ parent → Academic Plan                                │
    │ FK: subject → Game Subject                           │
    │ display_name: Data                                    │
    │ selection_type: Select (All Units | Specific Unit)   │
    │ FK: specific_unit → Game Unit                        │
    └──────────────────────────────────────────────────────┘


                               CONTENT HIERARCHY
                               ─────────────────

    ┌──────────────────┐
    │ Game Subject     │
    ├──────────────────┤
    │ PK: name         │◄───────────────────────────────┐
    │ title            │                                │
    │ icon             │                                │
    │ is_paid          │                                │
    │ is_published     │                                │
    └──────────────────┘                                │
             │                                          │
             │ has many                                 │
             ▼                                          │
    ┌──────────────────┐                                │
    │ Game Learning    │                                │
    │ Track            │                                │
    ├──────────────────┤                                │
    │ PK: name         │                                │
    │ track_name       │                                │
    │ FK: subject ─────┼────────────────────────────────┘
    │ is_default       │
    │ is_paid          │
    │ is_sold_separately│
    └──────────────────┘
             │
             │ has many
             ▼
    ┌──────────────────────────────────────────────────────┐
    │ Game Unit                                             │
    ├──────────────────────────────────────────────────────┤
    │ PK: name                                              │
    │ title                                                 │
    │ FK: subject → Game Subject                           │
    │ FK: learning_track → Game Learning Track             │
    │ structure_type: Select (Topic Based | Lesson Based)  │
    │ is_linear_topics                                      │
    │ is_free_preview                                       │
    └──────────────────────────────────────────────────────┘
             │
             │ has many (if Topic Based)
             ▼
    ┌──────────────────┐
    │ Game Topic       │
    ├──────────────────┤
    │ PK: name         │
    │ title            │
    │ FK: unit → Unit  │
    │ description      │
    │ is_linear        │
    │ is_free_preview  │
    └──────────────────┘
             │
             │ has many
             ▼
    ┌──────────────────────────────────────────────────────┐
    │ Game Lesson                                           │
    ├──────────────────────────────────────────────────────┤
    │ PK: name                                              │
    │ title                                                 │
    │ FK: unit → Game Unit                                 │
    │ FK: topic → Game Topic (NULL if Lesson Based)        │
    │ xp_reward                                             │
    │ is_published                                          │
    └──────────────────────────────────────────────────────┘
             │
             │ has many
             ▼
    ┌──────────────────────────────────────────────────────┐
    │ Game Stage (Child Table)                              │
    ├──────────────────────────────────────────────────────┤
    │ PK: name (auto-generated row name)                   │
    │ parent → Game Lesson                                 │
    │ title                                                 │
    │ type: Select (Reveal | Matching | Fill Blank | ...)  │
    │ config: JSON                                          │
    └──────────────────────────────────────────────────────┘


                               PLAYER DATA
                               ───────────

    ┌────────────────────────────────────────────────────────────┐
    │ Player Profile                                              │
    ├────────────────────────────────────────────────────────────┤
    │ PK: name                                                    │
    │ FK: user → User (unique)                                   │
    │ total_xp: Int                                               │
    │ gems_balance: Int                                           │
    │ FK: current_grade → Game Academic Grade                    │
    │ FK: current_stream → Game Academic Stream                  │
    │ academic_year: Data                                         │
    └────────────────────────────────────────────────────────────┘
             │
             │ has many
             ├──────────────────────────────────────────┐
             │                                          │
             ▼                                          ▼
    ┌────────────────────┐                 ┌────────────────────┐
    │ Player Memory      │                 │ Player Subject     │
    │ Tracker            │                 │ Score              │
    ├────────────────────┤                 ├────────────────────┤
    │ PK: name           │                 │ PK: name           │
    │ FK: player → User  │                 │ (SUB-SCR-user-subj)│
    │ question_id        │                 │ FK: player → User  │
    │ FK: subject        │                 │ FK: subject        │
    │ FK: topic          │                 │ total_xp           │
    │ stability (1-4)    │                 │ level              │
    │ last_review_date   │                 │ FK: season         │
    │ next_review_date   │                 └────────────────────┘
    │ FK: season         │
    └────────────────────┘
             │
             │
             ▼
    ┌────────────────────────────────────────────────────────────┐
    │ Gameplay Session                                            │
    ├────────────────────────────────────────────────────────────┤
    │ PK: name                                                    │
    │ FK: player → User                                          │
    │ lesson: Data/Link                                           │
    │ xp_earned: Int                                              │
    │ score: Int                                                  │
    │ raw_data: JSON                                              │
    │ creation: Datetime (auto)                                   │
    └────────────────────────────────────────────────────────────┘


                               ECONOMY
                               ───────

    ┌────────────────────────────────────────────────────────────┐
    │ Game Subscription Season                                    │
    ├────────────────────────────────────────────────────────────┤
    │ PK: name                                                    │
    │ start_date: Date                                            │
    │ end_date: Date  ◄──── CRITICAL: Controls all sub validity  │
    │ is_active: Check                                            │
    └────────────────────────────────────────────────────────────┘
             │
             │ referenced by
             ▼
    ┌────────────────────────────────────────────────────────────┐
    │ Game Sales Item                                             │
    ├────────────────────────────────────────────────────────────┤
    │ PK: name                                                    │
    │ item_name, description, price, discounted_price, image     │
    │ FK: linked_season → Season                                 │
    │ FK: target_grade → Grade                                   │
    │ target_streams → (Child: Game Item Target Stream)          │
    │ bundle_contents → (Child: Game Bundle Content)             │
    └────────────────────────────────────────────────────────────┘
             │
             │ purchased via
             ▼
    ┌────────────────────────────────────────────────────────────┐
    │ Game Purchase Request                                       │
    ├────────────────────────────────────────────────────────────┤
    │ PK: name                                                    │
    │ FK: user → User                                            │
    │ FK: sales_item → Sales Item                                │
    │ status: Select (Pending | Approved | Rejected)             │
    │ price, transaction_id                                       │
    └────────────────────────────────────────────────────────────┘
             │
             │ when approved, creates
             ▼
    ┌────────────────────────────────────────────────────────────┐
    │ Game Player Subscription                                    │
    ├────────────────────────────────────────────────────────────┤
    │ PK: name                                                    │
    │ FK: player → Player Profile                                │
    │ type: Select (Global Access | Specific)                    │
    │ FK: linked_season → Season                                 │
    │ status: Select (Active | Expired | Cancelled)              │
    │ access_items → (Child: Game Subscription Access)           │
    └────────────────────────────────────────────────────────────┘
```

---

## 7. Validation Rules and Edge Cases

### 7.1 Academic Setup Validations

| Rule | Validation | Error Handling |
|------|-----------|----------------|
| Valid Grade | Grade must exist in `Game Academic Grade` | Throw "Invalid Grade Selected" |
| Valid Stream for Grade | If stream provided, must exist in `Game Grade Valid Stream` with matching grade | Throw "Stream not valid for Grade" |
| Unique Plan | (grade, stream, year) must be unique | Database constraint |

### 7.2 Content Structure Validations

| Rule | Validation | Error Handling |
|------|-----------|----------------|
| Topic Required | If Unit is "Topic Based", Lesson MUST have topic | Auto-enforced in `game_lesson.py` |
| Topic Prohibited | If Unit is "Lesson Based", Lesson topic must be null | Auto-cleaned on save |
| Published Lessons Only | `get_lesson_details` checks `is_published = 1` | Throw "Lesson not found or access denied" |

### 7.3 Subscription Validations

| Rule | Validation | Error Handling |
|------|-----------|----------------|
| Season Validity | `Season.end_date >= CURDATE()` | Subscription treated as expired |
| No Duplicate Requests | Cannot have two pending requests for same item | Return "Request already pending" |
| Access Check Order | Unit free → Topic free → Subject free → Subscription | First match grants access |

### 7.4 SRS Edge Cases

| Scenario | Behavior |
|----------|----------|
| Student completed all topic reviews today | Fallback: Return 10 random questions from topic pool, award 10% XP |
| Memory tracker references deleted stage | Self-healing: Delete corrupt tracker, skip in review |
| AI distractor service unavailable | Fallback: Use local distractor pool from lesson content |
| Student hasn't finished any lessons in topic | "Review Topic" button hidden |

### 7.5 Store Edge Cases

| Scenario | Behavior |
|----------|----------|
| Student has Global subscription | Return empty store (nothing to buy) |
| Sales item targets different grade | Hide from store |
| Student already owns bundle contents | Hide the bundle |
| Student has pending request for item | Hide the item |

---

## 8. Important Business Rules and Assumptions

### 8.1 Access Control Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                   ACCESS CONTROL DECISION TREE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Is Unit.is_free_preview = true?                             │
│     └── YES → GRANT ACCESS (marketing teaser)                   │
│                                                                  │
│  2. Is Topic.is_free_preview = true? (if Topic Based)           │
│     └── YES → GRANT ACCESS                                      │
│                                                                  │
│  3. Is Subject.is_paid = false AND Track.is_paid = false?       │
│     └── YES → GRANT ACCESS (free content)                       │
│                                                                  │
│  4. Does user have active subscription?                         │
│     │                                                            │
│     ├── Global Access subscription?                             │
│     │   └── YES → GRANT ACCESS (full unlock)                    │
│     │                                                            │
│     ├── Subject Access for this subject?                        │
│     │   └── YES → GRANT ACCESS (unless Track.is_sold_separately)│
│     │                                                            │
│     └── Track Access for this specific track?                   │
│         └── YES → GRANT ACCESS                                  │
│                                                                  │
│  5. DEFAULT → DENY ACCESS (show locked_premium status)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 XP and Leveling System

**Level Formula**: `level = floor(0.07 * sqrt(total_xp)) + 1`

| XP Range | Level |
|----------|-------|
| 0 | 1 |
| 1-203 | 1 |
| 204-815 | 2 |
| 816-1834 | 3 |
| 1835-3264 | 4 |
| ... | ... |

**XP Sources**:
- Lesson completion: Based on `lesson.xp_reward`
- Review session: `(correct_count * 10) + (max_combo * 2)`

**Diminishing Returns (Topic Review)**:
- 1st review today: 100% XP
- 2nd review today: 50% XP
- 3rd+ review today: 10% XP

### 8.3 Streak Calculation

A streak counts consecutive days with at least one Gameplay Session. Calculation:
1. Get distinct activity dates (last 30 days)
2. If most recent is today or yesterday, start counting
3. Each consecutive day adds to streak
4. First gap breaks the chain

### 8.4 Key Assumptions

1. **Single Active Season**: Only one season can be `is_active = true` at a time
2. **Manual Payments**: The system supports manual/transfer payments requiring admin approval
3. **User = Player**: Each Frappe User has at most one Player Profile
4. **Arabic-First**: UI strings and lesson content are primarily in Arabic
5. **AI Optional**: AI distractor service is optional; system fully functional with local fallbacks
6. **Mobile-Ready API**: All APIs designed for mobile app consumption (JSON responses)

---

## 9. Diagrams Description (Flow/ERD Summary)

### 9.1 Data Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       DATA FLOW OVERVIEW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   [Student]                                                      │
│       │                                                          │
│       │ 1. Onboarding                                           │
│       ▼                                                          │
│   [Player Profile] ──────┬──────────────────────────────────────│
│       │                  │                                       │
│       │ 2. View          │ 3. Play                              │
│       │    Content       │    Lessons                           │
│       ▼                  ▼                                       │
│   [Academic Plan] ─→ [Subject/Unit/Topic/Lesson]                │
│       │                  │                                       │
│       │                  │ 4. Submit                            │
│       │                  ▼                                       │
│       │              [Gameplay Session]                         │
│       │                  │                                       │
│       │                  │ 5. Update Progress                   │
│       │                  ├─→ [Player Profile] (XP)              │
│       │                  ├─→ [Player Subject Score] (Level)     │
│       │                  └─→ [Player Memory Tracker] (SRS)      │
│       │                                                          │
│       │ 6. Review                                               │
│       ▼                                                          │
│   [Memory Tracker] ──→ [Review Session] ──→ [SRS Update]        │
│                                                                  │
│   [Student]                                                      │
│       │ 7. Purchase                                             │
│       ▼                                                          │
│   [Store Items] ──→ [Purchase Request] ──→ [Admin Approval]     │
│                              │                                   │
│                              ▼                                   │
│                      [Player Subscription]                       │
│                              │                                   │
│                              ▼                                   │
│                      [Access Granted]                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 SRS State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                     SRS STABILITY STATE MACHINE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ┌─────────────────┐                          │
│         ┌─────────│   STABILITY 1   │◄────────────┐             │
│         │   Wrong │   (New/Failed)  │    Wrong    │             │
│         │         │   Next: +1 day  │             │             │
│         │         └────────┬────────┘             │             │
│         │                  │                      │             │
│         │         Correct  │                      │             │
│         │         (slow)   │                      │             │
│         │                  ▼                      │             │
│         │         ┌─────────────────┐             │             │
│         └────────►│   STABILITY 2   │─────────────┤             │
│                   │   (Learning)    │    Wrong    │             │
│                   │   Next: +3 days │             │             │
│                   └────────┬────────┘             │             │
│                            │                      │             │
│                   Correct  │                      │             │
│                   (normal) │                      │             │
│                            ▼                      │             │
│                   ┌─────────────────┐             │             │
│         ┌────────│   STABILITY 3   │─────────────┤             │
│         │        │ (Intermediate)  │    Wrong    │             │
│         │        │  Next: +7 days  │             │             │
│         │        └────────┬────────┘             │             │
│         │                 │                      │             │
│         │        Correct  │                      │             │
│         │        (fast)   │                      │             │
│         │        +2 bonus ▼                      │             │
│         │        ┌─────────────────┐             │             │
│         └───────►│   STABILITY 4   │─────────────┘             │
│                  │   (Mastered)    │                            │
│                  │  Next: +14 days │                            │
│                  └─────────────────┘                            │
│                                                                  │
│  Speed Bonuses:                                                 │
│  - < 2 seconds (fast): stability += 2                          │
│  - 2-6 seconds (normal): stability += 1                        │
│  - > 6 seconds (slow): stability unchanged                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New Student Onboarding (Priority: P1)

A new student registers for Memora, selects their academic grade and stream (if applicable), and is directed to their personalized subject map showing only relevant content.

**Why this priority**: This is the entry point for all users. Without successful onboarding, no other features can be used.

**Independent Test**: Can be fully tested by registering a new user account and completing the grade/stream selection. Delivers value by showing the personalized subject list.

**Acceptance Scenarios**:

1. **Given** a new user without a Player Profile, **When** they access the app, **Then** they are prompted to complete onboarding
2. **Given** the onboarding screen, **When** user selects a grade that has no streams, **Then** stream selection is skipped
3. **Given** a grade with multiple streams, **When** user selects the grade, **Then** only valid streams for that grade are shown
4. **Given** completed onboarding, **When** user views subjects, **Then** only subjects from their Academic Plan are displayed

---

### User Story 2 - Complete a Learning Lesson (Priority: P1)

A student navigates to a lesson, completes all interactive stages (Reveal, Matching, Quiz, etc.), and receives XP rewards while their progress is tracked for spaced repetition.

**Why this priority**: This is the core learning experience. Without lesson completion, the app provides no educational value.

**Independent Test**: Can be fully tested by playing any published lesson and verifying XP is awarded and Memory Trackers are created.

**Acceptance Scenarios**:

1. **Given** an available lesson, **When** user completes all stages correctly, **Then** XP is added to their profile
2. **Given** a lesson with Reveal stages, **When** user views them, **Then** Memory Tracker entries are created for each highlighted word
3. **Given** lesson completion, **When** viewing the map, **Then** the lesson shows as "completed" status

---

### User Story 3 - Review Session with SRS (Priority: P1)

A student initiates a review session (daily or topic-focused), answers quiz cards generated from previously learned content, and sees their memory stability improve based on performance.

**Why this priority**: SRS is a core differentiator. It optimizes learning retention and drives daily engagement.

**Independent Test**: Can be fully tested by completing lessons first, then initiating a review session and verifying stability changes.

**Acceptance Scenarios**:

1. **Given** items due for review, **When** user opens review, **Then** quiz cards are generated from Memory Tracker items
2. **Given** a correct fast answer (<2s), **When** submitted, **Then** stability increases by 2 (max 4)
3. **Given** an incorrect answer, **When** submitted, **Then** stability resets to 1
4. **Given** all topic items reviewed correctly today, **When** user requests another review, **Then** fallback mode provides random items at 10% XP

---

### User Story 4 - Purchase Content Access (Priority: P2)

A student browses the store, selects a paid bundle, submits a purchase request, and gains access to locked content after admin approval.

**Why this priority**: Monetization enables the business model. Important but users can explore free content first.

**Independent Test**: Can be fully tested by creating a purchase request and having an admin approve it, then verifying content access.

**Acceptance Scenarios**:

1. **Given** a student without subscriptions, **When** viewing paid content, **Then** it shows as "locked_premium"
2. **Given** the store page, **When** student views items, **Then** only items matching their grade/stream are shown
3. **Given** approved subscription, **When** accessing previously locked content, **Then** it becomes available

---

### User Story 5 - View Profile and Progress (Priority: P2)

A student views their profile showing level, XP progress, streak, weekly activity, and mastery breakdown (new/learning/mature items).

**Why this priority**: Progress visibility drives motivation and engagement. Secondary to core learning.

**Independent Test**: Can be fully tested by viewing the profile page and verifying all stats display correctly.

**Acceptance Scenarios**:

1. **Given** a player with activity, **When** viewing profile, **Then** level is calculated correctly from XP
2. **Given** consecutive days of activity, **When** viewing profile, **Then** streak shows the correct count
3. **Given** memory trackers with various stabilities, **When** viewing mastery, **Then** counts are categorized correctly (1=new, 2=learning, 3-4=mature)

---

### Edge Cases

- What happens when a student's academic plan is missing? → Returns empty subject list, prompts to contact admin
- What happens when subscription season expires mid-lesson? → Current session completes, next request denies access
- What happens when AI distractor service times out? → Falls back to local distractor pool from lesson content
- What happens when a Memory Tracker references a deleted stage? → Self-healing: tracker is deleted, skipped in review
- What happens when student plays 4+ review sessions on same topic in one day? → 10% XP multiplier applied

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to register and create accounts through Frappe authentication
- **FR-002**: System MUST guide new users through academic profile setup (grade, stream selection)
- **FR-003**: System MUST display only subjects matching the user's Academic Plan
- **FR-004**: System MUST support two content structures: Topic Based (clusters) and Lesson Based (paths)
- **FR-005**: System MUST track lesson completion and award XP to Player Profile
- **FR-006**: System MUST create Memory Tracker entries for learnable content (Reveal highlights, Matching pairs)
- **FR-007**: System MUST calculate next review dates using stability-based SRS algorithm
- **FR-008**: System MUST generate review sessions by converting stored content to quiz format
- **FR-009**: System MUST support AI-generated distractors with local fallback
- **FR-010**: System MUST enforce financial access control (free preview → free content → subscription)
- **FR-011**: System MUST support Global and Specific subscription types
- **FR-012**: System MUST validate subscription against linked season's end_date, not purchase date
- **FR-013**: System MUST support manual purchase request workflow with admin approval
- **FR-014**: System MUST calculate and display leaderboards (global and per-subject)
- **FR-015**: System MUST track daily streaks based on Gameplay Session activity
- **FR-016**: System MUST provide daily quests with review tasks and XP goals
- **FR-017**: System MUST apply diminishing XP returns for repeated topic reviews (100% → 50% → 10%)
- **FR-018**: System MUST support linear progression enforcement (topics and lessons)

### Key Entities

- **Player Profile**: Central user record linking identity, academic context, and progression
- **Academic Plan**: Curriculum mapping connecting (grade, stream, year) to specific subjects/units
- **Game Lesson**: Playable content container with interactive stages (Reveal, Matching, Quiz, etc.)
- **Memory Tracker**: SRS record tracking stability and next review date for each learned item
- **Subscription**: Access grant with season-based validity and content-specific permissions

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New users can complete onboarding (grade/stream selection) within 60 seconds
- **SC-002**: Students can navigate from subject selection to lesson start within 30 seconds
- **SC-003**: Lesson stages load and respond to interactions within 2 seconds
- **SC-004**: Review sessions generate appropriate quiz content with 95% accuracy (correct questions match stored content)
- **SC-005**: SRS scheduling correctly spaces reviews to maximize retention (measured by mastery progression over time)
- **SC-006**: Purchase approval workflow completes within one business day of payment verification
- **SC-007**: Daily active users maintain average streak of 5+ days
- **SC-008**: Leaderboard queries return within 1 second for up to 10,000 users
- **SC-009**: 90% of locked content correctly reflects user's subscription status
- **SC-010**: System handles 1,000 concurrent review session submissions without data loss
