"""Run: python3 check/test_sandbox.py

Practice-case agents must not see the case key. bwrap is the reference
sandbox. When it is missing, the live probe prints SKIP.
"""
import os
import shutil
import stat
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attack_agents import bwrap_command, resolve_sandbox, run_all  # noqa: E402

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
expect("sandbox none is refused", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=head, sandbox="none",
), 2)
expect("docker is not a practice sandbox", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=head, sandbox="docker",
), 2)
expect("a bad sandbox name is usage", resolve_sandbox("nope"), "bad")

work = tempfile.mkdtemp()
argv = bwrap_command(["/tmp/stub-codex", "exec"], "/tmp/stub-codex", "codex", work, [root, head])
text = " ".join(argv)
expect("bwrap unshares", "--unshare-all" in argv, True)
expect("bwrap dies with the parent", "--die-with-parent" in argv, True)
expect("bwrap keeps the network", "--share-net" in argv, True)
expect("bwrap clears the environment", "--clearenv" in argv, True)
expect("the work dir is /work", "--chdir" in argv and "/work" in argv, True)
expect("the case key is not a mount", key not in text and "key.md" not in text, True)
expect("pwd inside is /work", "--setenv" in argv and "PWD" in argv and "/work" in argv, True)

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

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
