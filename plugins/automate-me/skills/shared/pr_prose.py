"""Checks the prose a pull request publishes against the [script] rules in writing-rules.md.

The prose is every comment line and markdown line the diff adds, each commit message, and the PR body.
Each hit is reported by where it lives, so it can be fixed at the source.

Usage: python3 pr_prose.py <base> [<head>] [--body FILE] [--message FILE]
With no <head>, the diff is the index against <base>, so staged changes count along with commits.
"""
import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_writing import check_writing  # noqa: E402

COMMENT_START = ("//", "#", "*", "/*", "{{--", "<!--", "--")
MAX_UNFENCED_BODY = 150
FENCE = re.compile(r"```.*?```", re.S)
TESTS_FIRST = re.compile(r"^Tests first[*_]*\s*(?::|$)", re.I)
REVIEWERS = re.compile(r"^Reviewers[*_]*\s*(?::|$)", re.I)
COMMENT_TRIM = re.compile(r"^(/\*\*?|\*+|//+|#+|\{\{--|<!--|--)\s?|\s*(\*/|--\}\}|-->)\s*$")
TRAILERS = ("co-authored-by:", "signed-off-by:", "fixes: http")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def added_prose(base, head):
    diff = git("diff", "-U0", f"{base}...{head}") if head else git("diff", "-U0", "--cached", base)
    items, path, line = [], None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            line = int(re.search(r"\+(\d+)", raw).group(1))
        elif raw.startswith("+") and path:
            text = raw[1:].strip()
            if path.endswith(".md"):
                if text:
                    items.append((f"{path}:{line}", text))
            elif text.startswith(COMMENT_START) and not text.startswith(("#!", "#[")):
                prose = COMMENT_TRIM.sub("", text).strip()
                if prose and not prose.startswith("@"):
                    items.append((f"{path}:{line}", prose))
            line += 1
    return items


def message_lines(label, text):
    return [(f"{label}:{n}", t.strip()) for n, t in enumerate(text.splitlines(), 1)
            if t.strip() and not t.strip().lower().startswith(TRAILERS)]


def collect(base, head=None, body=None, message=None):
    items = added_prose(base, head)
    if head:
        for sha in git("rev-list", "--reverse", f"{base}..{head}").split():
            items += message_lines(f"commit {sha[:9]}", git("log", "-1", "--format=%B", sha))
    if message:
        items += message_lines(f"message {message}", open(message).read())
    if body:
        items += message_lines(f"body {body}", open(body).read())
    return items


def check(items):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("\n".join(text for _, text in items) + "\n")
    with contextlib.redirect_stdout(io.StringIO()):
        fails = check_writing(f.name)
    os.unlink(f.name)
    hits = []
    for fail in fails:
        n, rule = re.match(r"line (\d+) (.*)", fail).groups()
        where, text = items[int(n) - 1]
        hits.append(f"{where} {rule}: {text}")
    return hits


def check_body_shape(path):
    """Checks W26: unfenced PR body shape.

    Unfenced prose is at most MAX_UNFENCED_BODY words. Fenced blocks do not count.
    A Tests first line is allowed only as a single line. A Reviewers section fails.
    """
    text = open(path).read()
    unfenced = FENCE.sub("", text)
    fails = []
    words = len(unfenced.split())
    if words > MAX_UNFENCED_BODY:
        fails.append(
            f"W26 unfenced body is {words} words, cap is {MAX_UNFENCED_BODY}"
        )
    lines = unfenced.splitlines()
    for i, line in enumerate(lines):
        line = re.sub(r"^[\s#*_]+", "", line)
        if TESTS_FIRST.match(line) and i + 1 < len(lines) and lines[i + 1].strip():
            fails.append("W26 multi-line Tests first narration")
        if REVIEWERS.match(line):
            fails.append("W26 Reviewers: section")
    return fails


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("base")
    p.add_argument("head", nargs="?")
    p.add_argument("--body")
    p.add_argument("--message")
    a = p.parse_args()
    items = collect(a.base, a.head, a.body, a.message)
    hits = check(items)
    if a.body:
        hits.extend(f"body {a.body} {m}" for m in check_body_shape(a.body))
    print(f"{'FAIL' if hits else 'PASS'} prose: {len(items)} lines checked")
    for h in hits:
        print(f"  {h}")
    sys.exit(1 if hits else 0)
