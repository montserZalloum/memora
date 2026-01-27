import unittest
from unittest.mock import Mock
from memora.services.cdn_export.access_calculator import calculate_access_level, calculate_linear_mode


class TestAccessCalculator(unittest.TestCase):
	def test_public_subject_access(self):
		"""Public subject (is_public=True) returns authenticated by default"""
		node = Mock()
		node.name = "public_subject"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node), "authenticated")

	def test_auth_subject_access(self):
		"""Subject with is_public=False is excluded (returns None)"""
		node = Mock()
		node.name = "auth_subject"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertIsNone(calculate_access_level(node))

	def test_published_other_node_access(self):
		"""Published non-subject node (is_published=True) returns authenticated by default"""
		node = Mock()
		node.name = "published_node"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node), "authenticated")

	def test_hidden_other_node_access(self):
		"""Non-subject node with is_published=False is excluded (returns None)"""
		node = Mock()
		node.name = "hidden_node"
		node.is_public = None
		node.is_published = False
		node.is_free_preview = False
		node.required_item = None
		self.assertIsNone(calculate_access_level(node))

	def test_paid_access_with_required_item(self):
		"""Node with required_item returns paid (if visible)"""
		node = Mock()
		node.name = "paid_node"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		self.assertEqual(calculate_access_level(node), "paid")

	def test_free_preview_overrides_paid(self):
		"""is_free_preview=True overrides required_item and returns free_preview"""
		node = Mock()
		node.name = "preview_node"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		self.assertEqual(calculate_access_level(node), "free_preview")

	def test_inheritance_from_paid_parent(self):
		"""Child inherits paid access from parent (if visible)"""
		node = Mock()
		node.name = "child_of_paid"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="paid"), "paid")

	def test_inheritance_from_authenticated_parent(self):
		"""Child inherits authenticated access from parent (if visible)"""
		node = Mock()
		node.name = "child_of_auth"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="authenticated"), "authenticated")

	def test_override_hide(self):
		"""Hide override returns None (excludes node)"""
		node = Mock()
		node.name = "node_to_hide"
		node.is_public = None
		node.is_published = True
		plan_overrides = {"node_to_hide": Mock(action="Hide")}
		self.assertIsNone(calculate_access_level(node, plan_overrides=plan_overrides))

	def test_override_set_free(self):
		"""Set Free override returns free_preview"""
		node = Mock()
		node.name = "node_to_set_free"
		node.is_public = None
		node.is_published = True
		node.required_item = "ITEM-001"
		plan_overrides = {"node_to_set_free": Mock(action="Set Free")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "free_preview")

	def test_override_set_access_level_to_paid(self):
		"""Set Access Level override sets access_level to paid"""
		node = Mock()
		node.name = "node_set_paid"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = False
		node.required_item = None
		plan_overrides = {"node_set_paid": Mock(action="Set Access Level", override_value="paid")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "paid")

	def test_override_set_access_level_to_authenticated(self):
		"""Set Access Level override sets access_level to authenticated"""
		node = Mock()
		node.name = "node_set_auth"
		node.is_public = None
		node.is_published = True
		node.required_item = None
		plan_overrides = {"node_set_auth": Mock(action="Set Access Level", override_value="authenticated")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "authenticated")

	def test_override_set_access_level_to_free_preview(self):
		"""Set Access Level override sets access_level to free_preview"""
		node = Mock()
		node.name = "node_set_preview"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		plan_overrides = {"node_set_preview": Mock(action="Set Access Level", override_value="free_preview")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "free_preview")

	def test_set_access_level_overrides_all_flags(self):
		"""Set Access Level override takes precedence over all node flags"""
		node = Mock()
		node.name = "node_all_flags"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		plan_overrides = {"node_all_flags": Mock(action="Set Access Level", override_value="authenticated")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "authenticated")

	def test_default_authenticated_when_no_flags(self):
		"""Published node with no flags returns authenticated by default"""
		node = Mock()
		node.name = "default_node"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node), "authenticated")


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
		node = Mock(spec=[])
		node.name = "node_no_linear"
		self.assertEqual(calculate_linear_mode(node), False)


class TestAccessControlIntegration(unittest.TestCase):
	"""Integration tests for access control inheritance and override precedence"""

	def test_paid_subject_inheritance_to_children(self):
		"""Paid subject makes all children inherit paid access"""
		subject = Mock()
		subject.name = "SUBJ-PAID"
		subject.is_public = None
		subject.is_published = True
		subject.is_free_preview = False
		subject.required_item = "ITEM-PAID"
		subject_access = calculate_access_level(subject)
		self.assertEqual(subject_access, "paid")

		track = Mock()
		track.name = "TRACK-CHILD"
		track.is_public = None
		track.is_published = True
		track.is_free_preview = False
		track.required_item = None
		track_access = calculate_access_level(track, parent_access=subject_access)
		self.assertEqual(track_access, "paid")

		unit = Mock()
		unit.name = "UNIT-CHILD"
		unit.is_public = None
		unit.is_published = True
		unit.is_free_preview = False
		unit.required_item = None
		unit_access = calculate_access_level(unit, parent_access=track_access)
		self.assertEqual(unit_access, "paid")

	def test_is_free_preview_piercing(self):
		"""is_free_preview on node pierces down to all descendants"""
		unit = Mock()
		unit.name = "UNIT-PREVIEW"
		unit.is_public = None
		unit.is_published = True
		unit.is_free_preview = True
		unit.required_item = None
		unit_access = calculate_access_level(unit, parent_access="paid")
		self.assertEqual(unit_access, "free_preview")

		topic = Mock()
		topic.name = "TOPIC-CHILD"
		topic.is_public = None
		topic.is_published = True
		topic.is_free_preview = False
		topic.required_item = None
		topic_access = calculate_access_level(topic, parent_access=unit_access)
		self.assertEqual(topic_access, "free_preview")

	def test_override_precedence(self):
		"""Override precedence: Set Access Level > Set Free > is_free_preview > required_item > inheritance"""
		node = Mock()
		node.name = "PRIORITY-TEST"
		node.is_public = None
		node.is_published = True
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		parent_access = "paid"

		access = calculate_access_level(node, parent_access=parent_access)
		self.assertEqual(access, "paid")

		override_set_free = Mock()
		override_set_free.action = "Set Free"
		overrides = {"PRIORITY-TEST": override_set_free}
		access = calculate_access_level(node, parent_access=parent_access, plan_overrides=overrides)
		self.assertEqual(access, "free_preview")

		override_set_level = Mock()
		override_set_level.action = "Set Access Level"
		override_set_level.override_value = "authenticated"
		overrides = {"PRIORITY-TEST": override_set_level}
		access = calculate_access_level(node, parent_access=parent_access, plan_overrides=overrides)
		self.assertEqual(access, "authenticated")

	def test_required_item_propagation(self):
		"""required_item propagates to children unless overridden"""
		track = Mock()
		track.name = "TRACK-ITEM"
		track.is_public = None
		track.is_published = True
		track.is_free_preview = False
		track.required_item = "PROD-TRACK"
		track_access = calculate_access_level(track)
		self.assertEqual(track_access, "paid")

		unit = Mock()
		unit.name = "UNIT-CHILD"
		unit.is_public = None
		unit.is_published = True
		unit.is_free_preview = False
		unit.required_item = None
		unit_access = calculate_access_level(unit, parent_access=track_access)
		self.assertEqual(unit_access, "paid")


if __name__ == "__main__":
	unittest.main()
