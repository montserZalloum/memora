import frappe
from frappe import _
from frappe.model.document import Document

class GameLesson(Document):
    def validate(self):
        # 1. التحقق من وجود الوحدة (أصلاً هي Mandatory بس زيادة تأكيد)
        if not self.unit:
            frappe.throw(_("يجب اختيار الوحدة (Unit) أولاً."))

        # 2. جلب إعدادات الوحدة المختارة
        # نحتاج نعرف: هل هي Topic Based أم Lesson Based؟
        unit_structure = frappe.db.get_value("Game Unit", self.unit, "structure_type")

        # 3. تطبيق المنطق الهجين 🧠
        if unit_structure == "Topic Based":
            # الحالة أ: نظام المواضيع
            if not self.topic:
                frappe.throw(_(f"الوحدة المختارة '{self.unit}' تعتمد نظام المواضيع. يجب عليك ربط هذا الدرس بـ (Topic)."))
            
            # (اختياري) التأكد أن التوبيك المختار تابع لنفس الوحدة فعلاً
            topic_unit = frappe.db.get_value("Game Topic", self.topic, "unit")
            if topic_unit != self.unit:
                frappe.throw(_("الموضوع المختار لا ينتمي للوحدة المختارة."))

        elif unit_structure == "Lesson Based":
            # الحالة ب: نظام الدروس المباشرة
            if self.topic:
                frappe.msgprint(_("تنبيه: الوحدة المختارة تعتمد نظام الدروس المباشرة. سيتم تجاهل الموضوع المختار."), alert=True)
                self.topic = None # تنظيف البيانات تلقائياً