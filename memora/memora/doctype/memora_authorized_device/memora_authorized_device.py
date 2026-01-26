import frappe
import uuid

def validate(self):
    if not self.device_id or len(self.device_id.strip()) < 3:
        frappe.throw(_("Device name must be at least 3 characters"))
    
    try:
        uuid.UUID(self.device_id, version=4)
    except ValueError:
        frappe.throw(_("Invalid device ID format. Must be UUID v4."))
    
    if not self.added_on:
        self.added_on = frappe.utils.now()
