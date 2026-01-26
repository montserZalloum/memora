import frappe
from frappe.tests.utils import FrappeTestCase

class PlayerCoreTestFixtures(FrappeTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def create_test_user(self, email="test@example.com"):
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": "Test",
            "last_name": "User",
            "enabled": 1
        }).insert(ignore_permissions=True)
        return user

    def create_test_grade(self, grade_name="Grade 10"):
        if frappe.db.exists("Memora Grade", grade_name):
            return frappe.get_doc("Memora Grade", grade_name)
        
        grade = frappe.get_doc({
            "doctype": "Memora Grade",
            "grade_name": grade_name
        }).insert(ignore_permissions=True)
        return grade

    def create_test_season(self, season_name="2025-2026"):
        if frappe.db.exists("Memora Season", season_name):
            return frappe.get_doc("Memora Season", season_name)
        
        season = frappe.get_doc({
            "doctype": "Memora Season",
            "season_name": season_name,
            "start_date": "2025-01-01",
            "end_date": "2026-12-31"
        }).insert(ignore_permissions=True)
        return season

    def create_test_academic_plan(self, plan_name="Test Plan"):
        if frappe.db.exists("Memora Academic Plan", plan_name):
            return frappe.get_doc("Memora Academic Plan", plan_name)
        
        plan = frappe.get_doc({
            "doctype": "Memora Academic Plan",
            "plan_name": plan_name,
            "grade": self.create_test_grade().name,
            "season": self.create_test_season().name
        }).insert(ignore_permissions=True)
        return plan

    def create_test_player_profile(self, user=None, device_id=None):
        if not user:
            user = self.create_test_user()
        
        profile = frappe.get_doc({
            "doctype": "Memora Player Profile",
            "user": user.name,
            "grade": self.create_test_grade().name,
            "season": self.create_test_season().name,
            "academic_plan": self.create_test_academic_plan().name
        })
        
        if device_id:
            from frappe.local import _request_data
            if not hasattr(frappe.local, 'request'):
                from unittest.mock import MagicMock
                frappe.local.request = MagicMock()
            frappe.local.request.headers = {"X-Device-ID": device_id}
        
        profile.insert(ignore_permissions=True)
        return profile

    def create_test_player_wallet(self, player_profile=None, total_xp=0, current_streak=0):
        if not player_profile:
            player_profile = self.create_test_player_profile()
        
        wallet = frappe.get_doc({
            "doctype": "Memora Player Wallet",
            "player": player_profile.name,
            "total_xp": total_xp,
            "current_streak": current_streak
        }).insert(ignore_permissions=True)
        return wallet

    def create_test_authorized_device(self, device_id, device_name="Test Device"):
        return {
            "device_id": device_id,
            "device_name": device_name
        }

    def cleanup_test_data(self):
        wallets = frappe.get_all("Memora Player Wallet", fields=["name"])
        for wallet in wallets:
            frappe.delete_doc("Memora Player Wallet", wallet.name, force=1)
        
        profiles = frappe.get_all("Memora Player Profile", fields=["name"])
        for profile in profiles:
            frappe.delete_doc("Memora Player Profile", profile.name, force=1)
        
        users = frappe.get_all("User", filters={"email": ["like", "test%"]}, fields=["name"])
        for user in users:
            frappe.delete_doc("User", user.name, force=1)
