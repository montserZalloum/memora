
import frappe

HIERARCHY = {
    "Memora Lesson Stage": ("Memora Lesson", "parent"),
    "Memora Lesson": ("Memora Topic", "parent_topic"),
    "Memora Topic": ("Memora Unit", "parent_unit"),
    "Memora Unit": ("Memora Track", "parent_track"),
    "Memora Track": ("Memora Subject", "parent_subject"),
}

def get_affected_plan_ids(doctype, docname):
    """
    Given a doctype and docname, find all Academic Plans that need rebuilding.
    Implements bottom-up dependency resolution to identify affected plans.

    Args:
        doctype (str): The DocType that was changed
        docname (str): The document name that was changed

    Returns:
        list: List of plan document names that need rebuilding
    """
    affected_plans = set()
    processed_docs = set()  # Prevent infinite loops in cyclic dependencies

    def _walk_up_hierarchy(current_doctype, current_docname):
        """Recursively walk up the content hierarchy to find plans."""
        if current_docname in processed_docs:
            return

        processed_docs.add(current_docname)

        # Find parent relationships from hierarchy mapping
        if current_doctype in HIERARCHY:
            parent_doctype, parent_field = HIERARCHY[current_doctype]

            try:
                current_doc = frappe.get_doc(current_doctype, current_docname)
                if hasattr(current_doc, parent_field):
                    parent_name = getattr(current_doc, parent_field)
                    if parent_name:
                        _walk_up_hierarchy(parent_doctype, parent_name)
            except frappe.DoesNotExistError as e:
                frappe.logger.warning(f"Document {current_doctype}/{current_docname} not found: {str(e)}")
            except Exception as e:
                frappe.log_error(f"Error traversing hierarchy for {current_doctype}/{current_docname}: {str(e)}", "Dependency Resolution Error")

        # Find plans that reference this document
        _find_plans_referencing_doc(current_doctype, current_docname)

    def _find_plans_referencing_doc(doc_type, doc_name):
        """Find all Memora Academic Plans that reference this document."""
        try:
            # Check plan subjects
            plan_subjects = frappe.db.get_all(
                "Memora Plan Subject",
                filters={"subject": doc_name},
                pluck="parent"
            )
            for plan_name in plan_subjects:
                if plan_name:
                    affected_plans.add(plan_name)
        except Exception as e:
            frappe.log_error(f"Error finding plans for {doc_type}/{doc_name}: {str(e)}", "Plan Resolution Error")

    try:
        # Start the walk from the changed document
        _walk_up_hierarchy(doctype, docname)
    except Exception as e:
        frappe.log_error(f"Error getting affected plans for {doctype}/{docname}: {str(e)}", "Affected Plans Calculation Error")

    return list(affected_plans)

def get_direct_plans_for_content(doctype, docname):
    """
    Get Academic Plans that directly reference the given content document.
    Faster than full hierarchy traversal for direct relationships.

    Args:
        doctype (str): The DocType
        docname (str): The document name

    Returns:
        list: List of plan document names
    """
    plans = []

    try:
        if doctype == "Memora Subject":
            # Plans via Memora Plan Subject
            plan_subjects = frappe.db.get_all(
                "Memora Plan Subject",
                filters={"subject": docname},
                pluck="parent"
            )
            plans.extend(plan_subjects)

        elif doctype in ["Memora Track", "Memora Unit", "Memora Topic", "Memora Lesson"]:
            # Find content in hierarchy and trace to plans
            current_doctype = doctype
            current_docname = docname

            while current_doctype in HIERARCHY:
                parent_doctype, parent_field = HIERARCHY[current_doctype]

                try:
                    parent_doc = frappe.get_doc(current_doctype, current_docname)

                    if hasattr(parent_doc, parent_field):
                        parent_name = getattr(parent_doc, parent_field)
                        if parent_name:
                            # Check if parent is a plan
                            if parent_doctype == "Memora Subject":
                                plan_subjects = frappe.db.get_all(
                                    "Memora Plan Subject",
                                    filters={"subject": parent_name},
                                    pluck="parent"
                                )
                                plans.extend(plan_subjects)

                            current_docname = parent_name
                            current_doctype = parent_doctype
                        else:
                            break
                    else:
                        break
                except frappe.DoesNotExistError:
                    frappe.logger.warning(f"Document {current_doctype}/{current_docname} not found in hierarchy traversal")
                    break
                except Exception as e:
                    frappe.log_error(f"Error traversing hierarchy for {current_doctype}/{current_docname}: {str(e)}", "Direct Plans Resolution Error")
                    break

    except Exception as e:
        frappe.log_error(f"Error getting direct plans for {doctype}/{docname}: {str(e)}", "Direct Plans Retrieval Error")

    return list(set(plans))  # Remove duplicates
