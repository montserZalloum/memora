app_name = "memora"
app_title = "Memora"
app_publisher = "corex"
app_description = "gamefication"
app_email = "dev@corex.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

doctype_js = {}

after_migrate = [
	
]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "memora",
# 		"logo": "/assets/memora/logo.png",
# 		"title": "Memora",
# 		"route": "/memora",
# 		"has_permission": "memora.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/memora/css/memora.css"
# app_include_js = "/assets/memora/js/memora.js"

# include js, css files in header of web template
# web_include_css = "/assets/memora/css/memora.css"
# web_include_js = "/assets/memora/js/memora.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "memora/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "memora/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "memora.utils.jinja_methods",
# 	"filters": "memora.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "memora.install.before_install"
# after_install = "memora.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "memora.uninstall.before_uninstall"
# after_uninstall = "memora.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "memora.utils.before_app_install"
# after_app_install = "memora.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "memora.utils.before_app_uninstall"
# after_app_uninstall = "memora.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "memora.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# CDN CONTENT EXPORT - Document Event Handlers
# ============================================
# These events track changes to educational content and trigger CDN synchronization.
#
# FLOW:
#   1. Content change (on_update, on_trash, after_delete, on_restore)
#   2. Handler queues affected plans to Redis queue or fallback MariaDB
#   3. Scheduler processes queue every 5 minutes or at 50-plan threshold
#   4. Plans rebuild JSON files and upload to CDN
#   5. Cache is purged on CDN (Cloudflare)
#
# HANDLERS:
#   - on_update: Content modified - queue plans for rebuild
#   - on_trash: Content marked for deletion - queue plans for rebuild
#   - after_delete: Content permanently deleted - queue plans for rebuild
#   - on_restore: Trashed content restored - queue plans for rebuild (treats as new)
#
# ERROR HANDLING:
#   - All handlers catch exceptions and log via frappe.log_error()
#   - Redis queue operations have MariaDB fallback (CDN Sync Log table)
#   - Locks prevent concurrent plan builds
#
# DEPENDENCY RESOLUTION:
#   - Uses get_affected_plan_ids() from dependency_resolver
#   - Walks up content hierarchy (Lesson -> Topic -> Unit -> Track -> Subject -> Plan)
#   - Prevents duplicate plan entries via Redis Set
#
doc_events = {
	# SUBJECT CONTENT HIERARCHY
	# ========================
	# Changes to subjects affect all plans using that subject
	"Memora Subject": {
		# on_update: Triggered when subject name, description, image, access fields change
		"on_update": "memora.services.cdn_export.change_tracker.on_subject_update",
		# on_trash: Subject moved to trash - queues plans for rebuild
		"on_trash": "memora.services.cdn_export.change_tracker.on_subject_delete",
		# after_delete: Subject permanently deleted from database - queues plans for rebuild
		"after_delete": "memora.services.cdn_export.change_tracker.on_subject_delete",
		# on_restore: Trashed subject restored - treats as new content, queues plans
		"on_restore": "memora.services.cdn_export.change_tracker.on_content_restore"
	},

	# TRACK CONTENT HIERARCHY
	# ======================
	# Tracks belong to subjects; changes affect parent subject's plans
	"Memora Track": {
		# on_update: Track properties or access fields changed
		"on_update": "memora.services.cdn_export.change_tracker.on_track_update",
		# on_trash/after_delete: Track removed - parent unit references updated on rebuild
		"on_trash": "memora.services.cdn_export.change_tracker.on_track_delete",
		"after_delete": "memora.services.cdn_export.change_tracker.on_track_delete",
		"on_restore": "memora.services.cdn_export.change_tracker.on_content_restore"
	},

	# UNIT CONTENT HIERARCHY
	# =====================
	# Units belong to tracks; changes affect ancestor subject's plans
	"Memora Unit": {
		# on_update: Unit name, description, or fields changed
		"on_update": "memora.services.cdn_export.change_tracker.on_unit_update",
		# on_trash/after_delete: Unit removed - parent track references cleaned up
		"on_trash": "memora.services.cdn_export.change_tracker.on_unit_delete",
		"after_delete": "memora.services.cdn_export.change_tracker.on_unit_delete",
		"on_restore": "memora.services.cdn_export.change_tracker.on_content_restore"
	},

	# TOPIC CONTENT HIERARCHY
	# ======================
	# Topics belong to units; changes affect ancestor subject's plans
	"Memora Topic": {
		# on_update: Topic name or fields changed
		"on_update": "memora.services.cdn_export.change_tracker.on_topic_update",
		# on_trash/after_delete: Topic removed - unit's topic list updated
		"on_trash": "memora.services.cdn_export.change_tracker.on_topic_delete",
		"after_delete": "memora.services.cdn_export.change_tracker.on_topic_delete",
		"on_restore": "memora.services.cdn_export.change_tracker.on_content_restore"
	},

	# LESSON CONTENT (LEAF NODE)
	# ==========================
	# Lessons belong to topics; most common changes trigger plan rebuilds
	"Memora Lesson": {
		# on_update: Lesson content, title, or stages modified
		"on_update": "memora.services.cdn_export.change_tracker.on_lesson_update",
		# on_trash/after_delete: Lesson removed - topic removes from lessons list
		"on_trash": "memora.services.cdn_export.change_tracker.on_lesson_delete",
		"after_delete": "memora.services.cdn_export.change_tracker.on_lesson_delete",
		"on_restore": "memora.services.cdn_export.change_tracker.on_content_restore"
	},

	# LESSON STAGE CONTENT
	# ====================
	# Lesson stages (child table) contain video configs and interactive content
	"Memora Lesson Stage": {
		# on_update: Stage content, video URL, or quiz changed
		"on_update": "memora.services.cdn_export.change_tracker.on_lesson_stage_update",
		# on_trash/after_delete: Stage removed from lesson - triggers parent lesson rebuild
		"on_trash": "memora.services.cdn_export.change_tracker.on_lesson_stage_delete",
		"after_delete": "memora.services.cdn_export.change_tracker.on_lesson_stage_delete",
		"on_restore": "memora.services.cdn_export.change_tracker.on_content_restore"
	},

	# PLAN MANAGEMENT
	# ===============
	# Academic Plans reference subject content; plan changes trigger own rebuild
	"Memora Academic Plan": {
		# on_update: Plan published status, grade, season, or subject assignments changed
		"on_update": "memora.services.cdn_export.change_tracker.on_plan_update",
		# on_trash/after_delete: Plan deleted - entire plan folder removed from CDN
		"on_trash": "memora.services.cdn_export.change_tracker.on_plan_delete",
		"after_delete": "memora.services.cdn_export.change_tracker.on_plan_delete"
	},

	# PLAN ACCESS OVERRIDES
	# =====================
	# Plan overrides (Hide, Set Free, Set Sold Separately) affect access levels in JSON
	"Memora Plan Override": {
		# on_update: Override action or target changed - parent plan requires rebuild
		"on_update": "memora.services.cdn_export.change_tracker.on_override_update",
		# on_trash: Override removed - parent plan access levels revert, trigger rebuild
		"on_trash": "memora.services.cdn_export.change_tracker.on_override_update"
	}
}

