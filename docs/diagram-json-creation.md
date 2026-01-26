================================================================================
                     MEMORA JSON CREATION & DISTRIBUTION FLOW
================================================================================

[ 1. المحفزات - TRIGGERS ]
       |
       +--> (تعديل محتوى) : Subject, Track, Unit, Topic, Lesson, Stage
       +--> (تعديل تجاري): Academic Plan, Plan Subject
       +--> (تعديل استثنائي): Plan Overrides (Hide, Set Free, etc.)
       |
       v
[ 2. الجدولة - QUEUEING SYSTEM ]
       |
       +--> تسجيل الـ Plan IDs المتأثرة في Redis Set (Deduplication)
       +--> [Trigger: Every 5m OR 50 changes]
       |
       v
[ 3. محرك البناء - BATCH PROCESSOR ]
       |
       +--> حجز قفل (Lock) للخطة في Redis (منع التضارب)
       +--> إنشاء سجل مزامنة (CDN Sync Log) بحالة "Processing"
       |
       v
[ 4. التحويل المنطقي - DATA TRANSFORMATION ENGINE ]
       |
       +---(A) جلب الـ Overrides الخاصة بالخطة من MariaDB
       +---(B) جلب الهيكل الأكاديمي الخام (Raw Structure)
       |   |
       |   +--> [ تطبيق منطق الوراثة والخرق - Inheritance & Piercing ]
       |   +--> [ تطبيق الـ Overrides (حذف المخفي / تغيير الصلاحيات) ]
       |   +--> [ تعيين الـ bit_index لكل درس ]
       |
       v
[ 5. توليد الملفات - ATOMIC JSON GENERATION ]
       |
       +---[ manifest.json ] : (Subjects Index)
       +---[ {sub}_h.json  ] : (Tracks/Units/Topics Hierarchy)
       +---[ {sub}_b.json  ] : (Internal Bitset Map)
       +---[ {top}.json    ] : (Lessons List)
       +---[ {les}.json    ] : (Stages Content + Signed Video URLs)
       +---[ search.json   ] : (Sharded Index if lessons > 500)
       |
       v
[ 6. التخزين المحلي - LOCAL STAGING (The Insurance Policy) ]
       |
       +--> فحص مساحة القرص (> 10%)
       +--> نقل النسخة القديمة إلى .prev
       +--> كتابة الملفات الجديدة ذرياً (Atomic Write) في /public/memora_content/
       |
       v
[ 7. التوزيع العالمي - CDN DISTRIBUTION ]
       |
       +--> هل الـ CDN مفعل؟
       |      |
       |      +-- (نعم) --> رفع الملفات إلى S3 / Cloudflare R2
       |      |          --> طلب تطهير الكاش (Purge Cache) عبر API
       |      |          --> تحديث سجل المزامنة إلى "Success"
       |      |
       |      +-- (لا)  --> البقاء على النسخة المحلية (Local Fallback)
       |                 --> تحديث سجل المزامنة إلى "Local Only"
       |
       v
[ 8. الاستهلاك - CLIENT CONSUMPTION ]
       |
       +--> (Frontend): يطلب الجيسون من CDN أو السيرفر المحلي
       +--> (Backend): يقرأ الجيسون المحلي لحساب الـ Progress والـ FSRS
       |


graph TD
    %% 1. المحفزات (Triggers)
    subgraph Triggers [1. Triggers]
        T1[تعديل محتوى: درس/وحدة/مادة] --> Q
        T2[تعديل خطة: إضافة مادة/تعديل خطة] --> Q
        T3[تعديل استثنائي: Plan Overrides] --> Q
    end

    %% 2. الجدولة (Queueing)
    subgraph Queueing [2. Queueing & Batching]
        Q[Redis Set: pending_plans] --> B{Batch Processor}
        B -- "كل 5 دقائق أو 50 تعديل" --> Lock[حجز قفل الخطة في Redis]
    end

    %% 3. معالجة البيانات (Data Logic)
    subgraph Logic [3. Data Transformation Engine]
        Lock --> Fetch[جلب الهيكل الأكاديمي + Overrides]
        Fetch --> Piercing{تطبيق منطق الوراثة والخرق}
        
        Piercing -->|Success| Ovr[تطبيق Overrides: إخفاء/تغيير صلاحية]
        Ovr --> Bit[تعيين bit_index لكل درس]
    end

    %% 4. توليد الملفات (Generation)
    subgraph Generation [4. Atomic JSON Generation]
        Bit --> G1[manifest.json: فهرس المواد]
        Bit --> G2[sub_h.json: هيكل الخريطة]
        Bit --> G3[sub_b.json: خريطة البتات للمحرك]
        Bit --> G4[topic.json: قائمة الدروس]
        Bit --> G5[lesson.json: محتوى + Signed URLs]
    end

    %% 5. التخزين المحلي (Local Staging)
    subgraph Local [5. Local Staging & Fallback]
        G1 & G2 & G3 & G4 & G5 --> Disk{فحص مساحة القرص}
        Disk -->|OK| Prev[نقل النسخة القديمة إلى .prev]
        Prev --> Write[Atomic Write to /public/memora_content/]
    end

    %% 6. التوزيع (Distribution)
    subgraph Distribution [6. CDN Distribution]
        Write --> CDN_Check{هل CDN مفعل؟}
        CDN_Check -- نعم --> Upload[رفع الملفات إلى S3/R2]
        Upload --> Purge[Purge CDN Cache]
        CDN_Check -- لا --> Fallback[الاعتماد على الرابط المحلي]
    end

    %% 7. الاستهلاك (Consumption)
    subgraph Consumption [7. Final Consumption]
        Purge --> App[الفرونت اند يطلب من CDN]
        Fallback --> App
        Write -.-> Engine[الباك اند يقرأ محلياً لحساب التقدم والذاكرة]
    end

/public/memora_content/
  ├── /plans/
  │    └── /{plan_id}/
  │         ├── manifest.json              (فهرس الخطة)
  │         ├── /subjects/
  │         │    ├── {sub_id}_h.json       (الهيكل: Subject > Track > Unit > Topic)
  │         │    └── {sub_id}_b.json       (خريطة البتات - للمحرك فقط)
  │         └── /topics/
  │              └── {topic_id}.json       (قائمة دروس التوبيك)
  └── /lessons/
       └── {lesson_id}.json                (محتوى الدرس - Stages)