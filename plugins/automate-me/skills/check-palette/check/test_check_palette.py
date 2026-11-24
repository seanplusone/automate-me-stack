"""Run: python3 check/test_check_palette.py. Runs every case, then breaks one rule at a time in a
copy of the script and fails if the copy still passes. Prints SKIP without Playwright."""
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
OK, ERR = "CHECK-PALETTE: OK", "CHECK-PALETTE: ERROR"
TMP = tempfile.mkdtemp()
BRIEF = os.path.join(TMP, "brief.md")
for name, text in [("brief.md", "# Brief\n- Allow Beige: yes\n"), ("empty-list.json", "[]"), ("empty-dict.json", "{}"), ("blue.json", '["#3A6EA5"]')]:
    open(os.path.join(TMP, name), "w").write(text)
shutil.copy(os.path.join(CASES, "beige-card.html"), os.path.join(TMP, "x#y.html"))

# label, case, args, exit code, substring in output
TABLE = [
    ("beige-card", "beige-card", [], 1, "beige (H="),
    ("beige-section", "beige-section", [], 1, "#F2EBD6 beige (H="),
    ("hash-in-path", f"{TMP}/x#y", [], 1, "beige (H="),
    ("faded", "faded", [], 1, "beige (H="),
    ("beige-allowed", "beige-allowed", ["--allow-beige"], 0, OK),
    ("beige-allowed-brief", "beige-allowed", ["--brief", BRIEF], 0, OK),
    ("beige-unallowed", "beige-allowed", [], 1, "beige (H="),
    ("palette-ok", "palette-ok", PAL, 0, OK),
    ("near-palette", "near-palette", PAL, 0, OK),
    ("off-palette", "off-palette", PAL, 1, "off-palette (nearest #"),
    ("off-palette-no-palette", "off-palette", [], 0, OK),
    ("blue-canvas", "blue-canvas", ["--palette", f"{TMP}/blue.json"], 0, OK),
    ("beige-canvas", "beige-canvas", [], 1, "FAIL html #FAF9F5 beige"),
    ("hidden", "hidden", [], 0, OK),
    ("empty-list", "palette-ok", ["--palette", f"{TMP}/empty-list.json"], 2, ERR),
    ("empty-dict", "palette-ok", ["--palette", f"{TMP}/empty-dict.json"], 2, ERR),
    *[(f"{o}={d}", "palette-ok", [*PAL, o, d], 2, ERR) for o in ("--max-delta", "--min-area") for d in ("nan", "inf", "-1")],
    ("neutral", "neutral", [], 0, OK),
    ("covered", "covered", [], 0, OK),
    ("group", "group", [], 0, OK),
    ("missing-page", "no-such-page", [], 2, ERR),
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
    ("alpha-ignored", "a = d[3] / 255", "a = d[3] && 1", "beige-section"),
    ("canvas-body-ignored", "bg(body) ? body : html", "html", "blue-canvas"),
    ("opacity-ignored", "o = +s.opacity", "o = 1", "faded"),
    ("group-ignored", "scale(over(c, b), o)", "over(c, scale(b, op(x)))", "group"),
    ("cover-ignored", "const seen = (e, r, skip) => {", "const seen = () => true, unused = (e, r, skip) => {", "covered"),
    ("all-painted", "const painted = s =>", "const painted = s => true ||", "neutral"),
]


def run(script, row):
    label, case, args, _, _ = row
    p = subprocess.run([sys.executable, script, os.path.join(CASES, case + ".html"), *args],
                       capture_output=True, text=True, timeout=60)
    return label, p.returncode, p.stdout + p.stderr


def table(script):
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
    for h in ["#FAF9F5", "#F0EEE6", "#F1E9D2", "#F5F5DC", "#FFFDD0", "#FFF8F0", "#FFF1E7", "#F6F5F4"]:
        if not cp.is_beige(cp.parse_hex(h)):
            fails.append(f"{h} should be beige")
    for h in ["#FFFFFF", "#F5F5F5", "#EEEEEE", "#E8F0FE", "#1F2937", "#FFE0B2"]:
        if cp.is_beige(cp.parse_hex(h)):
            fails.append(f"{h} should not be beige")
    if cp.ALLOW_LINE.search("allow beige:\nyes"):
        fails.append("the allow line must not span a newline")
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
        if mutated == src:
            fails.append(f"mutant {name} did not change the script")
            continue
        path = os.path.join(TMP, name + ".py")
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
