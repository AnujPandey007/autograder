import hashlib
from difflib import SequenceMatcher
from pathlib import Path
from analyzers.common import result, unavailable, tokens
from rules import project_path


# Called by grader.py to compare the submission with other C files.
def analyze(context, params):
    paths = list(context.get("peers", []))
    corpus = project_path(params.get("corpus_dir", "submissions/"))
    if corpus.is_dir():
        paths += sorted(corpus.rglob("*.c"))

    # Remove duplicate paths and the submission itself.
    own_path = Path(context["source_path"]).resolve()
    candidates = []
    for path in paths:
        path = Path(path).resolve()
        if path != own_path and path not in candidates:
            candidates.append(path)

    if not candidates:
        return unavailable("No other C files available for comparison.")
    if len(candidates) > 100:
        return unavailable("Use at most 100 comparison files.")

    own_tokens = tokens(context["source"])
    if len(own_tokens) > 5000:
        return unavailable("Submission exceeds the 5000-token limit.")

    matches = []
    best = 0

    # Compare each file after removing comments and whitespace.
    for path in sorted(candidates):
        if path.stat().st_size > 262144:
            return unavailable("A comparison file exceeds 256 KB.")

        text = path.read_text(encoding="utf-8")
        other_tokens = tokens(text)
        if len(other_tokens) > 5000:
            return unavailable("A comparison file exceeds the 5000-token limit.")

        comparison = SequenceMatcher(
            None, own_tokens, other_tokens, autojunk=False
        )
        similarity = round(comparison.ratio(), 4)
        best = max(best, similarity)

        matches.append({
            "file": path.name,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "similarity": similarity
        })

    threshold = params.get("flag_threshold", 0.85)
    evidence = {
        "matches": matches,
        "threshold": threshold,
        "max_similarity": best,
        "flagged": best >= threshold,
        "method": "Token comparison ignoring comments and whitespace",
        "limitations": (
            "No online search or reliable AI-authorship detection. "
            "Short programs commonly match."
        )
    }

    feedback = f"Max similarity: {best:.4f}; flag threshold: {threshold:.2f}. "
    if best >= threshold:
        return result(
            None, feedback + "Flagged for instructor review.",
            evidence, "review_required"
        )
    return result(
        1, feedback + "Below threshold; no similarity flag. This does not prove originality.",
        evidence
    )
