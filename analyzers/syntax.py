from analyzers.common import result, unavailable
from runtime import docker_runner


# Called by grader.py to check compiler errors and warnings.
def analyze(context, params):
    flags = params.get("flags", "-Wall -Wextra -Werror -std=c11")
    compiled = docker_runner.compile(context["folder"], flags, "syntax_check")

    if compiled["status"] == "unavailable":
        return unavailable("Compiler unavailable.", compiled)

    if compiled["status"] == "ok":
        return result(1, "Compiler checks passed.", compiled)

    return result(0, "Fix the compiler diagnostics.", compiled)
