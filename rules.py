"""Read the instructor's existing JSON format and external test cases."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ANALYZERS = {
    'correctness': 'io_tests', 'syntax': 'compiler_warnings',
    'structure': 'static_analysis', 'modularity': 'function_split',
    'logical': 'edge_case_runner', 'complexity': 'complexity_estimator',
    'memory_safety': 'sanitizer_run', 'readability': 'llm_review',
    'originality': 'similarity_flag'
}


def read_rules(filename):
    with open(filename, encoding='utf-8') as file:
        rules = json.load(file)
    names = []
    total = 0
    for metric in rules['metrics']:
        name = metric['name']
        if name not in ANALYZERS or metric['analyzer'] != ANALYZERS[name]:
            raise ValueError('Unknown metric/analyzer: ' + name)
        if name in names:
            raise ValueError('Duplicate metric: ' + name)
        weight = metric['weight']
        if type(weight) not in (int, float) or not math.isfinite(weight) or not 0 <= weight <= 1:
            raise ValueError('Weights must be numbers between 0 and 1.')
        if not isinstance(metric.get('params'), dict):
            raise ValueError('Each metric needs a params object.')
        total += weight
        names.append(name)
    if abs(total - 1) > 0.000001:
        raise ValueError('Weights must add up to 1.')
    if not 0.1 <= rules['time_limit_s'] <= 30:
        raise ValueError('Time limit must be between 0.1 and 30 seconds.')
    if not 32 <= rules['memory_limit_mb'] <= 1024:
        raise ValueError('Memory limit must be between 32 and 1024 MB.')
    return rules


def get_metric(rules, name):
    for metric in rules['metrics']:
        if metric['name'] == name:
            return metric
    return None


def project_path(relative_path):
    # Instructor paths are relative to this project, even for uploaded JSON files.
    path = (ROOT / relative_path).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise ValueError('Instructor paths must stay inside the project.')
    return path


def read_tests(filename):
    with open(filename, encoding='utf-8') as file:
        tests = json.load(file)

    if not isinstance(tests, list) or not 1 <= len(tests) <= 100:
        raise ValueError('Use 1 to 100 test cases.')

    for test in tests:
        if not isinstance(test, dict):
            raise ValueError('Each test must contain input and expected.')

        for key in ['input', 'expected']:
            if not isinstance(test.get(key), str):
                raise ValueError('Input and expected must be text.')

            if len(test[key].encode()) > 65536:
                raise ValueError('A test case is too large.')

    return tests