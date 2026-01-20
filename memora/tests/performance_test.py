#!/usr/bin/env python
# Copyright (c) 2026, Memora and contributors
# For license information, please see license.txt

"""
Performance Test: Load 100K records and verify <100ms read response

This script tests the SRS scalability implementation by:
1. Loading 100,000 memory tracker records into Redis
2. Measuring read response times for due item retrieval
3. Verifying that p99 response time is <100ms

Usage:
    python memora/tests/performance_test.py
"""

import time
import random
from datetime import datetime, timedelta
from typing import List, Dict

try:
    import frappe
    from memora.services.srs_redis_manager import SRSRedisManager
    FRAPPE_AVAILABLE = True
except ImportError:
    FRAPPE_AVAILABLE = False
    print("Warning: Frappe not available. Running in standalone mode.")


class PerformanceTest:
    """Performance testing for SRS scalability"""

    def __init__(self):
        """Initialize performance test"""
        self.redis_manager = None
        if FRAPPE_AVAILABLE:
            self.redis_manager = SRSRedisManager()
            self.test_season = "PERF-TEST-SEASON"
            self.test_user = "perf-test@example.com"
        else:
            print("Frappe environment required for performance testing")
            exit(1)

    def generate_test_data(self, count: int = 100000) -> List[Dict]:
        """
        Generate test memory tracker records

        Args:
            count: Number of records to generate

        Returns:
            List of test record dictionaries
        """
        print(f"Generating {count:,} test records...")
        records = []
        now = time.time()

        for i in range(count):
            # Distribute due times across next 30 days
            due_offset = random.randint(0, 30 * 24 * 60 * 60)
            next_review_ts = now + due_offset

            records.append({
                "question_id": f"question-{i:06d}",
                "next_review_ts": next_review_ts
            })

            if (i + 1) % 10000 == 0:
                print(f"  Generated {i+1:,} records...")

        return records

    def load_test_data_to_redis(self, records: List[Dict], batch_size: int = 1000) -> float:
        """
        Load test data into Redis in batches

        Args:
            records: List of test records
            batch_size: Number of records per batch

        Returns:
            Total time taken to load all records (seconds)
        """
        print(f"\nLoading {len(records):,} records into Redis (batch size: {batch_size})...")
        start_time = time.time()

        # Clear existing test data
        self.redis_manager.clear_user_cache(self.test_user, self.test_season)

        # Load in batches
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_dict = {r["question_id"]: r["next_review_ts"] for r in batch}
            self.redis_manager.add_batch(self.test_user, self.test_season, batch_dict)

            if (i + batch_size) % 10000 == 0:
                print(f"  Loaded {i + batch_size:,} records...")

        total_time = time.time() - start_time
        print(f"  Loaded {len(records):,} records in {total_time:.2f}s")
        print(f"  Throughput: {len(records)/total_time:,.0f} records/second")

        return total_time

    def test_read_performance(self, iterations: int = 1000) -> Dict:
        """
        Test read performance for due item retrieval

        Args:
            iterations: Number of read operations to test

        Returns:
            Dictionary with performance metrics
        """
        print(f"\nTesting read performance ({iterations} iterations)...")
        response_times = []

        for i in range(iterations):
            start_time = time.time()
            items = self.redis_manager.get_due_items(self.test_user, self.test_season, limit=20)
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)

            if (i + 1) % 100 == 0:
                print(f"  Completed {i+1} iterations...")

        # Calculate statistics
        response_times.sort()
        p50 = response_times[int(len(response_times) * 0.5)]
        p90 = response_times[int(len(response_times) * 0.9)]
        p95 = response_times[int(len(response_times) * 0.95)]
        p99 = response_times[int(len(response_times) * 0.99)]
        avg = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        results = {
            "iterations": iterations,
            "p50_ms": p50,
            "p90_ms": p90,
            "p95_ms": p95,
            "p99_ms": p99,
            "avg_ms": avg,
            "min_ms": min_time,
            "max_ms": max_time,
            "target_p99_ms": 100,
            "target_met": p99 < 100
        }

        return results

    def print_results(self, results: Dict):
        """Print performance test results"""
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST RESULTS")
        print("=" * 60)
        print(f"Test Iterations: {results['iterations']:,}")
        print(f"\nResponse Time Statistics:")
        print(f"  Average: {results['avg_ms']:.2f} ms")
        print(f"  Min:     {results['min_ms']:.2f} ms")
        print(f"  Max:     {results['max_ms']:.2f} ms")
        print(f"  P50:      {results['p50_ms']:.2f} ms")
        print(f"  P90:      {results['p90_ms']:.2f} ms")
        print(f"  P95:      {results['p95_ms']:.2f} ms")
        print(f"  P99:      {results['p99_ms']:.2f} ms")
        print(f"\nTarget: P99 < 100ms")
        print(f"Status: {'✓ PASS' if results['target_met'] else '✗ FAIL'}")
        print("=" * 60)

        if not results['target_met']:
            print(f"\n⚠ WARNING: P99 response time ({results['p99_ms']:.2f}ms) exceeds target of 100ms")
            print("This may indicate:")
            print("  - Redis network latency")
            print("  - Insufficient Redis resources")
            print("  - High Redis key count")
            print("  - Network congestion")

    def cleanup(self):
        """Clean up test data"""
        print("\nCleaning up test data...")
        try:
            self.redis_manager.clear_user_cache(self.test_user, self.test_season)
            print("  Test data cleared from Redis")
        except Exception as e:
            print(f"  Warning: Failed to clear test data: {e}")

    def run(self, record_count: int = 100000, test_iterations: int = 1000):
        """
        Run complete performance test

        Args:
            record_count: Number of records to test with
            test_iterations: Number of read iterations
        """
        print("=" * 60)
        print("SRS SCALABILITY PERFORMANCE TEST")
        print("=" * 60)
        print(f"Test Configuration:")
        print(f"  Record Count:   {record_count:,}")
        print(f"  Test Iterations: {test_iterations:,}")
        print(f"  Target P99:      <100ms")
        print(f"  Test User:       {self.test_user}")
        print(f"  Test Season:     {self.test_season}")
        print("=" * 60)

        try:
            # Generate test data
            records = self.generate_test_data(record_count)

            # Load to Redis
            load_time = self.load_test_data_to_redis(records)

            # Test read performance
            results = self.test_read_performance(test_iterations)

            # Print results
            self.print_results(results)

            # Cleanup
            self.cleanup()

            return results['target_met']

        except Exception as e:
            print(f"\n✗ ERROR: Performance test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    import sys

    # Parse command line arguments
    record_count = 100000
    test_iterations = 1000

    if len(sys.argv) > 1:
        try:
            record_count = int(sys.argv[1])
        except ValueError:
            print("Invalid record count. Using default: 100,000")

    if len(sys.argv) > 2:
        try:
            test_iterations = int(sys.argv[2])
        except ValueError:
            print("Invalid iteration count. Using default: 1,000")

    # Run performance test
    test = PerformanceTest()
    success = test.run(record_count, test_iterations)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
