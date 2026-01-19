# PRD: SRS High-Performance & Scalability Architecture
**Target:** Handling 1B+ records with <100ms response time.
**Technologies:** Frappe (MariaDB), Redis (Sorted Sets), Python Background Jobs.

---

## 1. الملخص التنفيذي (Executive Summary)
الهدف هو إعادة هندسة "محرك الذاكرة" (SRS Engine) لضمان عدم انهيار قاعدة البيانات عند وصول عدد السجلات إلى المليارات. الحل يعتمد على **فصل العمليات**:
1.  **الاستعلام السريع (Hot Reads):** يتم عبر **Redis** (في الذاكرة).
2.  **التخزين الهيكلي (Storage):** يتم عبر **MariaDB** مع تقنية **Partitioning**.
3.  **الكتابة (Writes):** تتم بشكل غير متزامن (Asynchronous) لعدم تعطيل واجهة المستخدم.

---

## 2. تعديلات قاعدة البيانات (DocTypes & Schema)

### 2.1 تعديل: Game Subscription Season
نحتاج لإضافة حقول للتحكم في التقسيم (Partitioning) والأرشفة.

| Field Label | Field Name | Type | Options / Note |
|:---|:---|:---|:---|
| **Is Active** | `is_active` | Check | يحدد الموسم الحالي |
| **Partition Created** | `partition_created` | Check | (Hidden) يحدد هل تم إنشاء قسم في الداتابيس لهذا الموسم أم لا |
| **Enable Redis Sync** | `enable_redis` | Check | لتفعيل/تعطيل المزامنة مع Redis لهذا الموسم |
| **Auto Archive** | `auto_archive` | Check | لتفعيل وظيفة الأرشفة الليلية التلقائية |

**Business Logic:**
*   عند إنشاء موسم جديد وحفظه، يجب أن يعمل `Hook` يقوم بتنفيذ كود SQL لإنشاء Partition جديد في جداول الذاكرة.

### 2.2 تعديل وتحسين: Player Memory Tracker (الجدول العملاق)
هذا الجدول سيحمل البيانات الضخمة.

| Field Label | Field Name | Type | Index? | Note |
|:---|:---|:---|:---|:---|
| **Player** | `player` | Link (User) | Yes | المستخدم |
| **Season** | `season` | Link (Season) | Yes | **مفتاح التقسيم (Partition Key)** |
| **Question ID** | `question_id` | Data | No | معرف السؤال (Stage ID) |
| **Next Review** | `next_review_date` | Datetime | No | (لسنا بحاجة لفهرسة هذا الحقل بفضل Redis) |
| **Stability** | `stability` | Float | No | مستوى الحفظ (0-4) |
| **Last Review** | `last_review_date` | Datetime | No | تاريخ آخر مراجعة |
| **Subject** | `subject` | Link | No | للفلترة الاختيارية |

**⚠️ متطلب تقني حرج (Backend Implementation):**
لا تعتمد على فهارس Frappe العادية. يجب تطبيق **Table Partitioning** على مستوى قاعدة البيانات مباشرة.
*   **Strategy:** List Partitioning by `season` column.
*   **SQL Logic (للمبرمج):**
    ```sql
    ALTER TABLE `tabPlayer Memory Tracker` 
    PARTITION BY LIST COLUMNS(season) (
        PARTITION p_season_2025 VALUES IN ('SEASON-2025-NAME'),
        PARTITION p_season_2026 VALUES IN ('SEASON-2026-NAME')
    );
    ```

### 2.3 جديد: Archived Memory Tracker
نسخة طبق الأصل عن الجدول السابق، ولكن يستخدم لتخزين البيانات "الميتة".

| Field Label | Field Name | Type | Note |
|:---|:---|:---|:---|
| **All Fields** | (Same as above) | ... | نفس حقول الجدول السابق تماماً |
| **Archived Date** | `archived_at` | Datetime | متى تمت الأرشفة |

---

## 3. هندسة Redis (استراتيجية السرعة القصوى)

سنستخدم **Redis Sorted Sets (ZSET)** لأنها تسمح بجلب البيانات بناءً على الوقت (Score) بسرعة خيالية.

### 3.1 هيكلية البيانات في Redis
*   **Key Format:** `srs:{user_id}:{season_id}`
    *   مثال: `srs:student1@email.com:SEASON-2026`
