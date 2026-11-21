"""Run: python3 check/test_sandbox.py

Practice-case agents must not see the case key. bwrap is the reference
sandbox. When it is missing, the live probe prints SKIP.
"""
import datetime
import io
import os
import shutil
import stat
import sys
import tempfile
import time
import tomllib
from contextlib import redirect_stderr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from attack_agents import _minimal_codex_config, _remove_tree, agent_cwd, bwrap_command, cleanup_stale, command, key_reachable, practice_roots, resolve_sandbox, run_all  # noqa: E402

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
expect("sandbox none refuses a practice case", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=head, sandbox="none",
), 2)
plain = tempfile.mkdtemp()
expect("sandbox none runs when no key is reachable", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=plain, sandbox="none",
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
pairs = list(zip(argv, argv[1:]))
file_fds = [nxt for flag, nxt in pairs if flag == "--file"]
expect("home is a fresh tmpfs", ("--tmpfs", "/home") in pairs, True)
expect("login files are fds", len(file_fds) == len(feed_fds) and all(item.isdigit() for item in file_fds), True)
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
for label, parts in (
    ("a dot-folder key is refused", (".cases", "item-cap")),
    ("a git key is refused", (".git", "x")),
    ("a modules key is refused", ("node_modules", "pkg")),
):
    tree = tempfile.mkdtemp()
    folder = tree
    for part in parts:
        folder = os.path.join(folder, part)
    os.makedirs(folder)
    open(os.path.join(folder, "key.md"), "w").write("Planted: yes\n")
    expect(label, run_all(
        brief, tempfile.mkdtemp(), search_path=stubs, cwd=tree, sandbox="bwrap",
    ), 2)
    expect(label + " with sandbox none", run_all(
        brief, tempfile.mkdtemp(), search_path=stubs, cwd=tree, sandbox="none",
    ), 2)
stale = tempfile.mkdtemp(prefix="attack-cwd-")
fresh = tempfile.mkdtemp(prefix="attack-cwd-")
empty = tempfile.mkdtemp(prefix="attack-cwd-")
open(os.path.join(stale, "head.txt"), "w").write("x\n")
open(os.path.join(fresh, "head.txt"), "w").write("x\n")
os.utime(stale, (time.time() - 7200, time.time() - 7200))
cleanup_stale()
expect("a stale copy is removed", os.path.isdir(stale), False)
expect("a fresh copy stays", os.path.isdir(fresh), True)
expect("an empty work copy is removed", os.path.isdir(empty), False)
dead_pid = None
for candidate in range(1 << 22, (1 << 22) + 50):
    try:
        os.kill(candidate, 0)
    except OSError:
        dead_pid = candidate
        break
dead = tempfile.mkdtemp(prefix="attack-cwd-%s-" % dead_pid)
open(os.path.join(dead, "head.txt"), "w").write("x\n")
cleanup_stale()
expect("a dead run's work copy is removed", os.path.isdir(dead), False)
live = tempfile.mkdtemp(prefix="attack-cwd-%s-" % os.getpid())
open(os.path.join(live, "head.txt"), "w").write("x\n")
os.utime(live, (time.time() - 7200, time.time() - 7200))
cleanup_stale()
expect("a live run's old work copy stays", os.path.isdir(live), True)
shutil.rmtree(live, ignore_errors=True)
home = os.path.expanduser("~")
repo = tempfile.mkdtemp()
sample = "\n".join([
    'model_reasoning_effort = "high"',
    'openai_base_url = "https://example.test/v1"',
    'cli_auth_credentials_store = "file"',
    '"" = 1',
    '"modèle" = "oui"',
    "when = 1979-05-27T07:32:00Z",
    "day = 1979-05-27",
    'cwd = "/"',
    'model_providers.openai.name = "OpenAI"',
    'model_providers.openai.base_url = "https://example.test/v1"',
    'model_providers.openai.wire_api = "responses"',
    'model_providers.openai.extra = "kept"',
    "note = '''",
    "alpha",
    "beta \"quote\" and \\slash",
    "'''",
    'sandbox_cwd = "%s"' % os.path.join(repo, "proj"),
    "",
    "[profiles.work]",
    'model = "gpt"',
    "",
    "[[tools]]",
    'name = "local"',
    'path = "%s"' % os.path.join(home, "tool"),
    'note = "keep"',
    "",
    '[projects."/secret/host-project"]',
    'trust_level = "trusted"',
    "",
    "[hooks]",
    'run = "%s"' % os.path.join(home, "hook.sh"),
    "",
    'notify = ["/usr/bin/notify-send"]',
    "",
    "[history]",
    'persistence = "none"',
    'path = "%s"' % os.path.join(home, ".codex", "history.jsonl"),
    "",
    "[mcp_servers.local]",
    'command = "/usr/bin/local-mcp"',
    "",
    "[plugins]",
    'path = "%s"' % os.path.join(home, "plugins"),
])
written = _minimal_codex_config(sample, [repo])
parsed = tomllib.loads(written.decode())
expected = {
    "model_reasoning_effort": "high",
    "openai_base_url": "https://example.test/v1",
    "cli_auth_credentials_store": "file",
    "": 1,
    "modèle": "oui",
    "when": datetime.datetime(1979, 5, 27, 7, 32, tzinfo=datetime.timezone.utc),
    "day": datetime.date(1979, 5, 27),
    "cwd": "/",
    "model_providers": {
        "openai": {
            "name": "OpenAI",
            "base_url": "https://example.test/v1",
            "wire_api": "responses",
            "extra": "kept",
        },
    },
    "note": "alpha\nbeta \"quote\" and \\slash\n",
    "profiles": {"work": {"model": "gpt"}},
    "tools": [{"name": "local", "note": "keep"}],
    "history": {"persistence": "none"},
}
expect("config round trip matches the kept settings", parsed, expected)
controls = "\n".join([
    r'"\u0000key" = "a\u0000b\u001fc\u007fd"',
    r'cr = "a\rb"',
    r'quotes = "\"\"\""',
])
control_original = tomllib.loads(controls)
control_written = _minimal_codex_config(controls)
control_text = control_written.decode()
control_parsed = tomllib.loads(control_text)
expect("control characters round trip", control_parsed, control_original)
expect(
    "control characters are escaped",
    "\r" not in control_text and "\x00" not in control_text and "\x1f" not in control_text and "\x7f" not in control_text,
    True,
)
shutil.rmtree(fresh, ignore_errors=True)
shutil.rmtree(repo, ignore_errors=True)

def locked_tree(mode):
    tree = tempfile.mkdtemp()
    secret = os.path.join(tree, "secret")
    os.makedirs(secret)
    open(os.path.join(tree, "x.py"), "w").write("x\n")
    open(os.path.join(secret, "key.md"), "w").write("Planted: SECRETLINE\n")
    os.chmod(secret, mode)
    return tree, secret

peek = os.path.join(tempfile.mkdtemp(), "codex")
open(peek, "w").write(
    "#!/bin/sh\n"
    "chmod 700 /work/secret 2>/dev/null\n"
    "if [ -f /work/secret/key.md ]; then cat /work/secret/key.md; else echo NOKEY; fi\n"
)
os.chmod(peek, 0o755)
for label, mode in (("mode 0111", 0o111), ("mode 000", 0o000)):
    tree, secret = locked_tree(mode)
    try:
        expect("key_reachable sees %s" % label, key_reachable(tree), True)
        code = run_all(brief, tempfile.mkdtemp(), search_path=os.path.dirname(peek), cwd=tree, sandbox="bwrap")
        expect("%s is refused" % label, code, 2)
        expect("%s does not change the host mode" % label, os.stat(secret).st_mode & 0o777, mode)
    finally:
        os.chmod(secret, 0o755)
        shutil.rmtree(tree, ignore_errors=True)
parent = tempfile.mkdtemp()
child = os.path.join(parent, "repo", "child")
os.makedirs(child)
open(os.path.join(parent, "repo", "key.md"), "w").write("Planted: SECRETLINE\n")
open(os.path.join(child, "x.py"), "w").write("x\n")
os.chmod(os.path.join(parent, "repo"), 0o111)
try:
    expect("an unreadable parent hides a key", key_reachable(child), True)
    expect("an unreadable parent is refused", run_all(
        brief, tempfile.mkdtemp(), search_path=os.path.dirname(peek), cwd=child, sandbox="bwrap",
    ), 2)
finally:
    os.chmod(os.path.join(parent, "repo"), 0o755)
    shutil.rmtree(parent, ignore_errors=True)
link_case = os.path.join(tempfile.mkdtemp(), "cases", "item")
link_head = os.path.join(link_case, "head")
os.makedirs(link_head)
link_key = os.path.join(link_case, "key.md")
open(link_key, "w").write("Planted: SECRETLINE\n")
open(os.path.join(link_head, "cap.py"), "w").write("x\n")
os.link(link_key, os.path.join(link_head, "alias.md"))
link_work, link_made = agent_cwd(link_head)
link_names = []
if link_work:
    for dirpath, dirnames, filenames in os.walk(link_work):
        link_names.extend(filenames)
expect("a hardlinked key is not copied", "alias.md" not in link_names, True)
if link_made and link_work:
    shutil.rmtree(link_work, ignore_errors=True)
pair = tempfile.mkdtemp()
case_a = os.path.join(pair, "cases", "a")
case_b = os.path.join(pair, "cases", "b", "head")
os.makedirs(os.path.join(case_a, "head"))
os.makedirs(case_b)
open(os.path.join(case_a, "key.md"), "w").write("SECRET-A\n")
open(os.path.join(pair, "cases", "b", "key.md"), "w").write("SECRET-B\n")
open(os.path.join(case_b, "cap.py"), "w").write("x\n")
os.link(os.path.join(case_a, "key.md"), os.path.join(case_b, "notes.md"))
pair_work, pair_made = agent_cwd(os.path.join(pair, "cases"))
pair_names, pair_text = [], []
if pair_work:
    for dirpath, dirnames, filenames in os.walk(pair_work):
        pair_names.extend(filenames)
        for name in filenames:
            pair_text.append(open(os.path.join(dirpath, name), errors="replace").read())
expect("another case's key is not linked into head", pair_work is not None and "notes.md" not in pair_names, True)
expect("another case's key text is not copied", pair_text and all("SECRET-A" not in item for item in pair_text), True)
if pair_made and pair_work:
    shutil.rmtree(pair_work, ignore_errors=True)
plain_root = tempfile.mkdtemp()
os.makedirs(os.path.join(plain_root, "cases", "a"))
plain = os.path.join(plain_root, "c")
os.makedirs(plain)
open(os.path.join(plain_root, "cases", "a", "key.md"), "w").write("SECRET-OUT\n")
os.link(os.path.join(plain_root, "cases", "a", "key.md"), os.path.join(plain, "hard"))
expect("a hard link outside the cwd is still a known case key", key_reachable(plain), False)
expect("a hard link to a case key is refused", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=plain, sandbox="bwrap",
), 2)
linked_root = tempfile.mkdtemp()
os.makedirs(os.path.join(linked_root, "cases", "a"))
os.makedirs(os.path.join(linked_root, "cases", "b", "head"))
open(os.path.join(linked_root, "cases", "a", "key.md"), "w").write("SECRET-LINK\n")
open(os.path.join(linked_root, "cases", "b", "key.md"), "w").write("Planted: yes\n")
open(os.path.join(linked_root, "cases", "b", "head", "cap.py"), "w").write("x\n")
os.link(
    os.path.join(linked_root, "cases", "a", "key.md"),
    os.path.join(linked_root, "cases", "b", "head", "notes.md"),
)
elink = os.path.join(tempfile.mkdtemp(), "Elink")
os.symlink(os.path.join(linked_root, "cases", "b"), elink)
link_err = io.StringIO()
with redirect_stderr(link_err):
    elink_work, elink_made = agent_cwd(elink)
