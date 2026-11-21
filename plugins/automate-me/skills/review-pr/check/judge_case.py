"""Meaning judge for a planted-bug attack review.

Usage: python3 check/judge_case.py <key.md> <attack.md>

The keyword scorer only checks that the catch terms are present. This judge
asks whether a finding states the same bug. It runs whichever agent CLI is
on PATH, `codex exec` or `claude -p`. The prompt is written to that command's
stdin. If neither CLI is installed, it prints SKIP and exits 0. Set
JUDGE_CLI to one executable to force a command. That executable must read
the prompt on stdin and write `ITEM 1: yes` or `ITEM 1: no`.

Exit 0 when the finding catches the bug, or when no CLI is available.
Exit 1 when the judge says the bug was missed.
Exit 2 when the judge times out, exits non-zero, or the arguments are wrong.
The default wait is 300 seconds. Set JUDGE_TIMEOUT to change it. A timeout
is SKIP, not a pass.
"""
import os
import re
import shutil
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import parse_attack  # noqa: E402

ITEM = re.compile(r"^ITEM\s+(\d+)\s*:\s*([A-Za-z]+)\b", re.I)
DEFAULT_TIMEOUT = 300


def find_cli(environ=None):
    """An argv list, or None when no judge can run."""
    env = os.environ if environ is None else environ
    override = env.get("JUDGE_CLI")
    if override:
        return [override]
    path = env.get("PATH", "")
    for name, extra in (("claude", ["-p"]), ("codex", ["exec"])):
        found = shutil.which(name, path=path)
        if found:
            return [found, *extra]
    return None


def build_prompt(key_text, findings):
    lines = [
        "You judge whether a review finding catches the planted bug.",
        "Answer yes only when a finding states that same bug.",
        "Answer no when the findings describe a different problem, or none do.",
        "",
        "BUG",
        key_text.strip(),
        "",
    ]
    if not findings:
        lines.append("FINDINGS")
        lines.append("(none)")
    for finding in findings:
        claim = finding.get("claim") or ""
        if isinstance(claim, list):
            claim = " ".join(claim)
        where = finding.get("where") or ""
        if not where and finding.get("file"):
            line = finding.get("line")
            where = finding["file"] if line is None else f"{finding['file']}:{line}"
        lines.append("FINDING " + finding.get("id", ""))
        lines.append("WHERE " + where)
        lines.append("CLAIM " + claim)
        lines.append("REPRO " + finding.get("repro", ""))
        lines.append("OBSERVED " + finding.get("observed", ""))
        lines.append("")
    lines.append("Reply with one line and nothing else.")
    lines.append("ITEM 1: yes")
    lines.append("ITEM 1: no")
    return "\n".join(lines)


def _judge_line(line):
    """Drop list markers and emphasis around the label and the answer."""
    text = line.strip()
    text = re.sub(r"^[-*+][ \t]+", "", text)
    text = re.sub(r"^\d+[.)][ \t]+", "", text)
    text = text.replace("*", "").replace("_", "").replace("`", "")
    text = re.sub(r"^[-+][ \t]+", "", text)
    return text.strip()


def parse_verdict(text):
    """True, False, 'conflict' when one item has both answers, or None."""
    found = {}
    for raw in (text or "").split("\n"):
        match = ITEM.match(_judge_line(raw))
        if not match:
            continue
        word = match.group(2).lower()
        if word not in ("yes", "no"):
            continue
        number = int(match.group(1))
        found.setdefault(number, []).append(word == "yes")
    answers = found.get(1) or []
    if not answers:
        return None
    if any(answer != answers[0] for answer in answers):
        return "conflict"
    return answers[0]


def _timeout(timeout):
    if timeout is not None:
        return float(timeout)
    raw = os.environ.get("JUDGE_TIMEOUT", "")
    if not raw:
        return DEFAULT_TIMEOUT
    return float(raw)


LIVE = []


def _preexec():
    """On Linux, die if the parent dies, including when the parent is SIGKILL'd."""
    if sys.platform != "linux":
        return
    try:
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(1, int(signal.SIGKILL)) != 0:
            return
        if os.getppid() == 1:
            os.kill(os.getpid(), signal.SIGKILL)
    except Exception:
        return


def _kill_live():
    for proc in list(LIVE):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            try:
                proc.kill()
            except OSError:
                pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _on_stop(signum, _frame):
    _kill_live()
    raise SystemExit(128 + signum)


def _stop_signals():
    found = []
    for name in ("SIGTERM", "SIGINT", "SIGHUP"):
        sig = getattr(signal, name, None)
        if sig is not None:
            found.append(sig)
    return found


def run_cli(argv, prompt, timeout):
    proc = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True, preexec_fn=_preexec,
    )
    LIVE.append(proc)
    try:
        try:
            stdout, _stderr = proc.communicate(prompt, timeout=timeout)
        except BaseException:
            _kill_live()
            raise
        return proc.returncode, stdout
    finally:
        if proc.poll() is None:
            _kill_live()
        if proc in LIVE:
            LIVE.remove(proc)


def judge(key_path, attack_path, environ=None, runner=None, findings=None, timeout=None):
    """0 when the bug is caught or no CLI exists, 1 on a miss, 2 on a bad exit or timeout."""
    doc = parse_attack(attack_path)
    chosen = doc["findings"] if findings is None else findings
    prompt = build_prompt(open(key_path).read(), chosen)
    argv = find_cli(environ)
    if argv is None and runner is None:
        print("SKIP no agent CLI on PATH")
        return 0
    previous = {sig: signal.signal(sig, _on_stop) for sig in _stop_signals()}
    try:
        return _judge_run(key_path, argv, prompt, runner, timeout)
    finally:
        _kill_live()
        for sig, old in previous.items():
            signal.signal(sig, old)


def _judge_run(key_path, argv, prompt, runner, timeout):
    if runner:
        out = runner(prompt)
        if isinstance(out, tuple):
            code, stdout = out
        else:
            code, stdout = 0, out
    else:
        try:
            code, stdout = run_cli(argv, prompt, _timeout(timeout))
        except subprocess.TimeoutExpired:
            print("SKIP judge timed out")
            return 2
        except (ValueError, OSError) as exc:
            print(f"SKIP judge {exc}")
            return 2
    if code:
        print("SKIP judge exited non-zero")
        return 2
    ok = parse_verdict(stdout)
    if ok is None:
        print("SKIP judge reply")
        return 2
    if ok is True:
        print("PASS judge caught planted bug")
        return 0
    print("FAIL judge missed planted bug")
    return 1


if __name__ == "__main__":
    try:
        if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
            print((__doc__ or "").strip())
            sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2)
        sys.exit(judge(sys.argv[1], sys.argv[2]))
    except SystemExit:
        raise
    except Exception:
        print((__doc__ or "").strip(), file=sys.stderr)
        sys.exit(2)
