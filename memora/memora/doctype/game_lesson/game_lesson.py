import frappe
import json
import uuid
from frappe import _
from frappe.model.document import Document

class GameLesson(Document):
    def validate(self):
        # 1. التحقق من وجود الوحدة
        if not self.unit:
            frappe.throw(_("يجب اختيار الوحدة (Unit) أولاً."))

        # 2. جلب إعدادات الوحدة المختارة
        unit_structure = frappe.db.get_value("Game Unit", self.unit, "structure_type")

        # 3. تطبيق المنطق الهجين 🧠
        if unit_structure == "Topic Based":
            # الحالة أ: نظام المواضيع
            if not self.topic:
                frappe.throw(_(f"الوحدة المختارة '{self.unit}' تعتمد نظام المواضيع. يجب عليك ربط هذا الدرس بـ (Topic)."))
            
            # التأكد أن التوبيك المختار تابع لنفس الوحدة
            topic_unit = frappe.db.get_value("Game Topic", self.topic, "unit")
            if topic_unit != self.unit:
                frappe.throw(_("الموضوع المختار لا ينتمي للوحدة المختارة."))

        elif unit_structure == "Lesson Based":
            # الحالة ب: نظام الدروس المباشرة
            if self.topic:
                frappe.msgprint(_("تنبيه: الوحدة المختارة تعتمد نظام الدروس المباشرة. سيتم تجاهل الموضوع المختار."), alert=True)
                self.topic = None # تنظيف البيانات تلقائياً

        # 4. حقن المعرفات (يجب أن تكون المسافة البادئة هنا مطابقة للسطر الأول في الدالة)
        self.inject_ids_into_stages()

    def inject_ids_into_stages(self):
        """
        تقوم هذه الدالة بالدوران على كل مرحلة، وفحص الـ Config JSON.
        إذا وجدت عناصر (pairs, highlights) بدون ID، تقوم بإضافته.
        """
        for stage in self.stages:
            if not stage.config: continue
            
            try:
                config = json.loads(stage.config)
                modified = False
                
                # 1. معالجة التوصيل (Matching)
                if stage.type == 'Matching' and 'pairs' in config:
                    for pair in config['pairs']:
                        if 'id' not in pair:
                            pair['id'] = str(uuid.uuid4())[:8]
                            modified = True
                            
                # 2. معالجة الكشف (Reveal)
                elif stage.type == 'Reveal' and 'highlights' in config:
                    for highlight in config['highlights']:
                        if 'id' not in highlight:
                            highlight['id'] = str(uuid.uuid4())[:8]
                            modified = True
                
                # إذا تم التعديل، نعيد الحفظ في الحقل
                if modified:
                    stage.config = json.dumps(config, ensure_ascii=False)
                    
            except Exception as e:
                frappe.log_error(f"Stage ID Injection Failed: {stage.name}", str(e))