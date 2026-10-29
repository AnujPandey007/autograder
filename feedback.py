import copy
import re
import json
from pathlib import Path
from llm_review import short_feedback


# Shared report notes are stored separately, not generated for each question.
def usefulness_limitations():
    filename = Path(__file__).with_name("report_notes.json")
    with filename.open(encoding="utf-8") as file:
        return json.load(file)


def explain_failure(test):
    status = test.get("status")

    if status == "skipped":
        return "Not executed because compilation failed or an earlier run stopped."

    if status == "timeout":
        return (
            "Time limit exceeded. This alone does not prove "
            "an infinite loop or a memory defect."
        )

    if status == "output_limit":
        return "The program exceeded the output limit."

    if status == "unavailable":
        return "The grader could not complete execution."

    if test.get("stderr"):
        return test["stderr"].strip()

    if status == "runtime_error":
        return "The program crashed or exited with an error."

    if test.get("label") == "int_overflow":
        return (
            "Output differs from the mathematical result at an integer "
            "boundary. Check numeric range and overflow handling."
        )

    return "Actual output differs from expected output, including whitespace."


def build_report(raw):
    # Already converted to the assignment-style format.
    if "submission" in raw:
        return raw

    if "error" in raw:
        return {
            "submission": raw["file"],
            "status": "error",
            "grade": None,
            "error": raw["error"],
            "metrics": [],
            "flags": ["evaluation_error"]
        }

    metrics = []
    flags = []

    for item in raw["metrics"]:
        evidence = copy.deepcopy(item["evidence"])
        tests = evidence.pop("tests", None)

        if tests is not None:
            evidence["tests_passed"] = sum(
                bool(test["passed"]) for test in tests
            )
            evidence["tests_total"] = len(tests)
            evidence["tests_run"] = sum(
                test["status"] != "skipped" for test in tests
            )
            evidence["tests_skipped"] = sum(
                test["status"] == "skipped" for test in tests
            )

            evidence["failing"] = []
            evidence["skipped"] = []

            for number, test in enumerate(tests, 1):
                if test["passed"]:
                    continue

                entry = {
                    "test": number,
                    "input": test["input"],
                    "expected": test["expected"],
                    "got": test["actual"],
                    "status": test["status"],
                    "note": explain_failure(test)
                }

                if test["status"] == "skipped":
                    evidence["skipped"].append(entry)
                else:
                    evidence["failing"].append(entry)

                if test["status"] in [
                    "timeout", "output_limit", "unavailable"
                ]:
                    flags.append(item["name"] + "_" + test["status"])

        if item["name"] == "modularity":
            evidence["functions_defined"] = len(
                evidence.get("functions", [])
            )
            evidence["expected_min"] = evidence.get("required")

        if item["status"] != "ok":
            flags.append(item["name"] + "_" + item["status"])

        if evidence.get("flagged"):
            flags.append("suspected_similarity")

        metrics.append({
            "name": item["name"],
            "analyzer": item["analyzer"],
            "score": item["score"],
            "weight": item["weight"],
            "contribution": item["marks"],
            "status": item["status"],
            "evidence": evidence,
            "feedback": short_feedback(item["feedback"])
        })

    first_pass = raw.get("first_pass", {
        "compiled": None,
        "smoke_ok": None,
        "suspected_infinite_loop": None
    })

    if first_pass.get("suspected_infinite_loop"):
        flags.append("suspected_infinite_loop")

    ai_feedback = raw.get("ai_feedback", {
        "status": "unavailable", "suggestions": [], "error": "No Llama feedback was recorded."
    })
    suggestions = ai_feedback["suggestions"]
    if ai_feedback["status"] != "ok":
        flags.append("llm_feedback_unavailable")

    return {
        "submission": raw["file"],
        "problem": raw["problem"],
        "rules_hash": "sha256:" + raw["rules_sha256"],
        "grade": raw["grade"],
        "status": raw["status"],
        "assessed_marks": raw["earned_marks"],
        "available_marks": raw["available_marks"],
        "first_pass": first_pass,
        "metrics": metrics,
        "flags": sorted(set(flags)),
        "suggestions": suggestions,
        "ai_feedback": ai_feedback,
        "usefulness_limitations": usefulness_limitations(),
        "tool_versions": {
            "compiler": raw["compiler"]["version"],
            "python": raw.get("python"),
            "pycparser": raw.get("pycparser")
        },
        "execution_note": raw.get("execution_note", "")
    }


