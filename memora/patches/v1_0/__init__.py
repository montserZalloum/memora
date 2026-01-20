"""
Patches for Memora SRS Scalability v1.0

This directory contains database migration patches for the SRS scalability feature:
- fix_null_seasons: Set season for existing NULL records
- setup_partitioning: Apply LIST partitioning to Player Memory Tracker
- add_safe_mode_index: Create composite index for Safe Mode queries
"""

__version__ = '1.0'
