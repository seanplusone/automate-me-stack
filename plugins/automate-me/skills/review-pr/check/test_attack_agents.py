"""Run: python3 check/test_attack_agents.py"""
import os
import stat
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attack_agents import command, detect, run_all, stamp  # noqa: E402

FAILS = []
STUB = """#!/usr/bin/env python3
import os, sys
sys.stdout.write("agent=" + os.path.basename(sys.argv[0]) + "\\n")
sys.stdout.write("args=" + " ".join(sys.argv[1:-1]) + "\\n")
sys.stdout.write("brief=" + sys.argv[-1])
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
expect("codex argv", command(codex_bin, "codex", "BRIEF")[1:],
       ["exec", "--skip-git-repo-check", "--sandbox", "workspace-write", "BRIEF"])
claude_bin = found[1][1]
expect("claude argv", command(claude_bin, "claude", "BRIEF")[1:],
       ["-p", "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "BRIEF"])

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
expect("claude was print mode", "args=-p" in claude_out, True)

only = bindir("claude")
expect("claude alone", [name for name, _binary in detect(only)], ["claude"])
expect("stamp adds the agent", "passes: claude" in stamp("### F1 | head/cap.py:3\nbroke\n", "claude"), True)
expect("stamp does not repeat the agent",
       stamp("### F1 | cap.py:3 | passes: claude\n", "claude").count("claude"), 1)

slow_dir = tempfile.mkdtemp()
slow = os.path.join(slow_dir, "codex")
open(slow, "w").write("#!/bin/sh\nsleep 5\n")
os.chmod(slow, os.stat(slow).st_mode | stat.S_IEXEC)
slow_out = tempfile.mkdtemp()
code = run_all(brief, slow_out, search_path=slow_dir, timeout=0.2, cwd=slow_dir)
expect("timeout exits 1", code, 1)
expect("timeout is not an approve", open(os.path.join(slow_out, "codex.md")).read().strip(), "Parse: timeout")
expect("timeout stderr is kept", "timed out after 0.2s" in open(os.path.join(slow_out, "codex.err")).read(), True)

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    total = 16
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
