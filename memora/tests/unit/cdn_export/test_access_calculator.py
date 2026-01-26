import unittest
from unittest.mock import Mock
from memora.services.cdn_export.access_calculator import calculate_access_level, calculate_linear_mode

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

    def test_override_set_access_level_to_public(self):
        """Test Set Access Level override action sets access_level to specified value"""
        node = Mock()
        node.name = "node_set_public"
        node.is_public = False
        node.is_free_preview = False
        node.required_item = "ITEM-001"
        plan_overrides = {"node_set_public": Mock(action="Set Access Level", override_value="public")}
        self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "public")

    def test_override_set_access_level_to_paid(self):
        """Test Set Access Level override action sets access_level to paid"""
        node = Mock()
        node.name = "node_set_paid"
        node.is_public = True
        node.is_free_preview = False
        node.required_item = None
        plan_overrides = {"node_set_paid": Mock(action="Set Access Level", override_value="paid")}
        self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "paid")

    def test_override_set_access_level_to_authenticated(self):
        """Test Set Access Level override action sets access_level to authenticated"""
        node = Mock()
        node.name = "node_set_auth"
        node.is_public = True
        node.required_item = None
        plan_overrides = {"node_set_auth": Mock(action="Set Access Level", override_value="authenticated")}
        self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "authenticated")

    def test_override_set_access_level_to_free_preview(self):
        """Test Set Access Level override action sets access_level to free_preview"""
        node = Mock()
        node.name = "node_set_preview"
        node.is_public = False
        node.is_free_preview = False
        node.required_item = "ITEM-001"
        plan_overrides = {"node_set_preview": Mock(action="Set Access Level", override_value="free_preview")}
        self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "free_preview")

    def test_set_access_level_overrides_all_flags(self):
        """Test Set Access Level override takes precedence over all node flags"""
        node = Mock()
        node.name = "node_all_flags"
        node.is_public = True
        node.is_free_preview = True
        node.required_item = "ITEM-001"
        plan_overrides = {"node_all_flags": Mock(action="Set Access Level", override_value="authenticated")}
        self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "authenticated")


class TestLinearModeCalculator(unittest.TestCase):

    def test_linear_mode_default_false(self):
        """Test default is_linear is False when no flag or override"""
        node = Mock()
        node.name = "node_default_linear"
        node.is_linear = False
        self.assertEqual(calculate_linear_mode(node), False)

    def test_linear_mode_default_true(self):
        """Test default is_linear is True when node has flag"""
        node = Mock()
        node.name = "node_linear_true"
        node.is_linear = True
        self.assertEqual(calculate_linear_mode(node), True)

    def test_override_set_linear_to_true(self):
        """Test Set Linear override sets is_linear to true"""
        node = Mock()
        node.name = "node_set_linear_true"
        node.is_linear = False
        plan_overrides = {"node_set_linear_true": Mock(action="Set Linear", override_value="true")}
        self.assertEqual(calculate_linear_mode(node, plan_overrides=plan_overrides), True)

    def test_override_set_linear_to_false(self):
        """Test Set Linear override sets is_linear to false"""
        node = Mock()
        node.name = "node_set_linear_false"
        node.is_linear = True
        plan_overrides = {"node_set_linear_false": Mock(action="Set Linear", override_value="false")}
        self.assertEqual(calculate_linear_mode(node, plan_overrides=plan_overrides), False)

    def test_set_linear_override_takes_precedence(self):
        """Test Set Linear override takes precedence over node flag"""
        node = Mock()
        node.name = "node_linear_override"
        node.is_linear = True
        plan_overrides = {"node_linear_override": Mock(action="Set Linear", override_value="false")}
        self.assertEqual(calculate_linear_mode(node, plan_overrides=plan_overrides), False)

    def test_linear_mode_with_missing_attribute(self):
        """Test handles nodes missing is_linear attribute gracefully"""
        node = Mock(spec=[])  # Node without is_linear attribute
        node.name = "node_no_linear"
        self.assertEqual(calculate_linear_mode(node), False)

