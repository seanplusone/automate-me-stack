"""Runs Verify commands from an outcome brief and checks the saved proof files.

Usage:
  python3 check/proof.py run [--timeout <seconds>] <brief.md> <out-dir>
  python3 check/proof.py check <brief.md> <out-dir>

Each proof file is <out-dir>/verify-<id>.txt:
- line 1: exit=<integer>
- line 2: cmd: <command>
- line 3 on: combined stdout and stderr

`run` checks the brief with check_brief.py first. If any check fails, it prints
the failing checks, writes nothing, and exits 2. Otherwise it runs each Verify
command in Must-haves order and writes verify-<id>.txt. A command that exceeds
the timeout (default 300 seconds) is recorded with exit=124. `run` exits 1 if
any command exits nonzero, else 0.

`check` runs nothing. It fails when:
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
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_brief import RULE_ID, TAG, UNKNOWN_START, VERIFY_ID, check, is_none, parse

DEFAULT_TIMEOUT = 300
CMD_TEXT = re.compile(r"^\s*`(\s*[^`\s][^`]*)`")
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
        cm = CMD_TEXT.match(rest)
        if cm:
            commands[vid] = cm.group(1).strip()
    return rule_ids, commands, verify_none


def run_brief(brief_path, outdir, timeout):
    with open(brief_path) as f:
        text = f.read()

    failed_checks = [(name, fails) for name, fails in check(text, brief_path) if fails]
    if failed_checks:
        print(f"FAIL brief: {brief_path}")
        for name, fails in failed_checks:
            print(f"FAIL {name}")
            for fail in fails:
                print(f"  {fail}")
        return 2

    rule_ids, commands, _ = load_verify(text)
    os.makedirs(outdir, exist_ok=True)
    any_failed = False

    for mid in rule_ids:
        cmd = commands[mid]
        try:
            proc = subprocess.run(
                ["bash", "-c", cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                text=True,
            )
            code = proc.returncode
            output = proc.stdout or ""
        except subprocess.TimeoutExpired as exc:
            code = 124
            raw = exc.output
            if raw is None:
                output = ""
            elif isinstance(raw, bytes):
                output = raw.decode("utf-8", errors="replace")
            else:
                output = raw

        out_path = os.path.join(outdir, f"verify-{mid}.txt")
        with open(out_path, "w") as f:
            f.write(f"exit={code}\ncmd: {cmd}\n{output}")
        print(f"{mid} exit={code}")
        if code != 0:
            any_failed = True

    return 1 if any_failed else 0


def check_brief_proof(brief_path, outdir):
    with open(brief_path) as f:
        text = f.read()

    rule_ids, commands, verify_none = load_verify(text)
    if verify_none and not rule_ids:
        print("note: Verify is none")
        print(f"PASS proof: {brief_path}")
        return 0

    failed = False
    for mid in rule_ids:
        if mid not in commands:
            print(f"FAIL {mid}: no Verify command in brief")
            failed = True
            continue

        path = os.path.join(outdir, f"verify-{mid}.txt")
        if not os.path.isfile(path):
            print(f"FAIL {mid}: no file {path}")
            failed = True
            continue

        with open(path) as f:
            lines = f.read().splitlines()

        m = EXIT_LINE.match(lines[0]) if lines else None
        if not m:
            print(f"FAIL {mid}: line 1 is not exit=<integer>")
            failed = True
            continue

        code = int(m.group(1))
        if code != 0:
            print(f"FAIL {mid}: recorded exit {code} is not 0")
            failed = True
            continue

        expected = f"cmd: {commands[mid]}"
        if len(lines) < 2 or lines[1] != expected:
            print(f"FAIL {mid}: line 2 does not match `{expected}`")
            failed = True
            continue

        print(f"PASS {mid}")

    known_ids = set(rule_ids)
    if os.path.isdir(outdir):
        for entry in sorted(os.listdir(outdir)):
            m = VERIFY_FILE.match(entry)
            if m and m.group(1) not in known_ids:
                print(f"note: {entry} is for an id not in the brief")

    print(f"{'FAIL' if failed else 'PASS'} proof: {brief_path}")
    return 1 if failed else 0


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
