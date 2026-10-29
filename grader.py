import hashlib
import json
import sys
import tempfile
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

import pycparser
from rules import read_rules, read_tests
from runtime import docker_runner
from llm_review import generate_feedback
from analyzers import syntax, correctness, structure, modularity, logical
from analyzers import complexity, memory_safety, readability, originality
from analyzers.common import parse_source, unavailable

ANALYZERS = {
    "syntax": syntax, "correctness": correctness,
    "structure": structure, "modularity": modularity,
    "logical": logical, "complexity": complexity,
    "memory_safety": memory_safety, "readability": readability,
    "originality": originality
}


def round_marks(value):
    # Round each metric first; the overall grade is their sum.
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


# Hide temporary folder names in report evidence.
def clean_paths(value, folder):
    if isinstance(value, str):
        return value.replace(str(Path(folder).resolve()), "<run>").replace(folder, "<run>")
    if isinstance(value, list):
        return [clean_paths(item, folder) for item in value]
    if isinstance(value, dict):
        return {key: clean_paths(item, folder) for key, item in value.items()}
    return value


# Grade one submission; peers are only for originality comparison.
def grade_submission(c_file, instructor_file, test_file, peers=None):
    try:
        return grade_file(c_file, instructor_file, test_file, peers)
    except Exception as error:
        return {"file": Path(c_file).name if c_file else "No C file", "error": str(error)}


def grade_file(c_file, instructor_file, test_file, peers):
    path = Path(c_file)
    source = path.read_text(encoding="utf-8")
    rules = read_rules(instructor_file)
    tests = read_tests(test_file)
    compiler = docker_runner.compiler_info()

    # Parsing failure should not stop compiler and execution checks.
    static, static_error = None, ""
    try:
        static = parse_source(source)
    except Exception as error:
        static_error = str(error)

    metrics = []
    earned, available = Decimal("0"), Decimal("0")
    complete = True

    with tempfile.TemporaryDirectory() as folder:
        Path(folder, "submission.c").write_text(source, encoding="utf-8")
        compiled = docker_runner.compile(folder)
        if compiled["status"] == "unavailable":
            raise RuntimeError(compiled["stderr"])

        first_pass = {
            "compiled": compiled["status"] == "ok",
            "smoke_ok": None,
            "suspected_infinite_loop": None
        }
        context = {
            "source": source, "source_path": str(path.resolve()),
            "folder": folder, "rules": rules, "tests": tests,
            "peers": peers or [], "compiled": compiled,
            "static": static, "static_error": static_error
        }

        # One failed analyzer must not stop the remaining checks.
        for rule in rules["metrics"]:
            try:
                answer = ANALYZERS[rule["name"]].analyze(context, rule["params"])
            except Exception as error:
                answer = unavailable(str(error))

            maximum = round_marks(rule["weight"] * 100)
            marks = None
            if answer["score"] is not None:
                marks = round_marks(answer["score"] * rule["weight"] * 100)
                earned += Decimal(str(marks))
                available += Decimal(str(maximum))
            elif rule["weight"] > 0:
                complete = False

            answer.update(
                name=rule["name"], analyzer=rule["analyzer"],
                weight=rule["weight"], maximum=maximum, marks=marks
            )
            metrics.append(clean_paths(answer, folder))

            # Use the first correctness test as smoke-test evidence.
            if rule["name"] == "correctness":
                cases = answer["evidence"].get("tests", [])
                if cases and cases[0]["status"] not in ("skipped", "unavailable"):
                    first_pass["smoke_ok"] = cases[0]["status"] == "ok"
                    first_pass["suspected_infinite_loop"] = cases[0]["status"] == "timeout"

    return {
        "file": path.name,
        "problem": rules["problem"],
        "grade": round_marks(earned) if complete else None,
        "earned_marks": round_marks(earned),
        "available_marks": round_marks(available),
        "status": "complete" if complete else "partial",
        "first_pass": first_pass,
        "metrics": metrics,
        "rules_sha256": sha(json.dumps(rules, sort_keys=True)),
        "compiler": compiler,
        "python": sys.version.split()[0],
        "pycparser": pycparser.__version__,
        "execution_note": docker_runner.EXECUTION_NOTE,
        "ai_feedback": generate_feedback(source, rules, metrics)
    }
