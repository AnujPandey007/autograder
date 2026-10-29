from analyzers.common import result, unavailable
from runtime import docker_runner


# Used by correctness, logical and memory-safety analyzers.
def run_tests(context, tests, compiled=None, sanitizer=False):
    if compiled is None:
        compiled = context["compiled"]

    answers = []
    stop = compiled["status"] != "ok"

    for test in tests:
        if stop:
            run = {
                "status": "skipped", "returncode": None,
                "stdout": "", "stderr": ""
            }
        else:
            run = docker_runner.execute(
                compiled, context["folder"], test,
                context["rules"], sanitizer
            )

        # Passing requires normal execution and an exact output match.
        passed = (
            run["status"] == "ok"
            and run["returncode"] == 0
            and run["stdout"] == test["expected"]
        )
        answers.append({
            "input": test["input"],
            "expected": test["expected"],
            "actual": run["stdout"],
            "passed": passed,
            "status": run["status"],
            "stderr": run["stderr"],
            "label": test.get("label", "instructor")
        })

        # Skip remaining tests after a timeout or runner failure.
        if run["status"] in ("timeout", "unavailable"):
            stop = True

    return answers


# Called by grader.py to calculate the correctness score.
def analyze(context, params):
    tests = context["tests"]
    if not tests:
        return unavailable("No instructor test cases configured.")

    answers = run_tests(context, tests)
    passed = 0

    for answer in answers:
        if answer["status"] == "unavailable":
            return unavailable("Test execution failed.", {"tests": answers})
        if answer["passed"]:
            passed += 1

    return result(
        passed / len(tests),
        f"{passed}/{len(tests)} instructor tests passed.",
        {"tests": answers}
    )