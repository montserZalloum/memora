import unittest
from unittest.mock import Mock

from memora.services.cdn_export.access_calculator import calculate_access_level


class TestAccessLevelPublic(unittest.TestCase):
	"""Test all scenarios for 'public' access level"""

	def test_is_public_flag_returns_public(self):
		"""Public flag sets access_level to public"""
		node = Mock()
		node.name = "public_node"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node), "public")

	def test_public_flag_overrides_authenticated_default(self):
		"""Public flag takes precedence over default authenticated"""
		node = Mock()
		node.name = "public_vs_auth"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node), "public")

	def test_public_flag_overrides_parent_paid(self):
		"""Public flag takes precedence over parent paid inheritance"""
		node = Mock()
		node.name = "public_child_of_paid"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="paid"), "public")

	def test_public_inherits_from_parent_public(self):
		"""Child inherits public from parent when no own flags"""
		node = Mock()
		node.name = "child_of_public"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="public"), "public")

	def test_public_override_sets_public(self):
		"""Set Access Level override to public"""
		node = Mock()
		node.name = "override_public"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		plan_overrides = {"override_public": Mock(action="Set Access Level", override_value="public")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "public")

	def test_public_from_parent_with_free_preview_parent(self):
		"""Child of free_preview parent without own flags inherits free_preview, not public"""
		node = Mock()
		node.name = "child_of_preview"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		# Parent is free_preview, child should NOT be public (inherits parent)
		self.assertEqual(calculate_access_level(node, parent_access="free_preview"), "free_preview")


class TestAccessLevelAuthenticated(unittest.TestCase):
	"""Test all scenarios for 'authenticated' access level"""

	def test_default_authenticated_no_flags(self):
		"""Default access level is authenticated when no flags set"""
		node = Mock()
		node.name = "auth_node"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node), "authenticated")

	def test_authenticated_inherits_from_parent(self):
		"""Child inherits authenticated from parent"""
		node = Mock()
		node.name = "child_of_auth"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="authenticated"), "authenticated")

	def test_authenticated_override_sets_authenticated(self):
		"""Set Access Level override to authenticated"""
		node = Mock()
		node.name = "override_auth"
		node.is_public = True
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		plan_overrides = {"override_auth": Mock(action="Set Access Level", override_value="authenticated")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "authenticated")

	def test_authenticated_with_none_parent(self):
		"""Default authenticated when parent_access is None"""
		node = Mock()
		node.name = "auth_no_parent"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access=None), "authenticated")

	def test_authenticated_with_free_preview_parent(self):
		"""Child of free_preview parent inherits free_preview, not authenticated"""
		node = Mock()
		node.name = "child_of_preview"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		# free_preview propagates to children
		self.assertEqual(calculate_access_level(node, parent_access="free_preview"), "free_preview")


class TestAccessLevelPaid(unittest.TestCase):
	"""Test all scenarios for 'paid' access level"""

	def test_required_item_returns_paid(self):
		"""required_item flag sets access_level to paid"""
		node = Mock()
		node.name = "paid_node"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		self.assertEqual(calculate_access_level(node), "paid")

	def test_paid_inherits_from_parent_paid(self):
		"""Child inherits paid from parent"""
		node = Mock()
		node.name = "child_of_paid"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="paid"), "paid")

	def test_paid_override_sets_paid(self):
		"""Set Access Level override to paid"""
		node = Mock()
		node.name = "override_paid"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = None
		plan_overrides = {"override_paid": Mock(action="Set Access Level", override_value="paid")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "paid")

	def test_required_item_overrides_parent_public(self):
		"""required_item takes precedence over parent public"""
		node = Mock()
		node.name = "paid_child_of_public"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = "ITEM-002"
		self.assertEqual(calculate_access_level(node, parent_access="public"), "paid")

	def test_required_item_overrides_parent_authenticated(self):
		"""required_item takes precedence over parent authenticated"""
		node = Mock()
		node.name = "paid_child_of_auth"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = "ITEM-003"
		self.assertEqual(calculate_access_level(node, parent_access="authenticated"), "paid")

	def test_required_item_propagation_through_hierarchy(self):
		"""required_item context propagates through multi-level hierarchy"""
		# Level 1: Subject with required_item
		subject = Mock()
		subject.name = "SUBJ-PAID"
		subject.is_public = False
		subject.is_free_preview = False
		subject.required_item = "ITEM-SUBJ"
		subject_access = calculate_access_level(subject)
		self.assertEqual(subject_access, "paid")

		# Level 2: Track inherits paid context
		track = Mock()
		track.name = "TRACK-CHILD"
		track.is_public = False
		track.is_free_preview = False
		track.required_item = None
		track_access = calculate_access_level(track, parent_access=subject_access)
		self.assertEqual(track_access, "paid")

		# Level 3: Unit inherits paid context
		unit = Mock()
		unit.name = "UNIT-CHILD"
		unit.is_public = False
		unit.is_free_preview = False
		unit.required_item = None
		unit_access = calculate_access_level(unit, parent_access=track_access)
		self.assertEqual(unit_access, "paid")

		# Level 4: Topic inherits paid context
		topic = Mock()
		topic.name = "TOPIC-CHILD"
		topic.is_public = False
		topic.is_free_preview = False
		topic.required_item = None
		topic_access = calculate_access_level(topic, parent_access=unit_access)
		self.assertEqual(topic_access, "paid")


