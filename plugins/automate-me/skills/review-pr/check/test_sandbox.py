"""Run: python3 check/test_sandbox.py

Practice-case agents must not see the case key. bwrap is the reference
sandbox. When it is missing, the live probe prints SKIP.
"""
import os
import shutil
import stat
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attack_agents import bwrap_command, cleanup_stale, command, key_reachable, practice_roots, resolve_sandbox, run_all  # noqa: E402

FAILS = []
CHECKS = []


def expect(name, got, want):
    CHECKS.append(name)
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


def practice():
    root = tempfile.mkdtemp()
    case = os.path.join(root, "cases", "item-cap")
    head = os.path.join(case, "head")
    os.makedirs(head)
    key = os.path.join(case, "key.md")
    open(key, "w").write("Planted: yes\nSECRET-KEY-LINE\n")
    open(os.path.join(head, "cap.py"), "w").write("visible\n")
    os.symlink(key, os.path.join(head, "sneak"))
    return root, head, key


brief = os.path.join(tempfile.mkdtemp(), "brief.md")
open(brief, "w").write("attack this diff\n")
root, head, key = practice()
stubs = tempfile.mkdtemp()
open(os.path.join(stubs, "codex"), "w").write("#!/usr/bin/python3\nprint('ran')\n")
os.chmod(os.path.join(stubs, "codex"), 0o755)
expect("sandbox none warns and runs", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=head, sandbox="none",
), 0)
expect("docker is not a practice sandbox", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=head, sandbox="docker",
), 2)
expect("a bad sandbox name is usage", resolve_sandbox("nope"), "bad")

work = tempfile.mkdtemp()
argv, feed_fds = bwrap_command(
    ["/tmp/stub-codex", "exec", "--sandbox", "danger-full-access"],
    "/tmp/stub-codex", work, [root, head],
)
for fd in feed_fds:
    os.close(fd)
text = " ".join(argv)
expect("bwrap unshares", "--unshare-all" in argv, True)
expect("bwrap dies with the parent", "--die-with-parent" in argv, True)
expect("bwrap keeps the network", "--share-net" in argv, True)
expect("bwrap clears the environment", "--clearenv" in argv, True)
expect("the work dir is /work", "--chdir" in argv and "/work" in argv, True)
expect("tmp is a fresh disk", argv.count("--tmpfs") >= 2 and "/tmp" in argv, True)
expect("home is a fresh tmpfs", "/home/agent" in argv and "--file" in argv or "/home/agent" in argv, True)
expect("login files are fds", "--file" in argv or not feed_fds, True)
expect("the case key is not a mount", key not in text and "key.md" not in text, True)
expect("host state is not mounted", os.path.expanduser("~/.codex") not in text, True)
expect("host claude dir is not mounted", os.path.expanduser("~/.claude") not in text, True)
expect("pwd inside is /work", "PWD" in argv and "/work" in argv, True)
expect("codex drops its inner sandbox", command("/usr/bin/codex", "codex", True)[4], "danger-full-access")
expect("claude keeps its permission mode", "acceptEdits" in command("/usr/bin/claude", "claude", True), True)
cases_dir = os.path.join(root, "cases")
expect("cases/ is a practice run", bool(practice_roots(cases_dir)), True)
expect("a parent of the case is a practice run", bool(practice_roots(root)), True)
expect("cases/ is reachable without a sandbox", key_reachable(cases_dir), True)
outside = tempfile.mkdtemp()
os.makedirs(os.path.join(outside, "mycase", "head"))
open(os.path.join(outside, "mycase", "key.md"), "w").write("Planted: yes\n")
expect("a case outside cases/ is reachable", key_reachable(os.path.join(outside, "mycase", "head")), True)
hidden = tempfile.mkdtemp()
os.makedirs(os.path.join(hidden, ".secret"))
open(os.path.join(hidden, ".secret", "key.md"), "w").write("Planted: yes\n")
expect("a dot-folder key is reachable", key_reachable(hidden), True)
linked = tempfile.mkdtemp()
os.symlink(cases_dir, os.path.join(linked, "jump"))
expect("a symlink to cases is reachable", key_reachable(linked), True)
stale = tempfile.mkdtemp(prefix="attack-cwd-")
fresh = tempfile.mkdtemp(prefix="attack-cwd-")
os.utime(stale, (time.time() - 7200, time.time() - 7200))
cleanup_stale()
expect("a stale copy is removed", os.path.isdir(stale), False)
expect("a fresh copy stays", os.path.isdir(fresh), True)
shutil.rmtree(fresh, ignore_errors=True)

