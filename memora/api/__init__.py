"""
Memora API Package

This package reorganizes the monolithic api.py into domain-specific modules
for improved code navigation and maintainability.

All public @frappe.whitelist() functions are re-exported from this module
to maintain backward compatibility with existing code that imports from memora.api.

Modules:
- utils: Shared utility functions
- subjects: Subjects & Tracks domain
- map_engine: Map Engine domain
- sessions: Session & Gameplay domain
- srs: SRS/Memory algorithms
- reviews: Review Session domain
- profile: Profile domain
- quests: Daily Quests domain
- leaderboard: Leaderboard domain
- onboarding: Onboarding domain
- store: Store domain
"""

# Re-export all public functions from domain modules
from .subjects import get_subjects, get_my_subjects, get_game_tracks
from .map_engine import get_map_data, get_track_details,get_topic_details,get_unit_topics
from .sessions import submit_session, get_lesson_details
from .reviews import get_review_session, submit_review_session
from .profile import get_player_profile, get_full_profile_stats,get_player_login_info
from .quests import get_daily_quests
from .leaderboard import get_leaderboard
from .onboarding import get_academic_masters, set_academic_profile
from .store import get_store_items, request_purchase
from .user_access import get_user_access_keys
from ..json_builders.academic_cache import get_plan_version,rebuild_subject_skeleton

from .srs import (
    archive_season,
    get_archive_status,
    delete_eligible_archived_records,
    get_cache_status,
    rebuild_season_cache,
    trigger_reconciliation,
)

__all__ = [
    # JSON Builders
    'get_plan_version',
    'rebuild_subject_skeleton',
    # Subjects
    'get_subjects',
    'get_my_subjects',
    'get_game_tracks',
    # Map Engine
    'get_map_data',
    'get_topic_details',
    'get_track_details',
    'get_unit_topics',
    # Sessions
    'submit_session',
    'get_lesson_details',
    # Reviews
    'get_review_session',
    'submit_review_session',
    # Profile
    'get_user_access_keys',
    'get_player_login_info',
    'get_player_profile',
    'get_full_profile_stats',
    # Quests
    'get_daily_quests',
    # Leaderboard
    'get_leaderboard',
    # Onboarding
    'get_academic_masters',
    'set_academic_profile',
    # Store
    'get_store_items',
    'request_purchase',
    # SRS Scalability
    'archive_season',
    'get_archive_status',
    'delete_eligible_archived_records',
    'get_cache_status',
    'rebuild_season_cache',
    'trigger_reconciliation',
]
