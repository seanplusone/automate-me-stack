"""Run: python3 check/test_break.py

Each fixture names the check that must fail. A passing fixture maps to None.
22 has no map line, and the template requires one, so it fails that check.
14 stops open-cap on turn 1. 26 is a real done stop with five extra opens.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_decisions import check  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
SCRIPT = os.path.join(HERE, "check_decisions.py")

# None means the file passes. Any other value is a check name that must fail.
EXPECT = {
    "00_valid_control.md": None,
    "01_slot_only_in_parked.md": "every slot is decided or open",
    "02_turns_0.md": "turn count recorded and at most 10",
    "03_duplicate_decided.md": "sections present once",
    "04_open_without_q.md": "no open item is a placeholder",
    "05_done_with_slot_in_open.md": "stop matches the file",
    "06_missing_writing.md": "handoff says writing pass",
    "07_writing_fail.md": "handoff says writing pass",
    "08_slot_in_both_decided_and_open.md": "a slot is not in Decided and Open",
    "09_duplicate_slot_decided.md": "no duplicate slot",
    "10_empty_slot_values.md": "slot values are not empty",
    "11_open_slot_bare_q.md": "slot values are not empty",
    "12_opencap_with_1_open.md": "stop matches the file",
    "13_turncap_at_turn_2.md": "stop matches the file",
    "14_opencap_on_turn_1.md": "stop matches the file",
    "15_no_title.md": "file has a Decisions title",
    "16_writing_pass_selfreport_with_slop.md": "prose passes the writing check",
    "17_wrong_next.md": "handoff names outcome",
    "18_none_plus_items_open.md": "no open item is a placeholder",
    "19_negative_turns.md": "turn count recorded and at most 10",
    "20_turns_unicode_digit.md": "turn count recorded and at most 10",
    "22_no_map_line.md": "handoff has a map line",
    "23_unknown_section.md": "no item longer than one line",
    "24_decided_slot_via_bold.md": "every slot is decided or open",
    "25_goal_prefix_word.md": "every slot is decided or open",
    "26_done_with_five_extra_opens.md": None,
    "lenient.md": "stop matches the file",
    "open-cap-beats-done.md": "stop is the first match",
    "turn-cap-beats-open-cap.md": "stop is the first match",
    "unclosed-fence.md": "code fence is closed",
    "shadow-handoff.md": "handoff fields are unique",
    "huge-turn.md": "turn count recorded and at most 10",
    "fenced-title.md": "file has a Decisions title",
    "a08_turncap_should_be_done.md": "stop is the first match",
    "a09_opencap_should_be_done.md": "stop is the first match",
    "a07_turncap_should_be_opencap.md": "stop is the first match",
    "a10_turn1_9_opens.md": "turn 1 parks overflow",
    "a01_slot_space_colon_open.md": "a slot is not in Decided and Open",
    "a25_dup_next.md": "handoff fields are unique",
}

FAILS = []


def names(path):
    return [label for label, items in check(open(path, encoding="utf-8").read()) if items]


for name in sorted(os.listdir(FIXTURES)):
    if not name.endswith(".md") or name not in EXPECT:
        continue
    want = EXPECT[name]
    try:
        got = names(os.path.join(FIXTURES, name))
    except Exception as exc:
        FAILS.append(f"{name}: crashed: {exc}")
        print(f"FAIL {name}: crashed: {exc}")
        continue
    if want is None:
        ok = not got
        detail = "ok" if ok else ", ".join(got)
    else:
        ok = want in got
        detail = want if ok else f"missing {want}; got {', '.join(got)}"
    print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    if not ok:
        FAILS.append(f"{name}: {detail}")

binary = os.path.join(FIXTURES, "a24_binary.bin")
ran = subprocess.run([sys.executable, SCRIPT, binary], capture_output=True, text=True, encoding="utf-8")
said = (ran.stdout + ran.stderr).strip().splitlines()
binary_ok = ran.returncode == 3 and len(said) == 1 and "not UTF-8" in said[0] and "Traceback" not in ran.stderr
print(f"{'PASS' if binary_ok else 'FAIL'} a24_binary.bin: file is not UTF-8, a usage error")
if not binary_ok:
    FAILS.append(f"a24_binary.bin: stdout={ran.stdout!r} stderr={ran.stderr!r}")

# A fixture that names a failing check exits 1 from the script. A format-valid one exits 0, or 2 for one-letter values
# such as `goal: g`. None crashes.
for name, want in sorted(EXPECT.items()):
    ran = subprocess.run([sys.executable, SCRIPT, os.path.join(FIXTURES, name)], capture_output=True, text=True,
                         encoding="utf-8")
    ok = ran.returncode in ((0, 2) if want is None else (1,)) and "Traceback" not in ran.stderr
    if not ok:
        FAILS.append(f"{name}: script exit {ran.returncode}, stderr {ran.stderr[-200:]!r}")
        print(f"FAIL {name}: script exit {ran.returncode}")

if __name__ == "__main__":
    print(f"{2 * len(EXPECT) + 1 - len(FAILS)}/{2 * len(EXPECT) + 1} fixtures matched")
    sys.exit(1 if FAILS else 0)