if shutil.which("bwrap") is None:
    print("SKIP bwrap is not installed")
    expect("auto refuses a practice case without bwrap", run_all(
        brief, tempfile.mkdtemp(), search_path=stubs, cwd=head, sandbox="auto",
    ), 2)
else:
    stub_dir = tempfile.mkdtemp()
    stub = os.path.join(stub_dir, "codex")
    open(stub, "w").write(
        "#!/usr/bin/python3\n"
        "import os, subprocess\n"
        "key = %r\n"
        "repo = %r\n"
        "def try_read(path):\n"
        "    try:\n"
        "        open(path).read()\n"
        "        return 'ok'\n"
        "    except OSError:\n"
        "        return 'fail'\n"
        "print('ABS:' + try_read(key))\n"
        "print('REPO:' + try_read(repo))\n"
        "try:\n"
        "    print('LSREPO:' + ','.join(os.listdir(repo)))\n"
        "except OSError:\n"
        "    print('LSREPO:fail')\n"
        "print('OLDPWD:' + os.environ.get('OLDPWD', 'missing'))\n"
        "print('DOT:' + ','.join(sorted(os.listdir('/work/..'))))\n"
        "try:\n"
        "    found = subprocess.check_output(['find', '/', '-name', 'key.md'], stderr=subprocess.DEVNULL, text=True, timeout=60)\n"
        "except Exception:\n"
        "    found = ''\n"
        "print('FIND:' + found.replace(chr(10), ','))\n"
        "print('READ:' + try_read('/work/head/cap.py'))\n"
        "try:\n"
        "    open('/work/head/wrote.txt', 'w').write('yes')\n"
        "    print('WRITE:ok')\n"
        "except OSError:\n"
        "    print('WRITE:fail')\n" % (key, root)
    )
    os.chmod(stub, os.stat(stub).st_mode | stat.S_IEXEC)
    out = tempfile.mkdtemp()
    code = run_all(brief, out, search_path=stub_dir, cwd=head, sandbox="auto")
    body = open(os.path.join(out, "codex.md")).read() if os.path.isfile(os.path.join(out, "codex.md")) else ""
    expect("bwrap run exits 0", code, 0)
    expect("absolute key is hidden", "ABS:fail" in body, True)
    expect("repo root is hidden", "REPO:fail" in body and "LSREPO:fail" in body, True)
    expect("OLDPWD is unset", "OLDPWD:missing" in body, True)
    expect("find does not see the key", key not in body.split("FIND:", 1)[-1], True)
    expect("parent of work is not the repo", os.path.basename(root) not in body.split("DOT:", 1)[-1].split("\n", 1)[0], True)
    expect("head is readable", "READ:ok" in body, True)
    expect("work is writable", "WRITE:ok" in body, True)
    expect("the secret is not in the output", "SECRET-KEY-LINE" not in body, True)
    tool = os.path.join(tempfile.mkdtemp(), "codex")
    open(tool, "w").write(
        "#!/bin/sh\n"
        "for t in awk sed grep find python3 git; do\n"
        "  if command -v \"$t\" >/dev/null 2>&1; then echo OK:$t; else echo MISSING:$t; fi\n"
        "done\n"
    )
    os.chmod(tool, 0o755)
    tool_out = tempfile.mkdtemp()
    tool_code = run_all(brief, tool_out, search_path=os.path.dirname(tool), cwd=head, sandbox="bwrap")
    tool_body = open(os.path.join(tool_out, "codex.md")).read() if os.path.isfile(os.path.join(tool_out, "codex.md")) else ""
    expect("common tools resolve", tool_code == 0 and "MISSING:" not in tool_body and "OK:awk" in tool_body, True)
    rel_parent = tempfile.mkdtemp()
    rel_case = os.path.join(rel_parent, "mycase")
    os.makedirs(os.path.join(rel_case, "head"))
    open(os.path.join(rel_case, "key.md"), "w").write("Planted: yes\n")
    open(os.path.join(rel_case, "head", "cap.py"), "w").write("x\n")
    rel_stub = os.path.join(tempfile.mkdtemp(), "codex")
    open(rel_stub, "w").write("#!/bin/sh\necho REL:$(pwd)\n")
    os.chmod(rel_stub, 0o755)
    here = os.getcwd()
    os.chdir(rel_parent)
    try:
        rel_code = run_all(brief, tempfile.mkdtemp(), search_path=os.path.dirname(rel_stub), cwd="mycase/head", sandbox="bwrap")
    finally:
        os.chdir(here)
    expect("a relative cwd is accepted", rel_code, 0)
    pkg = tempfile.mkdtemp()
    helper = os.path.join(pkg, "codex-code-mode-host")
    open(helper, "w").write("#!/bin/sh\n")
    os.chmod(helper, 0o755)
    linked_bin = os.path.join(tempfile.mkdtemp(), "codex")
    os.symlink(os.path.join(pkg, "codex"), linked_bin)
    open(os.path.join(pkg, "codex"), "w").write(
        "#!/bin/sh\n"
        "helper=\"$(dirname \"$0\")/codex-code-mode-host\"\n"
        "if [ -x \"$helper\" ]; then echo HELPER:ok; else echo HELPER:missing; fi\n"
    )
    os.chmod(os.path.join(pkg, "codex"), 0o755)
    helper_out = tempfile.mkdtemp()
    helper_code = run_all(brief, helper_out, search_path=os.path.dirname(linked_bin), cwd=head, sandbox="bwrap")
    helper_body = open(os.path.join(helper_out, "codex.md")).read() if os.path.isfile(os.path.join(helper_out, "codex.md")) else ""
    expect("a sibling helper is visible", helper_code == 0 and "HELPER:ok" in helper_body, True)
    escape = tempfile.mkdtemp()
    escape_head = os.path.join(escape, "mycase", "head")
    os.makedirs(escape_head)
    open(os.path.join(escape, "mycase", "key.md"), "w").write("SECRET-KEY-LINE\n")
    escape_stub = os.path.join(tempfile.mkdtemp(), "codex")
    open(escape_stub, "w").write(
        "#!/bin/sh\n"
        "if [ -f ../key.md ]; then echo PARENT:yes; else echo PARENT:no; fi\n"
    )
    os.chmod(escape_stub, 0o755)
    escape_out = tempfile.mkdtemp()
    escape_code = run_all(
        brief, escape_out, search_path=os.path.dirname(escape_stub), cwd=escape_head, sandbox="auto",
    )
    escape_body = open(os.path.join(escape_out, "codex.md")).read() if os.path.isfile(os.path.join(escape_out, "codex.md")) else ""
    expect("a case outside cases/ is sandboxed", escape_code == 0 and "PARENT:no" in escape_body, True)

    fake = tempfile.mkdtemp()
    os.makedirs(os.path.join(fake, ".codex", "sessions"))
    os.makedirs(os.path.join(fake, ".claude", "projects", "repo"))
    open(os.path.join(fake, ".codex", "auth.json"), "w").write('{"token": "AUTH-MARKER"}\n')
    open(os.path.join(fake, ".codex", "config.toml"), "w").write(
        'model = "gpt"\n[projects."/secret/host-project"]\ntrust_level = "trusted"\n'
    )
    open(os.path.join(fake, ".codex", "sessions", "old.txt"), "w").write("CANARY-TRANSCRIPT\n")
    open(os.path.join(fake, ".claude", ".credentials.json"), "w").write('{"claudeAiOauth": {"accessToken": "AUTH-MARKER"}}\n')
    open(os.path.join(fake, ".claude", "projects", "repo", "session.jsonl"), "w").write("CANARY-TRANSCRIPT\n")
    open(os.path.join(fake, ".claude.json"), "w").write(
        '{"hasCompletedOnboarding": true, "projects": {"/repo": {"history": "CANARY-TRANSCRIPT"}}}\n'
    )
    canary = os.path.join(tempfile.mkdtemp(), "codex")
    open(canary, "w").write(
        "#!/usr/bin/python3\n"
        "import os\n"
        "skip = {'proc', 'sys', 'dev'}\n"
        "leaks = []\n"
        "for dirpath, dirnames, filenames in os.walk('/'):\n"
        "    dirnames[:] = [name for name in dirnames if name not in skip]\n"
        "    for name in filenames:\n"
        "        path = os.path.join(dirpath, name)\n"
        "        try:\n"
        "            if os.path.getsize(path) > 1000000:\n"
        "                continue\n"
        "            text = open(path, errors='replace').read(1000000)\n"
        "        except OSError:\n"
        "            continue\n"
        "        if ('CANARY-' + 'TRANSCRIPT') in text:\n"
        "            leaks.append(path)\n"
        "print('LEAKS:' + ','.join(leaks))\n"
        "try:\n"
        "    print('AUTH:' + open('/home/agent/.codex/auth.json').read())\n"
        "except OSError:\n"
        "    print('AUTH:missing')\n"
        "try:\n"
        "    print('CONFIG:' + open('/home/agent/.codex/config.toml').read())\n"
        "except OSError:\n"
        "    print('CONFIG:missing')\n"
        "try:\n"
        "    print('ONBOARD:' + open('/home/agent/.claude/.claude.json').read())\n"
        "except OSError:\n"
        "    print('ONBOARD:missing')\n"
        "try:\n"
        "    open('/tmp/probe.txt', 'w').write('ok')\n"
        "    print('TMP:ok')\n"
        "except OSError:\n"
        "    print('TMP:fail')\n"
    )
    os.chmod(canary, 0o755)
    canary_dir = os.path.dirname(canary)
    saved = {name: os.environ.get(name) for name in ("HOME", "CODEX_HOME", "CLAUDE_CONFIG_DIR")}
    os.environ["HOME"] = fake
    os.environ.pop("CODEX_HOME", None)
    os.environ.pop("CLAUDE_CONFIG_DIR", None)
    canary_out = tempfile.mkdtemp()
    try:
        code = run_all(brief, canary_out, search_path=canary_dir, cwd=head, sandbox="bwrap")
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    seen = open(os.path.join(canary_out, "codex.md")).read() if os.path.isfile(os.path.join(canary_out, "codex.md")) else ""
    expect("canary run exits 0", code, 0)
    leak = ""
    for line in seen.splitlines():
        if line.startswith("LEAKS:"):
            leak = line[len("LEAKS:"):]
    expect("transcripts are not visible", leak, "")
    expect("the canary string is absent", "CANARY-TRANSCRIPT" not in seen, True)
    expect("the login file is present", "AUTH-MARKER" in seen, True)
    expect("config keeps the model and drops host projects", "model" in seen and "/secret/host-project" not in seen, True)
    expect("onboarding stays and history does not", "hasCompletedOnboarding" in seen and "CANARY-TRANSCRIPT" not in seen, True)
    expect("tmp is writable", "TMP:ok" in seen, True)

