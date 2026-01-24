"""
Central registry of all Memora DocType definitions.

This module imports all DocType definitions in the correct order:
1. Child tables first (must be created before parent DocTypes reference them)
2. Content hierarchy DocTypes
3. Planning and commerce DocTypes
4. Player and engine DocTypes

The order is critical for database foreign key constraints.
"""

from memora.services.schema.definitions.child_tables import CHILD_TABLE_DEFINITIONS
from memora.services.schema.definitions.content_doctypes import CONTENT_DOCTYPE_DEFINITIONS
from memora.services.schema.definitions.planning_doctypes import PLANNING_DOCTYPE_DEFINITIONS
from memora.services.schema.definitions.player_doctypes import PLAYER_DOCTYPE_DEFINITIONS
from memora.services.schema.definitions.engine_doctypes import ENGINE_COMMERCE_DOCTYPE_DEFINITIONS

# Consolidated list of all DocType definitions in creation order
DOCTYPE_DEFINITIONS = [
	# Child tables must be created first
	*CHILD_TABLE_DEFINITIONS,
	# Content hierarchy
	*CONTENT_DOCTYPE_DEFINITIONS,
	# Planning and commerce
	*PLANNING_DOCTYPE_DEFINITIONS,
	# Player system
	*PLAYER_DOCTYPE_DEFINITIONS,
	# Engine and commerce
	*ENGINE_COMMERCE_DOCTYPE_DEFINITIONS,
]

__all__ = ["DOCTYPE_DEFINITIONS"]