class TestAccessLevelFreePreview(unittest.TestCase):
	"""Test all scenarios for 'free_preview' access level"""

	def test_is_free_preview_flag_returns_free_preview(self):
		"""is_free_preview flag sets access_level to free_preview"""
		node = Mock()
		node.name = "preview_node"
		node.is_public = False
		node.is_free_preview = True
		node.required_item = None
		self.assertEqual(calculate_access_level(node), "free_preview")

	def test_free_preview_overrides_required_item(self):
		"""is_free_preview takes precedence over required_item"""
		node = Mock()
		node.name = "preview_with_item"
		node.is_public = False
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		self.assertEqual(calculate_access_level(node), "free_preview")

	def test_free_preview_inherits_from_parent_free_preview(self):
		"""Child inherits free_preview from parent (piercing behavior)"""
		node = Mock()
		node.name = "child_of_preview"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="free_preview"), "free_preview")

	def test_free_preview_override_sets_free_preview(self):
		"""Set Free override sets access_level to free_preview"""
		node = Mock()
		node.name = "override_preview"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		plan_overrides = {"override_preview": Mock(action="Set Free")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "free_preview")

	def test_free_preview_override_overrides_all_flags(self):
		"""Set Free override takes precedence over all node flags"""
		node = Mock()
		node.name = "preview_all_flags"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		plan_overrides = {"preview_all_flags": Mock(action="Set Free")}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "free_preview")

	def test_set_access_level_override_to_free_preview(self):
		"""Set Access Level override to free_preview"""
		node = Mock()
		node.name = "set_preview_override"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		plan_overrides = {
			"set_preview_override": Mock(action="Set Access Level", override_value="free_preview")
		}
		self.assertEqual(calculate_access_level(node, plan_overrides=plan_overrides), "free_preview")

	def test_free_preview_piercing_through_hierarchy(self):
		"""free_preview pierces down through entire hierarchy"""
		# Level 1: Unit with is_free_preview
		unit = Mock()
		unit.name = "UNIT-PREVIEW"
		unit.is_public = False
		unit.is_free_preview = True
		unit.required_item = None
		unit_access = calculate_access_level(unit, parent_access="paid")
		self.assertEqual(unit_access, "free_preview")

		# Level 2: Topic inherits free_preview
		topic = Mock()
		topic.name = "TOPIC-CHILD"
		topic.is_public = False
		topic.is_free_preview = False
		topic.required_item = None
		topic_access = calculate_access_level(topic, parent_access=unit_access)
		self.assertEqual(topic_access, "free_preview")

		# Level 3: Lesson inherits free_preview
		lesson = Mock()
		lesson.name = "LESSON-CHILD"
		lesson.is_public = False
		lesson.is_free_preview = False
		lesson.required_item = None
		lesson_access = calculate_access_level(lesson, parent_access=topic_access)
		self.assertEqual(lesson_access, "free_preview")

	def test_free_preview_with_required_item_child(self):
		"""Child with required_item inherits free_preview from parent"""
		parent = Mock()
		parent.name = "PARENT-PREVIEW"
		parent.is_public = False
		parent.is_free_preview = True
		parent.required_item = None
		parent_access = calculate_access_level(parent)

		child = Mock()
		child.name = "CHILD-WITH-ITEM"
		child.is_public = False
		child.is_free_preview = False
		child.required_item = "ITEM-CHILD"
		# Child should inherit free_preview despite having required_item
		child_access = calculate_access_level(child, parent_access=parent_access)
		self.assertEqual(child_access, "free_preview")