class TestAccessControlIntegration(unittest.TestCase):
	"""Integration tests for access control inheritance and override precedence - Phase 8: User Story 6"""

	def test_paid_subject_inheritance_to_children(self):
		"""T070: Paid subject makes all children inherit paid access"""
		# Setup subject as paid
		subject = Mock()
		subject.name = "SUBJ-PAID"
		subject.is_public = False
		subject.is_free_preview = False
		subject.required_item = "ITEM-PAID"
		subject_access = calculate_access_level(subject)
		self.assertEqual(subject_access, "paid")

		# Track should inherit paid
		track = Mock()
		track.name = "TRACK-CHILD"
		track.is_public = False
		track.is_free_preview = False
		track.required_item = None
		track_access = calculate_access_level(track, parent_access=subject_access)
		self.assertEqual(track_access, "paid")

		# Unit should inherit paid
		unit = Mock()
		unit.name = "UNIT-CHILD"
		unit.is_public = False
		unit.is_free_preview = False
		unit.required_item = None
		unit_access = calculate_access_level(unit, parent_access=track_access)
		self.assertEqual(unit_access, "paid")

	def test_is_free_preview_piercing(self):
		"""T071: is_free_preview on node pierces down to all descendants"""
		# Free preview node
		unit = Mock()
		unit.name = "UNIT-PREVIEW"
		unit.is_public = False
		unit.is_free_preview = True
		unit.required_item = None
		unit_access = calculate_access_level(unit, parent_access="paid")
		self.assertEqual(unit_access, "free_preview")

		# Child topic should inherit free_preview (pierce)
		topic = Mock()
		topic.name = "TOPIC-CHILD"
		topic.is_public = False
		topic.is_free_preview = False
		topic.required_item = None
		topic_access = calculate_access_level(topic, parent_access=unit_access)
		self.assertEqual(topic_access, "free_preview")

	def test_is_sold_separately_creates_independent_island(self):
		"""T072: is_sold_separately at track level creates independent paid scope"""
		# Subject is public
		subject = Mock()
		subject.name = "SUBJ-PUBLIC"
		subject.is_public = True
		subject.is_free_preview = False
		subject.required_item = None
		subject_access = calculate_access_level(subject)
		self.assertEqual(subject_access, "public")

		# Normal track inherits public
		track_normal = Mock()
		track_normal.name = "TRACK-NORMAL"
		track_normal.is_public = False
		track_normal.is_free_preview = False
		track_normal.required_item = None
		track_normal_access = calculate_access_level(track_normal, parent_access=subject_access)
		self.assertEqual(track_normal_access, "public")

		# Sold separately track becomes paid despite parent being public
		# (is_sold_separately flag makes it independent)
		track_sold = Mock()
		track_sold.name = "TRACK-SOLD"
		track_sold.is_public = False
		track_sold.is_free_preview = False
		track_sold.required_item = "ITEM-TRACK-SOLD"
		track_sold_access = calculate_access_level(track_sold, parent_access=subject_access)
		self.assertEqual(track_sold_access, "paid")

	def test_override_precedence(self):
		"""T073: Override precedence: Set Access Level > Set Free > is_free_preview > required_item > inheritance"""
		node = Mock()
		node.name = "PRIORITY-TEST"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		parent_access = "paid"

		# 1. Without override, required_item takes precedence
		access = calculate_access_level(node, parent_access=parent_access)
		self.assertEqual(access, "paid")

		# 2. Set Free override (middle priority) should override required_item
		override_set_free = Mock()
		override_set_free.action = "Set Free"
		overrides = {"PRIORITY-TEST": override_set_free}
		access = calculate_access_level(node, parent_access=parent_access, plan_overrides=overrides)
		self.assertEqual(access, "free_preview")

		# 3. Set Access Level override (highest priority) should override everything
		override_set_level = Mock()
		override_set_level.action = "Set Access Level"
		override_set_level.override_value = "authenticated"
		overrides = {"PRIORITY-TEST": override_set_level}
		access = calculate_access_level(node, parent_access=parent_access, plan_overrides=overrides)
		self.assertEqual(access, "authenticated")

	def test_required_item_propagation(self):
		"""T074: required_item propagates to children unless overridden"""
		# Track requires item
		track = Mock()
		track.name = "TRACK-ITEM"
		track.is_public = False
		track.is_free_preview = False
		track.required_item = "PROD-TRACK"
		track_access = calculate_access_level(track)
		self.assertEqual(track_access, "paid")

		# Unit child should inherit required_item context (access = paid)
		unit = Mock()
		unit.name = "UNIT-CHILD"
		unit.is_public = False
		unit.is_free_preview = False
		unit.required_item = None
		unit_access = calculate_access_level(unit, parent_access=track_access)
		self.assertEqual(unit_access, "paid")


if __name__ == '__main__':
    unittest.main()
