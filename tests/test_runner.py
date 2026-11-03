#!/usr/bin/env python3
"""
Unified E2E Test Runner for Decisn3.
Discovers and executes Tier 1 through Tier 4 test suites.
Reports detailed test metrics, summary tables, and proper exit codes.
"""

import os
import sys
import time
import argparse
import unittest
from typing import Dict, Any, List

# Ensure parent directory is on sys.path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tests.tier1_feature_tests import TestTier1FeatureCoverage
from tests.tier2_boundary_tests import TestTier2BoundaryAndCornerCases
from tests.tier3_pairwise_tests import TestTier3PairwiseInteractions
from tests.tier4_workload_tests import TestTier4RealWorldWorkloads
try:
    from tests.tier5_adversarial_tests import TestTier5AdversarialHardening
except ImportError:
    TestTier5AdversarialHardening = None


TIER_MAP = {
    1: ("Tier 1: Feature Coverage (R1-R5)", TestTier1FeatureCoverage),
    2: ("Tier 2: Boundary & Corner Cases", TestTier2BoundaryAndCornerCases),
    3: ("Tier 3: Pairwise & Cross-Feature", TestTier3PairwiseInteractions),
    4: ("Tier 4: Real-World Workloads", TestTier4RealWorldWorkloads),
}
if TestTier5AdversarialHardening is not None:
    TIER_MAP[5] = ("Tier 5: Adversarial Hardening", TestTier5AdversarialHardening)



class TierResultTracker:
    """Tracks counts, failures, and execution timings per tier."""

    def __init__(self, name: str):
        self.name = name
        self.total_run = 0
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.skipped = 0
        self.duration_seconds = 0.0

    def record(self, result: unittest.TestResult, duration: float):
        self.total_run = result.testsRun
        self.failed = len(result.failures)
        self.errors = len(result.errors)
        self.skipped = len(result.skipped)
        self.passed = self.total_run - self.failed - self.errors - self.skipped
        self.duration_seconds = duration


def run_tier_suite(name: str, test_class, verbosity: int = 1, failfast: bool = False) -> (TierResultTracker, unittest.TestResult):
    """Executes a single test tier suite and returns the metrics."""
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    tracker = TierResultTracker(name)

    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        failfast=failfast,
        resultclass=unittest.TextTestResult
    )

    print(f"\n{'=' * 70}")
    print(f"  RUNNING: {name}")
    print(f"{'=' * 70}")

    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time

    tracker.record(result, duration)
    return tracker, result


def print_summary_table(trackers: List[TierResultTracker], total_duration: float):
    """Prints formatted summary table of all test tiers."""
    print("\n" + "=" * 78)
    print("                      E2E TEST EXECUTION SUMMARY")
    print("=" * 78)
    print(f"{'Tier Name':<38} {'Run':>5} {'Pass':>6} {'Fail':>6} {'Err':>5} {'Skip':>6} {'Time':>7}")
    print("-" * 78)

    total_run = sum(t.total_run for t in trackers)
    total_passed = sum(t.passed for t in trackers)
    total_failed = sum(t.failed for t in trackers)
    total_errors = sum(t.errors for t in trackers)
    total_skipped = sum(t.skipped for t in trackers)

    for t in trackers:
        print(
            f"{t.name:<38} {t.total_run:>5} {t.passed:>6} {t.failed:>6} {t.errors:>5} {t.skipped:>6} {t.duration_seconds:>6.2f}s"
        )

    print("-" * 78)
    print(
        f"{'TOTAL':<38} {total_run:>5} {total_passed:>6} {total_failed:>6} {total_errors:>5} {total_skipped:>6} {total_duration:>6.2f}s"
    )
    print("=" * 78)

    if total_failed == 0 and total_errors == 0:
        print(f"\n  >>> [SUCCESS] All executed tests passed cleanly! (Exit Code 0)\n")
    else:
        print(f"\n  >>> [FAILURE] {total_failed} failure(s) and {total_errors} error(s) detected! (Exit Code 1)\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Unified E2E Test Runner for Decisn3",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Run only the specified test tier (1-5). Default is all available tiers.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce strict mode (missing milestone artifacts cause failure instead of skip).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=1,
        help="Increase output verbosity (e.g. -v or -vv).",
    )
    parser.add_argument(
        "-f", "--failfast",
        action="store_true",
        help="Stop execution on first test failure.",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Explicitly enable Playwright browser tests.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.strict:
        os.environ["TEST_STRICT"] = "1"
        print("[INFO] Strict mode enabled: all milestone artifacts are strictly required.")
    else:
        print("[INFO] Progressive mode: pending milestone artifacts will report as SKIPPED.")

    tiers_to_run = [args.tier] if args.tier else sorted(list(TIER_MAP.keys()))

    trackers: List[TierResultTracker] = []
    overall_success = True
    start_total_time = time.time()

    for tier_num in tiers_to_run:
        name, test_class = TIER_MAP[tier_num]
        tracker, result = run_tier_suite(
            name,
            test_class,
            verbosity=args.verbose,
            failfast=args.failfast,
        )
        trackers.append(tracker)
        if not result.wasSuccessful():
            overall_success = False
            if args.failfast:
                break

    total_duration = time.time() - start_total_time
    print_summary_table(trackers, total_duration)

    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()
