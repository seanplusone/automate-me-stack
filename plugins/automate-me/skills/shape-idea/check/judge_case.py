"""Meaning judge for a shape-idea decisions file.

Usage: python3 check/judge_case.py <key.md> <decisions.md>

For each key item it asks whether the matched line keeps the same meaning.
Reversed, negated, and merged lines are misses. The keyword scorer only
checks that the words are present. This judge checks what they mean.

It runs whichever agent CLI is on PATH, `codex exec` or `claude -p`. The
prompt is written to that command's stdin. If neither CLI is installed,
it prints SKIP and exits 0. Set JUDGE_CLI to one executable to force a
command. That executable must read the prompt on stdin and write the verdict
on stdout, one line per item: `ITEM <n>: yes` or `ITEM <n>: no`.

Exit 0 when every item is preserved, or when no CLI is available.
Exit 1 when an item is missing, reversed, negated, or merged.
Exit 2 on a usage error.
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_case import named, read_key  # noqa: E402
from check_decisions import SLOTS, parse, real_items, slot_of, split_fences  # noqa: E402

ITEM = re.compile(r"ITEM\s+(\d+)\s*:\s*(yes|no)\b", re.I)


def pool_for(sections, kind, ident):
    body = real_items(sections.get(kind, []))
    if ident.lower() in SLOTS:
        return [item for item in body if slot_of(item) == ident.lower()]
    return [item for item in body if slot_of(item) is None]


def pairs(key_path, decisions_path):
    """Each key item with the first unused line that holds its terms, if any."""
    from score_case import missing
    visible = split_fences(open(decisions_path, encoding="utf-8-sig").read())[0]
    sections, _, _, _ = parse(visible)
    rows, used, cache = [], {}, {}
    for kind, parts in read_key(key_path):
        ident, terms = named(parts)
        pool_key = (kind, ident.lower() if ident.lower() in SLOTS else "*")
        if pool_key not in cache:
            cache[pool_key] = pool_for(sections, kind, ident)
        body = cache[pool_key]
        taken = used.setdefault(pool_key, set())
        chosen = ""
        for index, item in enumerate(body):
            if index in taken or missing(terms, item):
                continue
            taken.add(index)
            chosen = item
            break
        rows.append((kind, ident, terms, chosen))
    return rows


def build_prompt(rows):
    lines = [
        "You judge whether a decisions line preserves a key item.",
        "Answer yes only when the line states the same meaning.",
        "Answer no when the line reverses it, negates it, merges it with another item, or does not state it.",
        "",
    ]
    for number, (kind, ident, terms, line) in enumerate(rows, 1):
        lines.append(f"ITEM {number} {kind} {ident}")
        lines.append("TERMS " + " | ".join(terms))
        lines.append("LINE " + (line or "(no line)"))
        lines.append("")
    lines.append("Reply with one line per item, and nothing else.")
    lines.append("ITEM <n>: yes")
    lines.append("ITEM <n>: no")
    return "\n".join(lines)


def parse_verdict(text, count):
    found = {}
    for match in ITEM.finditer(text or ""):
        found[int(match.group(1))] = match.group(2).lower() == "yes"
    return [found.get(number) for number in range(1, count + 1)]


def find_cli(environ=None):
    """Returns an argv list, or None when no judge can run."""
    env = os.environ if environ is None else environ
    override = env.get("JUDGE_CLI")
    if override:
        return [override]
    path = env.get("PATH", "")
    for name, extra in (("claude", ["-p"]), ("codex", ["exec"])):
        found = shutil.which(name, path=path)
        if found:
            return [found, *extra]
    return None


def run_cli(argv, prompt):
    result = subprocess.run(argv, input=prompt, text=True, capture_output=True)
    return result.stdout


def judge(key_path, decisions_path, environ=None, runner=None):
    rows = pairs(key_path, decisions_path)
    if not rows:
        print(f"FAIL no scorable lines in {key_path}")
        return 1
    argv = find_cli(environ)
    if argv is None and runner is None:
        print("SKIP no agent CLI on PATH")
        return 0
    prompt = build_prompt(rows)
    stdout = runner(prompt) if runner else run_cli(argv, prompt)
    verdicts = parse_verdict(stdout, len(rows))
    misses = 0
    for number, ((kind, ident, _, _), ok) in enumerate(zip(rows, verdicts), 1):
        if ok:
            print(f"{kind.lower()} {ident}: preserved")
        else:
            misses += 1
            print(f"{kind.lower()} {ident}: MISSED meaning not preserved")
    print(f"{'FAIL' if misses else 'PASS'} {len(rows) - misses}/{len(rows)} judged items")
    return 1 if misses else 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2)
    sys.exit(judge(sys.argv[1], sys.argv[2]))
