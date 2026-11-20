"""Meaning judge for a planted-bug attack review.

Usage: python3 check/judge_case.py <key.md> <attack.md>

The keyword scorer only checks that the catch terms are present. This judge
asks whether a finding states the same bug. It runs whichever agent CLI is
on PATH, `codex exec` or `claude -p`. The prompt is written to that command's
stdin. If neither CLI is installed, it prints SKIP and exits 0. Set
JUDGE_CLI to one executable to force a command. That executable must read
the prompt on stdin and write `ITEM 1: yes` or `ITEM 1: no`.

Exit 0 when the finding catches the bug, or when no CLI is available.
Exit 1 when the judge says the bug was missed.
Exit 2 on a usage error.
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import parse_attack  # noqa: E402

ITEM = re.compile(r"^ITEM\s+(\d+)\s*:\s*([A-Za-z]+)\b", re.I)


def find_cli(environ=None):
    """An argv list, or None when no judge can run."""
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


def build_prompt(key_text, findings):
    lines = [
        "You judge whether a review finding catches the planted bug.",
        "Answer yes only when a finding states that same bug.",
        "Answer no when the findings describe a different problem, or none do.",
        "",
        "BUG",
        key_text.strip(),
        "",
    ]
    if not findings:
        lines.append("FINDINGS")
        lines.append("(none)")
    for finding in findings:
        claim = finding.get("claim") or ""
        if isinstance(claim, list):
            claim = " ".join(claim)
        where = finding.get("where") or ""
        if not where and finding.get("file"):
            line = finding.get("line")
            where = finding["file"] if line is None else f"{finding['file']}:{line}"
        lines.append("FINDING " + finding.get("id", ""))
        lines.append("WHERE " + where)
        lines.append("CLAIM " + claim)
        lines.append("REPRO " + finding.get("repro", ""))
        lines.append("OBSERVED " + finding.get("observed", ""))
        lines.append("")
    lines.append("Reply with one line and nothing else.")
    lines.append("ITEM 1: yes")
    lines.append("ITEM 1: no")
    return "\n".join(lines)


def _judge_line(line):
    """Drop emphasis and backticks so a wrapped answer still counts."""
    text = line.strip()
    text = re.sub(r"^[>*_\s`]+", "", text)
    text = re.sub(r"[*_`]+$", "", text)
    return text.strip()


def parse_verdict(text):
    """True, False, 'conflict' when one item has both answers, or None."""
    found = {}
    for raw in (text or "").split("\n"):
        match = ITEM.match(_judge_line(raw))
        if not match:
            continue
        word = match.group(2).lower()
        if word not in ("yes", "no"):
            continue
        number = int(match.group(1))
        found.setdefault(number, []).append(word == "yes")
    answers = found.get(1) or []
    if not answers:
        return None
    if any(answer != answers[0] for answer in answers):
        return "conflict"
    return answers[0]


def run_cli(argv, prompt):
    result = subprocess.run(argv, input=prompt, text=True, capture_output=True)
    return result.returncode, result.stdout


def judge(key_path, attack_path, environ=None, runner=None, findings=None):
    """0 when the bug is caught or no CLI exists, 1 on a miss, 2 on a bad exit."""
    doc = parse_attack(attack_path)
    chosen = doc["findings"] if findings is None else findings
    prompt = build_prompt(open(key_path).read(), chosen)
    argv = find_cli(environ)
    if argv is None and runner is None:
        print("SKIP no agent CLI on PATH")
        return 0
    if runner:
        out = runner(prompt)
        if isinstance(out, tuple):
            code, stdout = out
        else:
            code, stdout = 0, out
    else:
        code, stdout = run_cli(argv, prompt)
    if code:
        print("SKIP judge exited non-zero")
        return 2
    ok = parse_verdict(stdout)
    if ok is True:
        print("PASS judge caught planted bug")
        return 0
    print("FAIL judge missed planted bug")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        print((__doc__ or "").strip())
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2)
    sys.exit(judge(sys.argv[1], sys.argv[2]))