elink_names = []
if elink_work:
    for dirpath, dirnames, filenames in os.walk(elink_work):
        elink_names.extend(filenames)
expect("a symlinked cwd drops the hard link", elink_work is not None and "notes.md" not in elink_names, True)
expect("a symlinked cwd records the skipped path", "notes.md" in link_err.getvalue(), True)
if elink_made and elink_work:
    shutil.rmtree(elink_work, ignore_errors=True)
group = tempfile.mkdtemp()
os.makedirs(os.path.join(group, "cases", "g", "a"))
os.makedirs(os.path.join(group, "cases", "g", "b", "head"))
open(os.path.join(group, "cases", "g", "a", "key.md"), "w").write("SECRET-NEST\n")
open(os.path.join(group, "cases", "g", "b", "key.md"), "w").write("Planted: yes\n")
open(os.path.join(group, "cases", "g", "b", "head", "cap.py"), "w").write("x\n")
os.link(
    os.path.join(group, "cases", "g", "a", "key.md"),
    os.path.join(group, "cases", "g", "b", "head", "notes.md"),
)
group_work, group_made = agent_cwd(os.path.join(group, "cases"))
group_names, group_text = [], []
if group_work:
    for dirpath, dirnames, filenames in os.walk(group_work):
        group_names.extend(filenames)
        for name in filenames:
            group_text.append(open(os.path.join(dirpath, name), errors="replace").read())
