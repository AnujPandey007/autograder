from analyzers.common import result, unavailable
from llm_review import ask_llama, short_feedback


# Llama reviews readability for any C problem, not correctness or execution.
def analyze(context, params):
    schema = {
        "type": "object", "required": ["score", "feedback"], "additionalProperties": False,
        "properties": {
            "score": {"type": "integer", "minimum": 0, "maximum": 10},
            "feedback": {"type": "string", "maxLength": 160}
        }
    }
    try:
        answer, evidence = ask_llama(
            "Grade readability from 0 to 10: naming 0-3, layout 0-3, "
            "clear organization 0-2, useful comments where needed 0-2. "
            "Do not penalize a simple self-explanatory program for lacking comments. "
            "Return exactly one short, complete sentence of at most 15 words. "
            "Give only the most useful observation or improvement. "
            "Mention the most useful observation or improvement; do not repeat the score. "
            "Do not reward advanced features or penalize a simple solution for being simple. "
            "Do not grade correctness, complexity or originality.",
            {"problem": context["rules"]["problem"], "source": context["source"]}, schema, params
        )
        score = answer.get("score")
        if type(score) is not int or not 0 <= score <= 10:
            raise ValueError("Llama readability score must be an integer from 0 to 10.")
        if not isinstance(answer.get("feedback"), str) or not answer["feedback"].strip():
            raise ValueError("Llama did not provide readability feedback.")
        evidence["method"] = "Ollama Llama readability review"
        return result(score / 10, short_feedback(answer["feedback"]), evidence)
    except Exception as error:
        return unavailable("Llama readability review unavailable: " + str(error))
