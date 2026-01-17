def create_subscription(self):
        # 1. جلب تفاصيل الباقة الأصلية
        if not self.sales_item:
            frappe.throw("لا يوجد باقة مختارة في هذا الطلب")
            
        sales_item = frappe.get_doc("Game Sales Item", self.sales_item)
        
        # تحقق من وجود موسم للباقة
        if not sales_item.linked_season:
            frappe.throw(f"الباقة '{sales_item.item_name}' غير مرتبطة بموسم دراسي! يرجى تعديل الباقة.")

        # 2. إنشاء اشتراك جديد (بدون تواريخ يدوية)
        sub = frappe.get_doc({
            "doctype": "Game Player Subscription",
            "player": self.user,
            "status": "Active",
            "type": "Specific Access", 
            "linked_season": sales_item.linked_season, # 👈 الربط الجوهري هنا
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
        frappe.msgprint(f"✅ تم تفعيل الاشتراك للطالب {self.user} لموسم {sales_item.linked_season}")



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

        profile_name = frappe.db.get_value("Player Profile", {"user": self.user}, "name")
        
        if not profile_name:
            frappe.throw(f"خطأ فادح: لم يتم العثور على بروفايل لاعب للمستخدم {self.user}")

        # 1. جلب تفاصيل الباقة الأصلية
        if not self.sales_item:
            frappe.throw("لا يوجد باقة مختارة في هذا الطلب")
            
        sales_item = frappe.get_doc("Game Sales Item", self.sales_item)
        
        # تحقق من وجود موسم للباقة
        if not sales_item.linked_season:
            frappe.throw(f"الباقة '{sales_item.item_name}' غير مرتبطة بموسم دراسي! يرجى تعديل الباقة.")

        # 2. إنشاء اشتراك جديد (بدون تواريخ يدوية)
        sub = frappe.get_doc({
            "doctype": "Game Player Subscription",
            "player": profile_name,
            "status": "Active",
            "type": "Specific Access", 
            "linked_season": sales_item.linked_season, # 👈 الربط الجوهري هنا
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
        frappe.msgprint(f"✅ تم تفعيل الاشتراك للطالب {self.user} لموسم {sales_item.linked_season}")

