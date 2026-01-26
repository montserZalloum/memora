[ البداية: مستوى المادة - Subject ]
           |
           v
    هل المادة مدفوعة (is_paid)?
    /             \
 (لا)             (نعم)
  |                |
  v                v
[Level: public]  [Level: paid]
  |                |
  +----------------+----( توريث الحالة للأبناء )----> [ المسار/الوحدة - Track/Unit ]
                                                              |
                                                              v
                                                   هل يوجد علامة "خرق"؟
                                                   /        |        \
                                          (لا يوجد)    (Free Preview)  (Sold Separately)
                                             |              |                |
                                             v              v                v
                                      [استمرار التوريث]  [Level: free_preview]  [Level: paid + Item]
                                             |              |                |
                                             +--------------+----------------+
                                                            |
                                                   ( توريث الحالة للأسفل )
                                                            |
                                                            v
                                                   [ التوبيك/الدرس - Topic/Lesson ]
                                                            |
                                                            v
                                               =============================
                                               مرحلة الحسم (Plan Overrides)
                                               =============================
                                                            |
              +---------------------------------------------+--------------------------------------------+
              |                                             |                                            |
        (Hide Override)                            (Set Free Override)                         (لا يوجد Override)
              |                                             |                                            |
              v                                             v                                            |
    [حذف العنصر تماماً من JSON]                    [تحويل الحالة إلى free_preview]                       |
                                                            |                                            |
              +---------------------------------------------+--------------------------------------------+
                                                            |
                                                            v
                                             [ النتيجة النهائية في ملف JSON ]
                                             { "access_level": "..." }


graph TD
    %% بداية العملية من مستوى المادة
    Start[بداية: مستوى المادة Subject] --> IsSubPaid{هل المادة<br/>is_paid?}

    %% تحديد حالة المادة
    IsSubPaid -- لا --> SubAuth[Initial Status: authenticated]
    IsSubPaid -- نعم --> SubPaid[Initial Status: paid]

    %% التوريث للمستويات الأدنى (Track / Unit / Topic)
    SubAuth --> Inherit[توريث الحالة للأسفل Inheritance]
    SubPaid --> Inherit

    %% مرحلة الخرق (Piercing) داخل الهيكل
    Inherit --> CheckPiercing{هل يوجد علامة خرق<br/>Piercing Flag?}

    CheckPiercing -- is_free_preview --> FreePrev[Status: free_preview]
    CheckPiercing -- is_sold_separately --> SoldSep[Status: paid + Specific Item]
    CheckPiercing -- لا يوجد --> KeepInherit[استمرار التوريث كما هو]

    %% انتقال الحالة للدرس
    FreePrev --> ToLesson[انتقال الحالة للدرس Lesson]
    SoldSep --> ToLesson
    KeepInherit --> ToLesson

    %% المرحلة الحاسمة: Overrides الخاصة بالخطة
    ToLesson --> PlanOverride{تطبيق Plan Overrides<br/>الكلمة الأخيرة}

    PlanOverride -- Hide --> Hidden[إخفاء: لا يظهر في JSON]
    PlanOverride -- Set Free --> ForcedFree[Force Status: free_preview]
    PlanOverride -- Set Paid --> ForcedPaid[Force Status: paid]
    PlanOverride -- لا يوجد --> FinalStatus[بقاء الحالة المستحوذة]

    %% النتيجة النهائية في ملفات JSON
    ForcedFree --> JSON[النتيجة النهائية في ملفات JSON]
    ForcedPaid --> JSON
    FinalStatus --> JSON
    Hidden --> Exclude[Exclude from JSON]