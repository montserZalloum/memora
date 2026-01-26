# وثيقة متطلبات المنتج (PRD): نظام توليد وتوزيع المحتوى الذري
**المشروع:** Memora Learning Platform  
**الدور:** JSON Content Structure & CDN Export System  
**الحالة:** المسودة التقنية النهائية (النسخة المعتمدة)

---

## 1. الهدف العام (High-Level Goal)
بناء نظام لتوليد ملفات JSON ثابتة (Static) تعكس هيكل المحتوى الأكاديمي مع تطبيق قواعد الصلاحيات والـ Overrides الخاصة بكل خطة دراسية، وتوزيعها عبر مسارات مادية محسنة لضمان سرعة تحميل فائقة (Sub-second loading) لآلاف الدروس.

---

## 2. الهيكلية المادية للتخزين (Physical Storage Architecture)

يتم تنظيم الملفات هرمياً لضمان عزل البيانات وتقليل حجم الملفات التي يحملها الطالب:

```text
/public/memora_content/
  ├── /plans/
  │    └── /{plan_id}/                   (مجلد خاص بكل خطة دراسية)
  │         ├── manifest.json            (الفهرس العام للمواد)
  │         ├── /subjects/
  │         │    ├── {sub_id}_h.json     (Hierarchy: الهيكل حتى مستوى التوبيك)
  │         │    └── {sub_id}_b.json     (BitMap: خريطة البتات للمحرك - مخفي)
  │         └── /topics/
  │              └── {topic_id}.json     (قائمة دروس التوبيك المخصصة للخطة)
  └── /lessons/
       └── {lesson_id}.json              (محتوى الدرس الخام - Stages)
```

---

## 3. مواصفات الملفات (JSON Contracts)

### 3.1 فهرس الخطة (`manifest.json`)
*   **المسار:** `/plans/{plan_id}/manifest.json`
*   **الوظيفة:** عرض قائمة المواد المتاحة للطالب في خطته.

```json
{
  "plan_id": "PLAN-001",
  "title": "توجيهي علمي 2007",
  "version": 1706275200,
  "subjects": [
    {
      "id": "SUB-MATH",
      "title": "الرياضيات",
      "image": "math_icon.png",
      "color": "#FF5733",
      "access_level": "paid",
      "required_item": "ITEM-MATH-01",
      "url": "subjects/SUB-MATH_h.json"
    }
  ]
}
```

### 3.2 هيكل المادة المخصص (`{subject_id}_h.json`)
*   **المسار:** `/plans/{plan_id}/subjects/{subject_id}_h.json`
*   **الوظيفة:** رسم شريان المادة (Tracks -> Units -> Topics).

```json
{
  "id": "SUB-MATH",
  "title": "الرياضيات",
  "description": "منهاج الرياضيات المطور",
  "access_level": "paid",
  "is_linear": true,
  "tracks": [
    {
      "id": "TR-01",
      "title": "الجبر",
      "is_linear": false,
      "units": [
        {
          "id": "UNIT-01",
          "title": "الأسس",
          "description": "شرح الأسس",
          "is_linear": true,
          "access_level": "free_preview",
          "topics": [
            {
              "id": "TOP-101",
              "title": "قوانين الأسس",
              "is_linear": true,
              "access_level": "free_preview",
              "url": "../../topics/TOP-101.json"
            }
          ]
        }
      ]
    }
  ]
}
```

### 3.3 دروس التوبيك المخصصة (`{topic_id}.json`)
*   **المسار:** `/plans/{plan_id}/topics/{topic_id}.json`
*   **الوظيفة:** عرض قائمة الدروس الخمسين داخل التوبيك.

```json
{
  "topic_id": "TOP-101",
  "title": "قوانين الأسس",
  "is_linear": true,
  "access_level": "free_preview",
  "lessons": [
    {
      "id": "LES-5001",
      "title": "مقدمة",
      "bit_index": 45,
      "url": "../../../lessons/LES-5001.json"
    }
  ]
}
```

