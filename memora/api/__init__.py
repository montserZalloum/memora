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
from .profile import get_player_profile, get_full_profile_stats
from .quests import get_daily_quests
from .leaderboard import get_leaderboard
from .onboarding import get_academic_masters, set_academic_profile
from .store import get_store_items, request_purchase

__all__ = [
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
]
