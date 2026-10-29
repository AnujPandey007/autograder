from analyzers.common import result, unavailable


# Called by grader.py to check function count and helper functions.
def analyze(context, params):
    if context["static"] is None:
        return unavailable(context["static_error"])

    names = []
    helper_score = 0
    for function in context["static"]["functions"]:
        names.append(function["name"])
        if function["name"] != "main":
            helper_score = 1

    # Award partial marks if fewer functions are defined than required.
    required = max(1, params.get("min_functions", 2))
    score = min(1, len(names) / required)

    # If helpers are required, average the two checks.
    if params.get("expect_helpers", True):
        score = (score + helper_score) / 2

    return result(
        score,
        "Separate helper functions improve modularity.",
        {"functions": names, "required": required}
    )