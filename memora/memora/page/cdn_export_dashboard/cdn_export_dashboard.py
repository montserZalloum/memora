"""
CDN Export Dashboard Page Controller
Handles server-side logic for the CDN export monitoring dashboard.
"""

import frappe


def get_context(context):
    """
    Prepare context for the CDN export dashboard page.
    Only accessible to System Managers.
    """
    # Verify user has admin permissions
    frappe.only_for("System Manager")

    # Set page context
    context.update({
        'title': 'CDN Export Dashboard',
        'description': 'Monitor CDN content export operations and manage sync queue'
    })

    return context
