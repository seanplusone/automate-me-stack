"""Run: python3 check/test_attack_agents.py"""
import os
import stat
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attack_agents import command, detect, main as agent_main, run_all, stamp  # noqa: E402

FAILS = []
STUB = """#!/usr/bin/env python3
import os, sys
sys.stdout.write("agent=" + os.path.basename(sys.argv[0]) + "\\n")
sys.stdout.write("args=" + " ".join(sys.argv[1:]) + "\\n")
sys.stdout.write("brief=" + sys.stdin.read())
"""


def expect(name, got, want):
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


def bindir(*names):
    path = tempfile.mkdtemp()
    for name in names:
        file = os.path.join(path, name)
        open(file, "w").write(STUB)
        os.chmod(file, os.stat(file).st_mode | stat.S_IEXEC)
    return path


empty = tempfile.mkdtemp()
expect("neither cli", detect(empty), [])
expect("none is not an error", run_all(os.path.join(empty, "missing"), empty, search_path=empty), 0)

both = bindir("codex", "claude")
found = detect(both)
expect("both names", [name for name, _binary in found], ["codex", "claude"])
codex_bin = found[0][1]
expect("codex argv has no prompt", command(codex_bin, "codex")[1:],
       ["exec", "--skip-git-repo-check", "--sandbox", "workspace-write"])
claude_bin = found[1][1]
expect("claude argv has no prompt", command(claude_bin, "claude")[1:],
       ["-p", "--permission-mode", "acceptEdits", "--allowedTools", "Bash"])

brief = os.path.join(tempfile.mkdtemp(), "brief.md")
open(brief, "w").write("attack this diff")
out = tempfile.mkdtemp()
code = run_all(brief, out, search_path=both)
expect("run exits 0", code, 0)
codex_out = open(os.path.join(out, "codex.md")).read()
claude_out = open(os.path.join(out, "claude.md")).read()
expect("codex saw the brief", "brief=attack this diff" in codex_out, True)
expect("codex was exec", "args=exec --skip-git-repo-check" in codex_out, True)
expect("claude saw the brief", "brief=attack this diff" in claude_out, True)
expect("claude was print mode", "args=-p --permission-mode acceptEdits --allowedTools Bash" in claude_out, True)
expect("prompt is not an argument", "attack this diff" not in claude_out.split("brief=")[0], True)

only = bindir("claude")
expect("claude alone", [name for name, _binary in detect(only)], ["claude"])
expect("stamp adds the agent", "passes: claude" in stamp("### F1 | head/cap.py:3\nbroke\n", "claude"), True)
expect("stamp does not repeat the agent",
       stamp("### F1 | cap.py:3 | passes: claude\n", "claude").count("claude"), 1)
section = stamp("## Findings (all in cap.py:3)\n### F1 | cap.py:3\n", "codex")
expect("stamp leaves a section header", section.splitlines()[0], "## Findings (all in cap.py:3)")
expect("stamp still marks the finding", "passes: codex" in section, True)

slow_dir = tempfile.mkdtemp()
slow = os.path.join(slow_dir, "codex")
open(slow, "w").write("#!/bin/sh\nsleep 5\n")
os.chmod(slow, os.stat(slow).st_mode | stat.S_IEXEC)
slow_out = tempfile.mkdtemp()
code = run_all(brief, slow_out, search_path=slow_dir, timeout=0.2, cwd=slow_dir)
expect("timeout exits 1", code, 1)
expect("timeout is not an approve", open(os.path.join(slow_out, "codex.md")).read().strip(), "Parse: timeout")
expect("timeout stderr is kept", "timed out after 0.2s" in open(os.path.join(slow_out, "codex.err")).read(), True)

bad = tempfile.mkdtemp()
bad_bin = os.path.join(bad, "codex")
open(bad_bin, "w").write("""#!/usr/bin/env python3
import sys
sys.stdout.write("# Attack review: t\\n\\nVerdict: approve\\n\\n## Tried\\n- Input: x\\n  Observed: ok\\n  Broke: no\\n\\n## Findings\\n\\n## Held\\n- Input: x\\n  Observed: ok\\n")
sys.exit(7)
""")
os.chmod(bad_bin, os.stat(bad_bin).st_mode | stat.S_IEXEC)
bad_out = tempfile.mkdtemp()
expect("non-zero exit is an error", run_all(brief, bad_out, search_path=bad) != 0, True)
expect("non-zero exit is not an approve", open(os.path.join(bad_out, "codex.md")).read().strip(), "Parse: error")

raw = tempfile.mkdtemp()
raw_bin = os.path.join(raw, "claude")
open(raw_bin, "w").write("""#!/usr/bin/env python3
import sys
sys.stdout.buffer.write(b"note \\xff\\n")
""")
os.chmod(raw_bin, os.stat(raw_bin).st_mode | stat.S_IEXEC)
raw_out = tempfile.mkdtemp()
expect("non-utf8 does not crash", run_all(brief, raw_out, search_path=raw), 0)
expect("non-utf8 is replaced", "\ufffd" in open(os.path.join(raw_out, "claude.md"), encoding="utf-8").read(), True)

wide = os.path.join(tempfile.mkdtemp(), "brief.md")
open(wide, "wb").write(b"A" * 200000)
wide_out = tempfile.mkdtemp()
run_all(wide, wide_out, search_path=both)
wide_text = open(os.path.join(wide_out, "claude.md")).read()
expect("long brief arrives on stdin", wide_text.endswith("A" * 200000), True)
expect("long brief stays off argv", "AAAA" not in wide_text.split("brief=")[0], True)

stale = tempfile.mkdtemp()
open(os.path.join(stale, "claude.md"), "w").write("STALE\n")
run_all(brief, stale, search_path=slow_dir and bindir("codex"))
expect("a stale pass is cleared", os.path.exists(os.path.join(stale, "claude.md")), False)

flags = tempfile.mkdtemp()
expect("timeout 0.5 does not crash",
       agent_main(["attack_agents.py", "--run", "--brief", brief, "--out", flags, "--timeout", "0.5"]), 0)
expect("repeated --out is an error",
       agent_main(["attack_agents.py", "--run", "--brief", brief, "--out", flags, "--out", flags]), 2)
expect("a bad timeout is an error",
       agent_main(["attack_agents.py", "--run", "--brief", brief, "--out", flags, "--timeout", "nope"]), 2)

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    total = 29
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