class TestAccessLevelPrecedence(unittest.TestCase):
	"""Test precedence rules between all 4 access levels"""

	def test_precedence_highest_override_set_access_level(self):
		"""Set Access Level override (highest) beats all flags and inheritance"""
		node = Mock()
		node.name = "override_highest"
		node.is_public = True
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		plan_overrides = {"override_highest": Mock(action="Set Access Level", override_value="authenticated")}
		self.assertEqual(
			calculate_access_level(node, parent_access="paid", plan_overrides=plan_overrides), "authenticated"
		)

	def test_precedence_set_free_second_highest(self):
		"""Set Free override beats is_free_preview, required_item, inheritance, is_public"""
		node = Mock()
		node.name = "override_set_free"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		plan_overrides = {"override_set_free": Mock(action="Set Free")}
		self.assertEqual(
			calculate_access_level(node, parent_access="paid", plan_overrides=plan_overrides), "free_preview"
		)

	def test_precedence_is_free_preview_third(self):
		"""is_free_preview beats required_item, inheritance, is_public"""
		node = Mock()
		node.name = "preview_vs_item"
		node.is_public = False
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		self.assertEqual(calculate_access_level(node, parent_access="public"), "free_preview")

	def test_precedence_required_item_fourth(self):
		"""required_item beats inheritance and is_public"""
		node = Mock()
		node.name = "item_vs_public"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		self.assertEqual(calculate_access_level(node, parent_access="public"), "paid")

	def test_precedence_parent_paid_inheritance(self):
		"""Parent paid inheritance beats is_public on child"""
		node = Mock()
		node.name = "inherit_vs_public"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="paid"), "paid")

	def test_precedence_parent_public_inheritance(self):
		"""Parent public inheritance when child has no flags"""
		node = Mock()
		node.name = "inherit_public"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access="public"), "public")

	def test_precedence_is_public_fifth(self):
		"""is_public beats default authenticated"""
		node = Mock()
		node.name = "public_vs_auth"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node), "public")

	def test_precedence_default_authenticated_lowest(self):
		"""Default authenticated when nothing else applies"""
		node = Mock()
		node.name = "default_auth"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		self.assertEqual(calculate_access_level(node, parent_access=None), "authenticated")

	def test_precedence_complete_chain_all_four_levels(self):
		"""Test complete precedence chain with all 4 access levels in order"""
		# Create node with all flags
		node = Mock()
		node.name = "full_chain"
		node.is_public = True
		node.is_free_preview = True
		node.required_item = "ITEM-001"

		# 1. Test lowest: authenticated (no flags, no parent)
		node1 = Mock()
		node1.name = "node1"
		node1.is_public = False
		node1.is_free_preview = False
		node1.required_item = None
		self.assertEqual(calculate_access_level(node1), "authenticated")

		# 2. is_public flag
		node2 = Mock()
		node2.name = "node2"
		node2.is_public = True
		node2.is_free_preview = False
		node2.required_item = None
		self.assertEqual(calculate_access_level(node2), "public")

		# 3. parent paid inheritance
		node3 = Mock()
		node3.name = "node3"
		node3.is_public = False
		node3.is_free_preview = False
		node3.required_item = None
		self.assertEqual(calculate_access_level(node3, parent_access="paid"), "paid")

		# 4. required_item
		node4 = Mock()
		node4.name = "node4"
		node4.is_public = False
		node4.is_free_preview = False
		node4.required_item = "ITEM-004"
		self.assertEqual(calculate_access_level(node4, parent_access="public"), "paid")

		# 5. is_free_preview
		node5 = Mock()
		node5.name = "node5"
		node5.is_public = False
		node5.is_free_preview = True
		node5.required_item = "ITEM-005"
		self.assertEqual(calculate_access_level(node5, parent_access="paid"), "free_preview")

		# 6. Set Free override
		node6 = Mock()
		node6.name = "node6"
		node6.is_public = True
		node6.is_free_preview = False
		node6.required_item = "ITEM-006"
		plan_overrides6 = {"node6": Mock(action="Set Free")}
		self.assertEqual(
			calculate_access_level(node6, parent_access="paid", plan_overrides=plan_overrides6),
			"free_preview",
		)

		# 7. Set Access Level override (highest)
		node7 = Mock()
		node7.name = "node7"
		node7.is_public = True
		node7.is_free_preview = True
		node7.required_item = "ITEM-007"
		plan_overrides7 = {"node7": Mock(action="Set Access Level", override_value="authenticated")}
		self.assertEqual(
			calculate_access_level(node7, parent_access="paid", plan_overrides=plan_overrides7),
			"authenticated",
		)


