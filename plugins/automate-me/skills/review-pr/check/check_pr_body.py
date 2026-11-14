"""Checks that a PR body is short and easy for a human reviewer to follow.

Usage: python3 check_pr_body.py <body.md>

A body passes when a person can read it once and know what changed and why:
- at most MAX_WORDS words
- at most MAX_OPENING sentences before the first list (what it does, and why)
- at most MAX_BULLETS list items, and at most one list
- at most MAX_HEADINGS headings
- no markdown tables, no glossary or definitions heading, no long fenced log
- no phrases that describe the review process rather than the change

An empty body fails. A short body with no list is allowed. Prints PASS or FAIL and exits 1 on FAIL.
"""
import re
import sys

MAX_WORDS = 180
MAX_OPENING = 3
MAX_BULLETS = 6
MAX_HEADINGS = 2
MAX_FENCE = 8

# Headings that turn a short PR into a document.
BAD_HEADING = re.compile(
    r"^(glossary|definitions?|terms(?: used)?|reviewers?|review notes|"
    r"how this was reviewed|how we scored|appendix|changelog)$",
    re.I,
)
# Process or write-up phrases that do not help a human reviewer.
BAD_PHRASE = re.compile(
    r"staff engineers?|security staff|as a reviewer|the review panel|"
    r"glossary|definition of|score tables?|pass/fail table|"
    r"how I reviewed|how we reviewed|refuter|lenses:\s*\d|"
    r"for the interview|this PR was reviewed by|generated with",
    re.I,
)
HEADING = re.compile(r"^#{1,6}\s+(.*)$")
TABLE = re.compile(r"^\s*\|.+\|\s*$")
BULLET = re.compile(r"^\s*[-*+]\s+\S")
FENCE = re.compile(r"^```")
ABBREV = re.compile(r"(?:e\.g|i\.e|etc|vs|Mr|Mrs|Ms|Dr|No)\.$")


def words(text):
    return [w for w in re.split(r"\s+", text.strip()) if w]


def sentences(text):
    """Split opening prose into sentences, ignoring common abbreviations."""
    text = " ".join(text.split())
    if not text:
        return []
    out, buf = [], []
    for part in re.split(r"(?<=[.!?])\s+", text):
        buf.append(part)
        joined = " ".join(buf)
        if ABBREV.search(joined) and not re.search(r"[.!?]\s+\S*$", joined):
            continue
        if re.search(r"[.!?]$", part):
            out.append(joined)
            buf = []
    if buf:
        out.append(" ".join(buf))
    return out


def check_pr_body(path):
    text = open(path, encoding="utf-8").read()
    fails = []
    if not text.strip():
        return ["body is empty; say what the PR does and why"]

    body_words = words(re.sub(r"`[^`]+`", "x", text))
    if len(body_words) > MAX_WORDS:
        fails.append(f"body is {len(body_words)} words, max {MAX_WORDS}")

    headings, bullets, tables, opening, in_fence, seen_list, after_list = [], 0, 0, [], False, False, False
    fence_lines = 0
    extra_lists = 0
    for line in text.splitlines():
        if FENCE.match(line):
            if in_fence and fence_lines > MAX_FENCE:
                fails.append(
                    f"fenced block is {fence_lines} lines, max {MAX_FENCE}; drop logs and paste a path or a short command"
                )
            in_fence = not in_fence
            fence_lines = 0
            continue
        if in_fence:
            fence_lines += 1
            continue
        m = HEADING.match(line)
        if m:
            title = m.group(1).strip()
            headings.append(title)
            if BAD_HEADING.match(title.rstrip(":")):
                fails.append(f"heading '{title}' is a glossary or review write-up; keep what, why, and a few bullets")
            continue
        if TABLE.match(line):
            tables += 1
            continue
        if BULLET.match(line):
            if seen_list and after_list:
                extra_lists += 1
            seen_list = True
            after_list = False
            bullets += 1
            continue
        if seen_list and line.strip():
            after_list = True
        if not seen_list and line.strip():
            opening.append(line.strip())

    if in_fence and fence_lines > MAX_FENCE:
        fails.append(
            f"fenced block is {fence_lines} lines, max {MAX_FENCE}; drop logs and paste a path or a short command"
        )
    if tables:
        fails.append("body has a markdown table; say the result in a sentence, not a score table")
    if len(headings) > MAX_HEADINGS:
        fails.append(f"body has {len(headings)} headings, max {MAX_HEADINGS}")
    if bullets > MAX_BULLETS:
        fails.append(f"body has {bullets} bullets, max {MAX_BULLETS}")
    if extra_lists:
        fails.append("body has more than one list; fold the changes into one short list")
    opening_text = " ".join(opening)
    n_sent = len(sentences(opening_text))
    if n_sent > MAX_OPENING:
        fails.append(f"opening has {n_sent} sentences, max {MAX_OPENING} (what it does, and why)")
    for m in BAD_PHRASE.finditer(text):
        fails.append(f"body names the review process or a glossary term: '{m.group(0)}'")
    return fails


def main(argv):
    fails = check_pr_body(argv[1])
    print(f"{'FAIL' if fails else 'PASS'} pr body: {argv[1]}")
    for f in fails:
        print(f"  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 1)
    sys.exit(main(sys.argv))
