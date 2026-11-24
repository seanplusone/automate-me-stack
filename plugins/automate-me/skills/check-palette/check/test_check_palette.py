"""Run: python3 check/test_check_palette.py

Runs check_palette.py on every case, then proves each rule matters: a copy of the script with one
rule broken must fail the table on the case that guards that rule. Prints SKIP without Playwright.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "..", "cases")
sys.path.insert(0, HERE)
import check_palette as cp  # noqa: E402

PAL = ["--palette", os.path.join(CASES, "palette.json")]
OK = "CHECK-PALETTE: OK"
TMP = tempfile.mkdtemp()
BRIEF = os.path.join(TMP, "brief.md")
open(BRIEF, "w").write("# Brief\n- Allow Beige: yes\n")

# label, case, args, exit code, substring in output
TABLE = [
    ("beige-card", "beige-card", [], 1, "beige (H="),
    ("beige-section", "beige-section", [], 1, "beige (H="),
    ("beige-allowed", "beige-allowed", ["--allow-beige"], 0, OK),
    ("beige-allowed-brief", "beige-allowed", ["--brief", BRIEF], 0, OK),
    ("beige-unallowed", "beige-allowed", [], 1, "beige (H="),
    ("palette-ok", "palette-ok", PAL, 0, OK),
    ("near-palette", "near-palette", PAL, 0, OK),
    ("off-palette", "off-palette", PAL, 1, "off-palette (nearest #"),
    ("off-palette-no-palette", "off-palette", [], 0, OK),
    ("neutral", "neutral", [], 0, OK),
    ("missing-page", "no-such-page", [], 2, "CHECK-PALETTE: ERROR"),
]

# name, old text, new text, the row that must catch it
MUTANTS = [
    ("beige-disabled", "CHECK_BEIGE = True", "CHECK_BEIGE = False", "beige-card"),
    ("hue-moved", "BEIGE_HUE = (25, 60)", "BEIGE_HUE = (180, 220)", "beige-card"),
    ("sat-floor-removed", "BEIGE_MIN_SAT = 10 ", "BEIGE_MIN_SAT = -1 ", "neutral"),
    ("allow-ignored", "allow = args.allow_beige or bool(", "allow = False and (", "beige-allowed"),
    ("delta-huge", "MAX_DELTA_DEFAULT = 5 ", "MAX_DELTA_DEFAULT = 1000 ", "off-palette"),
    ("delta-zero", "MAX_DELTA_DEFAULT = 5 ", "MAX_DELTA_DEFAULT = 0 ", "near-palette"),
    ("body-only", 'ELEMENTS = "*"', 'ELEMENTS = "html, body"', "beige-card"),
]


def run(script, row):
    label, case, args, _, _ = row
    p = subprocess.run([sys.executable, script, os.path.join(CASES, case + ".html"), *args],
                       capture_output=True, text=True, timeout=60)
    return label, p.returncode, p.stdout + p.stderr


def table(script):
    """Returns {label: (code, output, problem or None)}."""
    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(lambda r: run(script, r), TABLE))
    out = {}
    for (label, _, _, code, want), (_, got, text) in zip(TABLE, results):
        bad = None
        if got != code or want not in text:
            last = text.strip().splitlines()[-1] if text.strip() else "no output"
            bad = f"expected exit {code} with '{want}', got exit {got}: {last}"
        out[label] = (got, text, bad)
    return out


def self_check():
    fails = []
    for h in ["#FAF9F5", "#F0EEE6", "#F1E9D2", "#F5F5DC", "#FFFDD0", "#FFF8F0"]:
        if not cp.is_beige(cp.parse_hex(h)):
            fails.append(f"{h} should be beige")
    for h in ["#FFFFFF", "#F5F5F5", "#EEEEEE", "#E8F0FE", "#1F2937", "#FFE0B2"]:
        if cp.is_beige(cp.parse_hex(h)):
            fails.append(f"{h} should not be beige")
    d = cp.delta_e((50, 2.6772, -79.7751), (50, 0, -82.7485))  # Sharma 2005 pair 1
    if abs(d - 2.0425) > 1e-3:
        fails.append(f"CIEDE2000 pair 1 gave {d:.4f}, want 2.0425")
    return fails


def main():
    script = os.path.join(HERE, "check_palette.py")
    fails = self_check()
    probe = run(script, TABLE[-2])
    if probe[1] == 2 and "SKIP" in probe[2]:
        print(probe[2].strip(), *(f"  {f}" for f in fails), sep="\n")
        shutil.rmtree(TMP, ignore_errors=True)
        return 1 if fails else 0
    base = table(script)
    fails += [f"{label}: {bad}" for label, (_, _, bad) in base.items() if bad]
    survivors = 0
    for name, old, new, row in MUTANTS:
        src = open(script).read()
        mutated = src.replace(old, new, 1)
        assert mutated != src, f"mutant {name} did not change the script"
        path = os.path.join(TMP, name, "check_palette.py")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(mutated)
        got, text, bad = table(path)[row]
        if bad and got in (0, 1) and "Traceback" not in text:
            print(f"KILLED {name}: {row} {bad}")
        else:
            survivors += 1
            print(f"SURVIVED {name}" + (f" ({row} crashed: exit {got})" if bad else ""))
    shutil.rmtree(TMP, ignore_errors=True)
    for f in fails:
        print(f"  {f}")
    ok = not fails and not survivors
    print(f"{'PASS' if ok else 'FAIL'} test_check_palette: {len(TABLE)} cases, {len(MUTANTS) - survivors}/{len(MUTANTS)} mutants killed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