def make_feedback(raw):
    report = build_report(raw)

    lines = [
        f"===== Grading report for {report['submission']} ====="
    ]

    if "error" in report:
        lines.append("Evaluation error: " + report["error"])
        return "\n".join(lines)

    if report["grade"] is None:
        lines.append("Overall grade: pending (partial evaluation)")
        lines.append(
            f"Assessed marks: {report['assessed_marks']:.0f}"
            f" / {report['available_marks']:.0f}"
        )
    else:
        lines.append(
            f"Overall grade: {report['grade']:.0f} / 100"
        )

    lines.append("")
    lines.append(
        f"{'Metric':<16} {'Weight':>7} {'Score':>13} "
        f"{'Contribution':>13}  Feedback"
    )

    for metric in report["metrics"]:
        maximum = metric["weight"] * 100
        marks = metric["contribution"]

        if marks is None:
            score = "pending"
            contribution = "pending"
        else:
            score = f"{marks:.0f}/{maximum:g}"
            contribution = f"{marks:.0f}"

        lines.append(
            f"{metric['name']:<16} {maximum:>6g}% "
            f"{score:>13} {contribution:>13}  "
            f"{metric['feedback']}"
        )

    for metric in report["metrics"]:
        if metric["name"] == "originality":
            matches = metric["evidence"].get("matches", [])
            if matches:
                lines += ["", "--- Originality comparison ---"]
                for match in matches:
                    lines.append(
                        f"{match['file']}: similarity {match['similarity']:.4f}"
                    )

    lines += ["", "--- Where you failed ---"]
    found = False

    for metric in report["metrics"]:
        for test in metric["evidence"].get("failing", []):
            found = True

            # Hide the Docker location in readable reports; keep the error reason.
            note = re.sub(
                r"/work/submission\.c:\d+(?::\d+)?:\s*(?:runtime error:\s*)?",
                "", test["note"]
            )

            lines += [
                f"\n{metric['name']} - Test {test['test']:02d}",
                f"INPUT:    {test['input']!r}",
                f"EXPECTED: {test['expected']!r}",
                f"GOT:      {test['got']!r}",
                "WHY:      " + note
            ]

        diagnostics = metric["evidence"].get("stderr", "")

        if metric["name"] == "syntax" and diagnostics:
            found = True
            lines += ["\nCompiler diagnostics:", diagnostics]

    if not found:
        lines.append(
            "No failing execution cases or compiler diagnostics recorded."
        )

    lines += ["", "--- Checks not completed ---"]
    pending = []

    for metric in report["metrics"]:
        skipped = metric["evidence"].get("tests_skipped", 0)

        if skipped:
            pending.append(
                f"{metric['name']}: {skipped} cases were not executed."
            )

        if metric["score"] is None:
            pending.append(
                metric["name"] + ": " + metric["feedback"]
            )

    lines += pending or ["None."]

    lines += ["", "--- Suggestions to raise the grade ---"]

    ai_feedback = report.get("ai_feedback", {})
    if ai_feedback.get("status") != "ok":
        lines.append("Llama feedback unavailable: " + ai_feedback.get("error", "No response."))
    else:
        lines.append("Llama suggestions: review these alongside the test evidence.")
        if report["suggestions"]:
            for suggestion in report["suggestions"]:
                lines.append("- " + suggestion)
        else:
            lines.append("Llama returned no additional suggestions.")

    lines += [
        "",
        "--- Usefulness & limitations of this evaluation ---",
        "These are general evaluator examples, not an AI assessment of this submission.",
        "Useful for:"
    ]

    for item in report["usefulness_limitations"]["usefulness"]:
        lines += [
            "- " + item["use_case"],
            "  Example: " + item["example"],
            "  Benefit: " + item["benefit"]
        ]

    lines.append("\nLimitations:")

    for item in report["usefulness_limitations"]["limitations"]:
        lines += [
            "- " + item["limitation"],
            "  Example: " + item["example"],
            "  Mitigation: " + item["mitigation"]
        ]

    return "\n".join(lines)


def save_reports(reports, filename):
    # app.py currently passes [report].
    if isinstance(reports, list):
        if len(reports) != 1:
            raise ValueError(
                "Save one submission report at a time."
            )
        raw = reports[0]
    else:
        raw = reports

    report = build_report(raw)

    json_path = Path(filename)
    text_path = json_path.with_suffix(".txt")

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    text_path.write_text(
        make_feedback(report),
        encoding="utf-8"
    )

    return str(json_path), str(text_path)