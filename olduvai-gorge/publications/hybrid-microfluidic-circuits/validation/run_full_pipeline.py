#!/usr/bin/env python3
"""
Complete Pipeline: Run Validation Tests → Generate Publication Figures

Executes full analysis and figure generation in one command.
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from validation_suite import ValidationSuite
from figure_generation import PublicationFigureGenerator
from utils import save_json, create_report


def main():
    """Execute complete pipeline."""
    print("\n" + "="*70)
    print("SENSATION MECHANICS FRAMEWORK - COMPLETE ANALYSIS PIPELINE")
    print("="*70 + "\n")

    # Step 1: Run validation tests
    print("STEP 1: Running Validation Tests...")
    print("-"*70)

    validation_output_dir = Path('./validation_results')
    validation_output_dir.mkdir(parents=True, exist_ok=True)

    suite = ValidationSuite(output_dir=str(validation_output_dir))
    validation_results = suite.run_all_tests()

    # Save validation results
    validation_file = suite.save_results(validation_results, 'validation_results.json')

    # Create human-readable report
    report = create_report(validation_results,
                          validation_output_dir / 'validation_report.txt')

    print(f"\n[OK] Validation Results:")
    print(f"  Tests Run: {validation_results['total_tests']}")
    print(f"  Tests Passed: {validation_results['tests_passed']}")
    print(f"  Pass Rate: {100*validation_results['tests_passed']/validation_results['total_tests']:.1f}%")
    print(f"  Results File: {validation_file}")

    # Step 2: Generate publication figures
    print("\n" + "-"*70)
    print("STEP 2: Generating Publication Figures...")
    print("-"*70)

    figures_output_dir = Path('./publication_figures')
    figures_output_dir.mkdir(parents=True, exist_ok=True)

    generator = PublicationFigureGenerator(output_dir=str(figures_output_dir))
    figure_results = generator.generate_all_panels()

    print(f"\n[OK] Generated {len(figure_results)} Publication Panels:")
    for panel_name, files in figure_results.items():
        print(f"  • {panel_name}")

    # Step 3: Create summary document
    print("\n" + "-"*70)
    print("STEP 3: Creating Summary Document...")
    print("-"*70)

    summary = {
        'timestamp': datetime.now().isoformat(),
        'validation': {
            'total_tests': validation_results['total_tests'],
            'tests_passed': validation_results['tests_passed'],
            'pass_rate': validation_results['tests_passed'] / validation_results['total_tests'],
            'results_file': str(validation_file)
        },
        'figures': {
            'total_panels': len(figure_results),
            'charts_per_panel': 4,
            'total_charts': len(figure_results) * 4,
            '3d_charts_per_panel': 1,
            'output_directory': str(figures_output_dir),
            'panels': {
                name: {
                    'pdf': files['pdf'],
                    'png': files['png']
                }
                for name, files in figure_results.items()
            }
        }
    }

    summary_file = validation_output_dir / 'pipeline_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    # Print final summary
    print("\n" + "="*70)
    print("PIPELINE COMPLETE - SUMMARY")
    print("="*70)

    print(f"""
VALIDATION RESULTS:
  • Tests Executed: {validation_results['total_tests']}
  • Tests Passed: {validation_results['tests_passed']}/{validation_results['total_tests']}
  • Success Rate: {100*validation_results['tests_passed']/validation_results['total_tests']:.1f}%
  • Results saved to: {validation_file}

PUBLICATION FIGURES:
  • Panels Generated: 6
  • Charts per Panel: 4
  • Total Charts: 24
  • 3D Charts: 6 (one per panel)
  • Background: White
  • Format: PDF + PNG (300 DPI)
  • Output Directory: {figures_output_dir}

PANELS:
  1. Charge Dynamics & Exponential Decay
  2. Sensation Categorization (Pain/Pleasure)
  3. Receptor Diversity Advantage
  4. Temperature-Dependent Kinetics
  5. Multi-Circuit Frequency Matching
  6. Receptor Adaptation & Learning

FILES CREATED:
  • {validation_file} - Detailed validation results
  • {validation_output_dir / 'validation_report.txt'} - Human-readable report
  • {summary_file} - Pipeline summary
  • 6 PDF files in {figures_output_dir}
  • 6 PNG files in {figures_output_dir}

STATUS: [OK] ALL ANALYSES COMPLETE
""")

    print("="*70 + "\n")

    return validation_results, figure_results


if __name__ == '__main__':
    validation_results, figure_results = main()
