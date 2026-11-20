"""Find codex and claude on PATH and run one headless pass with each.

Usage: python3 attack_agents.py
       python3 attack_agents.py --run --brief <file> --out <dir> [--cwd <dir>] [--timeout <seconds>]

Prints one name per line, codex then claude. Prints `none` when neither
binary is on PATH. --run writes <dir>/<name>.md and <dir>/<name>.err.
The brief file is the whole prompt. Codex runs sandboxed workspace-write.
Claude may run Bash in the checkout (acceptEdits), not a bypass of the
whole machine. The default wait is 600 seconds. A timeout writes
`Parse: timeout` so a merge does not treat it as an approve.
This script does not decide what to attack, and it does not pick a fallback agent.
"""
import os
import re
import shutil
import subprocess
import sys

NAMES = ("codex", "claude")
DEFAULT_TIMEOUT = 600
FINDING = re.compile(r"^###\s+(\S+)\s*\|\s*(\S+?)(?:\s*\|\s*passes:\s*(.*))?$")


def command(binary, name, brief):
    """The headless argv for one CLI. The brief is the last argument."""
    if name == "codex":
        return [binary, "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", brief]
    if name == "claude":
        return [binary, "-p", "--permission-mode", "acceptEdits", "--allowedTools", "Bash", brief]
    raise SystemExit(f"unknown agent {name}")


def stamp(text, agent):
    """Put the agent name on every finding heading."""
    lines = []
    for line in (text or "").splitlines():
        match = FINDING.match(line)
        if not match:
            lines.append(line)
            continue
        names = [part.strip() for part in (match.group(3) or "").split(",") if part.strip()]
        if agent not in names:
            names.append(agent)
        lines.append(f"### {match.group(1)} | {match.group(2)} | passes: {', '.join(names)}")
    body = "\n".join(lines)
    if text and text.endswith("\n"):
        body += "\n"
    return body


def detect(search_path=None):
    """(name, binary) pairs that resolve, in a stable order. search_path replaces PATH."""
    found = []
    for name in NAMES:
        binary = shutil.which(name, path=search_path)
        if binary:
            found.append((name, binary))
    return found


def run_all(brief_path, out_dir, search_path=None, runner=None, timeout=DEFAULT_TIMEOUT, cwd=None):
    """Run each detected CLI. Returns 0, or 1 when a CLI exits non-zero or times out."""
    found = detect(search_path)
    if not found:
        print("none")
        return 0
    os.makedirs(out_dir, exist_ok=True)
    brief = open(brief_path).read()
    work = cwd if cwd is not None else os.getcwd()
    failed = 0
    for name, binary in found:
        cmd = command(binary, name, brief)
        out_path = os.path.join(out_dir, name + ".md")
        err_path = os.path.join(out_dir, name + ".err")
        try:
            if runner:
                result = runner(cmd)
            else:
                result = subprocess.run(
                    cmd, cwd=work, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            failed = 1
            err = exc.stderr or ""
            if isinstance(err, bytes):
                err = err.decode("utf-8", "replace")
            open(err_path, "w").write(err + f"\ntimed out after {timeout}s\n")
            open(out_path, "w").write("Parse: timeout\n")
            print(name)
            continue
        open(out_path, "w").write(stamp(result.stdout or "", name))
        open(err_path, "w").write(result.stderr or "")
        if result.returncode != 0:
            failed = 1
        print(name)
    return failed


def main(argv):
    if any(a in ("-h", "--help") for a in argv[1:]):
        print((__doc__ or "").strip())
        return 0
    if "--run" not in argv[1:]:
        names = [name for name, _binary in detect()]
        print("\n".join(names) if names else "none")
        return 0
    if "--brief" not in argv or "--out" not in argv:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    brief = argv[argv.index("--brief") + 1]
    out = argv[argv.index("--out") + 1]
    cwd = argv[argv.index("--cwd") + 1] if "--cwd" in argv else None
    timeout = DEFAULT_TIMEOUT
    if "--timeout" in argv:
        timeout = int(argv[argv.index("--timeout") + 1])
    return run_all(brief, out, timeout=timeout, cwd=cwd)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
