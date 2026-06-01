"""
Utility functions for data handling, analysis, and JSON export.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime


class NumpyEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for numpy types.

    Allows json.dump() to handle numpy arrays and scalars.
    """

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)


def save_json(data: Dict[str, Any], filepath: Path, pretty: bool = True) -> Path:
    """
    Save data to JSON file with numpy type handling.

    Args:
        data: Dictionary to save
        filepath: Output file path
        pretty: If True, indent with 2 spaces

    Returns:
        Path to saved file
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    indent = 2 if pretty else None

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=indent, cls=NumpyEncoder)

    return filepath


def load_json(filepath: Path) -> Dict[str, Any]:
    """
    Load data from JSON file.

    Args:
        filepath: Input file path

    Returns:
        Loaded dictionary
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def exponential_fit(t: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
    """
    Fit y(t) = A * e^(-t/tau) to data.

    Args:
        t: Time points
        y: Data values

    Returns:
        Tuple of (A, tau, r_squared)
    """
    from scipy.optimize import curve_fit

    def exponential(t, A, tau):
        return A * np.exp(-t / tau)

    try:
        popt, _ = curve_fit(exponential, t, y, p0=[y[0], 1.0], maxfev=5000)
        A, tau = popt

        # Compute R-squared
        y_pred = exponential(t, A, tau)
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r_squared = 1.0 - (ss_res / ss_tot)

        return float(A), float(tau), float(r_squared)
    except RuntimeError:
        return None, None, None


def compute_statistics(data: np.ndarray) -> Dict[str, float]:
    """
    Compute basic statistics on array.

    Args:
        data: Input array

    Returns:
        Dictionary with statistics
    """
    return {
        'mean': float(np.mean(data)),
        'std': float(np.std(data)),
        'min': float(np.min(data)),
        'max': float(np.max(data)),
        'median': float(np.median(data)),
        'q25': float(np.percentile(data, 25)),
        'q75': float(np.percentile(data, 75))
    }


def normalize_range(data: np.ndarray, target_min: float = 0.0,
                   target_max: float = 1.0) -> np.ndarray:
    """
    Normalize array to target range.

    Args:
        data: Input array
        target_min: Minimum of target range
        target_max: Maximum of target range

    Returns:
        Normalized array
    """
    data_min = np.min(data)
    data_max = np.max(data)

    if data_max == data_min:
        return np.ones_like(data) * (target_min + target_max) / 2

    normalized = (data - data_min) / (data_max - data_min)
    return normalized * (target_max - target_min) + target_min


def logarithmic_spacing(min_val: float, max_val: float, n_points: int) -> np.ndarray:
    """
    Generate logarithmically spaced array.

    Args:
        min_val: Minimum value
        max_val: Maximum value
        n_points: Number of points

    Returns:
        Logarithmically spaced array
    """
    return np.logspace(np.log10(min_val), np.log10(max_val), n_points)


def compute_matching_score(tau1: float, tau2: float) -> float:
    """
    Compute frequency matching score between two timescales.

    Score = |Δτ| / (τ1 + τ2)
    0 = perfect match, 1 = no match

    Args:
        tau1, tau2: Time constants

    Returns:
        Matching score [0, 1]
    """
    if tau1 + tau2 == 0:
        return 1.0
    return abs(tau1 - tau2) / (tau1 + tau2)


def create_report(results: Dict[str, Any], filepath: Path = None) -> str:
    """
    Create human-readable report from validation results.

    Args:
        results: Validation results dictionary
        filepath: Optional path to save report

    Returns:
        Report as string
    """
    lines = []

    lines.append("="*70)
    lines.append("VALIDATION REPORT")
    lines.append("="*70)
    lines.append("")

    lines.append(f"Timestamp: {results.get('timestamp', 'Unknown')}")
    lines.append(f"Tests Run: {results.get('total_tests', 0)}")
    lines.append(f"Tests Passed: {results.get('tests_passed', 0)}")
    lines.append(f"Tests Failed: {results.get('total_tests', 0) - results.get('tests_passed', 0)}")
    lines.append("")

    lines.append("-"*70)
    lines.append("INDIVIDUAL TEST RESULTS")
    lines.append("-"*70)
    lines.append("")

    for test in results.get('tests', []):
        test_name = test.get('test_name', 'Unknown')
        passes = test.get('passes', False)
        status = "✓ PASS" if passes else "✗ FAIL"

        lines.append(f"{status} - {test_name}")

        # Add key details
        for key, value in test.items():
            if key not in ['test_name', 'passes']:
                if isinstance(value, (int, float)):
                    lines.append(f"    {key}: {value:.6g}")
                elif isinstance(value, dict):
                    lines.append(f"    {key}:")
                    for k, v in value.items():
                        lines.append(f"      {k}: {v}")
                else:
                    lines.append(f"    {key}: {value}")

        lines.append("")

    lines.append("-"*70)
    lines.append("SUMMARY")
    lines.append("-"*70)

    pass_rate = 100 * results['tests_passed'] / results['total_tests'] if results['total_tests'] > 0 else 0
    lines.append(f"Pass Rate: {pass_rate:.1f}%")

    if results['tests_passed'] == results['total_tests']:
        lines.append("\n✓ ALL TESTS PASSED - Framework predictions validated")
    else:
        lines.append(f"\n✗ {results['total_tests'] - results['tests_passed']} test(s) failed")

    lines.append("\n" + "="*70)

    report = "\n".join(lines)

    if filepath:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)

    return report


def compare_results(results1: Dict, results2: Dict) -> Dict[str, Any]:
    """
    Compare two validation result sets.

    Args:
        results1: First validation results
        results2: Second validation results

    Returns:
        Comparison dictionary
    """
    comparison = {
        'results1_date': results1.get('timestamp'),
        'results2_date': results2.get('timestamp'),
        'results1_passed': results1.get('tests_passed'),
        'results2_passed': results2.get('tests_passed'),
        'test_comparison': []
    }

    tests1 = {t['test_name']: t for t in results1.get('tests', [])}
    tests2 = {t['test_name']: t for t in results2.get('tests', [])}

    for test_name in sorted(set(list(tests1.keys()) + list(tests2.keys()))):
        t1 = tests1.get(test_name, {})
        t2 = tests2.get(test_name, {})

        comparison['test_comparison'].append({
            'test_name': test_name,
            'result1_passes': t1.get('passes'),
            'result2_passes': t2.get('passes'),
            'changed': t1.get('passes') != t2.get('passes')
        })

    return comparison


def batch_run_analysis(results_dir: Path) -> Dict[str, Any]:
    """
    Analyze all validation results in a directory.

    Args:
        results_dir: Directory containing JSON result files

    Returns:
        Summary analysis
    """
    results_dir = Path(results_dir)
    json_files = list(results_dir.glob('*.json'))

    if not json_files:
        return {'error': f'No JSON files found in {results_dir}'}

    all_results = []
    for json_file in sorted(json_files):
        try:
            data = load_json(json_file)
            all_results.append(data)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    # Aggregate statistics
    pass_rates = [r['tests_passed'] / r['total_tests'] for r in all_results]

    return {
        'n_result_files': len(all_results),
        'total_tests_run': sum(r['total_tests'] for r in all_results),
        'total_tests_passed': sum(r['tests_passed'] for r in all_results),
        'mean_pass_rate': float(np.mean(pass_rates)),
        'min_pass_rate': float(np.min(pass_rates)),
        'max_pass_rate': float(np.max(pass_rates)),
        'dates': [r.get('timestamp') for r in all_results]
    }