### 3.4 محتوى الدرس الخام (`{lesson_id}.json`)
*   **المسار:** `/lessons/{lesson_id}.json`
*   **الوظيفة:** تشغيل المراحل (Stages) وبيانات الـ FSRS.

```json
{
  "lesson_id": "LES-5001",
  "title": "مقدمة",
  "stages": [
    {
      "id": "STG-01",
      "type": "MCQ",
      "weight": 1.5,
      "target_time": 20,
      "is_skippable": false,
      "data": { "question": "...", "options": [], "answer": "..." }
    }
  ]
}
```

---

## 4. محرك معالجة الـ Overrides (The Processing Engine)

تتم معالجة الملفات في المجلدات الخاصة بالـ `plans/` بناءً على منطق الـ **Plan Override**:

1.  **قاعدة الـ Hide (الإخفاء):**
    *   إذا تم إخفاء (Unit/Topic/Lesson) في الخطة، يقوم المولد بـ **حذفه تماماً** من مصفوفة الأبناء في ملف الجيسون.
2.  **قاعدة الـ Access Level (تغيير الصلاحية):**
    *   يتم تعديل حقل `access_level` (مثلاً من `paid` إلى `free_preview`) في ملفات الـ `Hierarchy` والـ `Topic` بناءً على تعليمات الخطة.
3.  **قاعدة الـ Linear (تغيير السلوك):**
    *   يتم تعديل حقل `is_linear` في الجيسون ليعكس رغبة الخطة (مثلاً فتح مادة خطية لتصبح حرة).

---

## 5. المسار التقني للتوليد (The Generation Pipeline)

1.  **Trigger:** عند حفظ (المادة، الدرس، الخطة، أو الـ Override).
2.  **Queue:** يتم إضافة الخطة المتأثرة إلى `pending_cdn_plans` في Redis.
3.  **Worker:**
    *   يجمع البيانات من الداتابيز.
    *   يطبق مصفوفة الـ Overrides في الذاكرة.
    *   يبني الملفات الذرية (Atomic Files).
    *   يحفظها محلياً في المجلدات الهيكلية (Local Staging).
    *   يرفعها للـ CDN ويحدث الـ Cache.

---

## 6. المتطلبات غير الوظيفية (Non-Functional Requirements)

1.  **Atomic Consistency:** لا يتم رفع أي ملف لـ Subject إلا إذا كانت جميع ملفات الـ Topics والـ Lessons التابعة له جاهزة.
2.  **Versioning:** كل ملف `manifest.json` يحتوي على `version` (Timestamp) لكسر الكاش (Cache Busting).
3.  **Security:** مجلد `/plans/` يخدم ملفات جيسون مخصصة، مما يضمن أن الطالب لا يمكنه الوصول لروابط محتوى غير متاح في خطته.

### رأي المعماري النهائي:
بهذا الـ PRD، قمنا بتحويل "كتلة بيانات" ضخمة إلى "نظام ملفات ذكي". الطالب يحمل فقط ما يراه، والباك اند يحسب فقط ما يحتاجه المحرك، والـ Overrides تعمل كفلتر أمني وتنظيمي قبل خروج البيانات للـ CDN.


بصفتي **Architect**، سأشرح لك الآن "منطق بوابة الوصول" (The Gatekeeper Logic). هذا الجزء هو المسؤول عن تحديد من يدفع، ومن يشاهد مجاناً، وكيف تتدفق هذه الصلاحيات من الأعلى (المادة) إلى الأسفل (الدرس).

سنعتمد مبدأ **"التوريث مع الخرق" (Inheritance with Piercing)**.

---

### 1. حالات الوصول التعريفية (Access Level Types)
في ملفات الجيسون، سيظهر حقل `access_level` بواحد من القيم التالية:
1.  **`public`**: متاح للجميع (حتى بدون تسجيل دخول - إن وجد).
2.  **`authenticated`**: متاح لأي مستخدم مسجل دخول (حتى لو لم يشترِ المادة).
3.  **`free_preview`**: متاح مجاناً كـ "عينة" رغم أنه يتبع لمادة مدفوعة.
4.  **`paid`**: مقفل، يتطلب وجود "منتج" (Grant) في محفظة الطالب.

