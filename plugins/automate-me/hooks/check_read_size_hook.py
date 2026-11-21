"""Claude Code PreToolUse adapter for skills/shared/check_read_size.py. Holds no read-size logic of its own.

Usage: python3 check_read_size_hook.py < hook-input.json

Reads tool_name, tool_input and cwd from stdin. Read passes file_path (or path), offset and limit to the check.
Bash passes the command, run from cwd so relative paths resolve. Other tools are allowed.
Exits 2 with the check's one-line reason on stderr when the check blocks, which makes Claude Code deny the call.
Fails open (exit 0) on bad input, a usage error from the check, or a check that cannot run.
"""
import json
import os
import subprocess
import sys

CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "shared", "check_read_size.py")


def number(v, low):
    return str(v) if isinstance(v, int) and not isinstance(v, bool) and v >= low else None


def check_args(event):
    tool, ti = event.get("tool_name"), event.get("tool_input")
    if not isinstance(ti, dict):
        return None
    if tool == "Read":
        path = ti.get("file_path") or ti.get("path")
        if not isinstance(path, str) or not path:
            return None
        args = []
        for flag, key, low in (("--offset", "offset", 0), ("--limit", "limit", 1)):
            v = number(ti.get(key), low)
            if v:
                args += [flag, v]
        return args + ["--", path]
    if tool == "Bash":
        cmd = ti.get("command")
        return ["--command", cmd] if isinstance(cmd, str) and cmd.strip() else None
    return None


def main():
    try:
        event = json.load(sys.stdin)
        args = check_args(event) if isinstance(event, dict) else None
        if not args:
            return 0
        cwd = event.get("cwd")
        cwd = cwd if isinstance(cwd, str) and os.path.isdir(cwd) else None
        p = subprocess.run([sys.executable, CHECK, *args], capture_output=True, text=True, cwd=cwd, timeout=20)
    except Exception:
        return 0
    if p.returncode == 2 and p.stderr.strip():
        print(p.stderr.strip().splitlines()[0], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
