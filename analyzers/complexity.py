
from analyzers.common import result, unavailable
from llm_review import ask_llama, short_feedback


# Ordered from lower to higher time complexity.
COMPLEXITIES = [
    "O(1)",
    "O(log n)",
    "O(n)",
    "O(n log n)",
    "O(n^2)",
    "O(n^3)",
    "O(2^n)",
    "O(n!)"
]


# Called by grader.py to estimate complexity using Llama.
def analyze(context, params):
    required = params.get("required", "O(1)")
    if required not in COMPLEXITIES:
        return unavailable("The required complexity is not supported.")

    # Use the same model settings as the readability analyzer.
    settings = {}
    for rule in context["rules"]["metrics"]:
        if rule["name"] == "readability":
            settings = rule["params"].copy()

    # Allow separate model settings in the complexity metric.
    for key in ("model", "temperature", "seed"):
        if key in params:
            settings[key] = params[key]

    schema = {
        "type": "object",
        "required": ["estimate", "explanation"],
        "additionalProperties": False,
        "properties": {
            "estimate": {
                "type": "string",
                "enum": COMPLEXITIES + ["unknown"]
            },
            "explanation": {
                "type": "string",
                "maxLength": 160
            }
        }
    }

    try:
        answer, evidence = ask_llama(
            "Estimate worst-case time complexity of this C program. "
            "Follow function calls, loop bounds and recursion. "
            "Use n for the logical input size, such as the number of elements. "
            "Treat fixed buffer capacity as a storage limit, not a reason "
            "to classify an input-dependent algorithm as constant time. "
            "Do not confuse incorrect output with high time complexity. "
            "Return unknown if termination, input size or complexity is unclear, "
            "or if the complexity cannot be expressed by the allowed labels. "
            "Explain the estimate in one sentence of at most 20 words.",
            {
                "problem": context["rules"]["problem"],
                "source": context["source"]
            },
            schema,
            settings
        )

        estimate = answer.get("estimate")
        explanation = answer.get("explanation")

        if not isinstance(explanation, str) or not explanation.strip():
            raise ValueError("Llama did not explain its estimate.")

        evidence["method"] = "LLM-estimated worst-case time complexity"
        evidence["estimate"] = estimate
        evidence["required"] = required
        evidence["explanation"] = explanation
        evidence["note"] = "No timing tests or mathematical proof."

        if estimate == "unknown":
            return unavailable(
                short_feedback(explanation),
                evidence
            )

        if estimate not in COMPLEXITIES:
            raise ValueError("Llama returned an unsupported complexity.")

        score = 0
        if COMPLEXITIES.index(estimate) <= COMPLEXITIES.index(required):
            score = 1

        return result(
            score,
            f"LLM estimate: {estimate}; required: {required}. Review advised.",
            evidence
        )

    except Exception as error:
        return unavailable("Llama complexity review unavailable: " + str(error))


# from pycparser import c_ast
# from analyzers.common import result, unavailable

# CONSTANT_CALLS = {
#     "printf", "scanf", "puts", "putchar", "getchar",
#     "abs", "labs", "llabs", "exit", "abort"
# }

# # Used by estimate(): check a for loop and return its cost.
# def loop_cost(loop):
#     condition = loop.cond
#     step = loop.next

#     if not isinstance(condition, c_ast.BinaryOp):
#         raise ValueError("Unsupported loop condition.")
#     if condition.op not in ("<", "<="):
#         raise ValueError("Only < and <= loops are supported.")
#     if not isinstance(condition.left, c_ast.ID):
#         raise ValueError("The loop needs a variable counter.")

#     if not isinstance(step, c_ast.UnaryOp):
#         raise ValueError("The loop must use i++ or ++i.")
#     if step.op not in ("p++", "++"):
#         raise ValueError("The loop must use i++ or ++i.")
#     if not isinstance(step.expr, c_ast.ID):
#         raise ValueError("Unsupported loop counter.")
#     if step.expr.name != condition.left.name:
#         raise ValueError("Loop counters do not match.")

#     if isinstance(condition.right, c_ast.Constant):
#         return 0
#     return 1


# # Used by analyze(): 0 means O(1), 1 means O(n), 2 means O(n²).
# def estimate(node, functions, active):
#     if node is None:
#         return 0

#     if isinstance(node, (c_ast.While, c_ast.DoWhile)):
#         raise ValueError("while and do-while loops need manual analysis.")

#     # Check calls to other functions.
#     if isinstance(node, c_ast.FuncCall):
#         if not isinstance(node.name, c_ast.ID):
#             raise ValueError("Function pointers need manual analysis.")

#         name = node.name.name
#         if name in active:
#             raise ValueError("Recursion needs manual analysis.")

#         cost = estimate(node.args, functions, active)
#         if name in functions:
#             body = functions[name].body
#             helper_cost = estimate(body, functions, active + [name])
#             return max(cost, helper_cost)

#         if name not in CONSTANT_CALLS:
#             raise ValueError("Unknown function cost: " + name)
#         return cost

#     # Find the highest cost inside this part of the code.
#     cost = 0
#     for _, child in node.children():
#         cost = max(cost, estimate(child, functions, active))

#     if isinstance(node, c_ast.For):
#         cost += loop_cost(node)

#     return cost


# # Called by grader.py to calculate the complexity score.
# def analyze(context, params):
#     if context["static"] is None:
#         return unavailable(context["static_error"])

#     functions = {}
#     for function in context["static"]["functions"]:
#         functions[function["name"]] = function["node"]

#     if "main" not in functions:
#         return result(0, "No main function found.")

#     try:
#         degree = estimate(functions["main"].body, functions, ["main"])
#     except ValueError as error:
#         return unavailable(str(error))

#     label = f"O(n^{degree})"
#     if degree == 0:
#         label = "O(1)"
#     elif degree == 1:
#         label = "O(n)"

#     required = params.get("required", "O(1)")
#     bounds = {"O(1)": 0, "O(n)": 1, "O(n^2)": 2, "O(n^3)": 3}
#     if required not in bounds:
#         return unavailable("Required complexity is not supported.")

#     score = 0
#     if degree <= bounds[required]:
#         score = 1

#     return result(
#         score,
#         f"Estimated {label}; required {required}. This is not a proof.",
#         {
#             "estimate": label,
#             "required": required,
#             "method": "Static loop and function-call analysis",
#             "sizes": params.get("sizes", []),
#             "note": "No timing tests. Fixed-size input/output is assumed constant."
#         }
#     )
