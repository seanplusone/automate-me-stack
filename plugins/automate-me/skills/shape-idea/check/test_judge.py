"""Run: python3 check/test_judge.py

Uses a fake CLI. No network and no real agent.
"""
import os
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_case import build_prompt, find_cli, judge, parse_verdict  # noqa: E402

FAILS = []
RAN = []
HERE = os.path.dirname(os.path.abspath(__file__))
SALAD = os.path.join(HERE, "fixtures", "keyword-salad.md")


def expect(name, ok, detail=""):
    RAN.append(name)
    if not ok:
        FAILS.append(f"{name}: {detail}")


prompt = build_prompt([("Decided", "goal", ["phone", "water"], "phone water is not the goal")])
expect("prompt names the line and the terms", "ITEM 1 Decided goal" in prompt and "not the goal" in prompt and "phone" in prompt,
       prompt)
expect("a no answer parses as false", parse_verdict("ITEM 1: no\n", 1) == [False])
expect("a yes answer parses as true", parse_verdict("item 2: yes", 2) == [None, True])

fake_dir = tempfile.mkdtemp()
fake = os.path.join(fake_dir, "judge-fake")
open(fake, "w").write("""#!/bin/sh
python3 -c '
import sys
text = sys.stdin.read()
blocks = text.split("ITEM ")
for block in blocks[1:]:
    number = block.split()[0]
    line = ""
    for row in block.splitlines():
        if row.startswith("LINE "):
            line = row[5:]
    answer = "no" if (" not " in line or "banana" in line or line == "(no line)") else "yes"
    print("ITEM %s: %s" % (number, answer))
'
""")
os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)

key = os.path.join(fake_dir, "key.md")
bad = os.path.join(fake_dir, "decisions.md")
open(key, "w").write("Decided: goal | phone | water\nDecided: done | streak\n")
open(bad, "w").write("""# Decisions: t

## Decided

- goal: phone water is not the goal
- done: the streak is the point
- output: o
- verify: v
- constraints: c

## Open

- none

## Parked

- none

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 3
- writing: pass
- map: goal goes to Goal.
""")
env = {"PATH": "/nonexistent", "JUDGE_CLI": fake}
code = judge(key, bad, environ=env)
expect("fake CLI fails a reversed goal", code == 1, f"exit {code}")

empty = {"PATH": "/nonexistent"}
expect("no CLI means skip", find_cli(empty) is None)
skip = subprocess.run([sys.executable, os.path.join(HERE, "judge_case.py"), key, bad],
                      capture_output=True, text=True, env={"PATH": "/nonexistent"})
expect("skip exits 0", skip.returncode == 0 and "SKIP" in skip.stdout, skip.stdout + skip.stderr)

if os.path.exists(SALAD):
    salad_key = os.path.join(fake_dir, "salad-key.md")
    open(salad_key, "w").write(
        "Decided: goal | lunch | vote\nDecided: constraints | payments | orders\n")
    salad_code = judge(salad_key, SALAD, environ=env)
    expect("fake CLI fails keyword salad", salad_code == 1, f"exit {salad_code}")

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
