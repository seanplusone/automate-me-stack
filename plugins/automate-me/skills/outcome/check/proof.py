"""Runs Verify commands from an outcome brief and checks the saved proof files.

Usage:
  python3 check/proof.py run [--timeout <seconds>] <brief.md> <out-dir>
  python3 check/proof.py check <brief.md> <out-dir>

Each proof file is <out-dir>/verify-<id>.txt:
- line 1: exit=<integer>
- line 2: cmd: <command>
- line 3 on: combined stdout and stderr

Both `run` and `check` validate the brief with check_brief.py first. If any
check fails, they print the failing checks, touch no proof files, and exit 2.
Both also resolve git from the current working directory; if it is not inside
a git repo, they print an error naming git, write no proof files, and exit 2.

Dirty means a non-empty `git status --porcelain` after dropping paths that are
the out-dir or under it, when the out-dir is inside the repo. Gitignored files
already stay out of porcelain, so they do not count as dirty.

`run` records the starting HEAD, executes each Verify command in Must-haves
order, and writes verify-<id>.txt. An existing verify-<id>.txt, including a
symlink, is replaced with a new file and a link's target is left alone. Proof
files get the normal default mode (0666 masked by the umask). A command that
exceeds the timeout (default 300 seconds) has its process group killed and is
recorded with exit=124. After running all commands, `run` re-reads HEAD and
dirty state and writes <out-dir>/proof-summary.txt (atomic replace, same mode)
with `sha=<starting sha>`, `dirty=yes|no`, and a last non-empty line
`VERIFY: PASS sha=<starting sha>` or `VERIFY: FAIL sha=<starting sha>`. `run`
exits 0 only when every command exits 0, HEAD is unchanged, and the tree is
clean; otherwise it writes FAIL and exits 1.

`check` runs nothing. It fails with exit 1 when:
- a Must-have id has no Verify command in the brief;
- verify-<id>.txt is missing;
- line 1 is not exit=<integer>;
- the recorded exit code is not 0;
- line 2 does not match `cmd: <current command>`;
- proof-summary.txt is missing or has no `sha=` line matching current HEAD;
- the last non-empty line of proof-summary.txt is not `VERIFY: PASS sha=<HEAD>`;
- the current git tree is dirty.
Extra verify-*.txt files for ids not in the brief are noted and do not fail the
check. A brief whose Verify is none with no rule ids prints a note and passes.

`check` proves the command ran and passed at that time; it does not prove the
command tests the right thing.
"""
import argparse
import os
import re
import signal
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_brief import BACKTICK_CMD, RULE_ID, TAG, UNKNOWN_START, VERIFY_ID, check, is_none, parse

DEFAULT_TIMEOUT = 300
EXIT_LINE = re.compile(r"^exit=(-?\d+)$")
VERIFY_FILE = re.compile(r"^verify-(.+)\.txt$")
SUMMARY_FILE = "proof-summary.txt"


def run_git(*args, cwd=None):
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="replace",
        )
    except OSError:
        return None


def resolve_git():
    """Returns (repo_root, head_sha) for the current directory, or None."""
    top = run_git("rev-parse", "--show-toplevel")
    if top is None or top.returncode != 0:
        print("FAIL git: current directory is not inside a git repository")
        return None
    head = run_git("rev-parse", "HEAD")
    if head is None or head.returncode != 0:
        print("FAIL git: could not resolve git HEAD")
        return None
    return top.stdout.strip(), head.stdout.strip()


def current_head():
    head = run_git("rev-parse", "HEAD")
    if head is None or head.returncode != 0:
        return None
    return head.stdout.strip()


def outdir_in_repo(repo_root, outdir):
    root_real = os.path.realpath(repo_root)
    out_real = os.path.realpath(outdir)
    try:
        rel = os.path.relpath(out_real, root_real)
    except ValueError:
        return None
    if rel == ".." or rel.startswith(".." + os.sep):
        return None
    if rel == ".":
        return "."
    return rel.replace(os.sep, "/").rstrip("/")