expect(
    "a nested case group does not copy the other key",
    group_text and "notes.md" not in group_names and all("SECRET-NEST" not in item for item in group_text),
    True,
)
if group_made and group_work:
    shutil.rmtree(group_work, ignore_errors=True)
other = tempfile.mkdtemp()
os.makedirs(os.path.join(other, "cases", "other-repo", "src"))
os.makedirs(os.path.join(other, "app"))
open(os.path.join(other, "cases", "other-repo", "src", "key.md"), "w").write("SECRET-OTHER\n")
os.link(
    os.path.join(other, "cases", "other-repo", "src", "key.md"),
    os.path.join(other, "app", "hard"),
)
expect("a hard link from another repo is refused", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=os.path.join(other, "app"), sandbox="bwrap",
), 2)
nested_repo = tempfile.mkdtemp()
os.makedirs(os.path.join(nested_repo, "tests", "cases", "k"))
os.makedirs(os.path.join(nested_repo, "plain"))
open(os.path.join(nested_repo, "tests", "cases", "k", "key.md"), "w").write("SECRET-NESTED\n")
os.link(
    os.path.join(nested_repo, "tests", "cases", "k", "key.md"),
    os.path.join(nested_repo, "plain", "h"),
)
expect("a nested cases hard link in a plain cwd is refused", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=os.path.join(nested_repo, "plain"), sandbox="bwrap",
), 2)
expect("a missing cwd is refused", run_all(
    brief, tempfile.mkdtemp(), search_path=stubs, cwd=os.path.join(tempfile.mkdtemp(), "missing"), sandbox="bwrap",
), 2)
once = tempfile.mkdtemp()
once_case = os.path.join(once, "cases", "item")
once_head = os.path.join(once_case, "head")
os.makedirs(once_head)
open(os.path.join(once_case, "key.md"), "w").write("Planted: yes\n")
open(os.path.join(once_head, "cap.py"), "w").write("x\n")
open(os.path.join(once_head, "a.txt"), "w").write("same\n")
os.link(os.path.join(once_head, "a.txt"), os.path.join(once_head, "b.txt"))
once_err = io.StringIO()
with redirect_stderr(once_err):
    agent_cwd(once_head)
