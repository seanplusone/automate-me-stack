"""Tests for check_verify.py against the pr-1 sample. Run: cd check && python3 test_check_verify.py"""
import io
import os
import re
import shutil
import struct
import sys
import tempfile
import zlib
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_verify  # noqa: E402

SAMPLE = os.path.join(HERE, "..", "cases", "demo-app", "pr-1", "sample-verify.md")
FAILS = []


def png_bytes(rgb=(255, 0, 0)):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00" + bytes(rgb)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def write_dummy(path, idx):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".png":
        data = png_bytes((idx % 256, (idx * 37) % 256, (idx * 73) % 256))
    elif ext in (".jpg", ".jpeg"):
        data = b"\xff\xd8\xff\xe0" + bytes([idx % 256])
    elif ext == ".webp":
        data = b"RIFF\x04\x00\x00\x00WEBP" + bytes([idx % 256])
    else:
        data = b""
    with open(path, "wb") as f:
        f.write(data)


def run(text, touch=True):
    d = tempfile.mkdtemp(prefix="verify-md-")
    p = os.path.join(d, "verify.md")
    open(p, "w").write(text)
    if touch:
        idx = 0
        for line in text.splitlines():
            names = []
            if line.startswith("Evidence: ") and "/" not in line:
                names = [f.strip() for f in line[len("Evidence: "):].split(",") if f.strip()]
            elif line.startswith(("Persist screenshot: ", "Before screenshot: ")):
                name = line.split(":", 1)[1].strip()
                if name and "/" not in name and "\\" not in name:
                    names = [name]
            for name in names:
                fp = os.path.join(d, name)
                if not os.path.exists(fp):
                    idx += 1
                    write_dummy(fp, idx)
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

def s1(steps="click Refund", base="button enabled", head="button disabled",
       evidence="s1.png", extra="", verdict="VERIFIED", s2_verdict="CONTRADICTED"):
    summary = ("1 CONTRADICTED, 1 VERIFIED, 0 NOT RUN" if verdict == "VERIFIED" and s2_verdict == "CONTRADICTED"
               else "0 CONTRADICTED, 2 VERIFIED, 0 NOT RUN" if verdict == "VERIFIED" and s2_verdict == "VERIFIED"
               else "2 CONTRADICTED, 0 VERIFIED, 0 NOT RUN")
    return (
        "# verify: example/demo-shop#1 x\n"
        "PR: https://github.com/example/demo-shop/pull/1\n"
        "Base: main 0000000aaaaaaa\n"
        "Head: fix/refund-double-click 1111111bbbbbbb\n"
        "App: http://127.0.0.1:8000 (demo)\n"
        "Evidence: ev\n"
        "Doctor: base OK, head OK\n"
        "\n"
        "## S1. One click\n"
        'Claimed: "x" (body)\n'
        f"Steps: {steps}\n"
        f"Base: {base}\n"
        f"Head: {head}\n"
        f"Evidence: {evidence}\n"
        f"{extra}"
        f"Verdict: {verdict}\n"
        "\n"
        "## S2. Double click\n"
        'Claimed: "y" (body)\n'
        "Steps: click\n"
        "Base: two refunds\n"
        "Head: two refunds\n"
        "Evidence: s2.png\n"
        f"Verdict: {s2_verdict}\n"
        "\n"
        f"Summary: {summary}\n"
    )


FIELD = "Persist: reload\nPersist screenshot: s1-persist.png\nBefore screenshot: s1.png\n"

# Old loose cases: prose or a filename looks like a persist check, but there is no field.
expect("did not reload in prose without a field fails VERIFIED",
       s1(head="did not reload, button disabled"), "Persist:")
expect("skipped the reload in prose without a field fails VERIFIED",
       s1(head="skipped the reload, button disabled"), "Persist:")
expect("a reload word only in a filename without a field fails VERIFIED",
       s1(evidence="s1-head-reload.png"), "Persist:")
expect("persist named only on Base without a field fails VERIFIED",
       s1(base="after a reload the button stays enabled", head="button disabled"), "Persist:")
expect("Reloaded the page in prose without a field fails VERIFIED",
       s1(steps="click Refund, Reloaded the page"), "Persist:")
expect("missing Persist field fails VERIFIED", s1(), "Persist:")
expect("Persist value other than reload or fresh-context fails VERIFIED",
       s1(extra="Persist: yes\nPersist screenshot: s1-persist.png\n"), "Persist:")
# Good field: prose does not matter.
expect("Persist: reload with an existing screenshot passes",
       s1(steps="click Refund, Reloaded the page", evidence="s1.png, s1-persist.png", extra=FIELD))
expect("Persist: fresh-context with an existing screenshot passes",
       s1(evidence="s1.png, s1-persist.png",
          extra="Persist: fresh-context\nPersist screenshot: s1-persist.png\nBefore screenshot: s1.png\n"))
expect("CONTRADICTED without a Persist field still passes",
       s1(verdict="CONTRADICTED", s2_verdict="CONTRADICTED"))


# Persist screenshot path is named, but the file is not in the folder.
d = tempfile.mkdtemp(prefix="verify-md-")
p = os.path.join(d, "verify.md")
open(p, "w").write(s1(extra="Persist: reload\nPersist screenshot: missing.png\n"))
open(os.path.join(d, "s1.png"), "w").close()
open(os.path.join(d, "s2.png"), "w").close()
with redirect_stdout(io.StringIO()) as out:
    fails = check_verify.check(p)
