"""
Play Page Controller for Jordan Project
Serves the React Frontend at /play
"""

import json
import os
from pathlib import Path
import frappe


def get_context(context):
	"""
	Load the Vite manifest and inject hashed asset paths
	"""

	# Hide Frappe header, footer, sidebar for immersive game experience
	context.no_header = 1
	context.no_footer = 1
	context.no_sidebar = 1

	# Get the app path
	app_path = frappe.get_app_path("memora")
	manifest_path = os.path.join(app_path, "public", "frontend", ".vite", "manifest.json")

	# Initialize variables
	game_js = None
	game_css = None

	try:
		# Check if manifest.json exists
		if os.path.exists(manifest_path):
			with open(manifest_path, 'r') as f:
				manifest = json.load(f)

			# Find the index.html entry point
			if 'index.html' in manifest:
				entry = manifest['index.html']

				# Get the main JS file
				if 'file' in entry:
					game_js = f"/assets/memora/frontend/{entry['file']}"

				# Get CSS imports
				if 'css' in entry and len(entry['css']) > 0:
					# Take the first CSS file (usually the main one)
					game_css = f"/assets/memora/frontend/{entry['css'][0]}"
		else:
			# Manifest not found, log warning
			frappe.logger().warning(f"Vite manifest not found at {manifest_path}")

	except Exception as e:
		frappe.logger().error(f"Error loading Vite manifest: {str(e)}")

	# Pass to template
	context.game_js = game_js
	context.game_css = game_css

	# Debugging in development
	if frappe.conf.developer_mode:
		print(f"[PLAY.PY] Manifest path: {manifest_path}")
		print(f"[PLAY.PY] game_js: {game_js}")
		print(f"[PLAY.PY] game_css: {game_css}")
