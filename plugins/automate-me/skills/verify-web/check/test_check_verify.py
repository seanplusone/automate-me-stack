"""Tests for check_verify.py against the pr-1 sample. Run: cd check && python3 test_check_verify.py"""
import io
import os
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_verify  # noqa: E402

SAMPLE = os.path.join(HERE, "..", "cases", "demo-app", "pr-1", "sample-verify.md")
FAILS = []


def run(text, touch=True):
    d = tempfile.mkdtemp(prefix="verify-md-")
    p = os.path.join(d, "verify.md")
    open(p, "w").write(text)
    if touch:
        for line in text.splitlines():
            if line.startswith("Evidence: ") and "/" not in line:
                for f in line[len("Evidence: "):].split(","):
                    open(os.path.join(d, f.strip()), "w").close()
    with redirect_stdout(io.StringIO()) as out:
        fails = check_verify.check(p)
    shutil.rmtree(d)
    return fails, out.getvalue()


def expect(name, text, needle=None, touch=True):
    fails, out = run(text, touch)
    ok = not fails if needle is None else any(needle in f for f in fails)
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        FAILS.append(name)
        print("    " + out.replace("\n", "\n    "))


sample = open(SAMPLE).read()
expect("sample passes with its evidence files present", sample)
expect("a missing evidence file fails", sample, "evidence file not in the folder", touch=False)
expect("a made-up verdict fails", sample.replace("Verdict: CONTRADICTED", "Verdict: PARTLY"), "verdict must be")
expect("NOT RUN without a reason fails", sample.replace("Verdict: CONTRADICTED", "Verdict: NOT RUN"), "verdict must be")
expect("NOT RUN with a reason passes once the summary matches",
       sample.replace("Verdict: CONTRADICTED", "Verdict: NOT RUN: head would not start")
             .replace("Summary: 1 CONTRADICTED, 2 VERIFIED, 0 NOT RUN", "Summary: 0 CONTRADICTED, 2 VERIFIED, 1 NOT RUN"))
expect("a wrong summary fails", sample.replace("Summary: 1 CONTRADICTED", "Summary: 0 CONTRADICTED"), "Summary line")
expect("a head line without a sha fails", re.sub(r"(?m)^Head: .*$", "Head: fix/refund-double-click", sample), "header Head")
one = sample[: sample.index("## S2.")] + "Summary: 0 CONTRADICTED, 1 VERIFIED, 0 NOT RUN\n"
expect("one scenario is too few", one, "1 scenarios")
expect("a scenario without Base fails", sample.replace("Base: two refund rows", "Seen: two refund rows"), "S2: missing Base:")

print(f"\n{'FAIL' if FAILS else 'PASS'} test_check_verify ({len(FAILS)} failing)")
shutil.rmtree(os.path.join(HERE, "__pycache__"), ignore_errors=True)
sys.exit(1 if FAILS else 0)
