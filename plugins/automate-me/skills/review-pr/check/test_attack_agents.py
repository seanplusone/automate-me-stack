"""Run: python3 check/test_attack_agents.py"""
import os
import signal
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attack_agents import command, contract_bytes, detect, main as agent_main, run_all  # noqa: E402

FAILS = []
CHECKS = []
STUB = """#!/usr/bin/python3
import os, sys
sys.stdout.write("agent=" + os.path.basename(sys.argv[0]) + "\\n")
sys.stdout.write("args=" + " ".join(sys.argv[1:]) + "\\n")
sys.stdout.write("brief=" + sys.stdin.read())
"""


def expect(name, got, want):
    CHECKS.append(name)
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
expect("codex saw the brief", "attack this diff" in codex_out.split("brief=", 1)[1], True)
expect("codex was exec", "args=exec --skip-git-repo-check" in codex_out, True)
expect("claude saw the brief", "attack this diff" in claude_out.split("brief=", 1)[1], True)
expect("claude was print mode", "args=-p --permission-mode acceptEdits --allowedTools Bash" in claude_out, True)
expect("prompt is not an argument", "attack this diff" not in claude_out.split("brief=")[0], True)

only = bindir("claude")
expect("claude alone", [name for name, _binary in detect(only)], ["claude"])
plain = tempfile.mkdtemp()
plain_bin = os.path.join(plain, "codex")
open(plain_bin, "w").write("#!/usr/bin/python3\nimport sys\nsys.stdout.write('## Findings (all in cap.py:3)\\n')\n")
os.chmod(plain_bin, os.stat(plain_bin).st_mode | stat.S_IEXEC)
plain_out = tempfile.mkdtemp()
run_all(brief, plain_out, search_path=plain)
expect("stdout is stored unchanged", open(os.path.join(plain_out, "codex.md")).read(), "## Findings (all in cap.py:3)\n")

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
open(bad_bin, "w").write("""#!/usr/bin/python3
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
open(raw_bin, "w").write("""#!/usr/bin/python3
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
expect("the contract is in the brief", "## Attack file" in wide_text, True)

kept = tempfile.mkdtemp()
for name in ("attack.md", "key.md"):
    open(os.path.join(kept, name), "w").write("KEEP\n")
open(os.path.join(kept, "notes.err"), "w").write("KEEP\n")
open(os.path.join(kept, "codex.md"), "w").write("STALE\n")
run_all(brief, kept, search_path=both)
expect("attack.md stays", open(os.path.join(kept, "attack.md")).read(), "KEEP\n")
expect("key.md stays", open(os.path.join(kept, "key.md")).read(), "KEEP\n")
expect("another err stays", open(os.path.join(kept, "notes.err")).read(), "KEEP\n")
expect("the owned pass is replaced", "STALE" not in open(os.path.join(kept, "codex.md")).read(), True)

quiet = tempfile.mkdtemp()
open(os.path.join(quiet, "codex.md"), "w").write("STALE\n")
open(os.path.join(quiet, "attack.md"), "w").write("KEEP\n")
expect("no cli still returns 0", run_all(brief, quiet, search_path=tempfile.mkdtemp()), 0)
expect("a stale pass is cleared with no cli", os.path.exists(os.path.join(quiet, "codex.md")), False)
expect("attack.md stays with no cli", open(os.path.join(quiet, "attack.md")).read(), "KEEP\n")

marker = os.path.join(tempfile.mkdtemp(), "late.txt")
group = tempfile.mkdtemp()
open(os.path.join(group, "codex"), "w").write(
    "#!/usr/bin/python3\nimport os, time\npath = %r\n"
    "if os.fork() == 0:\n    time.sleep(1.5)\n    open(path, 'w').write('late')\n    os._exit(0)\n"
    "time.sleep(30)\n" % marker
)
os.chmod(os.path.join(group, "codex"), os.stat(os.path.join(group, "codex")).st_mode | stat.S_IEXEC)
group_out = tempfile.mkdtemp()
expect("a timeout kills the group", run_all(brief, group_out, search_path=group, timeout=0.3), 1)
time.sleep(2)
expect("a child does not write after the timeout", os.path.exists(marker), False)
expect("the contract does not name the key", b"key.md" not in contract_bytes(), True)

owned = tempfile.mkdtemp()
owned_brief = os.path.join(owned, "codex.md")
open(owned_brief, "w").write("KEEP THE BRIEF\n")
expect("a brief that is a pass is refused", run_all(owned_brief, owned, search_path=both), 2)
expect("the brief was not deleted", open(owned_brief).read(), "KEEP THE BRIEF\n")

root = tempfile.mkdtemp()
head = os.path.join(root, "cases", "item-cap", "head")
os.makedirs(head)
open(os.path.join(root, "cases", "item-cap", "key.md"), "w").write("Planted: yes\nSECRET-KEY-LINE\n")
open(os.path.join(head, "cap.py"), "w").write("x = 1\n")
os.symlink(os.path.join(root, "cases", "item-cap", "key.md"), os.path.join(head, "sneak"))
walker = tempfile.mkdtemp()
open(os.path.join(walker, "codex"), "w").write(
    "#!/usr/bin/python3\nimport os\n"
    "print('PWD=' + os.environ.get('PWD', ''))\n"
    "print('OLDPWD=' + os.environ.get('OLDPWD', 'missing'))\n"
    "print('cwd=' + os.getcwd())\n"
    "for dirpath, dirs, files in os.walk('.'):\n"
    "    for name in files:\n"
    "        path = os.path.join(dirpath, name)\n"
    "        print(path)\n"
    "        try:\n"
    "            print(open(path).read())\n"
    "        except OSError:\n"
    "            print('unreadable')\n"
)
os.chmod(os.path.join(walker, "codex"), os.stat(os.path.join(walker, "codex")).st_mode | stat.S_IEXEC)
walk_out = tempfile.mkdtemp()
os.environ["REPO_PATH"] = head
try:
    run_all(brief, walk_out, search_path=walker, cwd=head)
finally:
    os.environ.pop("REPO_PATH", None)
walked = open(os.path.join(walk_out, "codex.md")).read()
expect("the copy has the code", "cap.py" in walked, True)
expect("the copy has no key", "key.md" not in walked and "SECRET-KEY-LINE" not in walked and "sneak" not in walked, True)
expect("OLDPWD is not leaked", "OLDPWD=missing" in walked, True)
expect("PWD is the agent cwd", "PWD=" in walked and head not in walked.split("PWD=", 1)[1].split("\n", 1)[0], True)
agent_dir = walked.split("cwd=", 1)[1].split("\n", 1)[0]
expect("the copy is removed", os.path.isdir(agent_dir), False)

script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attack_agents.py")
for stop in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT):
    late = os.path.join(tempfile.mkdtemp(), "late.txt")
    sleeper = tempfile.mkdtemp()
    open(os.path.join(sleeper, "codex"), "w").write(
        "#!/usr/bin/python3\nimport os, time\npath = %r\ntime.sleep(3)\nopen(path, 'w').write('late')\n" % late
    )
    os.chmod(os.path.join(sleeper, "codex"), 0o755)
    env = os.environ.copy()
    env["PATH"] = sleeper
    proc = subprocess.Popen(
        [sys.executable, script, "--run", "--brief", brief, "--out", tempfile.mkdtemp(), "--timeout", "30"],
        env=env, cwd=tempfile.mkdtemp(),
    )
    time.sleep(0.4)
    proc.send_signal(stop)
    proc.wait(timeout=5)
    time.sleep(3.2)
    expect("signal %s kills the agent" % stop.name, os.path.exists(late), False)

