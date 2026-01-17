import frappe
from frappe.model.document import Document
from frappe.utils import add_months, nowdate

class GamePurchaseRequest(Document):
    def before_submit(self):
        """
        قبل الترحيل، نجبر الحالة لتصبح Approved تلقائياً
        حتى لو نسي الآدمن تغييرها من القائمة.
        """
        if self.status != "Rejected":
            self.status = "Approved"

    def on_submit(self):
        """
        عند الترحيل (Submit)، ننشئ الاشتراك.
        """
        if self.status == "Approved":
            self.create_subscription()

    def create_subscription(self):
        # 1. جلب تفاصيل الباقة الأصلية
        if not self.sales_item:
            frappe.throw("لا يوجد باقة مختارة في هذا الطلب")
            
        sales_item = frappe.get_doc("Game Sales Item", self.sales_item)
        
        # 2. إنشاء اشتراك جديد
        sub = frappe.get_doc({
            "doctype": "Game Player Subscription",
            "player": self.user,
            "status": "Active",
            "type": "Specific Access", 
            "start_date": nowdate(),
            "expiry_date": add_months(nowdate(), 12), # مدة سنة
            "access_items": []
        })
        
        # 3. نسخ المحتويات
        for content in sales_item.bundle_contents:
            sub.append("access_items", {
                "type": content.type,
                "subject": content.target_subject,
                "track": content.target_track
            })
            
        sub.insert(ignore_permissions=True)
        frappe.msgprint(f"✅ تم تفعيل الاشتراك للطالب {self.user} بنجاح!")