def path_under_outdir(path, out_prefix):
    if out_prefix is None:
        return False
    if out_prefix == ".":
        return True
    norm = path.rstrip("/")
    return norm == out_prefix or norm.startswith(out_prefix + "/")


def is_tree_dirty(repo_root, outdir):
    proc = run_git("status", "--porcelain", "-z", "-uall", cwd=repo_root)
    if proc is None or proc.returncode != 0:
        return True
    out_prefix = outdir_in_repo(repo_root, outdir)
    entries = proc.stdout.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        xy = entry[:2]
        paths = [entry[3:]]
        if "R" in xy or "C" in xy:
            if i < len(entries):
                paths.append(entries[i])
                i += 1
        if any(not path_under_outdir(p, out_prefix) for p in paths):
            return True
    return False


def write_atomic(outdir, filename, content, mode, prefix=".verify-"):
    out_path = os.path.join(outdir, filename)
    fd, tmp = tempfile.mkstemp(dir=outdir, prefix=prefix, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = None
            f.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, out_path)
    except BaseException:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_verify(text):
    """Returns (rule_ids, commands, verify_none) from a brief's text."""
    slots, _, _ = parse(text)
    rules = [i for i in slots.get("Must-haves", []) if not (TAG.match(i) or UNKNOWN_START.match(i))]
    rule_ids = []
    for item in rules:
        m = RULE_ID.match(item)
        if m:
            rule_ids.append(m.group(1))
    rule_ids = list(dict.fromkeys(rule_ids))

    verify = slots.get("Verify", [])
    verify_none = is_none(verify)
    verify_items = [] if verify_none else verify
    commands = {}
    for item in verify_items:
        m = VERIFY_ID.match(item)
        if not m:
            continue
        vid, rest = m.group(1), m.group(2)
        cm = BACKTICK_CMD.match(rest)
        if cm:
            commands[vid] = cm.group(0).strip().strip("`").strip()
    return rule_ids, commands, verify_none


def load_valid_brief(brief_path):
    with open(brief_path, encoding="utf-8") as f:
        text = f.read()

    failed_checks = [(name, fails) for name, fails in check(text, brief_path) if fails]
    if failed_checks:
        print(f"FAIL brief: {brief_path}")
        for name, fails in failed_checks:
            print(f"FAIL {name}")
            for fail in fails:
                print(f"  {fail}")
        return None
    return text


def default_file_mode():
    mask = os.umask(0)
    os.umask(mask)
    return 0o666 & ~mask


