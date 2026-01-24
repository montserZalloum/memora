# 🏗️ Data Schema Design Document (Data Schema PRD) - Final Version
**Project:** Memora
**Platform:** Frappe Framework (Backend)
**Naming Prefix:** `Memora`

---

## 1. Standard Mixins
*These fields must be added to all hierarchical content DocTypes (Subject, Track, Unit, Topic, Lesson) to standardize criteria.*

| Field Name | Type | Description & Goal |
| :--- | :--- | :--- |
| `is_published` | Check | **Emergency Stop:** If disabled, the item and all its children disappear immediately from the API. |
| `is_free_preview` | Check | **Marketing:** To identify free content (Hooks). |
| `sort_order` | Int | **Sorting:** For manual control of item display order (Index: Enabled). |
| `image` | Attach Image | Thumbnail. |
| `description` | Small Text | Short description appearing in the interface. |

---

## 2. Educational Content (Content Hierarchy)
*The tree structure of the scientific material (free from any financial links).*

### 2.1. `Memora Subject`
*   **title** (Data): Subject name (Math, Physics).
*   **color_code** (Data/Color): Visual identity color.

### 2.2. `Memora Track`
*   **parent_subject** (Link: `Memora Subject`): The subject it belongs to **(Index)**.
*   **is_sold_separately** (Check): *Field for display only (UI Hint)*; tells the frontend that this track might be locked differently than the parent subject.

### 2.3. `Memora Unit`
*   **parent_track** (Link: `Memora Track`): The track it belongs to **(Index)**.
*   **badge_image** (Attach Image): Badge image upon completion.

### 2.4. `Memora Topic`
*   **parent_unit** (Link: `Memora Unit`): The unit it belongs to **(Index)**.

### 2.5. `Memora Lesson`
*   **parent_topic** (Link: `Memora Topic`): The topic it belongs to **(Index)**.
*   **stages** (Table Field): Stages table (Child Table: `Memora Lesson Stage`).

### 2.6. `Memora Lesson Stage` (Child Table)
*Used inside `Memora Lesson`.*
*   **title** (Data): Stage title (Optional).
*   **type** (Select): (Video, Question, Text, Interactive).
*   **config** (JSON): A field storing all stage data (video link, question text, options) in JSON format to reduce tables.

---

## 3. Planning & Products (Planning & Grants)
*The logic layer connecting content to the student and the financial system.*

### 3.1. `Memora Academic Plan`
*   **title** (Data): Plan name (Tawjihi Scientific 2010).
*   **season** (Link: `Memora Season`): The academic season **(Index)**.
*   **stream** (Link: `Memora Stream`): The stream/major **(Index)**.
*   **subjects** (Table Field): Included subjects (Child Table: `Memora Plan Subject`).
*   **overrides** (Table Field): Special modifications (Child Table: `Memora Plan Override`).

### 3.2. `Memora Plan Subject` (Child Table)
*   **subject** (Link: `Memora Subject`): The subject.
*   **sort_order** (Int): Its order in the plan.

### 3.3. `Memora Plan Override` (Child Table)
*   **target_doctype** (Select): (Track, Unit, Topic, Lesson).
*   **target_name** (Dynamic Link): Name of the specific element.
*   **action** (Select): (Hide, Rename, Set Free, Set Sold Separately).
*   **override_value** (Data): The new value.

### 3.4. `Memora Product Grant` (New 🆕)
*   **item_code** (Link: `Item`): ERPNext product (that is being purchased).
*   **academic_plan** (Link: `Memora Academic Plan`): The target plan **(Index)**.
*   **grant_type** (Select): (Full Plan Access, Specific Components).
*   **unlocked_components** (Table Field): (Child Table: `Memora Grant Component`).
    *   *Note:* If the type is Full Plan, leave the table empty.

### 3.5. `Memora Grant Component` (Child Table)
*   **target_doctype** (Select): (Subject, Track, Unit).
*   **target_name** (Dynamic Link): The element to be unlocked upon purchasing the product.

