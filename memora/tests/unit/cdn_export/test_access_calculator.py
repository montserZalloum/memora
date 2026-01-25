import unittest
from unittest.mock import Mock
from memora.services.cdn_export.access_calculator import calculate_access_level

class TestAccessCalculator(unittest.TestCase):

    def test_public_access(self):
        node = Mock()
        node.name = "public_node"
        node.is_public = True
        node.is_free_preview = False
        node.required_item = None
        self.assertEqual(calculate_access_level(node), "public")

    def test_authenticated_access(self):
        node = Mock()
        node.name = "auth_node"
        node.is_public = False
        node.is_free_preview = False
        node.required_item = None
        self.assertEqual(calculate_access_level(node), "authenticated")

    def test_paid_access(self):
        node = Mock()
        node.name = "paid_node"
        node.is_public = False
        node.is_free_preview = False
        node.required_item = "ITEM-001"
        self.assertEqual(calculate_access_level(node), "paid")

    def test_free_preview_overrides_paid(self):
        node = Mock()
        node.name = "preview_node"
        node.is_public = False
        node.is_free_preview = True
        node.required_item = "ITEM-001"
        self.assertEqual(calculate_access_level(node), "free_preview")

    def test_inheritance_from_paid_parent(self):
        node = Mock()
        node.name = "child_of_paid"
        node.is_public = False
        node.is_free_preview = False
        node.required_item = None
        self.assertEqual(calculate_access_level(node, parent_access="paid"), "paid")

    def test_inheritance_from_public_parent(self):
        node = Mock()
        node.name = "child_of_public"
        node.is_public = False
        node.is_free_preview = False
        node.required_item = None
        self.assertEqual(calculate_access_level(node, parent_access="public"), "public")

    def test_inheritance_from_authenticated_parent(self):
        node = Mock()
        node.name = "child_of_auth"
        node.is_public = False
        node.is_free_preview = False
        node.required_item = None
        self.assertEqual(calculate_access_level(node, parent_access="authenticated"), "authenticated")

    def test_override_hide(self):
        node = Mock()
        node.name = "node_to_hide"
        node.is_public = True
        plan_overrides = {"node_to_hide": Mock(action="Hide")}
        self.assertIsNone(calculate_access_level(node, plan_overrides=plan_overrides))

    def test_override_set_free(self):
        node = Mock()
        node.name = "node_to_set_free"
        node.is_public = False
        node.required_item = "ITEM-001"
        plan_overrides = {"node_to_set_free": Mock(action="Set Free")}
        self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "free_preview")

    def test_public_node_in_paid_hierarchy(self):
        node = Mock()
        node.name = "public_in_paid"
        node.is_public = True
        node.is_free_preview = False
        node.required_item = None
        # is_public should not be overridden by parent
        self.assertEqual(calculate_access_level(node, parent_access="paid"), "public")

if __name__ == '__main__':
    unittest.main()