def run_brief(brief_path, outdir, timeout):
    text = load_valid_brief(brief_path)
    if text is None:
        return 2

    git_state = resolve_git()
    if git_state is None:
        return 2
    repo_root, start_sha = git_state

    rule_ids, commands, _ = load_verify(text)
    os.makedirs(outdir, exist_ok=True)
    mode = default_file_mode()
    any_failed = False

    for mid in rule_ids:
        cmd = commands[mid]
        proc = subprocess.Popen(
            ["bash", "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            raw, _ = proc.communicate(timeout=timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            raw, _ = proc.communicate()
            code = 124

        output = (raw or b"").decode("utf-8", errors="replace")
        write_atomic(outdir, f"verify-{mid}.txt", f"exit={code}\ncmd: {cmd}\n{output}", mode)
        print(f"{mid} exit={code}")
        if code != 0:
            any_failed = True

    end_sha = current_head()
    dirty = is_tree_dirty(repo_root, outdir)
    passed = (not any_failed) and (end_sha == start_sha) and (not dirty)
    verdict = "PASS" if passed else "FAIL"
    dirty_str = "yes" if dirty else "no"
    summary = f"sha={start_sha}\ndirty={dirty_str}\nVERIFY: {verdict} sha={start_sha}\n"
    write_atomic(outdir, SUMMARY_FILE, summary, mode, prefix=".proof-summary-")

    return 0 if passed else 1


def check_brief_proof(brief_path, outdir):
    text = load_valid_brief(brief_path)
    if text is None:
        return 2

    git_state = resolve_git()
    if git_state is None:
        return 2
    repo_root, head_sha = git_state

    rule_ids, commands, verify_none = load_verify(text)
    if verify_none and not rule_ids:
        print("note: Verify is none")
        print(f"PASS proof: {brief_path}")
        return 0

    failing = []
    for mid in rule_ids:
        if mid not in commands:
            print(f"FAIL {mid}: no Verify command in {brief_path}")
            failing.append(mid)
            continue

        expected = f"cmd: {commands[mid]}"
        path = os.path.join(outdir, f"verify-{mid}.txt")
        if not os.path.isfile(path):
            print(f"FAIL {mid}: no file {path}; expected line 1 exit=0 and line 2 {expected}")
            failing.append(mid)
            continue

        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()

        m = EXIT_LINE.match(lines[0]) if lines else None
        if not m:
            actual = repr(lines[0]) if lines else "missing"
            print(f"FAIL {mid}: {path} line 1 is {actual}, expected exit=<integer>")
            failing.append(mid)
            continue

        code = int(m.group(1))
        if code != 0:
            print(f"FAIL {mid}: {path} line 1 records exit {code}, expected exit=0")
            failing.append(mid)
            continue

        if len(lines) < 2 or lines[1] != expected:
            actual = repr(lines[1]) if len(lines) >= 2 else "missing"
            print(f"FAIL {mid}: {path} line 2 is {actual}, expected {expected}")
            failing.append(mid)
            continue

        print(f"PASS {mid}")

    known_ids = set(rule_ids)
    if os.path.isdir(outdir):
        for entry in sorted(os.listdir(outdir)):
            m = VERIFY_FILE.match(entry)
            if m and m.group(1) not in known_ids:
                print(f"note: {entry} is for an id not in the brief")

    summary_path = os.path.join(outdir, SUMMARY_FILE)
    summary_failed = False
    if not os.path.isfile(summary_path):
        print(f"FAIL summary: no file {summary_path}")
        summary_failed = True
    else:
        with open(summary_path, encoding="utf-8", errors="replace") as f:
            summary_lines = f.read().splitlines()
        sha_values = [line[4:] for line in summary_lines if line.startswith("sha=")]
        if not sha_values:
            print(f"FAIL summary: {summary_path} missing sha= line")
            summary_failed = True
        elif sha_values[0] != head_sha:
            print(f"FAIL summary: {summary_path} sha={sha_values[0]}, expected {head_sha}")
            summary_failed = True
        non_empty = [line for line in summary_lines if line.strip()]
        last_line = non_empty[-1] if non_empty else ""
        expected_last = f"VERIFY: PASS sha={head_sha}"
        if last_line != expected_last:
            print(f"FAIL summary: {summary_path} last line is {last_line!r}, expected {expected_last!r}")
            summary_failed = True

    if summary_failed:
        failing.append("summary")

    if is_tree_dirty(repo_root, outdir):
        print("FAIL git: working tree is dirty")
        failing.append("git")

    if failing:
        print(f"FAIL proof: {brief_path} (failing: {', '.join(failing)})")
        return 1
    print(f"PASS proof: {brief_path}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run Verify commands from a brief and check saved proof files.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run each Verify command and save output.")
    p_run.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Seconds per command (default: 300).")
    p_run.add_argument("brief", help="Path to the brief markdown file.")
    p_run.add_argument("outdir", help="Directory to write verify-<id>.txt files.")

    p_check = sub.add_parser("check", help="Check saved proof files against the brief.")
    p_check.add_argument("brief", help="Path to the brief markdown file.")
    p_check.add_argument("outdir", help="Directory containing verify-<id>.txt files.")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return run_brief(args.brief, args.outdir, args.timeout)
    return check_brief_proof(args.brief, args.outdir)


if __name__ == "__main__":
    sys.exit(main())