if os.environ.get("AMS_REAL_CLI") != "1":
    print("SKIP real CLI smoke (set AMS_REAL_CLI=1)")
elif shutil.which("bwrap") is None:
    print("SKIP bwrap is not installed")
else:
    smoke_brief = os.path.join(tempfile.mkdtemp(), "brief.md")
    open(smoke_brief, "w").write(
        "Write the word pong into /tmp/pong.txt. Reply with the single word pong.\n"
    )
    for cli in ("codex", "claude"):
        if shutil.which(cli) is None:
            print("SKIP %s is not installed" % cli)
            continue
        smoke_dir = tempfile.mkdtemp()
        host_tmp = tempfile.mkdtemp()
        smoke_out = tempfile.mkdtemp()
        code = run_all(
            smoke_brief, smoke_out, cwd=smoke_dir, sandbox="bwrap", timeout=180, host_tmp=host_tmp,
        )
        path = os.path.join(smoke_out, cli + ".md")
        text = open(path).read() if os.path.isfile(path) else ""
        lowered = text.lower()
        pong_path = os.path.join(host_tmp, "pong.txt")
        pong = open(pong_path).read() if os.path.isfile(pong_path) else ""
        expect(
            "%s logs in and writes /tmp/pong.txt" % cli,
            code == 0 and "pong" in lowered and "not logged in" not in lowered and "401" not in text and "pong" in pong,
            True,
        )

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
