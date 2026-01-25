# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import re


class CDNSettings(Document):
	def validate(self):
		self.validate_endpoint_url()
		self.validate_bucket_name()
		self.validate_cloudflare_config()
		self.validate_signed_url_expiry()

	def validate_endpoint_url(self):
		"""Validate that endpoint_url is a valid URL."""
		if self.endpoint_url:
			url_pattern = re.compile(
				r'^https?://'  # http:// or https://
				r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
				r'localhost|'  # localhost
				r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
				r'(?::\d+)?'  # optional port
				r'(?:/?|[/?]\S+)$', re.IGNORECASE
			)
			if not url_pattern.match(self.endpoint_url):
				frappe.throw(_("Endpoint URL must be a valid URL"))

	def validate_bucket_name(self):
		"""Validate that bucket_name is not empty."""
		if not self.bucket_name or not self.bucket_name.strip():
			frappe.throw(_("Bucket Name is required"))

	def validate_cloudflare_config(self):
		"""Validate Cloudflare configuration for R2 provider."""
		if self.storage_provider == "Cloudflare R2":
			# Cloudflare config is optional, but if one is provided, both should be provided
			has_zone_id = self.cloudflare_zone_id and self.cloudflare_zone_id.strip()
			has_api_token = self.cloudflare_api_token and self.cloudflare_api_token.strip()
			
			if (has_zone_id and not has_api_token) or (has_api_token and not has_zone_id):
				frappe.throw(_("Both Cloudflare Zone ID and API Token are required for cache purge"))

	def validate_signed_url_expiry(self):
		"""Validate that signed_url_expiry_hours is between 1 and 24."""
		if self.signed_url_expiry_hours:
			try:
				expiry = int(self.signed_url_expiry_hours)
				if expiry < 1 or expiry > 24:
					frappe.throw(_("Signed URL Expiry must be between 1 and 24 hours"))
			except (ValueError, TypeError):
				frappe.throw(_("Signed URL Expiry must be a valid integer"))

	def before_save(self):
		"""Ensure proper defaults before saving."""
		if not self.batch_interval_minutes or self.batch_interval_minutes < 1:
			self.batch_interval_minutes = 5
		if not self.batch_threshold or self.batch_threshold < 1:
			self.batch_threshold = 50
		if not self.signed_url_expiry_hours or self.signed_url_expiry_hours < 1:
			self.signed_url_expiry_hours = 4

	def on_update(self):
		"""Invalidate CDN settings cache when settings change."""
		from memora.services.cdn_export.url_resolver import invalidate_settings_cache
		invalidate_settings_cache()