class TestAccessLevelCombinations(unittest.TestCase):
	"""Test complex combinations of access levels"""

	def test_public_child_of_free_preview(self):
		"""Child with is_public under free_preview parent stays public"""
		node = Mock()
		node.name = "public_child_preview"
		node.is_public = True
		node.is_free_preview = False
		node.required_item = None
		# is_public flag overrides parent free_preview
		self.assertEqual(calculate_access_level(node, parent_access="free_preview"), "public")

	def test_paid_child_of_free_preview(self):
		"""Child with required_item under free_preview parent becomes paid"""
		node = Mock()
		node.name = "paid_child_preview"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = "ITEM-001"
		# required_item overrides parent free_preview
		self.assertEqual(calculate_access_level(node, parent_access="free_preview"), "paid")

	def test_free_preview_child_of_paid(self):
		"""Child with is_free_preview under paid parent becomes free_preview"""
		node = Mock()
		node.name = "preview_child_paid"
		node.is_public = False
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		# is_free_preview overrides required_item and parent paid
		self.assertEqual(calculate_access_level(node, parent_access="paid"), "free_preview")

	def test_authenticated_child_of_public_parent_with_parent_public(self):
		"""Authenticated child when parent is public - special case"""
		node = Mock()
		node.name = "auth_child_public"
		node.is_public = False
		node.is_free_preview = False
		node.required_item = None
		# When parent is public, child with no flags inherits public (not authenticated)
		self.assertEqual(calculate_access_level(node, parent_access="public"), "public")

	def test_four_levels_in_hierarchy(self):
		"""Test hierarchy with all 4 access levels at different levels"""
		# Subject: public
		subject = Mock()
		subject.name = "SUBJ-PUBLIC"
		subject.is_public = True
		subject.is_free_preview = False
		subject.required_item = None
		subject_access = calculate_access_level(subject)
		self.assertEqual(subject_access, "public")

		# Track: authenticated (inherits from public -> public, but default would be authenticated)
		track = Mock()
		track.name = "TRACK-AUTH"
		track.is_public = False
		track.is_free_preview = False
		track.required_item = None
		track_access = calculate_access_level(track, parent_access=subject_access)
		self.assertEqual(track_access, "public")  # Inherits public

		# Unit: paid (required_item)
		unit = Mock()
		unit.name = "UNIT-PAID"
		unit.is_public = False
		unit.is_free_preview = False
		unit.required_item = "ITEM-UNIT"
		unit_access = calculate_access_level(unit, parent_access=track_access)
		self.assertEqual(unit_access, "paid")

		# Topic: free_preview (is_free_preview)
		topic = Mock()
		topic.name = "TOPIC-PREVIEW"
		topic.is_public = False
		topic.is_free_preview = True
		topic.required_item = None
		topic_access = calculate_access_level(topic, parent_access=unit_access)
		self.assertEqual(topic_access, "free_preview")

	def test_all_four_levels_as_overrides(self):
		"""Test all 4 levels as Set Access Level overrides"""
		base_node = Mock()
		base_node.is_public = False
		base_node.is_free_preview = False
		base_node.required_item = None

		# Override to public
		node_public = Mock(spec=base_node)
		node_public.name = "override_public"
		plan_overrides_public = {"override_public": Mock(action="Set Access Level", override_value="public")}
		self.assertEqual(calculate_access_level(node_public, plan_overrides=plan_overrides_public), "public")

		# Override to authenticated
		node_auth = Mock(spec=base_node)
		node_auth.name = "override_auth"
		plan_overrides_auth = {
			"override_auth": Mock(action="Set Access Level", override_value="authenticated")
		}
		self.assertEqual(
			calculate_access_level(node_auth, plan_overrides=plan_overrides_auth), "authenticated"
		)

		# Override to paid
		node_paid = Mock(spec=base_node)
		node_paid.name = "override_paid"
		plan_overrides_paid = {"override_paid": Mock(action="Set Access Level", override_value="paid")}
		self.assertEqual(calculate_access_level(node_paid, plan_overrides=plan_overrides_paid), "paid")

		# Override to free_preview
		node_preview = Mock(spec=base_node)
		node_preview.name = "override_preview"
		plan_overrides_preview = {
			"override_preview": Mock(action="Set Access Level", override_value="free_preview")
		}
		self.assertEqual(
			calculate_access_level(node_preview, plan_overrides=plan_overrides_preview), "free_preview"
		)


class TestAccessLevelHideOverride(unittest.TestCase):
	"""Test Hide override scenario (returns None, not one of the 4 levels)"""

	def test_hide_override_returns_none(self):
		"""Hide override returns None regardless of flags"""
		node = Mock()
		node.name = "hidden_node"
		node.is_public = True
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		plan_overrides = {"hidden_node": Mock(action="Hide")}
		self.assertIsNone(calculate_access_level(node, parent_access="paid", plan_overrides=plan_overrides))

	def test_hide_override_overrides_all_flags(self):
		"""Hide override takes highest precedence over all flags"""
		node = Mock()
		node.name = "hidden_all"
		node.is_public = True
		node.is_free_preview = True
		node.required_item = "ITEM-001"
		plan_overrides = {"hidden_all": Mock(action="Hide")}
		self.assertIsNone(calculate_access_level(node, plan_overrides=plan_overrides))

	def test_hide_vs_set_access_level_precedence(self):
		"""Hide and Set Access Level can't both apply - Hide checked first"""
		node = Mock()
		node.name = "hide_vs_set"
		node.is_public = True
		plan_overrides = {"hide_vs_set": Mock(action="Hide")}
		self.assertIsNone(calculate_access_level(node, plan_overrides=plan_overrides))


if __name__ == "__main__":
	unittest.main()
