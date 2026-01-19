# API Contracts: API Module Reorganization

**Date**: 2026-01-19
**Feature**: 002-api-reorganization

## Overview

**No API contract changes required.**

This feature reorganizes the internal code structure without modifying any API signatures, request/response formats, or endpoint paths.

## Preserved Endpoints

All existing `@frappe.whitelist()` endpoints remain unchanged:

### Subjects Module
- `get_subjects()` → Returns list of subjects for current user
- `get_my_subjects()` → Returns subjects with metadata
- `get_game_tracks(subject)` → Returns learning tracks for a subject

### Map Module
- `get_map_data(subject=None)` → Returns map structure with units/topics
- `get_lesson_details(lesson_id)` → Returns lesson configuration
- `get_topic_details(topic_id)` → Returns topic with lessons

### SRS Module
- `get_review_session(subject=None, topic_id=None)` → Returns quiz cards for review
- `submit_review_session(session_data)` → Processes review answers
- `submit_session(session_meta, gamification_results, interactions)` → Records gameplay session

### Profile Module
- `get_player_profile()` → Returns basic player stats
- `get_full_profile_stats(subject=None)` → Returns detailed profile
- `get_daily_quests(subject=None)` → Returns daily missions

### Leaderboard Module
- `get_leaderboard(subject=None, period='all_time')` → Returns rankings

### Store Module
- `get_store_items()` → Returns available store items
- `request_purchase(item_id, transaction_id=None)` → Initiates purchase request

### Onboarding Module
- `get_academic_masters()` → Returns grades/streams for onboarding
- `set_academic_profile(grade, stream=None)` → Sets user academic profile

## Verification

After implementation, verify each endpoint responds identically by:
1. Calling via Frappe API: `/api/method/memora.api.{function_name}`
2. Comparing response structure and data with pre-refactoring responses
