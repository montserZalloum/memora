🏗️ **Winston** here.

Here is the **ARCHITECT.md** file. This document serves as the "Constitution" for your project. It contains every design decision, data structure, and algorithm logic we have agreed upon.

Save this file in the root of your repository. It will be the reference point for you and any developer working on the project.

***

# ARCHITECT.md

> **Project:** Gamified Education Platform (Code Name: *The Jordan Project*)  
> **Version:** 1.0.0  
> **Status:** Active Development  
> **Architect:** Winston
> **APP Name:** memora

---

## 1. Executive Summary
This project is a **Mobile-First, Gamified Learning Management System (LMS)** designed to feel like a high-end mobile game (e.g., Duolingo).

**Core Philosophy:**
1.  **Juicy UI/UX:** The interface must feel alive (animations, haptics, instant feedback).
2.  **Offline-Optimized:** Users can play a full lesson with spotty internet; data syncs in batches.
3.  **Data-Driven:** An invisible "Brain" (SRS Algorithm) tracks every interaction to personalize learning.
4.  **Generic Content:** The engine is content-agnostic (History, Math, Science) controlled by a flexible Admin Panel.

---

## 2. Technology Stack

### Backend (The Brain & Factory)
*   **Framework:** **Frappe Framework** (Python).
*   **Database:** MariaDB (Standard Frappe DB).
*   **Role:**
    *   Content Management (CMS) for creating lessons.
    *   User Authentication & Session Management.
    *   SRS Algorithm Execution.
    *   Long-term Data Storage (Logs/Profiles).

### Frontend (The Player)
*   **Framework:** **React.js** (Vite).
*   **Language:** TypeScript.
*   **Styling:** Tailwind CSS (Mobile-First approach).
*   **State Management:** **Zustand** (Handling session state, hearts, XP, and retry queues).
*   **Integration:** Hosted inside Frappe’s `www` folder as a Single Page Application (SPA).

### Analytics
*   **Transactional:** Custom Frappe DocTypes (`Gameplay Session`).
*   **Behavioral:** **Firebase Analytics** (Screen views, drop-offs, device stats).

---

## 3. Data Architecture (Schema)

We strictly use **Game/Player** nomenclature. We avoid "LMS/Student/Academy" to maintain the gamification psychology.

### A. Content Structure (Static)

| DocType Name | Type | Description | Key Fields |
| :--- | :--- | :--- | :--- |
| **`Game Subject`** | Master | e.g., "Jordan History" | `title`, `icon`, `is_published` |
| **`Game Unit`** | Master | e.g., "The Foundation" | `subject`, `title`, `order` |
| **`Game Lesson`** | Master | e.g., "Independence Day" | `unit`, `title`, `xp_reward` |
| **`Game Stage`** | **Child** | The actual gameplay screens | `type` (Select), `config` (JSON Blob) |

**The `config` Field Protocol:**
This field stores the raw JSON that the React frontend interprets.
*   *Example (Matching):* `{"pairs": [{"l": "1946", "r": "Independence"}]}`
*   *Example (Reveal):* `{"image": "img.png", "sentence": "...", "highlights": [...]}`

### B. User Data (Dynamic)

| DocType Name | Purpose | Key Fields |
| :--- | :--- | :--- |
| **`Player Profile`** | Gamification State | `user` (Link), `total_xp`, `gems_balance`, `current_streak` |
| **`Player Memory Tracker`** | The SRS Brain | `player`, `question_atom` (ID), `stability`, `next_review_date` |
| **`Gameplay Session`** | Analytics Log | `player`, `lesson`, `score`, `duration`, `raw_data` (JSON) |

---

## 4. The "Brain" Algorithm (SRS & Logic)

The system does not ask "Easy/Hard". It infers difficulty based on **Behavioral Metrics**.

### Logic Flow
1.  **Frontend Capture:** React records `duration_ms` (Time to answer) and `attempts_count`.
2.  **Inference (Backend):**
    *   **FAIL:** `attempts > 1` (Incorrect first try) → **Queue for Immediate Retry** (in session).
    *   **HARD:** `Correct` AND `duration > 5s` → **Review in 2 days**.
    *   **GOOD:** `Correct` AND `duration 2-5s` → **Review in 4 days**.
    *   **EASY:** `Correct` AND `duration < 2s` → **Review in 7 days**.

### The "Atom" Approach
We track performance on the **Question/Fact Level** (Atoms), not the Lesson Level.
*   *Effect:* If a player fails "Date of Independence" inside a generic lesson, only that specific fact is scheduled for review later.

---

## 5. Data Synchronization Strategy

We use an **Optimistic UI + Batching** strategy to ensure server stability and offline resilience.

### The Workflow
1.  **Start:** App fetches Lesson JSON (`GET /api.../get_lesson_content`).
2.  **Play (Offline-Capable):**
    *   Zustand Store records every tap, error, and timer locally.
    *   **Short-term Loop:** If player fails, the question is pushed to a local `RetryQueue` array.
    *   The lesson **cannot** be finished until the `RetryQueue` is empty.
3.  **Finish:**
    *   App compiles a **Single JSON Payload**.
    *   Sends `POST /api.../submit_session`.
4.  **Server Process:**
    *   Updates `Player Profile` (Add XP/Gems).
    *   Updates `Memory Tracker` (Schedule future reviews).
    *   Archives `Gameplay Session`.

### API Contract (The Payload)

```json
{
  "session_meta": {
    "lesson_id": "LESSON-001",
    "start_timestamp": "ISO-8601",
    "end_timestamp": "ISO-8601",
    "device_info": "Mobile/iOS"
  },
  "gamification_results": {
    "xp_earned": 50,
    "gems_collected": 10
  },
  "interactions": [
    {
      "question_id": "ATOM-101",
      "type": "MATCHING",
      "attempts_count": 1,
      "duration_ms": 3400,
      "is_final_outcome_correct": true
    },
    {
      "question_id": "ATOM-102",
      "attempts_count": 2, 
      "duration_ms": 12000,
      "mistake_details": "wrong_selection"
    }
  ]
}
```

---

## 6. Frontend Architecture (React)

### Directory Structure
```
/src
  /components
    /atoms       (Buttons, Icons)
    /molecules   (ProgressBar, HeartContainer)
    /stages      (RevealStage, MatchingStage, QuizStage)
  /store
    useGameStore.ts  (Zustand: Handles logic, queue, and score)
  /hooks
    useSound.ts      (Audio system)
    useSRS.ts        (Local logic)
  /types
    index.ts         (Shared Interfaces)
```

### State Management (Zustand)
The `useGameStore` is the single source of truth during gameplay.
*   **State:** `currentStageIndex`, `hearts`, `xp`, `historyLog`, `retryQueue`.
*   **Actions:** `submitAnswer()`, `nextStage()`, `loseHeart()`, `retryFailedQuestions()`.

---

## 7. Deployment & Ops

*   **Hosting:** Frappe Cloud or Self-Hosted VPS.
*   **Portal Mode:**
    *   File: `my_app/www/play.html`
    *   Context Override: `context.no_header = 1`, `context.no_footer = 1`.
    *   This ensures the React App takes over the entire screen (SPA feel).

---

> **Signed:** Winston, System Architect.  
> **Date:** January 8, 2026.