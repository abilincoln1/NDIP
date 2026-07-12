#!/usr/bin/env python3
"""
NDIP Dead-Code Detector
Scans backend service files for the specific bug pattern discovered twice
in this codebase: a function body containing a `return` statement that is
NOT the final statement, meaning subsequent code (often newly-added
enrichment/tracking logic) is unreachable.

This does not catch every possible dead-code pattern (e.g. dead code after
an if/else where both branches return), but it catches exactly the pattern
that caused the V5.6 decision_support.py bug: an early unconditional
top-level `return {...}` followed by additional top-level statements.

Run: docker exec agora-backend-1 python scripts/detect_dead_code.py
Or locally before packaging any change: python3 scripts/detect_dead_code.py
"""
import ast
import sys
import os
import glob


def check_file(filepath: str) -> list:
    """Return a list of (function_name, line_number, issue) tuples for a single file."""
    try:
        source = open(filepath).read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        return [(f"<parse error>", e.lineno or 0, f"SyntaxError: {e}")]
    except Exception as e:
        return [(f"<read error>", 0, str(e))]

    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body = node.body
            for i, stmt in enumerate(body[:-1]):
                if isinstance(stmt, ast.Return):
                    next_stmt = body[i + 1]
                    issues.append((
                        node.name,
                        stmt.lineno,
                        f"return statement at line {stmt.lineno} is followed by unreachable "
                        f"code starting at line {next_stmt.lineno} ({len(body) - i - 1} statement(s))"
                    ))
    return issues


def main():
    target_dirs = [
        "/app/app/services",
        "/app/app/api/routes",
        "/app/app/analytics",
    ]
    if not os.path.exists(target_dirs[0]):
        # running locally, not in container
        target_dirs = [d.replace("/app/app", "app") for d in target_dirs]

    total_issues = 0
    files_checked = 0

    print("=" * 60)
    print("  NDIP Dead-Code Detector")
    print("=" * 60)

    for target_dir in target_dirs:
        if not os.path.isdir(target_dir):
            continue
        for filepath in sorted(glob.glob(f"{target_dir}/**/*.py", recursive=True)):
            files_checked += 1
            issues = check_file(filepath)
            if issues:
                total_issues += len(issues)
                print(f"\n  [!!] {filepath}")
                for func_name, line_no, issue in issues:
                    print(f"       Function '{func_name}' (line {line_no}): {issue}")

    print(f"\n{'=' * 60}")
    print(f"  Files checked: {files_checked}")
    print(f"  Issues found:  {total_issues}")
    print("=" * 60)

    if total_issues > 0:
        print("\n  ACTION REQUIRED: review flagged functions above.")
        print("  This exact pattern caused a real production bug in decision_support.py")
        print("  (a dict literal `return {...}` instead of `result = {...}`, leaving")
        print("  enrichment/tracking code permanently unreachable).")
        sys.exit(1)
    else:
        print("\n  No dead-code patterns detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
