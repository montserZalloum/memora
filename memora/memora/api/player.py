"""
Player API Endpoints

RESTful API for Player Core functionality including:
- Device authorization and management
- Session validation and enforcement
- Wallet operations (XP, streak, last_played_at)
- Batch wallet synchronization triggers

Security Features:
- @require_authorized_device decorator enforces device authorization
- @rate_limit decorator prevents API abuse
- X-Device-ID header required for all authenticated endpoints
- X-RateLimit-* response headers for rate limit status

Performance Guarantees:
- Device/session check: <2ms (Redis)
- XP display: <1s (cache-first)
- Session invalidation: <2s (Redis)

Endpoints:
- POST /login (guest): Login with device authorization
- GET /check_device_authorization: Check current device status
- POST /register_device (admin): Add authorized device
- POST /remove_device (admin): Remove device
- GET /validate_session: Validate current session
- POST /logout: Invalidate session
- POST /complete_lesson: Complete lesson (update XP/streak)
- GET /get_wallet: Get wallet data (cache-first)
- POST /add_xp: Award XP
- POST /trigger_wallet_sync (admin): Manual batch sync
"""

import time
import uuid
from functools import wraps

import frappe

from memora.services import device_auth, session_manager, wallet_engine
from memora.utils.redis_keys import get_rate_limit_key


def validate_uuid(uuid_str, param_name="uuid"):
    """
    Validate UUID v4 format

    Args:
        uuid_str (str): String to validate
        param_name (str): Parameter name for error messages

    Raises:
        frappe.ValidationError: If UUID is invalid
    """
    try:
        uuid.UUID(uuid_str, version=4)
    except (ValueError, AttributeError, TypeError):
        frappe.throw(f"{param_name} must be a valid UUID v4", exc_type="ValidationError")


def validate_xp_amount(xp_amount):
    """
    Validate XP amount is within allowed range

    Args:
        xp_amount (int): XP amount to validate

    Raises:
        frappe.ValidationError: If XP amount is invalid
    """
    if not isinstance(xp_amount, int):
        frappe.throw("XP amount must be an integer", exc_type="ValidationError")
    if xp_amount < 1 or xp_amount > 1000:
        frappe.throw("XP amount must be between 1 and 1000", exc_type="ValidationError")


def validate_hearts_earned(hearts):
    """
    Validate hearts earned from lesson

    Args:
        hearts (int): Hearts earned (0-3)

    Raises:
        frappe.ValidationError: If hearts value is invalid
    """
    if not isinstance(hearts, int):
        frappe.throw("hearts_earned must be an integer", exc_type="ValidationError")
    if hearts < 0 or hearts > 3:
        frappe.throw("hearts_earned must be between 0 and 3", exc_type="ValidationError")


def validate_email(email):
    """
    Validate email format

    Args:
        email (str): Email to validate

    Raises:
        frappe.ValidationError: If email is invalid
    """
    if not email or "@" not in email or "." not in email:
        frappe.throw("Invalid email format", exc_type="ValidationError")


def log_security_event(event_type, user_id, device_id, endpoint, result, **kwargs):
    """
    Log security events for audit trail

    Args:
        event_type (str): Type of security event (e.g., "login", "rate_limit_exceeded")
        user_id (str): User identifier
        device_id (str): Device identifier
        endpoint (str): API endpoint name
        result (str): Result of operation (success/failure)
        **kwargs: Additional context
    """
    log_data = {
        "event_type": event_type,
        "user_id": user_id,
        "device_id": device_id,
        "endpoint": endpoint,
        "result": result,
        "timestamp": frappe.utils.now(),
        **kwargs
    }
    frappe.logger().info(f"Security Event: {event_type} - {log_data}")


