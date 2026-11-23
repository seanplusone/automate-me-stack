"""Run: python3 check/test_break.py

Each fixture names the check that must fail. A passing fixture maps to None.
Most fixtures are the control, 00_valid_control.md, with a few lines changed: PATCHED builds them in memory.
FILES holds the control and the fixtures that are not a small patch on it. a24_binary.bin is not UTF-8.
Most patches drop the map line, which the template requires, so `handoff has a map line` fails beside the check named.
14 stops open-cap on turn 1. 26 is a real done stop with five extra opens.
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_decisions import check  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
SCRIPT = os.path.join(HERE, "check_decisions.py")

# None means the file passes. Any other value is a check name that must fail.
FILES = {
    "00_valid_control.md": None,
    "lenient.md": "stop matches the file",
    "unclosed-fence.md": "code fence is closed",
}

CONTROL = open(os.path.join(FIXTURES, "00_valid_control.md"), encoding="utf-8").read()
MAP = next(line for line in CONTROL.splitlines(keepends=True) if line.startswith("- map:"))
NO_MAP = (MAP, "")
CONSTRAINTS = ("- constraints: c\n", "")
NEXT = "- next: /automate-me:outcome\n"


def opens(*lines):
    """Open holds these lines in place of `none`."""
    return ("## Open\n\n- none\n", "## Open\n\n" + "".join(f"- {line}\n" for line in lines))


def stop(reason, turns):
    return ("- stop: done\n- turns: 3\n", f"- stop: {reason}\n- turns: {turns}\n")


def turns(n):
    return ("- turns: 3\n", f"- turns: {n}\n")


def line(old, new):
    return (f"{old}\n", f"{new}\n")


SIX = ("a?", "b?", "c?", "d?", "e?", "f?")
ITEMS = tuple(f"Is item {i} in scope?" for i in range(1, 7))

# (name, patches on the control, check that must fail or None). Each patch is (old, new), and old is there once.
PATCHED = [
    ("01_slot_only_in_parked.md", [CONSTRAINTS, ("## Parked\n\n- none\n", "## Parked\n\n- constraints: maybe later\n"),
                                   stop("turn-cap", 10), NO_MAP], "every slot is decided or open"),
    ("02_turns_0.md", [turns(0), NO_MAP], "turn count recorded and at most 10"),
    ("03_duplicate_decided.md", [("- constraints: c\n\n", "- constraints: c\n\n## Decided\n\n- goal: x\n\n"), NO_MAP],
     "sections present once"),
    ("04_open_without_q.md", [CONSTRAINTS, opens("constraints: none yet"), stop("turn-cap", 10), NO_MAP],
     "no open item is a placeholder"),
    ("05_done_with_slot_in_open.md", [CONSTRAINTS, opens("constraints: what limits?"), NO_MAP], "stop matches the file"),
    ("06_missing_writing.md", [("- writing: pass\n", ""), NO_MAP], "handoff says writing pass"),
    ("07_writing_fail.md", [line("- writing: pass", "- writing: fail"), NO_MAP], "handoff says writing pass"),
    ("08_slot_in_both_decided_and_open.md", [opens("goal: which goal?"), NO_MAP], "a slot is not in Decided and Open"),
    ("09_duplicate_slot_decided.md", [line("- constraints: c", "- constraints: c\n- goal: another goal"), NO_MAP],
     "no duplicate slot"),
    ("10_empty_slot_values.md", [("- goal: g\n- done: d\n- output: o\n- verify: v\n- constraints: c\n",
                                  "- goal:\n- done:\n- output:\n- verify:\n- constraints:\n"), NO_MAP],
     "slot values are not empty"),
    ("11_open_slot_bare_q.md", [CONSTRAINTS, opens("constraints: ?"), stop("turn-cap", 10), NO_MAP],
     "slot values are not empty"),
    ("12_opencap_with_1_open.md", [CONSTRAINTS, opens("constraints: what limits?"), stop("open-cap", 2), NO_MAP],
     "stop matches the file"),
    ("13_turncap_at_turn_2.md", [CONSTRAINTS, opens("constraints: what limits?"), stop("turn-cap", 2), NO_MAP],
     "stop matches the file"),
    ("14_opencap_on_turn_1.md", [CONSTRAINTS, opens("constraints: a?", *SIX[1:]), stop("open-cap", 1), NO_MAP],
     "stop matches the file"),
    ("15_no_title.md", [("# Decisions: t\n\n", ""), NO_MAP], "file has a Decisions title"),
    ("16_writing_pass_selfreport_with_slop.md",
     [line("- goal: g", "- goal: we will leverage a robust, seamless synergy — truly delve into it"), NO_MAP],
     "prose passes the writing check"),
    ("17_wrong_next.md", [line("- next: /automate-me:outcome", "- next: /automate-me:outcome extra"), NO_MAP],
     "handoff names outcome"),
    # `none` beside other Open lines is on the CHECK WITH ME list, as `none` is everywhere. The missing map line is
    # what fails.
    ("18_none_plus_items_open.md", [CONSTRAINTS, opens("none", "constraints: what?"), stop("turn-cap", 10), NO_MAP],
     "handoff has a map line"),
    ("19_negative_turns.md", [turns(-1), NO_MAP], "turn count recorded and at most 10"),
    ("20_turns_unicode_digit.md", [turns("²"), NO_MAP], "turn count recorded and at most 10"),
    ("22_no_map_line.md", [NO_MAP], "handoff has a map line"),
    ("23_unknown_section.md", [("## Handoff", "## Notes\n\n- stray\n\n## Handoff"), NO_MAP],
     "no item longer than one line"),
    ("24_decided_slot_via_bold.md", [line("- goal: g", "- **goal**: g"), NO_MAP], "every slot is decided or open"),
    ("25_goal_prefix_word.md", [line("- goal: g", "- goalpost: g"), stop("turn-cap", 10), NO_MAP],
     "every slot is decided or open"),
    ("26_done_with_five_extra_opens.md", [opens(*SIX[:5])], None),
    ("a01_slot_space_colon_open.md", [opens("Output : still unsure?"), NO_MAP], "a slot is not in Decided and Open"),
    ("a07_turncap_should_be_opencap.md", [("- done: d\n- output: o\n- verify: v\n- constraints: c\n", ""),
                                          opens("done: d?", "output: o?", "verify: v?", "constraints: c?", *SIX),
                                          stop("turn-cap", 10), NO_MAP], "stop is the first match"),
    ("a08_turncap_should_be_done.md", [stop("turn-cap", 10), NO_MAP], "stop is the first match"),
    ("a09_opencap_should_be_done.md", [opens(*SIX), stop("open-cap", 4), NO_MAP], "stop is the first match"),
    ("a10_turn1_9_opens.md", [opens(*SIX, "g?", "h?", "i?"), turns(1), NO_MAP], "turn 1 parks overflow"),
    ("a25_dup_next.md", [(NEXT, NEXT + "- next: /automate-me:breakdown\n" * 2), (MAP, "\n")],
     "handoff fields are unique"),
    ("fenced-title.md", [line("# Decisions: t", "```md\n# Decisions: example\n```"), NO_MAP],
     "file has a Decisions title"),
    ("huge-turn.md", [turns("9" * 5000), NO_MAP], "turn count recorded and at most 10"),
    ("open-cap-beats-done.md", [opens(*ITEMS), stop("open-cap", 2), NO_MAP], "stop is the first match"),
    ("shadow-handoff.md", [line("- stop: done", "- stop: done\n- next: /other\n- **stop:** open-cap"), NO_MAP],
     "handoff fields are unique"),
    ("turn-cap-beats-open-cap.md", [("- output: o\n", ""), opens("output: What comes back?", *ITEMS),
                                    stop("turn-cap", 10), NO_MAP], "stop is the first match"),
]
EXPECT = {**FILES, **{name: want for name, _, want in PATCHED}}


def patched(patches):
    text = CONTROL
    for old, new in patches:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text


def fixture_texts():
    """(name, text) for every decisions fixture, the .md files and the patched ones, sorted by name."""
    texts = {name: open(os.path.join(FIXTURES, name), encoding="utf-8").read()
             for name in os.listdir(FIXTURES) if name.endswith(".md")}
    texts.update((name, patched(patches)) for name, patches, _ in PATCHED)
    return sorted(texts.items())


def main():
    fails = []
    texts = dict(fixture_texts())
    folder = tempfile.mkdtemp()
    for name, want in sorted(EXPECT.items()):
        try:
            got = [label for label, items in check(texts[name]) if items]
        except Exception as exc:
            fails.append(f"{name}: crashed: {exc}")
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
            fails.append(f"{name}: {detail}")

    binary = os.path.join(FIXTURES, "a24_binary.bin")
    ran = subprocess.run([sys.executable, SCRIPT, binary], capture_output=True, text=True, encoding="utf-8")
    said = (ran.stdout + ran.stderr).strip().splitlines()
    binary_ok = ran.returncode == 3 and len(said) == 1 and "not UTF-8" in said[0] and "Traceback" not in ran.stderr
    print(f"{'PASS' if binary_ok else 'FAIL'} a24_binary.bin: file is not UTF-8, a usage error")
    if not binary_ok:
        fails.append(f"a24_binary.bin: stdout={ran.stdout!r} stderr={ran.stderr!r}")

    # A fixture that names a failing check exits 1 from the script. A format-valid one exits 0, or 2 for one-letter
    # values such as `goal: g`. None crashes. A patched fixture is written to a temp file for the script to read.
    for name, want in sorted(EXPECT.items()):
        path = os.path.join(FIXTURES, name)
        if name not in FILES:
            path = os.path.join(folder, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(texts[name])
        ran = subprocess.run([sys.executable, SCRIPT, path], capture_output=True, text=True, encoding="utf-8")
        ok = ran.returncode in ((0, 2) if want is None else (1,)) and "Traceback" not in ran.stderr
        if not ok:
            fails.append(f"{name}: script exit {ran.returncode}, stderr {ran.stderr[-200:]!r}")
            print(f"FAIL {name}: script exit {ran.returncode}")

    print(f"{2 * len(EXPECT) + 1 - len(fails)}/{2 * len(EXPECT) + 1} fixtures matched")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
