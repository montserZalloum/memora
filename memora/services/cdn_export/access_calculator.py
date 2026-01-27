import frappe


def apply_plan_overrides(plan_id):
	"""
	Load and index plan-specific overrides for fast lookup.

	Args:
	    plan_id (str): Plan document name

	Returns:
	    dict: Indexed overrides {node_name: {action, fields}}
	"""
	overrides = {}

	try:
		plan_overrides = frappe.get_all(
			"Memora Plan Override", filters={"parent": plan_id}, fields=["target_name", "action"], pluck=False
		)

		for override in plan_overrides:
			overrides[override.target_name] = override

	except Exception as e:
		frappe.log_error(
			f"Error loading overrides for plan {plan_id}: {str(e)}", "CDN Export: Access Calculator"
		)

	return overrides


def calculate_access_level(node, parent_access=None, plan_overrides=None):
	"""
	Calculate access level with inheritance and override application.

	Access Level Hierarchy:
	1. Visibility Check (is_public/is_published must be True)
	2. Plan-specific overrides (Hide, Set Free, Set Access Level, Set Sold Separately)
	3. is_free_preview flag (piercing)
	4. required_item (paid) or parent_access (paid inheritance)
	5. Default: authenticated

	Args:
		node: Document object (Subject, Track, Unit, Topic, Lesson)
		parent_access (str, optional): Parent's access level
		plan_overrides (dict, optional): Indexed overrides from apply_plan_overrides()

	Returns:
		str or None: "authenticated", "paid", "free_preview", or None if hidden/not published
	"""
	import frappe

	is_visible = getattr(node, "is_public", None)
	if is_visible is None:
		is_visible = getattr(node, "is_published", True)

	if not is_visible:
		frappe.log_error(
			f"[DEBUG] Content not visible (is_public/is_published=False): {node.name}", "CDN JSON Generation"
		)
		return None

	if plan_overrides and node.name in plan_overrides:
		override = plan_overrides[node.name]
		if override.action == "Hide":
			frappe.log_error(
				f"[WARN] Content hidden by override: {node.name} (action: Hide)", "CDN JSON Generation"
			)
			return None
		if override.action == "Set Free":
			frappe.log_error(f"[DEBUG] Content set to free by override: {node.name}", "CDN JSON Generation")
			return "free_preview"
		if override.action == "Set Access Level":
			access_value = override.override_value
			frappe.log_error(
				f"[DEBUG] Content access level set to {access_value} by override: {node.name}",
				"CDN JSON Generation",
			)
			return access_value
		if override.action == "Set Sold Separately":
			pass

	if getattr(node, "is_free_preview", False):
		return "free_preview"

	if getattr(node, "required_item", None):
		return "paid"

	if parent_access == "paid":
		return "paid"

	return "authenticated"


def calculate_linear_mode(node, plan_overrides=None):
	"""
	Calculate is_linear flag with override application.

	Linear Mode Hierarchy:
	1. Plan-specific overrides (Set Linear)
	2. is_linear flag on node
	3. Default: False (non-linear navigation)

	Args:
		node: Document object (Subject, Track, Unit, Topic, Lesson)
		plan_overrides (dict, optional): Indexed overrides from apply_plan_overrides()

	Returns:
		bool: True if linear mode, False if non-linear
	"""
	if plan_overrides and node.name in plan_overrides:
		override = plan_overrides[node.name]
		if override.action == "Set Linear":
			# Parse string value to boolean
			is_linear = override.override_value.lower() in ("true", "1", "yes")
			frappe.log_error(
				f"[DEBUG] Content linear mode set to {is_linear} by override: {node.name}",
				"CDN JSON Generation",
			)
			return is_linear

	# Return node's is_linear flag if present, default to False
	return getattr(node, "is_linear", False)
