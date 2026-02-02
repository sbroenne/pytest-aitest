#!/usr/bin/env python3
"""Generate report fixtures by running integration tests.

This script runs the fixture scenario tests and saves the JSON output
as versioned fixtures for HTML report testing.

Usage:
    python scripts/generate_fixtures.py --all
    python scripts/generate_fixtures.py --fixture 06
    python scripts/generate_fixtures.py --fixture 07
    python scripts/generate_fixtures.py --fixture 08
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "reports"
INTEGRATION_DIR = REPO_ROOT / "tests" / "integration"

# Fixture definitions: (fixture_name, test_class, extra_args)
FIXTURE_CONFIGS = {
    "06": (
        "06_with_ai_summary.json",
        "test_fixture_scenarios.py::TestWithAISummary",
        ["--aitest-summary", "--aitest-summary-model=azure/gpt-5-mini"],
    ),
    "07": (
        "07_with_skipped.json",
        "test_fixture_scenarios.py::TestWithSkipped",
        [],
    ),
    "08": (
        "08_matrix_full.json",
        "test_fixture_scenarios.py::TestMatrixFull",
        ["--aitest-summary", "--aitest-summary-model=azure/gpt-5-mini"],
    ),
}


def generate_fixture(fixture_id: str) -> bool:
    """Generate a single fixture by running its test class.
    
    Returns True if successful.
    """
    if fixture_id not in FIXTURE_CONFIGS:
        print(f"Unknown fixture ID: {fixture_id}")
        print(f"Available: {', '.join(FIXTURE_CONFIGS.keys())}")
        return False

    filename, test_path, extra_args = FIXTURE_CONFIGS[fixture_id]
    output_path = FIXTURES_DIR / filename

    print(f"\n{'='*60}")
    print(f"Generating fixture {fixture_id}: {filename}")
    print(f"{'='*60}")

    cmd = [
        sys.executable, "-m", "pytest",
        str(INTEGRATION_DIR / test_path),
        "-v",
        f"--aitest-json={output_path}",
        *extra_args,
    ]

    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=REPO_ROOT)

    if output_path.exists():
        print(f"\n✅ Generated: {output_path}")
        print(f"   Size: {output_path.stat().st_size:,} bytes")
        return True
    else:
        print(f"\n❌ Failed to generate: {output_path}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate report fixtures")
    parser.add_argument(
        "--all", 
        action="store_true",
        help="Generate all fixtures (06, 07, 08)"
    )
    parser.add_argument(
        "--fixture",
        choices=list(FIXTURE_CONFIGS.keys()),
        help="Generate specific fixture"
    )
    args = parser.parse_args()

    if not args.all and not args.fixture:
        parser.print_help()
        return 1

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    if args.all:
        fixtures_to_generate = list(FIXTURE_CONFIGS.keys())
    else:
        fixtures_to_generate = [args.fixture]

    results = []
    for fixture_id in fixtures_to_generate:
        success = generate_fixture(fixture_id)
        results.append((fixture_id, success))

    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    for fixture_id, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} Fixture {fixture_id}")

    return 0 if all(s for _, s in results) else 1


if __name__ == "__main__":
    sys.exit(main())