# Scheduled Tasks
# ---------------

# CDN CONTENT EXPORT - Scheduler Events
# ======================================
# Background job processing for CDN content generation and upload
#
# SCHEDULER: process_pending_plans
# --------------------------------
# - Frequency: Every hour (via Frappe hourly scheduler)
# - NOTE: The batch_interval_minutes in CDN Settings is for documentation only.
#   Actual frequency is hourly per Frappe scheduler constraints.
#   For more frequent processing, modify this to "All" or use Cron frequency.
# - Max plans per run: 10 (prevents overload)
# - Early trigger: Processes immediately if 50+ plans queued (threshold)
#   This happens via frappe.enqueue() call in change_tracker.py
# - Processing:
#   1. Acquire exclusive lock for each plan (prevents concurrent builds)
#   2. Create CDN Sync Log entry with "Processing" status
#   3. Generate JSON files (manifest, subjects, units, lessons, search index)
#   4. Validate JSON against schemas
#   5. Upload files to S3/Cloudflare R2
#   6. Purge Cloudflare cache (if configured)
#   7. Update CDN Sync Log with success/failure status
#
# RETRY LOGIC:
# - Retry 1: 30 seconds delay
# - Retry 2: 1 minute delay
# - Retry 3: 2 minutes delay
# - Retry 4: 5 minutes delay
# - Retry 5: 15 minutes delay
# - After 5 failures: Move to dead-letter queue for manual intervention
#
# QUEUE MANAGEMENT:
# - Primary: Redis Set "cdn_export:pending_plans" (fast, in-memory)
# - Fallback: CDN Sync Log table with is_fallback=1 flag (when Redis down)
# - Dead-letter: Redis Hash "cdn_export:dead_letter" (failed plans)
# - Locking: Redis key "cdn_export:lock:{plan_id}" with 5-min TTL
#
# ERROR HANDLING:
# - All errors logged to frappe error log
# - Sync status tracked in CDN Sync Log DocType
# - Failed uploads don't block other plan processing
# - Cache purge failures non-blocking (content still updated)
#
# MONITORING:
# - View status: Memora > CDN Export Status (dashboard)
# - View logs: Memora > CDN Sync Log (list view)
# - Dead-letter: API endpoint /api/method/memora.api.cdn_admin.get_queue_status
#
# CONFIGURATION (via CDN Settings):
# - batch_interval_minutes: For future use - currently fixed to hourly by Frappe scheduler (default: 5)
# - batch_threshold: Immediate processing when queue >= this via frappe.enqueue() (default: 50)
# - enabled: Master switch to enable/disable CDN export (default: 0)
# NOTE: For more frequent processing, deploy custom scheduler or use "All" frequency
#
scheduler_events = {
	"Hourly": [
		"memora.services.cdn_export.batch_processor.process_pending_plans",
		"memora.services.cdn_export.health_checker.hourly_health_check"
	],
	"Daily": [
		"memora.services.cdn_export.health_checker.daily_full_scan"
	],
	"All": [
		"memora.services.progress_engine.snapshot_syncer.sync_pending_bitmaps"
	],
	"cron": {
		"*/15 * * * *": [
			"memora.services.wallet_sync.sync_pending_wallets"
		]
	}
}

# Testing
# -------

# before_tests = "memora.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "memora.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "memora.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["memora.utils.before_request"]
# after_request = ["memora.utils.after_request"]

# Job Events
# ----------
# before_job = ["memora.utils.before_job"]
# after_job = ["memora.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"memora.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

