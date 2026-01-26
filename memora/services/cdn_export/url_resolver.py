"""
URL Resolver for CDN Export.

Provides a single function to get the correct content URL based on CDN settings.
"""

import frappe
from frappe.utils import get_url
import os


def get_cdn_settings() -> dict:
	"""
	Get cached CDN settings.

	Returns:
		dict: {"enabled": bool, "cdn_base_url": str, "local_fallback_mode": bool}
	
	Caching: 60-second TTL, invalidated on CDN Settings save
	"""
	cache_key = "cdn_settings_config"
	settings = frappe.cache().get_value(cache_key)
	
	if settings is None:
		doc = frappe.get_single("CDN Settings")
		settings = {
			"enabled": bool(doc.enabled),
			"cdn_base_url": doc.cdn_base_url or "",
			"local_fallback_mode": bool(doc.local_fallback_mode),
		}
		frappe.cache().set_value(cache_key, settings, expires_in_sec=60)
	
	return settings


def invalidate_settings_cache() -> None:
	"""
	Clear the CDN settings cache. Called from CDN Settings on_update.
	"""
	cache_key = "cdn_settings_config"
	frappe.cache().delete_value(cache_key)


def get_site_url() -> str:
	"""
	Get the base URL for the current site.
	
	Returns:
		str: e.g., https://mysite.com
	"""
	if frappe.request:
		return frappe.request.url_root.rstrip('/')
	else:
		return get_url().rstrip('/')


def get_content_url(path: str) -> str:
	"""
	Resolve a content path to full URL based on CDN settings.

	Parameters:
		path (str): Relative path (e.g., "plans/PLAN-001/manifest.json")

	Returns:
		str: Full URL to the content
	"""
	settings = get_cdn_settings()
	
	if settings["local_fallback_mode"]:
		return f"{get_site_url()}/files/memora_content/{path}"
	elif settings["enabled"] and settings["cdn_base_url"]:
		return f"{settings['cdn_base_url']}/{path}"
	else:
		return f"{get_site_url()}/files/memora_content/{path}"