once_notes = [line for line in once_err.getvalue().splitlines() if "skipped hard link" in line]
expect("a hard link is noted once", len(once_notes), 1)
keep_dir = tempfile.mkdtemp()
keep_target = os.path.join(keep_dir, "target")
os.makedirs(keep_target)
open(os.path.join(keep_target, "file.txt"), "w").write("keep\n")
holder = os.path.join(keep_dir, "holder")
os.makedirs(holder)
os.symlink(keep_target, os.path.join(holder, "dirlink"))
_remove_tree(holder)
expect("a directory symlink is unlinked", os.path.exists(holder), False)
expect("the symlink target stays", os.path.isfile(os.path.join(keep_target, "file.txt")), True)
deep_root = tempfile.mkdtemp()
deep_case = os.path.join(deep_root, "cases", "item")
deep_head = os.path.join(deep_case, "head")
os.makedirs(deep_head)
open(os.path.join(deep_case, "key.md"), "w").write("Planted: yes\n")
nested = deep_head
for _ in range(1100):
    nested = os.path.join(nested, "n")
    os.mkdir(nested)
deep_err = io.StringIO()
with redirect_stderr(deep_err):
    deep_code = run_all(brief, tempfile.mkdtemp(), search_path=stubs, cwd=deep_case, sandbox="bwrap")