def rate_limit(max_requests=100, window_seconds=60):
    """
    Decorator to enforce rate limiting per user per endpoint

    Uses Redis INCR with TTL for atomic rate limiting.
    Returns X-RateLimit-* headers on all responses.

    Args:
        max_requests (int): Maximum requests allowed in time window
        window_seconds (int): Time window in seconds

    Returns:
        Decorated function with rate limiting applied
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = frappe.session.user if frappe.session.user != "Guest" else None

            if not user_id:
                return fn(*args, **kwargs)

            if "System Manager" in frappe.get_roles():
                return fn(*args, **kwargs)

            redis_client = frappe.cache()
            function_name = fn.__name__
            rate_limit_key = get_rate_limit_key(user_id, function_name)

            current_count = redis_client.incr(rate_limit_key)

            if current_count == 1:
                redis_client.expire(rate_limit_key, window_seconds)

            ttl = redis_client.ttl(rate_limit_key) if current_count >= max_requests else window_seconds

            if current_count > max_requests:
                log_security_event(
                    event_type="rate_limit_exceeded",
                    user_id=user_id,
                    device_id=frappe.get_request_header("X-Device-ID"),
                    endpoint=function_name,
                    result="rejected",
                    current_count=current_count,
                    max_requests=max_requests
                )

                frappe.local.response.headers["X-RateLimit-Limit"] = str(max_requests)
                frappe.local.response.headers["X-RateLimit-Remaining"] = "0"
                frappe.local.response.headers["X-RateLimit-Reset"] = str(int(time.time()) + ttl)
                frappe.throw(
                    f"Rate limit exceeded: {max_requests} requests per {window_seconds}s. "
                    f"Please wait {ttl} seconds before retrying.",
                    exc_type="RateLimitExceeded",
                    http_status_code=429
                )

            frappe.local.response.headers["X-RateLimit-Limit"] = str(max_requests)
            frappe.local.response.headers["X-RateLimit-Remaining"] = str(max_requests - current_count)
            frappe.local.response.headers["X-RateLimit-Reset"] = str(int(time.time()) + ttl)

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_authorized_device(fn):
    """
    Decorator to enforce device authorization and session validation on API endpoints

    FR-007: Reject unauthorized devices
    FR-010: Complete device check in <2ms (Redis-backed)
    FR-011: Enforce single active session
    FR-016: Complete session check in <2ms (Redis-backed)

    Args:
        fn: API function to wrap

    Returns:
        Wrapped function that checks device authorization and session validity before calling fn
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = frappe.session.user
        device_id = frappe.get_request_header("X-Device-ID")

        if not device_id:
            log_security_event(
                event_type="missing_device_id",
                user_id=user_id,
                device_id=None,
                endpoint=fn.__name__,
                result="rejected"
            )
            frappe.throw("X-Device-ID header required", exc_type="MissingDeviceError")

        if not device_auth.is_device_authorized(user_id, device_id):
            log_security_event(
                event_type="unauthorized_device",
                user_id=user_id,
                device_id=device_id,
                endpoint=fn.__name__,
                result="rejected"
            )
            frappe.throw(
                "Unauthorized device. Contact administrator to authorize this device.",
                exc_type="UnauthorizedDeviceError"
            )

        session_id = frappe.session.sid
        if not session_manager.validate_session(user_id, session_id):
            log_security_event(
                event_type="session_invalidated",
                user_id=user_id,
                device_id=device_id,
                endpoint=fn.__name__,
                result="rejected",
                session_id=session_id
            )
            frappe.throw(
                "Session invalidated. Another device has logged in. Please log in again.",
                exc_type="SessionExpiredError"
            )

        wallet_engine.update_last_played_at(user_id)

        return fn(*args, **kwargs)
    return wrapper


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(max_requests=5, window_seconds=60)
def login(usr, pwd, device_name=None):
    """
    Student login with device authorization

    FR-005a: First device auto-authorized on account creation
    FR-011: Enforces single active session
    FR-012: Invalidates previous session on new login

    Args:
        usr (str): Student email
        pwd (str): Student password
        device_name (str, optional): Device name for first device auto-authorization

    Returns:
        dict: Login response with session info

    Raises:
        frappe.AuthenticationError: Invalid credentials
        frappe.PermissionError: Device not authorized
    """
    device_id = frappe.get_request_header("X-Device-ID")

    if not device_id:
        log_security_event(
            event_type="missing_device_id",
            user_id=usr,
            device_id=None,
            endpoint="login",
            result="rejected"
        )
        frappe.throw("X-Device-ID header required", exc_type="MissingDeviceError")

    validate_email(usr)

    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(usr, pwd)
        login_manager.post_login()
    except frappe.AuthenticationError:
        log_security_event(
            event_type="login_failed",
            user_id=usr,
            device_id=device_id,
            endpoint="login",
            result="failed",
            reason="invalid_credentials"
        )
        raise

    user_id = login_manager.user

    profile = frappe.db.get_value(
        "Memora Player Profile",
        {"user": user_id},
        ["name", "user", "authorized_devices"]
    )

    if not profile:
        frappe.throw("Player profile not found. Please contact administrator.")

    profile_name = profile["name"]

    existing_devices = frappe.get_all(
        "Memora Authorized Device",
        filters={"parent": profile_name},
        fields=["device_id"]
    )

    if len(existing_devices) == 0:
        first_device = frappe.get_doc({
            "doctype": "Memora Authorized Device",
            "parent": profile_name,
            "parenttype": "Memora Player Profile",
            "device_id": device_id,
            "device_name": device_name or "First Device (Auto-authorized)",
            "added_on": frappe.utils.now()
        })
        first_device.insert(ignore_permissions=True)

        redis_client = frappe.cache()
        redis_client.sadd(f"player:{user_id}:devices", device_id)

        frappe.logger().info(f"First device auto-authorized for {user_id}: {device_id}")

        devices_authorized = 1
        is_first_device = True
    elif not device_auth.is_device_authorized(user_id, device_id):
        log_security_event(
            event_type="unauthorized_device",
            user_id=user_id,
            device_id=device_id,
            endpoint="login",
            result="rejected"
        )
        frappe.throw(
            "Unauthorized device. Contact administrator to authorize this device.",
            exc_type="UnauthorizedDeviceError"
        )
    else:
        devices_authorized = len(existing_devices)
        is_first_device = False

    session_id = session_manager.create_session(user_id, device_id, frappe.session.sid)

    log_security_event(
        event_type="login_success",
        user_id=user_id,
        device_id=device_id,
        endpoint="login",
        result="success",
        is_first_device=is_first_device
    )

    return {
        "message": "Logged in successfully",
        "session_id": session_id,
        "is_first_device": is_first_device,
        "devices_authorized": devices_authorized
    }


