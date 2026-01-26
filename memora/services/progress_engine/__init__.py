"""
Progress Engine Service Module

This module provides high-performance progress tracking using Redis bitmaps.

Services:
    - bitmap_manager: Redis bitmap operations for lesson completion tracking
    - structure_loader: LRU-cached JSON structure loading
    - unlock_calculator: Linear/non-linear unlock logic computation
    - progress_computer: Main progress computation orchestration
    - xp_calculator: XP calculation with record-breaking bonuses
    - snapshot_syncer: 30-second batch sync to MariaDB
    - cache_warmer: Restore from MariaDB on cache miss
"""

from memora.services.progress_engine.bitmap_manager import (
    set_bit,
    check_bit,
    get_bitmap,
    update_bitmap,
    mark_dirty,
)
from memora.services.progress_engine.structure_loader import (
    load_subject_structure,
    clear_cache,
    validate_structure,
    get_lesson_bit_index,
    count_total_lessons,
    get_lesson_ids,
)
from memora.services.progress_engine.unlock_calculator import (
    compute_node_states,
    flatten_nodes,
    find_node_by_id,
)
from memora.services.progress_engine.progress_computer import (
    compute_progress,
    find_next_lesson,
)
from memora.services.progress_engine.xp_calculator import (
    calculate_xp,
)
from memora.services.progress_engine.cache_warmer import (
    warm_from_mariadb,
    warm_best_hearts_from_mariadb,
    warm_all_from_mariadb,
    warm_on_cache_miss,
    warm_best_hearts_on_cache_miss,
)
from memora.services.progress_engine.snapshot_syncer import (
    sync_pending_bitmaps,
    sync_best_hearts_with_bitmap,
)

__all__ = [
    "set_bit",
    "check_bit",
    "get_bitmap",
    "update_bitmap",
    "mark_dirty",
    "load_subject_structure",
    "clear_cache",
    "validate_structure",
    "get_lesson_bit_index",
    "count_total_lessons",
    "get_lesson_ids",
    "compute_node_states",
    "flatten_nodes",
    "find_node_by_id",
    "compute_progress",
    "find_next_lesson",
    "calculate_xp",
    "warm_from_mariadb",
    "warm_best_hearts_from_mariadb",
    "warm_all_from_mariadb",
    "warm_on_cache_miss",
    "warm_best_hearts_on_cache_miss",
    "sync_pending_bitmaps",
    "sync_best_hearts_with_bitmap",
]