deep_text = deep_err.getvalue()
expect("a very deep head is an error", deep_code, 2)
expect("a very deep head names the problem", "too deep" in deep_text and "Usage:" not in deep_text, True)
for dirpath, dirnames, filenames in os.walk(deep_root, topdown=False):
    for name in filenames:
        os.remove(os.path.join(dirpath, name))
    os.rmdir(dirpath)

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
        "for t in awk sed grep find python3 python git; do\n"
        "  if command -v \"$t\" >/dev/null 2>&1; then echo OK:$t; else echo MISSING:$t; fi\n"
        "done\n"
    )
    os.chmod(tool, 0o755)
    tool_out = tempfile.mkdtemp()
    tool_code = run_all(brief, tool_out, search_path=os.path.dirname(tool), cwd=head, sandbox="bwrap")
    tool_body = open(os.path.join(tool_out, "codex.md")).read() if os.path.isfile(os.path.join(tool_out, "codex.md")) else ""
    expect("common tools resolve", tool_code == 0 and "MISSING:" not in tool_body and "OK:awk" in tool_body and "OK:python" in tool_body, True)
    rel_parent = tempfile.mkdtemp()
    rel_case = os.path.join(rel_parent, "cases", "item")
    os.makedirs(os.path.join(rel_case, "head"))
    open(os.path.join(rel_case, "key.md"), "w").write("Planted: yes\n")
    open(os.path.join(rel_case, "head", "cap.py"), "w").write("x\n")
    rel_stub = os.path.join(tempfile.mkdtemp(), "codex")
    open(rel_stub, "w").write("#!/bin/sh\necho REL:$(pwd)\n")
    os.chmod(rel_stub, 0o755)
    here = os.getcwd()
    os.chdir(rel_parent)
    try:
        rel_code = run_all(brief, tempfile.mkdtemp(), search_path=os.path.dirname(rel_stub), cwd="cases/item/head", sandbox="bwrap")
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
    expect("a case outside cases/ is refused", escape_code, 2)
    wide = tempfile.mkdtemp()
    os.makedirs(os.path.join(wide, ".codex"))
    open(os.path.join(wide, ".codex", "config.toml"), "w").write(
        'model = "gpt"\nnote = """\n%s\n"""\n' % ("y" * 70000)
    )
    wide_stub = os.path.join(tempfile.mkdtemp(), "codex")
    open(wide_stub, "w").write(
        "#!/bin/sh\nwc -c < /home/agent/.codex/config.toml\n"
    )
    os.chmod(wide_stub, 0o755)
    saved_env = {name: os.environ.get(name) for name in ("HOME", "CODEX_HOME")}
    os.environ["HOME"] = wide
    os.environ.pop("CODEX_HOME", None)
    wide_out = tempfile.mkdtemp()
    try:
        wide_code = run_all(
            brief, wide_out, search_path=os.path.dirname(wide_stub), cwd=head, sandbox="bwrap", timeout=20,
        )
    finally:
        for name, value in saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(wide, ignore_errors=True)
    wide_body = open(os.path.join(wide_out, "codex.md")).read() if os.path.isfile(os.path.join(wide_out, "codex.md")) else ""
    wide_size = 0
    for token in wide_body.split():
        if token.isdigit():
            wide_size = int(token)
    expect("a login file over 64KB is readable", wide_code == 0 and wide_size > 70000, True)

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
        shutil.rmtree(fake, ignore_errors=True)
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
    for cli in ("codex", "claude"):
        binary = shutil.which(cli)
        if binary is None:
            print("SKIP %s is not installed" % cli)
            continue
        only = tempfile.mkdtemp()
        os.symlink(binary, os.path.join(only, cli))
        filename = "pong-%s.txt" % cli
        other = "pong-claude.txt" if cli == "codex" else "pong-codex.txt"
        smoke_brief = os.path.join(tempfile.mkdtemp(), "brief.md")
        open(smoke_brief, "w").write(
            "Write the word pong into /tmp/%s. Reply with the single word pong.\n" % filename
        )
        smoke_dir = tempfile.mkdtemp()
        host_tmp = tempfile.mkdtemp()
        smoke_out = tempfile.mkdtemp()
        code = run_all(
            smoke_brief, smoke_out, search_path=only, cwd=smoke_dir, sandbox="bwrap", timeout=180, host_tmp=host_tmp,
        )
        path = os.path.join(smoke_out, cli + ".md")
        text = open(path).read() if os.path.isfile(path) else ""
        lowered = text.lower()
        pong_path = os.path.join(host_tmp, filename)
        pong = open(pong_path).read() if os.path.isfile(pong_path) else ""
        expect(
            "%s logs in and writes /tmp/%s" % (cli, filename),
            code == 0 and "pong" in lowered and "not logged in" not in lowered and "401" not in text and "pong" in pong and not os.path.exists(os.path.join(host_tmp, other)),
            True,
        )

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(CHECKS) - len(FAILS)}/{len(CHECKS)} passed")
    sys.exit(1 if FAILS else 0)