*   **Member (Value):** `question_id` (رقم السؤال).
*   **Score:** `next_review_timestamp` (تاريخ المراجعة بصيغة Unix Timestamp).

### 3.2 العمليات (Redis Operations)

#### أ. إضافة/تحديث سؤال (عند حل الطالب للسؤال):
```redis
ZADD srs:student1:SEASON-2026  1737380000 "PHYSICS-Q-101"
```
*(المعنى: يا سؤال 101، اذهب إلى آخر الطابور، وموعدك القادم هو التوقيت 1737380000)*

#### ب. جلب أسئلة المراجعة (عند ضغط زر "مراجعة"):
```redis
ZRANGEBYSCORE srs:student1:SEASON-2026  -inf  (CURRENT_TIMESTAMP)  LIMIT 0 20
```
*(المعنى: أعطني أول 20 سؤالاً موعدهم أقل من أو يساوي "الآن" - أي مستحقين للمراجعة)*

---

## 4. تدفق البيانات (Data Flow Logic)

### 4.1 مسار الكتابة (Submit Session Flow)
عندما ينتهي الطالب من درس أو مراجعة:

1.  **الواجهة (Frontend):** ترسل البيانات للـ API.
2.  **API (Server):**
    *   **خطوة 1 (فورية):** تحديث **Redis** بالموعد الجديد للأسئلة التي تمت مراجعتها (باستخدام `ZADD`).
    *   **خطوة 2 (فورية):** إرجاع رد `200 OK` للطالب (تم الحفظ).
    *   **خطوة 3 (خلفية):** إرسال البيانات إلى **Background Queue** (باستخدام `frappe.enqueue`).
3.  **Worker (Background Job):**
    *   يستلم البيانات من الطابور.
    *   يقوم بعمل `Insert` أو `Update` في جدول **MariaDB** (`Player Memory Tracker`).
    *   *الفائدة:* المستخدم لا ينتظر قاعدة البيانات حتى تنتهي من الكتابة.

### 4.2 مسار القراءة (Get Review Session Flow)
عندما يطلب الطالب بدء مراجعة:

1.  **API (Server):**
    *   **خطوة 1:** يتصل بـ **Redis**.
    *   **خطوة 2:** ينفذ `ZRANGEBYSCORE` لجلب الـ `question_ids` المستحقة.
    *   **خطوة 3:** (اختياري وسريع) يجلب نصوص الأسئلة (Content) من جدول `Game Stage` بناءً على الـ IDs التي عادت من Redis.
    *   *ملاحظة:* لم نقم بأي عملية بحث معقدة (`WHERE next_review_date < now`) في قاعدة البيانات الضخمة.

---

## 5. الأرشفة التلقائية (Auto-Maintenance)

يتم إنشاء **Scheduled Job** في ملف `hooks.py` يعمل يومياً (Daily).

**الخوارزمية:**
1.  جلب المواسم التي فيها `auto_archive = 1`.
2.  تكرار المواسم:
    *   نقل البيانات من `Player Memory Tracker` (Partition الخاص بالموسم القديم) إلى `Archived Memory Tracker`.
    *   حذف البيانات من الجدول الأصلي.
    *   (خطوة متقدمة): حذف مفاتيح هذا الموسم من **Redis** لتوفير الرام (`DEL srs:*:{old_season}`).

---

## 6. متطلبات التنفيذ للمطور (Action Plan)

سلم هذه القائمة للمبرمج ليبدأ التنفيذ:

1.  **Install Redis:** التأكد من تثبيت Redis وتفعيل `bench setup redis`.
2.  **Schema Migration:**
    *   تعديل DocTypes حسب الجدول أعلاه.
    *   كتابة `Patch` لتطبيق الـ Partitioning على الجدول الموجود حالياً (تحذير: يجب أخذ Backup قبل هذه الخطوة).
3.  **Implement Wrapper:** كتابة `class SRSRedisManager` في الباك اند لتسهيل التعامل مع Redis (وظائف: `add_item`, `get_due_items`, `remove_item`).
4.  **Refactor APIs:**
    *   تعديل `submit_session` لتستخدم `frappe.enqueue`.
    *   تعديل `get_review_session` لتقرأ من Redis أولاً.
5.  **Testing:** إجراء اختبار تحميل (Load Test) بإدخال مليون سجل وهمي ومراقبة سرعة استجابة الـ API.