import re
from pycparser import c_parser, c_ast

STRINGS = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
BRANCHES = (c_ast.If, c_ast.For, c_ast.While, c_ast.DoWhile, c_ast.Case, c_ast.TernaryOp)

# Used by all 9 analyzers to return marks, feedback and evidence.
def result(score, feedback, evidence=None, status="ok"):
    return {"score": score, "status": status, "feedback": feedback, "evidence": evidence or {}}

# Used by grader.py and analyzers when a check cannot finish.
def unavailable(message, evidence=None): 
    return result(None, message, evidence, "unavailable")

# Used by parse_source() to visit each part of the C code.
def walk(node):
    yield node
    for _, child in node.children():
        yield from walk(child)

# Used by readability.py, parse_source() and tokens().
def strip_comments(source):
    def replace(match):
        text = match.group()
        if text.startswith(("//", "/*")):
            return re.sub(r"[^\n]", " ", text)
        return text
    return re.sub(STRINGS + r"|//[^\n]*|/\*[\s\S]*?\*/", replace, source)

# Called by grader.py; used by structure, modularity and complexity.
def parse_source(source):
    clean = strip_comments(source)
    for line in clean.splitlines():
        if line.lstrip().startswith("#") and not re.match(r"\s*#\s*include\b", line):
            raise ValueError("Macros and conditional preprocessing are not supported.")
    clean = re.sub(r"^[ \t]*#\s*include\b[^\n]*", "", clean, flags=re.MULTILINE)
    prefix = "typedef unsigned long size_t; typedef long ptrdiff_t; typedef struct FILE FILE;\n"
    tree = c_parser.CParser().parse(prefix + clean)
    masked = re.sub(STRINGS, lambda m: re.sub(r"[^\n]", " ", m.group()), clean)
    functions = []
    for node in tree.ext:
        if not isinstance(node, c_ast.FuncDef):
            continue
        start = node.coord.line - 1
        end = node.body.coord.line - 1
        body = "\n".join(masked.splitlines()[end - 1:])
        depth, branches = 0, 1
        # Count through the matching closing brace, ignoring strings.
        for char in body[node.body.coord.column - 1:]:
            if char == "\n":
                end += 1
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    break
        for item in walk(node):
            if isinstance(item, BRANCHES):
                branches += 1
            elif isinstance(item, c_ast.BinaryOp) and item.op in ("&&", "||"):
                branches += 1
        functions.append({"name": node.decl.name, "line": start, "length": end - start + 1, "cyclomatic": branches, "node": node})
    return {"tree": tree, "functions": functions, "clean": clean}

# Used by originality.py to compare C submissions.
def tokens(source):
    return re.findall(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|==|!=|<=|>=|\+\+|--|&&|\|\||[^\s]", strip_comments(source))