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
            "Memora Plan Override",
            filters={"parent": plan_id},
            fields=["target_name", "action"],
            pluck=False
        )
        
        for override in plan_overrides:
            overrides[override.target_name] = override
            
    except Exception as e:
        frappe.log_error(
            f"Error loading overrides for plan {plan_id}: {str(e)}",
            "CDN Export: Access Calculator"
        )
    
    return overrides

def calculate_access_level(node, parent_access=None, plan_overrides=None):
    """
    Calculate access level with inheritance and override application.

    Access Level Hierarchy:
    1. Plan-specific overrides (Hide, Set Free, Set Sold Separately)
    2. is_free_preview flag
    3. required_item (paid)
    4. Parent access level (inheritance)
    5. is_public flag
    6. Default: authenticated

    Args:
        node: Document object (Subject, Track, Unit, Topic, Lesson)
        parent_access (str, optional): Parent's access level
        plan_overrides (dict, optional): Indexed overrides from apply_plan_overrides()

    Returns:
        str or None: "public", "authenticated", "paid", "free_preview", or None if hidden
    """
    
    if plan_overrides and node.name in plan_overrides:
        override = plan_overrides[node.name]
        if override.action == "Hide":
            return None
        if override.action == "Set Free":
            return "free_preview"
        if override.action == "Set Sold Separately":
            pass
    
    if getattr(node, 'is_free_preview', False):
        return "free_preview"
    
    if getattr(node, 'required_item', None):
        return "paid"
    
    if getattr(node, 'is_public', False):
        return "public"
    
    if parent_access == "paid":
        return "paid"
    
    return "authenticated" if parent_access != "public" else "public"
