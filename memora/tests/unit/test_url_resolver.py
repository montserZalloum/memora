"""
Unit tests for URL Resolver.
Tests CDN/local URL switching and settings caching.
"""

import unittest
from unittest.mock import patch, MagicMock

import frappe
from frappe.tests.utils import FrappeTestCase

from memora.services.cdn_export.url_resolver import (
	get_content_url,
	get_cdn_settings,
	invalidate_settings_cache,
	get_site_url
)


class TestURLResolver(unittest.TestCase):
	"""Test suite for URL resolution based on CDN settings."""

	@patch('memora.services.cdn_export.url_resolver.get_cdn_settings')
	@patch('memora.services.cdn_export.url_resolver.get_site_url')
	def test_get_content_url_returns_cdn_when_enabled(self, mock_get_site_url, mock_get_settings):
		"""Test that get_content_url returns CDN URL when CDN is enabled and fallback mode is off."""
		mock_get_site_url.return_value = "https://mysite.com"
		mock_get_settings.return_value = {
			"enabled": True,
			"cdn_base_url": "https://cdn.example.com",
			"local_fallback_mode": False
		}

		url = get_content_url("plans/PLAN-001/manifest.json")

		self.assertEqual(url, "https://cdn.example.com/plans/PLAN-001/manifest.json", "Should return CDN URL")

	@patch('memora.services.cdn_export.url_resolver.get_cdn_settings')
	@patch('memora.services.cdn_export.url_resolver.get_site_url')
	def test_get_content_url_returns_local_when_disabled(self, mock_get_site_url, mock_get_settings):
		"""Test that get_content_url returns local URL when CDN is disabled."""
		mock_get_site_url.return_value = "https://mysite.com"
		mock_get_settings.return_value = {
			"enabled": False,
			"cdn_base_url": "https://cdn.example.com",
			"local_fallback_mode": False
		}

		url = get_content_url("plans/PLAN-001/manifest.json")

		self.assertEqual(url, "https://mysite.com/files/memora_content/plans/PLAN-001/manifest.json", "Should return local URL")

	@patch('memora.services.cdn_export.url_resolver.get_cdn_settings')
	@patch('memora.services.cdn_export.url_resolver.get_site_url')
	def test_get_content_url_returns_local_when_fallback_mode(self, mock_get_site_url, mock_get_settings):
		"""Test that get_content_url returns local URL when fallback mode is enabled, even if CDN is enabled."""
		mock_get_site_url.return_value = "https://mysite.com"
		mock_get_settings.return_value = {
			"enabled": True,
			"cdn_base_url": "https://cdn.example.com",
			"local_fallback_mode": True
		}

		url = get_content_url("plans/PLAN-001/manifest.json")

		self.assertEqual(url, "https://mysite.com/files/memora_content/plans/PLAN-001/manifest.json", "Should return local URL in fallback mode")

	@patch('memora.services.cdn_export.url_resolver.frappe.cache')
	def test_settings_cache_invalidated_on_save(self, mock_cache):
		"""Test that invalidate_settings_cache clears the cache."""
		mock_cache_instance = MagicMock()
		mock_cache.return_value = mock_cache_instance

		invalidate_settings_cache()

		mock_cache_instance.delete_value.assert_called_once_with("cdn_settings_config")

	@patch('memora.services.cdn_export.url_resolver.frappe.cache')
	@patch('memora.services.cdn_export.url_resolver.frappe.get_single')
	def test_get_cdn_settings_uses_cache(self, mock_get_single, mock_cache):
		"""Test that get_cdn_settings caches settings."""
		mock_cache_instance = MagicMock()
		mock_cache.return_value = mock_cache_instance

		cached_settings = {
			"enabled": True,
			"cdn_base_url": "https://cdn.example.com",
			"local_fallback_mode": False
		}
		mock_cache_instance.get_value.return_value = cached_settings

		settings = get_cdn_settings()

		self.assertEqual(settings, cached_settings, "Should return cached settings")
		mock_get_single.assert_not_called(), "Should not fetch from DB if cache hit"

	@patch('memora.services.cdn_export.url_resolver.frappe.cache')
	@patch('memora.services.cdn_export.url_resolver.frappe.get_single')
	def test_get_cdn_settings_fetches_on_cache_miss(self, mock_get_single, mock_cache):
		"""Test that get_cdn_settings fetches from DB on cache miss."""
		mock_cache_instance = MagicMock()
		mock_cache.return_value = mock_cache_instance
		mock_cache_instance.get_value.return_value = None

		mock_doc = MagicMock()
		mock_doc.enabled = True
		mock_doc.cdn_base_url = "https://cdn.example.com"
		mock_doc.local_fallback_mode = False
		mock_get_single.return_value = mock_doc

		settings = get_cdn_settings()

		self.assertEqual(settings["enabled"], True, "Should fetch enabled from DB")
		self.assertEqual(settings["cdn_base_url"], "https://cdn.example.com", "Should fetch cdn_base_url from DB")
		self.assertEqual(settings["local_fallback_mode"], False, "Should fetch local_fallback_mode from DB")
		mock_get_single.assert_called_once_with("CDN Settings"), "Should fetch from DB on cache miss"
		mock_cache_instance.set_value.assert_called_once(), "Should set cache after fetch"
