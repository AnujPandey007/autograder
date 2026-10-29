import lizard
from analyzers.common import result


# Check function length and branching using Lizard.
def analyze(context, params):
    analysis = lizard.analyze_file.analyze_source_code(
        "submission.c", context["source"]
    )
    functions = analysis.function_list

    if not functions:
        return result(0, "No function definitions found.")

    max_length = params.get("max_function_length", 40)
    max_complexity = params.get("max_cyclomatic", 8)
    passed = 0
    evidence = []

    for function in functions:
        length = function.end_line - function.start_line + 1
        complexity = function.cyclomatic_complexity

        if length <= max_length:
            passed += 1
        if complexity <= max_complexity:
            passed += 1

        evidence.append({
            "name": function.name,
            "line": function.start_line,
            "length": length,
            "cyclomatic": complexity
        })

    return result(
        passed / (2 * len(functions)),
        "Function length and branching checked using Lizard.",
        {"functions": evidence, "method": "Lizard"}
    )