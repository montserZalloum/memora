import frappe

def setup_review_system():
    """
    يقوم بتهيئة النظام بالاعتماد على (Titles) لتجنب مشاكل تسمية الـ IDs.
    """
    print("🚀 Setting up Review System Infrastructure...")
    
    # تنظيف أي معاملات سابقة عالقة
    frappe.db.commit()

    # 1. المادة (Subject)
    if not frappe.db.exists("Game Subject", {"title": "System"}):
        frappe.get_doc({
            "doctype": "Game Subject",
            "title": "System",
            # لا نضع name يدوياً، نترك النظام يقرره
            "is_published": 0
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        print("✅ Checked/Created Subject: System")

    # 2. الوحدة (Unit)
    # نفحص بالعنوان وليس بالاسم
    if not frappe.db.exists("Game Unit", {"title": "System Reviews"}):
        frappe.get_doc({
            "doctype": "Game Unit",
            "title": "System Reviews",
            "subject": "System",
            "order": 9999
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        print("✅ Created Unit: System Reviews")
    else:
        print("ℹ️ Unit 'System Reviews' already exists.")

    # 3. الدرس (Lesson)
    # نحتاج لمعرفة "الاسم الحقيقي" للوحدة لنربط الدرس بها
    unit_name = frappe.db.get_value("Game Unit", {"title": "System Reviews"}, "name")
    
    if not frappe.db.exists("Game Lesson", {"name": "REVIEW-SESSION"}):
        # هنا نحاول فرض الاسم لأننا نستخدمه في الكود (Hardcoded ID)
        # إذا كان النظام يمنع الأسماء اليدوية، قد يفشل هذا الجزء ويأخذ اسماً تلقائياً
        # لذلك سنحاول البحث بالعنوان أيضاً
        if not frappe.db.exists("Game Lesson", {"title": "مراجعة الذاكرة"}):
            doc = frappe.get_doc({
                "doctype": "Game Lesson",
                "title": "مراجعة الذاكرة",
                "name": "REVIEW-SESSION", 
                "unit": unit_name,
                "xp_reward": 0
            })
            # محاولة الإدخال (مع تجاهل خطأ التكرار إذا حدث سباق)
            try:
                doc.insert(ignore_permissions=True)
                frappe.db.commit()
                print("✅ Created Lesson: REVIEW-SESSION")
            except frappe.DuplicateEntryError:
                frappe.db.rollback()
                pass
    
    print("✅ Review System Setup Check Complete.")