---

### 2. لوجيك التوريث (The Inheritance Logic)
يعمل المولد (Generator) أثناء بناء الملفات بالقواعد التالية:

1.  **قاعدة المادة (Subject):** إذا كانت المادة `is_paid: true` -> كل ما تحتها يصبح `paid` تلقائياً.
2.  **خرق العينة (Free Preview Piercing):** إذا وجد المولد أن (Unit أو Topic أو Lesson) لديه علامة `is_free_preview: true` -> يتم كسر التوريث ويصبح هذا العنصر وكل ما تحته `free_preview`.
3.  **قاعدة المسار المنفصل (Sold Separately):** إذا كان التراك `is_sold_separately: true` -> يصبح هذا التراك "جزيرة مدفوعة" مستقلة، حتى لو كانت المادة الأصلية مجانية.

---

### 3. طبقة الـ Overrides (المتحكم النهائي)
بعد حساب التوريث، يتدخل الـ **Plan Override** ليقوم بالتعديل النهائي:
*   **Hide:** يحذف العنصر تماماً (أعلى مستويات الحظر).
*   **Set Free:** يغير الـ `access_level` إلى `free_preview` مهما كانت الحالة الأصلية.
*   **Set Paid:** يغير الـ `access_level` إلى `paid` ويشترط شراء منتج معين.

---

### 4. السيناريو العملي (كيف يطبق اللوجيك؟)

تخيل مادة "الفيزياء" (مدفوعة):

1.  **المادة (Subject):** `is_paid: true`.
    *   *الجيسون:* `access_level: "paid"`.
2.  **الوحدة الأولى:** لم يحدد عليها شيء.
    *   *الجيسون:* ترث الحالة وتصبح `access_level: "paid"`.
3.  **الوحدة الثانية:** تم تحديد `is_free_preview: true`.
    *   *الجيسون:* تكسر الحالة وتصبح `access_level: "free_preview"`.
    *   **الدروس داخل الوحدة الثانية:** كلها ستصبح `access_level: "free_preview"` (توريث العينة المجانية).
4.  **تراك المكثف:** تم تحديد `is_sold_separately: true`.
    *   *الجيسون:* يحمل `access_level: "paid"` وطلب شراء منتج خاص بالمكثف فقط.

---

### 5. كيف يتعامل الفرونت اند مع هذا اللوجيك؟

التطبيق (الويب أو الموبايل) يتبع هذه الخوارزمية البسيطة عند محاولة فتح أي نود (Node):

```python
def can_user_open(node, user_grants):
    # 1. إذا كان مجانياً أو عينة، افتح فوراً
    if node.access_level in ["public", "authenticated", "free_preview"]:
        return True
    
    # 2. إذا كان مدفوعاً، ابحث عن كود المنتج في محفظة الطالب
    if node.access_level == "paid":
        if node.required_item in user_grants:
            return True
        else:
            return False # أظهر قفل الشراء
```

---

### 6. الربط مع "الخطة الدراسية" (Plan Specific)
تذكر أن هذا اللوجيك يُطبق **أثناء توليد ملفات المجلد الخاص بالخطة** (`/plans/{plan_id}/...`). 
*   **الميزة:** إذا كان "درس النهايات" مجانياً لطلاب "خطة 2007" ولكنه مدفوع لطلاب "خطة 2008"، سيحتوي ملف الجيسون الخاص بـ 2007 على `free_preview` وملف 2008 على `paid`.
*   **النتيجة:** الباك اند لا يحتاج لحساب المعايير في كل مرة يطلب فيها الطالب الدرس، المعايير "محقونة" مسبقاً في الجيسون الثابت.

### لماذا هذا اللوجيك "ذكي"؟
لأنه يفصل بين **"القاعدة الأكاديمية"** (المعلم قرر أن هذا الدرس عينة) وبين **"القرار التجاري"** (الأدمن قرر أن هذه المادة لهذا الجيل مدفوعة). الـ JSON الناتج هو الخلاصة النهائية لهذين القرارين.