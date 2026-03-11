"""Strip all comments and docstrings from Python source files."""
import ast
import io
import os
import re
import tokenize

SRC_DIR = os.path.join(os.path.dirname(__file__), "src")

SKIP_DIRS = {"__pycache__", "migrations", "static"}
SKIP_FILES = {"prompt_builder.py"}  # has template strings that look like docstrings


def strip_comments_and_docstrings(source: str) -> str:
    result = []
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return source

    docstring_lines: set[int] = set()
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                ):
                    ds = node.body[0]
                    for ln in range(ds.lineno, ds.end_lineno + 1):
                        docstring_lines.add(ln)
    except SyntaxError:
        pass

    for tok in tokens:
        token_type = tok.type
        token_string = tok.string
        start_line, start_col = tok.start
        end_line, end_col = tok.end

        if token_type == tokenize.COMMENT:
            continue

        if token_type == tokenize.STRING and start_line in docstring_lines:
            for ln in range(start_line, end_line + 1):
                docstring_lines.add(ln)
            continue

        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            result.append(" " * (start_col - last_col))
        result.append(token_string)
        prev_toktype = token_type
        last_lineno = end_line
        last_col = end_col

    text = "".join(result)

    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.rstrip()
        if stripped == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(stripped)

    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()

    return "\n".join(cleaned) + "\n"


def process_file(filepath: str) -> bool:
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()

    if not original.strip():
        return False

    cleaned = strip_comments_and_docstrings(original)
    if cleaned != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cleaned)
        return True
    return False


def main():
    count = 0
    for root, dirs, files in os.walk(SRC_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in sorted(files):
            if not fname.endswith(".py"):
                continue
            if fname in SKIP_FILES:
                print(f"  SKIP {os.path.relpath(os.path.join(root, fname))}")
                continue
            filepath = os.path.join(root, fname)
            if process_file(filepath):
                count += 1
                print(f"  CLEAN {os.path.relpath(filepath)}")
    print(f"\nDone. Cleaned {count} files.")


if __name__ == "__main__":
    main()
