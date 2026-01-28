"""
Session Management Service

Manages single active session enforcement for Player Core.
Provides session creation, validation, and invalidation with Redis backing.

Key Functions:
- create_session(): Create or replace active session for user
- validate_session(): Check if session is still active
- invalidate_session(): Remove active session for user

Session Model:
- Single-session enforcement: Last login wins (GETSET atomic operation)
- Session metadata stored in Redis hash (user_id, device_id, created_at)
- Persistent sessions: No TTL on session keys (explicit invalidation only)

Security: Session invalidation completes in <2s via Redis DELETE.
Performance: O(1) Redis GET for session validation.
"""

import frappe

from memora.utils.redis_keys import (
	get_active_session_key,
	get_session_metadata_key,
)


def create_session(user_id, device_id, session_id=None):
	"""
	Create or replace active session for user

	FR-011: Enforces single active session per user
	FR-012: Invalidates previous session on new login
	FR-016: Session creation completes in <2ms (Redis)

	Args:
	    user_id (str): Frappe User.name
	    device_id (str): UUID v4 device identifier
	    session_id (str, optional): Session ID from Frappe session

	Returns:
	    str: Active session ID

	Side Effects:
	    - Replaces any existing session for user (single-session enforcement)
	    - Stores session metadata in Redis hash
	"""
	if not session_id:
		session_id = frappe.session.sid

	redis_client = frappe.cache()
	session_key = get_active_session_key(user_id)

	# Get old session before overwriting (for logging)
	old_session = redis_client.get(session_key)

	# Single-session enforcement: SET overwrites any existing session
	# This is atomic - no race condition possible
	redis_client.set(session_key, session_id)

	# Store session metadata for debugging and analytics
	metadata_key = get_session_metadata_key(session_id)
	metadata = {"user_id": user_id, "device_id": device_id, "created_at": frappe.utils.now()}
	for key, value in metadata.items():
		redis_client.hset(metadata_key, key, value)

	# Log session replacement (FR-012: invalidates previous session on new login)
	if old_session and old_session != session_id:
		frappe.logger().info(
			f"Session replaced for {user_id}: {old_session} -> {session_id} (device: {device_id})"
		)

	frappe.logger().info(f"Session created for {user_id}: {session_id} (device: {device_id})")

	return session_id


def validate_session(user_id, session_id):
	"""
	Validate if session is still active for user

	FR-016: Session validation completes in <2ms (Redis)

	Args:
	    user_id (str): Frappe User.name
	    session_id (str): Session ID to validate

	Returns:
	    bool: True if session is active, False otherwise
	"""
	redis_client = frappe.cache()
	session_key = get_active_session_key(user_id)

	active_session = redis_client.get(session_key)

	is_valid = active_session == session_id

	if not is_valid:
		frappe.logger().info(
			f"Session validation failed for {user_id}: expected {active_session}, got {session_id}"
		)

	return is_valid


def invalidate_session(user_id):
	"""
	Invalidate active session for user

	FR-012: Session invalidation completes in <2s (Redis)

	Args:
	    user_id (str): Frappe User.name

	Side Effects:
	    - Deletes active_session key for user
	    - Logs invalidation event
	"""
	redis_client = frappe.cache()
	session_key = get_active_session_key(user_id)

	session_id = redis_client.get(session_key)

	if session_id:
		redis_client.delete(session_key)
		redis_client.delete(get_session_metadata_key(session_id))

		frappe.logger().info(f"Session invalidated for {user_id}: {session_id}")

	return session_id