shutil.rmtree(d)
ok = any("Persist screenshot" in f or "missing.png" in f for f in fails)
print(f"{'PASS' if ok else 'FAIL'} missing Persist screenshot file fails VERIFIED")
if not ok:
    FAILS.append("missing Persist screenshot file fails VERIFIED")
    print("    " + out.getvalue().replace("\n", "\n    "))


RED, BLUE = png_bytes((255, 0, 0)), png_bytes((0, 0, 255))


def run_files(text, files, needle=None, name=""):
    d = tempfile.mkdtemp(prefix="verify-md-")
    p = os.path.join(d, "verify.md")
    open(p, "w").write(text)
    for n, data in files.items():
        open(os.path.join(d, n), "wb").write(data)
    with redirect_stdout(io.StringIO()) as out:
        fails = check_verify.check(p)
    shutil.rmtree(d)
    ok = not fails if needle is None else any(needle in f for f in fails)
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        FAILS.append(name)
        print("    " + out.getvalue().replace("\n", "\n    "))
    return fails


def write_case(persist_shot="s1-persist.png", before="s1.png", evidence=None, persist="reload",
               extra=None):
    ev = evidence if evidence is not None else f"{before}, {persist_shot}, s2.png"
    fields = extra if extra is not None else (
        f"Persist: {persist}\nPersist screenshot: {persist_shot}\nBefore screenshot: {before}\n"
    )
    return s1(evidence=ev, extra=fields)


GOOD = {"s1.png": RED, "s1-persist.png": BLUE, "s2.png": RED}

run_files(write_case(persist_shot="notes.txt", evidence="s1.png, notes.txt, s2.png"),
          {**GOOD, "notes.txt": b"not an image"},
          needle="Persist screenshot", name="notes.txt as persist screenshot fails VERIFIED")
run_files(write_case(persist_shot="empty.bin", evidence="s1.png, empty.bin, s2.png"),
          {**GOOD, "empty.bin": b""},
          needle="Persist screenshot", name="empty .bin as persist screenshot fails VERIFIED")
run_files(write_case(persist_shot="verify.md", evidence="s1.png, verify.md, s2.png"),
          GOOD,
          needle="Persist screenshot", name="verify.md as persist screenshot fails VERIFIED")
run_files(write_case(persist_shot="s1.png", evidence="s1.png, s2.png"),
          GOOD,
          needle="Persist screenshot", name="reuse of the pre-action s1.png fails VERIFIED")
run_files(write_case(persist_shot="s1-persist.png", evidence="s1.png, s2.png"),
          GOOD,
          needle="Evidence", name="persist screenshot not listed in Evidence fails VERIFIED")
run_files(write_case(),
          {"s1.png": RED, "s1-persist.png": RED, "s2.png": BLUE},
          needle="Persist screenshot", name="persist screenshot with the same bytes as before fails VERIFIED")
run_files(s1(extra="Persist: none\n"),
          {"s1.png": RED, "s2.png": BLUE},
          needle=None, name="Persist: none with no screenshots passes VERIFIED")
run_files(write_case(persist="reloaded"),
          GOOD,
          needle="Persist:", name="Persist: reloaded fails VERIFIED")
run_files(s1(evidence="s1.png, s1-persist.png", extra="Persist: reload\nPersist screenshot: s1-persist.png\n"),
          GOOD,
          needle="Before screenshot", name="missing Before screenshot fails VERIFIED")
run_files(write_case(before="s1.png", evidence="s1-persist.png, s2.png"),
          GOOD,
          needle="Before screenshot", name="Before screenshot not listed in Evidence fails VERIFIED")
run_files(s1(evidence="s1.png, s2.png, s1-persist.png",
             extra="Persist: reload\nPersist screenshot: s1.png\nBefore screenshot: s1.png\nBefore screenshot: s2.png\n"),
          {"s1.png": RED, "s2.png": BLUE, "s1-persist.png": BLUE},
          needle="duplicate Before screenshot", name="reuse of s1.png hidden by a second Before screenshot fails VERIFIED")
run_files(s1(evidence="s1.png, s1-persist.png",
             extra="Persist: reload\nPersist: reload\nPersist screenshot: s1-persist.png\nBefore screenshot: s1.png\n"),
          GOOD,
          needle="duplicate", name="a repeated Persist line fails VERIFIED")
run_files(s1(evidence="s1.png, s2.png, s1-persist.png",
             extra="Persist: reload\nPersist screenshot: s1-persist.png\nBefore screenshot: s1.png\nBefore screenshot: s2.png\n"),
          {"s1.png": RED, "s2.png": png_bytes((0, 255, 0)), "s1-persist.png": BLUE},
          needle="duplicate", name="a repeated Before screenshot line fails VERIFIED")
run_files(s1(evidence="s1.png, notes.txt, s1-persist.png",
             extra="Persist: reload\nPersist screenshot: notes.txt\nPersist screenshot: s1-persist.png\nBefore screenshot: s1.png\n"),
          {**GOOD, "notes.txt": b"not an image"},
          needle="duplicate", name="a duplicate Persist screenshot hides a bad earlier value and fails VERIFIED")

print(f"\n{'FAIL' if FAILS else 'PASS'} test_check_verify ({len(FAILS)} failing)")
shutil.rmtree(os.path.join(HERE, "__pycache__"), ignore_errors=True)
sys.exit(1 if FAILS else 0)
