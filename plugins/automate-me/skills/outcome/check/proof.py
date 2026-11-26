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

`run` executes each Verify command in Must-haves order and writes
verify-<id>.txt. An existing verify-<id>.txt, including a symlink, is replaced
with a new file and a link's target is left alone. Proof files get the normal
default mode (0666 masked by the umask). A command that exceeds the timeout
(default 300 seconds) has its process group killed and is recorded with
exit=124. `run` exits 1 if any command exits nonzero, else 0.

`check` runs nothing. It fails with exit 1 when:
- a Must-have id has no Verify command in the brief;
- verify-<id>.txt is missing;
- line 1 is not exit=<integer>;
- the recorded exit code is not 0;
- line 2 does not match `cmd: <current command>`.
Extra verify-*.txt files for ids not in the brief are noted and do not fail the
check. A brief whose Verify is none prints a note and passes.

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
        out_path = os.path.join(outdir, f"verify-{mid}.txt")
        fd, tmp = tempfile.mkstemp(dir=outdir, prefix=".verify-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                fd = None
                f.write(f"exit={code}\ncmd: {cmd}\n{output}")
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
        print(f"{mid} exit={code}")
        if code != 0:
            any_failed = True

    return 1 if any_failed else 0


def check_brief_proof(brief_path, outdir):
    text = load_valid_brief(brief_path)
    if text is None:
        return 2

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
