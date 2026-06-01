#!/usr/bin/env python3
"""
Main entry point for validation suite.

Usage:
    python run_validation.py
    python run_validation.py --output ./my_results
    python run_validation.py --quiet
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from validation_suite import ValidationSuite


def main():
    parser = argparse.ArgumentParser(
        description='Run Sensation Mechanics Framework validation suite'
    )
    parser.add_argument(
        '--output',
        default='./validation_results',
        help='Output directory for results (default: ./validation_results)'
    )
    parser.add_argument(
        '--filename',
        default='validation_results.json',
        help='Output JSON filename (default: validation_results.json)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress console output'
    )

    args = parser.parse_args()

    # Create and run suite
    suite = ValidationSuite(output_dir=args.output)

    if not args.quiet:
        print("\n" + "="*70)
        print("SENSATION MECHANICS FRAMEWORK VALIDATION SUITE")
        print("="*70)
        print(f"\nRunning all tests...\n")

    try:
        results = suite.run_all_tests()

        # Print summary
        if not args.quiet:
            print("\n" + "="*70)
            print(f"RESULTS: {results['tests_passed']}/{results['total_tests']} tests passed")
            print("="*70 + "\n")

        # Save results
        output_path = suite.save_results(results, args.filename)

        if not args.quiet:
            print(f"Full results saved to: {output_path}\n")

        # Return exit code based on test results
        if results['tests_passed'] == results['total_tests']:
            if not args.quiet:
                print("✓ All validation tests PASSED\n")
            return 0
        else:
            failed = results['total_tests'] - results['tests_passed']
            if not args.quiet:
                print(f"✗ {failed} validation test(s) FAILED\n")
            return 1

    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}\n", file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