@frappe.whitelist(allow_guest=False, methods=["GET"])
@require_authorized_device
def check_device_authorization():
    """
    Check if current device is authorized

    FR-007: Reject unauthorized devices
    FR-010: Complete check in <2ms (Redis-backed)

    Returns:
        dict: Authorization status with device count
    """
    user_id = frappe.session.user

    profile_name = frappe.db.get_value(
        "Memora Player Profile",
        {"user": user_id},
        "name"
    )

    if not profile_name:
        return {
            "authorized": False,
            "device_count": 0
        }

    device_count = len(frappe.get_all(
        "Memora Authorized Device",
        filters={"parent": profile_name},
        fields=["name"]
    ))

    device_id = frappe.get_request_header("X-Device-ID")
    authorized = device_auth.is_device_authorized(user_id, device_id)

    return {
        "authorized": authorized,
        "device_count": device_count
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
@rate_limit(max_requests=3, window_seconds=3600)
def register_device(student_email, device_id, device_name):
    """
    Register a new authorized device

    FR-009: Only administrators can add devices
    FR-005b: Maximum 2 devices per student
    FR-009a: Cannot add third device without removing existing

    Args:
        student_email (str): Student's email
        device_id (str): UUID v4 device identifier
        device_name (str): Human-readable device name

    Returns:
        dict: Registration result

    Raises:
        frappe.PermissionError: Not a System Manager
        frappe.ValidationError: Device limit exceeded or invalid UUID
    """
    validate_email(student_email)
    validate_uuid(device_id, "device_id")

    if not device_name or len(device_name) < 3 or len(device_name) > 100:
        frappe.throw("device_name must be between 3 and 100 characters", exc_type="ValidationError")

    if "System Manager" not in frappe.get_roles():
        log_security_event(
            event_type="unauthorized_admin_action",
            user_id=frappe.session.user,
            device_id=frappe.get_request_header("X-Device-ID"),
            endpoint="register_device",
            result="rejected",
            action="register_device",
            target_user=student_email
        )
        frappe.throw("Only System Manager can register devices", exc_type="PermissionError")

    profile_name = frappe.db.get_value(
        "Memora Player Profile",
        {"user": student_email},
        "name"
    )

    if not profile_name:
        frappe.throw("Player profile not found for this student")

    device_auth.add_authorized_device(profile_name, device_id, device_name)

    device_count = len(frappe.get_all(
        "Memora Authorized Device",
        filters={"parent": profile_name},
        fields=["name"]
    ))

    log_security_event(
        event_type="device_registered",
        user_id=frappe.session.user,
        device_id=frappe.get_request_header("X-Device-ID"),
        endpoint="register_device",
        result="success",
        target_user=student_email,
        registered_device=device_id
    )

    return {
        "message": "Device registered successfully",
        "device_id": device_id,
        "authorized_devices_count": device_count
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
@rate_limit(max_requests=10, window_seconds=3600)
def remove_device(student_email, device_id):
    """
    Remove an authorized device

    FR-009: Only administrators can remove devices

    Side Effects:
    - Invalidates active session if student was logged in on this device
    - Removes device from Redis cache immediately

    Args:
        student_email (str): Student's email
        device_id (str): UUID v4 device identifier

    Returns:
        dict: Removal result

    Raises:
        frappe.PermissionError: Not a System Manager
        frappe.ValidationError: Device not found
    """
    validate_email(student_email)
    validate_uuid(device_id, "device_id")

    if "System Manager" not in frappe.get_roles():
        log_security_event(
            event_type="unauthorized_admin_action",
            user_id=frappe.session.user,
            device_id=frappe.get_request_header("X-Device-ID"),
            endpoint="remove_device",
            result="rejected",
            action="remove_device",
            target_user=student_email
        )
        frappe.throw("Only System Manager can remove devices", exc_type="PermissionError")

    profile_name = frappe.db.get_value(
        "Memora Player Profile",
        {"user": student_email},
        "name"
    )

    if not profile_name:
        frappe.throw("Player profile not found for this student")

    device_auth.remove_authorized_device(profile_name, device_id)

    log_security_event(
        event_type="device_removed",
        user_id=frappe.session.user,
        device_id=frappe.get_request_header("X-Device-ID"),
        endpoint="remove_device",
        result="success",
        target_user=student_email,
        removed_device=device_id
    )

    return {
        "message": "Device removed and session invalidated"
    }


@frappe.whitelist(allow_guest=False, methods=["GET"])
@require_authorized_device
def validate_session():
    """
    Validate current session

    FR-011: Single active session enforcement
    FR-016: Session validation in <2ms (Redis-backed)

    Returns:
        dict: Session validation status

    Raises:
        frappe.PermissionError: Session invalidated or device not authorized
    """
    user_id = frappe.session.user
    session_id = frappe.session.sid

    is_valid = session_manager.validate_session(user_id, session_id)

    return {
        "valid": is_valid,
        "session_id": session_id
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def logout():
    """
    Logout and invalidate current session

    FR-012: Session invalidation completes in <2s (Redis-backed)

    Side Effects:
    - Invalidates active session for user
    - Clears session metadata from Redis

    Returns:
        dict: Logout result
    """
    user_id = frappe.session.user
    session_id = frappe.session.sid

    session_manager.invalidate_session(user_id)

    log_security_event(
        event_type="logout",
        user_id=user_id,
        device_id=frappe.get_request_header("X-Device-ID"),
        endpoint="logout",
        result="success",
        session_id=session_id
    )

    frappe.logger().info(f"Logout successful for {user_id}, session {session_id}")

    return {
        "message": "Logged out successfully"
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
@require_authorized_device
@rate_limit(max_requests=10, window_seconds=60)
def complete_lesson(lesson_id, hearts_earned):
    """
    Complete a lesson and update streak and XP

    FR-022 through FR-028: Streak calculation logic
    FR-025: Streak increments only once per day
    FR-027: Server time authority (prevents client manipulation)
    FR-031: XP awarded based on hearts * 10 formula

    Args:
        lesson_id (str): ID of completed lesson
        hearts_earned (int): Hearts earned from lesson (must be > 0)

    Returns:
        dict: Completion result with streak and XP update details

    Raises:
        frappe.ValidationError: Invalid hearts_earned value
        frappe.PermissionError: Device not authorized or session invalid
    """
    validate_hearts_earned(hearts_earned)

    if not lesson_id or not isinstance(lesson_id, str):
        frappe.throw("lesson_id is required and must be a string", exc_type="ValidationError")

    user_id = frappe.session.user

    streak_result = wallet_engine.update_streak(user_id, hearts_earned)

    xp_awarded = hearts_earned * 10
    new_total_xp = wallet_engine.add_xp(user_id, xp_awarded)

    log_security_event(
        event_type="lesson_completed",
        user_id=user_id,
        device_id=frappe.get_request_header("X-Device-ID"),
        endpoint="complete_lesson",
        result="success",
        lesson_id=lesson_id,
        hearts_earned=hearts_earned,
        xp_awarded=xp_awarded,
        streak_action=streak_result.get("streak_action")
    )

    frappe.logger().info(
        f"Lesson {lesson_id} completed by {user_id}, "
        f"hearts={hearts_earned}, xp=+{xp_awarded}, new_xp={new_total_xp}, "
        f"streak {streak_result.get('streak_action')}: "
        f"{streak_result.get('old_streak')} -> {streak_result.get('new_streak')}"
    )

    return {
        "message": "Lesson completed successfully",
        "lesson_id": lesson_id,
        "hearts_earned": hearts_earned,
        "xp": {
            "awarded": xp_awarded,
            "new_total": new_total_xp
        },
        "streak": {
            "old_streak": streak_result.get("old_streak"),
            "new_streak": streak_result.get("new_streak"),
            "action": streak_result.get("streak_action"),
            "last_success_date": streak_result.get("last_success_date")
        }
    }


@frappe.whitelist(allow_guest=False, methods=["GET"])
@require_authorized_device
@rate_limit(max_requests=60, window_seconds=60)
def get_wallet():
    """
    Get current player wallet (cache-first)

    FR-019a: Always read from Redis first for <1s response time
    FR-019b: Return total_xp, current_streak, last_success_date, last_played_at

    Returns:
        dict: Wallet data with total_xp, current_streak, last_success_date, last_played_at

    Raises:
        frappe.PermissionError: Device not authorized or session invalid
    """
    user_id = frappe.session.user

    wallet_data = wallet_engine.get_wallet_safe(user_id)

    frappe.logger().debug(f"Wallet retrieved for {user_id}: XP={wallet_data.get('total_xp')}")

    return {
        "total_xp": int(wallet_data.get("total_xp", 0)),
        "current_streak": int(wallet_data.get("current_streak", 0)),
        "last_success_date": wallet_data.get("last_success_date"),
        "last_played_at": wallet_data.get("last_played_at")
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
@require_authorized_device
@rate_limit(max_requests=10, window_seconds=60)
def add_xp(xp_amount):
    """
    Award XP to player

    FR-031: XP award with immediate Redis update
    FR-034: User added to pending_wallet_sync set for batch sync

    Args:
        xp_amount (int): XP to add (must be positive)

    Returns:
        dict: XP award result with new total

    Raises:
        frappe.ValidationError: If xp_amount is negative or zero
        frappe.PermissionError: Device not authorized or session invalid
    """
    validate_xp_amount(xp_amount)

    user_id = frappe.session.user

    new_total_xp = wallet_engine.add_xp(user_id, xp_amount)

    log_security_event(
        event_type="xp_awarded",
        user_id=user_id,
        device_id=frappe.get_request_header("X-Device-ID"),
        endpoint="add_xp",
        result="success",
        xp_amount=xp_amount,
        new_total_xp=new_total_xp
    )

    return {
        "message": "XP awarded successfully",
        "xp_awarded": xp_amount,
        "new_total_xp": new_total_xp
    }


@frappe.whitelist(allow_guest=False, methods=["POST"])
def trigger_wallet_sync(force=False):
    """
    Manually trigger wallet sync (System Manager only)

    FR-035: Run every 15 minutes (scheduled via hooks.py)
    FR-036: Process in chunks of 500 players maximum

    Args:
        force (bool): If True, sync all active users regardless of queue

    Returns:
        dict: Sync results with count and duration

    Raises:
        frappe.PermissionError: If user is not System Manager
    """
    if "System Manager" not in frappe.get_roles():
        log_security_event(
            event_type="unauthorized_admin_action",
            user_id=frappe.session.user,
            device_id=frappe.get_request_header("X-Device-ID"),
            endpoint="trigger_wallet_sync",
            result="rejected",
            action="trigger_wallet_sync"
        )
        frappe.throw("Only System Manager can trigger wallet sync", exc_type="PermissionError")

    from memora.services.wallet_sync import trigger_wallet_sync as sync_trigger

    result = sync_trigger(force=force)

    log_security_event(
        event_type="wallet_sync_triggered",
        user_id=frappe.session.user,
        device_id=frappe.get_request_header("X-Device-ID"),
        endpoint="trigger_wallet_sync",
        result="success",
        force=force,
        synced_count=result.get("synced", 0)
    )

    return result

