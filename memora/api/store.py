"""
Store Domain Module

This module handles store item listing and purchase requests.
"""

import frappe
from frappe import _
from .utils import get_user_active_subscriptions


@frappe.whitelist()
def get_store_items():
    """
    Fetch products with hiding what was purchased (based on active season).
    """
    try:
        user = frappe.session.user

        # 1. Fetch student context
        profile = frappe.db.get_value("Player Profile", {"user": user},
            ["current_grade", "current_stream"], as_dict=True)

        user_grade = profile.get("current_grade") if profile else None
        user_stream = profile.get("current_stream") if profile else None

        # 2. What subjects does student currently own? (Active Season Subs)
        # We use helper function that depends on season date
        active_access = get_user_active_subscriptions(user)

        # Convert list to Sets for fast search
        owned_subjects = {x['subject'] for x in active_access if x['type'] == 'Subject'}
        owned_tracks = {x['track'] for x in active_access if x['type'] == 'Track'}
        has_global = any(x['type'] == 'Global' for x in active_access)

        if has_global:
            return []  # They have global subscription, no need to buy anything

        # 3. Pending requests (Pending)
        pending_items = frappe.get_all("Game Purchase Request",
            filters={"user": user, "docstatus": 0}, pluck="sales_item")

        # 4. Fetch products
        items = frappe.get_all("Game Sales Item",
            fields=["name", "item_name", "description", "price", "discounted_price", "image", "sku", "target_grade"],
            order_by="price asc"
        )

        # 5. Analyze bundle contents (to know what to hide)
        item_names = [i.name for i in items]
        bundle_contents = frappe.get_all("Game Bundle Content",
            filters={"parent": ["in", item_names]},
            fields=["parent", "type", "target_subject", "target_track"]
        )

        # Map: Item -> Contents
        content_map = {}
        for c in bundle_contents:
            if c.parent not in content_map: content_map[c.parent] = []
            content_map[c.parent].append(c)

        # 6. Fetch stream rules (Streams)
        stream_rules = {}
        targets = frappe.get_all("Game Item Target Stream", filters={"parent": ["in", item_names]}, fields=["parent", "stream"])
        for t in targets:
            if t.parent not in stream_rules: stream_rules[t.parent] = []
            stream_rules[t.parent].append(t.stream)

        # 7. Final filtering
        filtered_items = []
        for item in items:
            # أ. Was it requested before?
            if item.name in pending_items: continue

            # ب. Do they own its content?
            # Rule: If bundle contains subject student owns, hide bundle
            contents = content_map.get(item.name, [])
            is_owned = False
            for c in contents:
                if c.type == 'Subject' and c.target_subject in owned_subjects:
                    is_owned = True; break
                if c.type == 'Track' and c.target_track in owned_tracks:
                    is_owned = True; break

            if is_owned: continue  # Hide purchased items

            # ج. Grade and stream filtering
            if item.target_grade and item.target_grade != user_grade: continue

            allowed_streams = stream_rules.get(item.name, [])
            if allowed_streams and (not user_stream or user_stream not in allowed_streams):
                continue

            filtered_items.append(item)

        return filtered_items

    except Exception as e:
        frappe.log_error("Get Store Items Failed", frappe.get_traceback())
        return []


@frappe.whitelist()
def request_purchase(item_id, transaction_id=None):
    """
    Student submits purchase request.

    Default status: Pending.
    Content won't open until admin approves.
    """
    try:
        user = frappe.session.user

        # Ensure no duplicate pending request for same bundle (prevent repetition)
        existing = frappe.db.exists("Game Purchase Request", {
            "user": user,
            "sales_item": item_id,
            "docstatus": 0  # 0 means Draft/Pending
        })

        if existing:
            return {"status": "pending", "message": "لديك طلب قيد المراجعة لهذه الباقة بالفعل."}

        # Fetch price for saving
        item_price = frappe.db.get_value("Game Sales Item", item_id, "discounted_price") or \
                     frappe.db.get_value("Game Sales Item", item_id, "price")

        # Create request
        doc = frappe.get_doc({
            "doctype": "Game Purchase Request",
            "user": user,          # Ensure field name matches DocType
            "sales_item": item_id,  # Ensure field name matches DocType
            "status": "Pending",
            "price": item_price,
            "transaction_id": transaction_id  # If sent from frontend
        })
        doc.insert(ignore_permissions=True)

        return {
            "status": "success",
            "message": "تم إرسال طلبك! سيتم تفعيل الاشتراك بعد مراجعة الإدارة."
        }

    except Exception as e:
        frappe.log_error("Purchase Request Failed", frappe.get_traceback())
        return {"status": "error", "message": "حدث خطأ أثناء الطلب."}
