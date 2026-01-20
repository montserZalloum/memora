#!/usr/bin/env python
# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Safe Mode Test: Verify fallback when Redis is unavailable

This script tests Safe Mode functionality by:
1. Stopping Redis service
2. Attempting to retrieve due reviews
3. Verifying Safe Mode fallback activates
4. Verifying rate limiting works
5. Restarting Redis and verifying normal mode resumes

Usage:
    # First, ensure Redis is running
    redis-cli -p 13000 ping  # Should return PONG

    # Run the test
    python memora/tests/safe_mode_test.py

    # The script will guide you through stopping/starting Redis
"""

import time
import subprocess
import sys

try:
    import frappe
    from memora.api.utils import SafeModeManager
    from memora.services.srs_redis_manager import SRSRedisManager
    FRAPPE_AVAILABLE = True
except ImportError:
    FRAPPE_AVAILABLE = False
    print("Warning: Frappe not available. Running in standalone mode.")


class SafeModeTest:
    """Test Safe Mode fallback functionality"""

    def __init__(self):
        """Initialize Safe Mode test"""
        self.redis_port = 13000
        self.safe_mode_manager = None
        self.redis_manager = None

        if FRAPPE_AVAILABLE:
            self.safe_mode_manager = SafeModeManager()
            self.redis_manager = SRSRedisManager()
            self.test_user = "safe-mode-test@example.com"
            self.test_season = "SAFE-MODE-TEST"
        else:
            print("Frappe environment required for Safe Mode testing")
            sys.exit(1)

    def check_redis_status(self) -> bool:
        """
        Check if Redis is running

        Returns:
            bool: True if Redis is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["redis-cli", "-p", str(self.redis_port), "ping"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and "PONG" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def stop_redis(self):
        """Stop Redis service"""
        print("\n" + "=" * 60)
        print("STOPPING REDIS")
        print("=" * 60)

        # Try to stop Redis using redis-cli
        try:
            subprocess.run(
                ["redis-cli", "-p", str(self.redis_port), "shutdown"],
                capture_output=True,
                timeout=5
            )
            print("Redis shutdown command sent")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("Note: Could not shutdown Redis via CLI")
            print("Please manually stop Redis and press Enter to continue...")
            input()

        # Wait for Redis to stop
        print("Waiting for Redis to stop...")
        time.sleep(3)

        if not self.check_redis_status():
            print("✓ Redis is now stopped")
        else:
            print("⚠ Warning: Redis may still be running")
            print("  Please manually stop Redis before continuing")

    def start_redis(self):
        """Start Redis service"""
        print("\n" + "=" * 60)
        print("STARTING REDIS")
        print("=" * 60)

        # Try to start Redis
        try:
            subprocess.run(
                ["redis-server", "--port", str(self.redis_port), "--daemonize", "yes"],
                capture_output=True,
                timeout=5
            )
            print("Redis start command sent")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("Note: Could not start Redis via CLI")
            print("Please manually start Redis and press Enter to continue...")
            input()

        # Wait for Redis to start
        print("Waiting for Redis to start...")
        for i in range(10):
            time.sleep(1)
            if self.check_redis_status():
                print("✓ Redis is now running")
                return True
            print(f"  Waiting... ({i+1}/10)")

        print("⚠ Warning: Redis may not have started")
        return False

    def test_redis_availability(self, expected_available: bool) -> bool:
        """
        Test if Redis availability matches expectation

        Args:
            expected_available: Whether Redis should be available

        Returns:
            bool: True if test passes, False otherwise
        """
        is_available = self.redis_manager.is_available()

        if is_available == expected_available:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"

        print(f"\nRedis Availability Test:")
        print(f"  Expected: {'Available' if expected_available else 'Unavailable'}")
        print(f"  Actual:   {'Available' if is_available else 'Unavailable'}")
        print(f"  Status:    {status}")

        return is_available == expected_available

    def test_safe_mode_activation(self) -> bool:
        """
        Test if Safe Mode activates when Redis is unavailable

        Returns:
            bool: True if Safe Mode activates correctly
        """
        print("\n" + "=" * 60)
        print("SAFE MODE ACTIVATION TEST")
        print("=" * 60)

        is_safe_mode = self.safe_mode_manager.is_safe_mode_active()

        if is_safe_mode:
            print("✓ Safe Mode is ACTIVE")
            print("  Safe Mode correctly detected Redis unavailability")
            return True
        else:
            print("✗ Safe Mode is NOT ACTIVE")
            print("  Safe Mode should activate when Redis is unavailable")
            return False

    def test_rate_limiting(self) -> bool:
        """
        Test if rate limiting works in Safe Mode

        Returns:
            bool: True if rate limiting works correctly
        """
        print("\n" + "=" * 60)
        print("RATE LIMITING TEST")
        print("=" * 60)
        print("Testing per-user rate limit (1 request per 30 seconds)...")

        # First request should be allowed
        allowed_1 = self.safe_mode_manager.check_rate_limit(self.test_user)
        print(f"\nFirst request:  {'✓ ALLOWED' if allowed_1 else '✗ BLOCKED'}")

        # Immediate second request should be blocked
        allowed_2 = self.safe_mode_manager.check_rate_limit(self.test_user)
        print(f"Second request: {'✗ BLOCKED' if not allowed_2 else '✓ ALLOWED (ERROR)'}")

        # Wait 30 seconds and try again
        print("\nWaiting 30 seconds for rate limit to expire...")
        time.sleep(30)

        allowed_3 = self.safe_mode_manager.check_rate_limit(self.test_user)
        print(f"Third request:  {'✓ ALLOWED' if allowed_3 else '✗ BLOCKED (ERROR)'}")

        # Check if rate limiting works correctly
        if allowed_1 and not allowed_2 and allowed_3:
            print("\n✓ Rate limiting works correctly")
            print("  First request allowed")
            print("  Second request blocked (within 30s window)")
            print("  Third request allowed (after 30s)")
            return True
        else:
            print("\n✗ Rate limiting NOT working correctly")
            return False

    def test_normal_mode_resume(self) -> bool:
        """
        Test if normal mode resumes when Redis is available

        Returns:
            bool: True if normal mode resumes correctly
        """
        print("\n" + "=" * 60)
        print("NORMAL MODE RESUME TEST")
        print("=" * 60)

        is_safe_mode = self.safe_mode_manager.is_safe_mode_active()

        if not is_safe_mode:
            print("✓ Normal Mode is ACTIVE")
            print("  Normal mode correctly resumed after Redis restart")
            return True
        else:
            print("✗ Safe Mode is STILL ACTIVE")
            print("  Safe Mode should deactivate when Redis is available")
            return False

    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("SAFE MODE TEST SUMMARY")
        print("=" * 60)

        all_passed = all(results.values())

        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{test_name}: {status}")

        print("=" * 60)
        if all_passed:
            print("✓ ALL TESTS PASSED")
            print("\nSafe Mode is working correctly:")
            print("  - Activates when Redis is unavailable")
            print("  - Implements rate limiting (1 req/30s per user)")
            print("  - Deactivates when Redis is available")
        else:
            print("✗ SOME TESTS FAILED")
            print("\nPlease review the failed tests above")

        print("=" * 60)

        return all_passed

    def run(self):
        """
        Run complete Safe Mode test

        Returns:
            bool: True if all tests pass, False otherwise
        """
        print("=" * 60)
        print("SAFE MODE FUNCTIONALITY TEST")
        print("=" * 60)
        print(f"Test Configuration:")
        print(f"  Redis Port:     {self.redis_port}")
        print(f"  Test User:      {self.test_user}")
        print(f"  Test Season:     {self.test_season}")
        print("=" * 60)

        results = {}

        try:
            # Test 1: Verify Redis is running initially
            print("\nTest 1: Verify Redis is running")
            if not self.check_redis_status():
                print("✗ Redis is not running. Please start Redis first:")
                print("  redis-server --port 13000 --daemonize yes")
                return False

            # Test 2: Verify Redis is available
            print("\nTest 2: Verify Redis availability")
            if not self.test_redis_availability(expected_available=True):
                return False

            # Test 3: Stop Redis and verify Safe Mode activates
            print("\n" + "=" * 60)
            print("Test 3: Stop Redis and verify Safe Mode activation")
            print("=" * 60)
            print("\nPlease stop Redis now. You can use:")
            print("  redis-cli -p 13000 shutdown")
            print("\nPress Enter when Redis is stopped...")
            input()

            # Verify Redis is stopped
            if self.check_redis_status():
                print("⚠ Warning: Redis appears to still be running")
                print("  Please ensure Redis is stopped before continuing")
                print("\nPress Enter to continue anyway...")
                input()

            # Test Redis is unavailable
            if not self.test_redis_availability(expected_available=False):
                return False

            # Test Safe Mode activation
            results["Safe Mode Activation"] = self.test_safe_mode_activation()

            # Test 4: Test rate limiting
            print("\n" + "=" * 60)
            print("Test 4: Rate limiting in Safe Mode")
            print("=" * 60)
            print("\nTesting rate limiting...")
            results["Rate Limiting"] = self.test_rate_limiting()

            # Test 5: Restart Redis and verify normal mode resumes
            print("\n" + "=" * 60)
            print("Test 5: Restart Redis and verify normal mode")
            print("=" * 60)
            print("\nPlease start Redis now. You can use:")
            print("  redis-server --port 13000 --daemonize yes")
            print("\nPress Enter when Redis is started...")
            input()

            # Verify Redis is running
            if not self.check_redis_status():
                print("⚠ Warning: Redis may not be running")
                print("  Please ensure Redis is started before continuing")
                print("\nPress Enter to continue anyway...")
                input()

            # Test Redis is available
            if not self.test_redis_availability(expected_available=True):
                return False

            # Test normal mode resume
            results["Normal Mode Resume"] = self.test_normal_mode_resume()

            # Print summary
            return self.print_summary(results)

        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            return False
        except Exception as e:
            print(f"\n✗ ERROR: Safe Mode test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    test = SafeModeTest()
    success = test.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