late = os.path.join(tempfile.mkdtemp(), "late.txt")
sleeper = tempfile.mkdtemp()
open(os.path.join(sleeper, "codex"), "w").write(
    "#!/usr/bin/python3\nimport time\npath = %r\ntime.sleep(3)\nopen(path, 'w').write('late')\n" % late
)
os.chmod(os.path.join(sleeper, "codex"), 0o755)
env = os.environ.copy()
env["PATH"] = sleeper
proc = subprocess.Popen(
    [sys.executable, script, "--run", "--brief", brief, "--out", tempfile.mkdtemp(), "--timeout", "30"],
    env=env, cwd=tempfile.mkdtemp(), start_new_session=True,
)
time.sleep(0.4)
os.killpg(proc.pid, signal.SIGKILL)
proc.wait(timeout=5)
time.sleep(3.2)
expect("killing the runner group kills the agent", os.path.exists(late), False)

stale = tempfile.mkdtemp()
open(os.path.join(stale, "claude.md"), "w").write("STALE\n")
run_all(brief, stale, search_path=slow_dir and bindir("codex"))
expect("a stale pass is cleared", os.path.exists(os.path.join(stale, "claude.md")), False)

flags = tempfile.mkdtemp()
isolated = tempfile.mkdtemp()
saved = os.environ.get("PATH")
os.environ["PATH"] = isolated
try:
    expect("timeout 0.5 does not crash",
           agent_main(["attack_agents.py", "--run", "--brief", brief, "--out", flags, "--timeout", "0.5"]), 0)
    expect("repeated --out is an error",
           agent_main(["attack_agents.py", "--run", "--brief", brief, "--out", flags, "--out", flags]), 2)
    expect("a bad timeout is an error",
           agent_main(["attack_agents.py", "--run", "--brief", brief, "--out", flags, "--timeout", "nope"]), 2)
    os.environ["PATH"] = both
    stub_out = tempfile.mkdtemp()
    expect("main uses PATH stubs", agent_main(
        ["attack_agents.py", "--run", "--brief", brief, "--out", stub_out]), 0)
    expect("the stub ran, not another binary",
           "agent=codex" in open(os.path.join(stub_out, "codex.md")).read(), True)
finally:
    if saved is None:
        os.environ.pop("PATH", None)
    else:
        os.environ["PATH"] = saved

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
