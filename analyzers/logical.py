from analyzers.common import result, unavailable
from analyzers.correctness import run_tests


# Run uploaded tests whose labels match the instructor's logical categories.
def analyze(context, params):
    categories = params.get("cases", [])
    tests = []
    for test in context["tests"]:
        if not categories or test.get("label") in categories:
            tests.append(test)

    if not tests:
        return unavailable("No uploaded tests match the logical categories.")

    answers = run_tests(context, tests)
    passed = 0
    for answer in answers:
        if answer["status"] == "unavailable":
            return unavailable("Test execution failed.", {"tests": answers})
        if answer["passed"]:
            passed += 1

    return result(
        passed / len(tests),
        f"{passed}/{len(tests)} uploaded logical tests passed.",
        {"tests": answers, "oracle": "Expected outputs from the uploaded test JSON"}
    )