---

## 4. Player Profile
*Separating game data from user data.*

### 4.1. `Memora Player Profile`
*   **user** (Link: `User`): Link to the system account **(Index - Unique)**.
*   **display_name** (Data).
*   **avatar** (Attach Image).
*   **current_plan** (Link: `Memora Academic Plan`): The active plan **(Index)**.
*   **devices** (Table Field): Trusted devices (Child Table: `Memora Player Device`).

### 4.2. `Memora Player Device` (Child Table)
*   **device_id** (Data): Unique device identifier.
*   **device_name** (Data).
*   **is_trusted** (Check).

### 4.3. `Memora Player Wallet`
*High Velocity Data.*
*   **player** (Link: `Memora Player Profile`): **(Index - Unique)**.
*   **total_xp** (Int).
*   **current_streak** (Int).
*   **last_played_at** (Datetime): To calculate Streak and churn.

---

## 5. Engine & Logs
*Big Data tables.*

### 5.1. `Memora Interaction Log`
*Write-Only.*
*   **player** (Link: `Memora Player Profile`): **(Index)**.
*   **academic_plan** (Link: `Memora Academic Plan`): **(Index)**.
*   **question_id** (Data): **(Index)** Question ID (from JSON).
*   **student_answer** (Text): The selected answer.
*   **correct_answer** (Text): The correct answer at the time of solving.
*   **is_correct** (Check).
*   **time_taken** (Float): In seconds.
*   **timestamp** (Datetime): Time of solving.

### 5.2. `Memora Memory State` (FSRS)
*Read-Optimized.*
*   **player** (Link: `Memora Player Profile`): **(Index)**.
*   **question_id** (Data): **(Index)**.
*   **stability** (Float): Stability metric (FSRS).
*   **difficulty** (Float): Difficulty metric (FSRS).
*   **next_review** (Datetime): Date of next review **(Index - Critical)**.
*   **state** (Select): (New, Learning, Review, Relearning).

---

## 6. Commerce & Subscriptions (Commerce)
*Isolated financial handling layer.*

### 6.1. `Memora Subscription Transaction`
*   **naming_series**: `SUB-TX-.YYYY.-`
*   **player** (Link: `Memora Player Profile`): **(Index)**.
*   **transaction_type** (Select): (Purchase, Renewal, Upgrade).
*   **payment_method** (Select): (Payment Gateway, Manual/Admin, Voucher).
*   **status** (Select): (Pending Approval, Completed, Failed, Cancelled).
*   **transaction_id** (Data): Reference number from the gateway (Stripe ID / CliQ Ref).
*   **amount** (Currency).
*   **receipt_image** (Attach Image): For manual transfers.
*   **related_grant** (Link: `Memora Product Grant`): **(Index)** The privilege purchased (to activate it for the student).
*   **erpnext_invoice** (Link: `Sales Invoice`): *Read Only* - For the invoice posted later.

---

## 7. Settings (Configuration)

### 7.1. `Memora Season`
*   **title** (Data): (Generation 2007).
*   **is_published** (Check).
*   **start_date** (Date).
*   **end_date** (Date): To control the validity duration of subscriptions linked to the season.

### 7.2. `Memora Stream`
*   **title** (Data): (Scientific, Literary, Industrial).

---

### 📝 Appendix: Indexing Strategy
To ensure system stability under a load of 100,000 users, you **must** enable the Database Index in Frappe exclusively for the following fields:

1.  **The Tree:** `parent_subject`, `parent_track`, `parent_unit`, `parent_topic`.
2.  **The Player:** `player` in Logs, Wallet, and Transaction tables.
3.  **The Algorithm:** `next_review` in the Memory State table (The most important index in the system).
4.  **Plans:** `season`, `stream`, `academic_plan`.
5.  **Sales:** `item_code` in Product Grant.