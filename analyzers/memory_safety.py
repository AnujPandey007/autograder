from analyzers.common import result, unavailable
from analyzers.correctness import run_tests
from runtime import docker_runner


# Called by grader.py to check memory errors and undefined behavior.
def analyze(context, params):
    if context["compiled"]["status"] != "ok":
        return result(0, "Program did not compile.", status="skipped")

    # Compile with AddressSanitizer and UndefinedBehaviorSanitizer.
    flags = params.get("flags", "-fsanitize=address,undefined")
    flags += " -std=c11 -O0 -g -fno-sanitize-recover=all"
    compiled = docker_runner.compile(context["folder"], flags, "sanitized")

    if compiled["status"] != "ok":
        return unavailable("Sanitizer compilation failed.", compiled)

    # Run only the tests supplied in the uploaded JSON.
    tests = context["tests"]
    if not tests:
        return unavailable("No tests for memory safety.")

    answers = run_tests(context, tests, compiled, sanitizer=True)
    safe = 0

    for answer in answers:
        if answer["status"] == "unavailable":
            return unavailable("Sanitizer execution failed.", {"tests": answers})

        # Keep output correctness separate from memory checks.
        answer["correct_output"] = answer["passed"]
        answer["passed"] = (
            answer["status"] == "ok"
            and "runtime error:" not in answer["stderr"]
            and "ERROR: AddressSanitizer" not in answer["stderr"]
        )
        if answer["passed"]:
            safe += 1

    return result(
        safe / len(answers),
        f"{safe}/{len(answers)} runs completed without sanitizer/runtime failure.",
        {
            "tests": answers,
            "flags": flags,
            "limitations": (
                "No leak scan. Docker enforces the instructor memory limit. "
                "Passing these tests does not prove memory safety."
            )
        }
    )