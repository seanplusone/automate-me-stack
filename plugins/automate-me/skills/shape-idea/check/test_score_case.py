"""Run: python3 check/test_score_case.py"""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_case import score  # noqa: E402

FAILS = []
RAN = []

DECISIONS = """# Decisions: t

## Decided

- goal: a tiny habit tracker on my phone
- done: mark today done in under 10 seconds
- no accounts, only me

## Open

- Do you want a reminder, or would that be annoying?
- should the day reset at midnight or at 4am?

## Parked

- share streaks with friends

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 1
"""


def write(name, text):
    path = os.path.join(tempfile.mkdtemp(), name)
    open(path, "w").write(text)
    return path


def run(key, decisions=DECISIONS):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = score(write("key.md", key), write("decisions.md", decisions))
    return code, out.getvalue()


def expect(name, key, code, needle="", decisions=DECISIONS):
    RAN.append(name)
    got, out = run(key, decisions)
    if got != code or needle not in out:
        FAILS.append(f"{name}: wanted exit {code} with {needle!r}, got exit {got}:\n{out}")


expect("terms found", "Decided: goal | goal | phone\nOpen: reminder | annoying\nParked: friends | streaks\n", 0, "PASS 3/3")
expect("missing term", "Decided: goal | bedroom\n", 1, "no decided item names: bedroom")
expect("term in another section fails", "Open: phone | phone\n", 1, "no open item names: phone")
expect("terms must share one item", "Open: mixed | reminder | 4am\n", 1, "no open item names")
expect("10 does not match 100", "Decided: done | 10\n", 1, "no decided item names: 10",
       decisions=DECISIONS.replace("10 seconds", "100 seconds"))
expect("a short word is the whole word", "Decided: goal | app\n", 1, "no decided item names: app",
       decisions=DECISIONS.replace("habit tracker", "apply a filter"))
expect("a short word takes a plural s", "Open: pets | pet\n", 0, "PASS",
       decisions=DECISIONS.replace("Do you want a reminder, or would that be annoying?", "Do you have pets?"))
expect("pet does not match carpet", "Parked: pets | pet\n", 1, "no parked item names: pet",
       decisions=DECISIONS.replace("share streaks with friends", "the carpet is fine"))
expect("alternation", "Decided: goal | phone/tablet\n", 0, "PASS")
expect("a non-slot id does not read a slot line", "Decided: label | phone\n", 1, "no decided item names: phone")
expect("a slot id reads that slot line", "Decided: goal | phone\n", 0, "PASS")
RICH = """# Decisions: t

## Decided

- goal: a phone habit with drinking water, 10 seconds, a streak, accounts, and only me
- done: later
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
"""
expect("a slot key with no terms fails", "Decided: goal\n", 1, "needs at least one term")
expect("two key items cannot share one line",
       "Open: reminders | reminder | annoying\nOpen: name | call the app | midnight\n",
       1, "MISSED",
       decisions=DECISIONS.replace("- Do you want a reminder, or would that be annoying?",
                                   "- reminder annoying call the app midnight 4am?"))
expect("keywords on the wrong slot score low",
       "Decided: goal | phone | habit\nDecided: done | 10 seconds | streak\nDecided: constraints | accounts | only me\n",
       1, "FAIL 1/3", decisions=RICH)
expect("lone none is empty", "Parked: friends | friends\n", 1, "no parked item names: friends",
       decisions=DECISIONS.replace("- share streaks with friends", "- none"))
expect("key lines in a code block are ignored", "```\nDecided: nowhere | nowhere\n```\nDecided: goal | phone\n", 0, "PASS 1/1")
expect("empty key fails", "# nothing\n", 1, "no scorable lines")

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
