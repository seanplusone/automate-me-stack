"""Run: python3 check/test_proof.py"""
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUTCOME = os.path.dirname(HERE)
PROOF = os.path.join(HERE, "proof.py")
BRIEFS = "check/fixtures/proof/briefs/demo"

FAILS = []
RAN = []


def run_proof(*args, timeout=None, env=None, umask=None, cwd=None):
    if not os.path.isfile(PROOF):
        return None, f"missing {PROOF}"
    work_dir = OUTCOME if cwd is None else cwd
    proof_arg = "check/proof.py" if work_dir == OUTCOME else PROOF
    try:
        proc = subprocess.run(
            [sys.executable, proof_arg, *args],
            cwd=work_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            preexec_fn=(lambda: os.umask(umask)) if umask is not None else None,
        )
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"
    return proc, None


def git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def git_head(repo):
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def read_pass_brief():
    with open(os.path.join(OUTCOME, BRIEFS, "pass.md")) as f:
        return f.read()


def make_repo(brief_text=None, extra_files=None):
    repo = tempfile.mkdtemp()
    try:
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "test")
        git(repo, "config", "user.email", "test@example.com")
        git(repo, "config", "commit.gpgsign", "false")
        brief_dir = os.path.join(repo, BRIEFS)
        os.makedirs(brief_dir, exist_ok=True)
        workstreams = os.path.join(os.path.dirname(brief_dir), "WORKSTREAMS")
        with open(workstreams, "w") as f:
            f.write("demo\n")
        pass_dst = os.path.join(brief_dir, "pass.md")
        if brief_text is None:
            shutil.copyfile(os.path.join(OUTCOME, BRIEFS, "pass.md"), pass_dst)
        else:
            with open(pass_dst, "w") as f:
                f.write(brief_text)
        if extra_files:
            for rel, content in extra_files.items():
                full = os.path.join(repo, rel)
                parent = os.path.dirname(full)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(full, "w") as f:
                    f.write(content)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "init")
    except BaseException:
        shutil.rmtree(repo, ignore_errors=True)
        raise
    return repo


def read_lines(path):
    with open(path) as f:
        return f.read().splitlines()


def set_line(path, index, value):
    lines = read_lines(path)
    while len(lines) <= index:
        lines.append("")
    lines[index] = value
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def drop_first_line(path):
    lines = read_lines(path)
    with open(path, "w") as f:
        f.write("\n".join(lines[1:]) + "\n")


def test_run_pass():
    name = "run on pass.md writes verify files and exits 0"
    RAN.append(name)
    out = tempfile.mkdtemp()
    repo = None
    try:
        repo = make_repo()
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 0:
            reasons.append(f"wanted exit 0, got {proc.returncode}")
        for mid in ("m1", "m2", "m3"):
            path = os.path.join(out, f"verify-{mid}.txt")
            if not os.path.isfile(path):
                reasons.append(f"missing verify-{mid}.txt")
                continue
            lines = read_lines(path)
            if not lines or lines[0] != "exit=0":
                reasons.append(f"verify-{mid}.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=0'")
        m2_path = os.path.join(out, "verify-m2.txt")
        if os.path.isfile(m2_path):
            m2 = read_lines(m2_path)
            if len(m2) < 2 or m2[1] != "cmd: echo ok":
                reasons.append(f"verify-m2.txt line 2 was {m2[1] if len(m2) >= 2 else None!r}, wanted 'cmd: echo ok'")
            if len(m2) < 3 or m2[2] != "ok":
                reasons.append(f"verify-m2.txt line 3 was {m2[2] if len(m2) >= 3 else None!r}, wanted 'ok'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)
        if repo:
            shutil.rmtree(repo, ignore_errors=True)


def test_run_fail():
    name = "run on fail.md exits 1 and records exit=3"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/fail.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 1:
            reasons.append(f"wanted exit 1, got {proc.returncode}")
        path = os.path.join(out, "verify-m1.txt")
        if not os.path.isfile(path):
            reasons.append("missing verify-m1.txt")
        else:
            lines = read_lines(path)
            if not lines or lines[0] != "exit=3":
                reasons.append(f"verify-m1.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=3'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_run_slow():
    name = "run --timeout 1 on slow.md exits 1 with exit=124"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        start = time.monotonic()
        proc, err = run_proof("run", "--timeout", "1", f"{BRIEFS}/slow.md", out, timeout=20)
        elapsed = time.monotonic() - start
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 1:
            reasons.append(f"wanted exit 1, got {proc.returncode}")
        if elapsed >= 20:
            reasons.append(f"took {elapsed:.1f}s, limit 20s")
        path = os.path.join(out, "verify-m1.txt")
        if not os.path.isfile(path):
            reasons.append("missing verify-m1.txt")
        else:
            lines = read_lines(path)
            if not lines or lines[0] != "exit=124":
                reasons.append(f"verify-m1.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=124'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_run_child():
    name = "run --timeout 1 on child.md kills process group with exit=124"
    RAN.append(name)
    tmp = tempfile.mkdtemp()
    try:
        marker = os.path.join(tmp, "marker")
        out = os.path.join(tmp, "out")
        env = dict(os.environ)
        env["PROOF_MARKER"] = marker
        proc, err = run_proof("run", "--timeout", "1", f"{BRIEFS}/child.md", out, timeout=20, env=env)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 1:
            reasons.append(f"wanted exit 1, got {proc.returncode}")
        path = os.path.join(out, "verify-m1.txt")
        if not os.path.isfile(path):
            reasons.append("missing verify-m1.txt")
        else:
            lines = read_lines(path)
            if not lines or lines[0] != "exit=124":
                reasons.append(f"verify-m1.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=124'")
        time.sleep(3)
        if os.path.exists(marker):
            reasons.append(f"child process created {marker}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_run_binary():
    name = "run on binary.md exits 0 and preserves non-UTF-8 output"
    RAN.append(name)
    out = tempfile.mkdtemp()
    repo = None
    try:
        repo = make_repo()
        proc, err = run_proof("run", os.path.join(OUTCOME, BRIEFS, "binary.md"), out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 0:
            reasons.append(f"wanted exit 0, got {proc.returncode}")
        path = os.path.join(out, "verify-m1.txt")
        if not os.path.isfile(path):
            reasons.append("missing verify-m1.txt")
        else:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            if not lines or lines[0] != "exit=0":
                reasons.append(f"verify-m1.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=0'")
            if len(lines) < 3 or lines[2] != "a\ufffdb":
                reasons.append(f"verify-m1.txt line 3 was {lines[2] if len(lines) >= 3 else None!r}, wanted 'a\\ufffdb'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)
        if repo:
            shutil.rmtree(repo, ignore_errors=True)


def test_run_symlink():
    name = "run replaces a symlinked verify file and leaves its target alone"
    RAN.append(name)
    d = tempfile.mkdtemp()
    repo = None
    try:
        repo = make_repo()
        target = os.path.join(d, "target")
        new_target = os.path.join(d, "new")
        out = os.path.join(d, "out")
        with open(target, "w") as f:
            f.write("keep")
        os.mkdir(out)
        m1_path = os.path.join(out, "verify-m1.txt")
        m2_path = os.path.join(out, "verify-m2.txt")
        os.symlink(target, m1_path)
        os.symlink(new_target, m2_path)
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 0:
            reasons.append(f"wanted exit 0, got {proc.returncode}")
        if not os.path.isfile(target):
            reasons.append("target is missing")
        else:
            with open(target) as f:
                target_content = f.read()
            if target_content != "keep":
                reasons.append(f"target content was {target_content!r}, wanted 'keep'")
        if os.path.exists(new_target):
            reasons.append(f"dangling link target {new_target} was created")
        for mid, path in (("m1", m1_path), ("m2", m2_path)):
            if os.path.islink(path):
                reasons.append(f"verify-{mid}.txt is still a symlink")
            if not os.path.isfile(path):
                reasons.append(f"missing verify-{mid}.txt")
            else:
                lines = read_lines(path)
                if not lines or lines[0] != "exit=0":
                    reasons.append(f"verify-{mid}.txt line 1 was {lines[0] if lines else None!r}, wanted 'exit=0'")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(d, ignore_errors=True)
        if repo:
            shutil.rmtree(repo, ignore_errors=True)


def test_run_mode():
    name = "run writes proof files with the umask's default mode"
    RAN.append(name)
    reasons = []
    repo = make_repo()
    try:
        for umask, wanted in ((0o022, 0o644), (0o027, 0o640)):
            d = tempfile.mkdtemp()
            try:
                out = os.path.join(d, "out")
                proc, err = run_proof("run", f"{BRIEFS}/pass.md", out, umask=umask, cwd=repo)
                if err:
                    FAILS.append(f"{name}: {err}")
                    return
                if proc.returncode != 0:
                    reasons.append(f"umask {umask:03o}: wanted exit 0, got {proc.returncode}")
                    continue
                path = os.path.join(out, "verify-m1.txt")
                if not os.path.isfile(path):
                    reasons.append(f"umask {umask:03o}: missing verify-m1.txt")
                    continue
                mode = stat.S_IMODE(os.stat(path).st_mode)
                if mode != wanted:
                    reasons.append(f"umask {umask:03o}: mode was {oct(mode)}, wanted {oct(wanted)}")
            finally:
                shutil.rmtree(d, ignore_errors=True)
    finally:
        shutil.rmtree(repo, ignore_errors=True)
    if reasons:
        FAILS.append(f"{name}: {'; '.join(reasons)}")


def test_run_broken():
    name = "run on broken.md exits 2 and writes nothing"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/broken.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 2:
            reasons.append(f"wanted exit 2, got {proc.returncode}")
        entries = os.listdir(out)
        if entries:
            reasons.append(f"wanted empty out dir, found {entries!r}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_round_trip():
    name = "round trip run then check on pass.md exits 0"
    RAN.append(name)
    out = tempfile.mkdtemp()
    repo = None
    try:
        repo = make_repo()
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
    finally:
        shutil.rmtree(out, ignore_errors=True)
        if repo:
            shutil.rmtree(repo, ignore_errors=True)


def test_check_extra_file():
    name = "check passes with an extra verify file for an unknown id"
    RAN.append(name)
    out = tempfile.mkdtemp()
    repo = None
    try:
        repo = make_repo()
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        with open(os.path.join(out, "verify-zz.txt"), "w") as f:
            f.write("exit=0\ncmd: true\n")
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
    finally:
        shutil.rmtree(out, ignore_errors=True)
        if repo:
            shutil.rmtree(repo, ignore_errors=True)


def test_check_none():
    name = "check on none.md with empty out dir exits 0"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("check", f"{BRIEFS}/none.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def check_m1_failure(proc, line_parts):
    reasons = []
    if proc.returncode != 1:
        reasons.append(f"wanted exit 1, got {proc.returncode}")
    lines = proc.stdout.splitlines()
    fail_lines = [line for line in lines if line.startswith("FAIL m1:")]
    if not fail_lines:
        reasons.append("wanted stdout line starting with 'FAIL m1:'")
    else:
        for part in line_parts:
            if part not in fail_lines[0]:
                reasons.append(f"wanted {part!r} in {fail_lines[0]!r}")
    non_empty = [line for line in lines if line.strip()]
    last = non_empty[-1] if non_empty else ""
    if not (last.startswith("FAIL proof:") and "m1" in last):
        reasons.append(f"wanted final line starting with 'FAIL proof:' containing 'm1', got {last!r}")
    return reasons


def test_check_invalid_brief(brief_name):
    name = f"check on {brief_name} exits 2 with FAIL brief and no proof lines"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        with open(os.path.join(out, "verify-m1.txt"), "w") as f:
            f.write("exit=0\ncmd: true\n")
        proc, err = run_proof("check", f"{BRIEFS}/{brief_name}", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 2:
            reasons.append(f"wanted exit 2, got {proc.returncode}")
        lines = proc.stdout.splitlines()
        if not any(line.startswith("FAIL brief:") for line in lines):
            reasons.append("wanted stdout line starting with 'FAIL brief:'")
        bad = [line for line in lines if line.startswith(("PASS m", "FAIL m", "PASS proof:", "FAIL proof:"))]
        if bad:
            reasons.append(f"unexpected proof lines: {bad!r}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_check_tampered(name, mutate, line_parts=()):
    RAN.append(name)
    out = tempfile.mkdtemp()
    repo = None
    try:
        repo = make_repo()
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        target = os.path.join(out, "verify-m1.txt")
        if not os.path.isfile(target):
            FAILS.append(f"{name}: setup did not create verify-m1.txt")
            return
        mutate(target)
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", out, cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = check_m1_failure(proc, line_parts)
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)
        if repo:
            shutil.rmtree(repo, ignore_errors=True)


def test_check_no_pycache():
    name = "check writes no __pycache__"
    RAN.append(name)
    tmp = tempfile.mkdtemp()
    try:
        copy = os.path.join(tmp, "check")
        out = os.path.join(tmp, "out")
        os.mkdir(out)
        shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
        copied_proof = os.path.join(copy, "proof.py")
        if not os.path.isfile(copied_proof):
            FAILS.append(f"{name}: missing {PROOF}")
            return
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        proc = subprocess.run(
            [sys.executable, copied_proof, "check", f"{BRIEFS}/none.md", out],
            cwd=OUTCOME,
            env=env,
            capture_output=True,
            text=True,
        )
        reasons = []
        if proc.returncode != 0:
            reasons.append(f"wanted exit 0, got {proc.returncode}")
        caches = [
            os.path.join(root, d)
            for root, dirs, _ in os.walk(copy)
            for d in dirs
            if d == "__pycache__"
        ]
        if caches:
            reasons.append(f"wrote __pycache__: {caches!r}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_check_empty_dir():
    name = "check on pass.md with empty out dir exits 1"
    RAN.append(name)
    out = tempfile.mkdtemp()
    try:
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", out)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = check_m1_failure(proc, ("verify-m1.txt", "no file", "expected", "exit=0", "cmd: true"))
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_proof_source():
    name = "proof.py imports check_brief and does not copy parse or regexes"
    RAN.append(name)
    if not os.path.isfile(PROOF):
        FAILS.append(f"{name}: missing {PROOF}")
        return
    with open(PROOF) as f:
        src = f.read()
    reasons = []
    if not re.search(r"^(from check_brief import|import check_brief)", src, re.M):
        reasons.append("missing check_brief import")
    if re.search(r"^def parse\(", src, re.M):
        reasons.append("defines def parse(")
    m = re.search(r"^(RULE_ID|VERIFY_ID|BACKTICK_CMD|SLOT) =", src, re.M)
    if m:
        reasons.append(f"defines {m.group(1)} =")
    if "BACKTICK_CMD" not in src:
        reasons.append("missing BACKTICK_CMD")
    for line in src.splitlines():
        if re.search(r"re\.compile\(.*`", line):
            reasons.append(f"compiles backtick regex: {line.strip()!r}")
    if reasons:
        FAILS.append(f"{name}: {'; '.join(reasons)}")


def test_git_clean_ignored_and_outdir_in_repo():
    name = "run and check pass in clean repo with gitignored file and in-repo out dir"
    RAN.append(name)
    repo = make_repo(extra_files={".gitignore": "ign\n"})
    try:
        head = git_head(repo)
        with open(os.path.join(repo, "ign"), "w") as f:
            f.write("ignored\n")
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 0:
            reasons.append(f"run wanted exit 0, got {proc.returncode}")
        summary_path = os.path.join(repo, "out", "proof-summary.txt")
        if not os.path.isfile(summary_path):
            reasons.append("missing proof-summary.txt")
        else:
            lines = read_lines(summary_path)
            if f"sha={head}" not in lines:
                reasons.append(f"proof-summary.txt missing sha={head}")
            if "dirty=no" not in lines:
                reasons.append("proof-summary.txt missing dirty=no")
            non_empty = [line for line in lines if line.strip()]
            last = non_empty[-1] if non_empty else ""
            wanted_last = f"VERIFY: PASS sha={head}"
            if last != wanted_last:
                reasons.append(f"proof-summary.txt last line was {last!r}, wanted {wanted_last!r}")
        m2_path = os.path.join(repo, "out", "verify-m2.txt")
        if not os.path.isfile(m2_path):
            reasons.append("missing verify-m2.txt")
        else:
            m2 = read_lines(m2_path)
            if len(m2) < 1 or m2[0] != "exit=0":
                reasons.append(f"verify-m2.txt line 1 was {m2[0] if m2 else None!r}, wanted 'exit=0'")
            if len(m2) < 2 or m2[1] != "cmd: echo ok":
                reasons.append(f"verify-m2.txt line 2 was {m2[1] if len(m2) >= 2 else None!r}, wanted 'cmd: echo ok'")
            if len(m2) < 3 or m2[2] != "ok":
                reasons.append(f"verify-m2.txt line 3 was {m2[2] if len(m2) >= 3 else None!r}, wanted 'ok'")
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            reasons.append(f"check wanted exit 0, got {proc.returncode}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_git_dirty_after_verify():
    name = "run exits 1 with dirty=yes when a verify command leaves an untracked file"
    RAN.append(name)
    brief_text = read_pass_brief().replace(
        "test -f check/fixtures/proof/briefs/demo/pass.md",
        "touch made",
    )
    repo = make_repo(brief_text=brief_text)
    try:
        head = git_head(repo)
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 1:
            reasons.append(f"wanted exit 1, got {proc.returncode}")
        summary_path = os.path.join(repo, "out", "proof-summary.txt")
        if not os.path.isfile(summary_path):
            reasons.append("missing proof-summary.txt")
        else:
            lines = read_lines(summary_path)
            if "dirty=yes" not in lines:
                reasons.append("proof-summary.txt missing dirty=yes")
            non_empty = [line for line in lines if line.strip()]
            last = non_empty[-1] if non_empty else ""
            wanted_last = f"VERIFY: FAIL sha={head}"
            if last != wanted_last:
                reasons.append(f"proof-summary.txt last line was {last!r}, wanted {wanted_last!r}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_git_check_missing_summary():
    name = "check exits 1 when proof-summary.txt is missing"
    RAN.append(name)
    repo = make_repo()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        summary_path = os.path.join(repo, "out", "proof-summary.txt")
        if os.path.exists(summary_path):
            os.remove(summary_path)
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 1:
            FAILS.append(f"{name}: wanted exit 1, got {proc.returncode}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_git_check_dirty_clean_and_moved_head():
    name = "check rejects dirty tree, passes when clean at same HEAD, rejects moved HEAD"
    RAN.append(name)
    repo = make_repo()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        reasons = []
        junk = os.path.join(repo, "junk")
        with open(junk, "w") as f:
            f.write("dirty\n")
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 1:
            reasons.append(f"dirty tree: wanted exit 1, got {proc.returncode}")
        os.remove(junk)
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            reasons.append(f"cleaned tree: wanted exit 0, got {proc.returncode}")
        git(repo, "commit", "-q", "--allow-empty", "-m", "move")
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 1:
            reasons.append(f"moved HEAD: wanted exit 1, got {proc.returncode}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_git_check_summary_missing_sha_line():
    name = "check exits 1 when sha= line is removed from proof-summary.txt"
    RAN.append(name)
    repo = make_repo()
    try:
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            FAILS.append(f"{name}: setup run exited {proc.returncode}")
            return
        summary_path = os.path.join(repo, "out", "proof-summary.txt")
        if not os.path.isfile(summary_path):
            FAILS.append(f"{name}: setup did not create proof-summary.txt")
            return
        lines = [line for line in read_lines(summary_path) if not line.startswith("sha=")]
        with open(summary_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        proc, err = run_proof("check", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 1:
            FAILS.append(f"{name}: wanted exit 1, got {proc.returncode}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_not_git_repo():
    name = "run and check exit 2 outside a git repo and run writes no proof files"
    RAN.append(name)
    d = tempfile.mkdtemp()
    try:
        brief_dir = os.path.join(d, "briefs", "demo")
        os.makedirs(brief_dir, exist_ok=True)
        with open(os.path.join(d, "briefs", "WORKSTREAMS"), "w") as f:
            f.write("demo\n")
        shutil.copyfile(os.path.join(OUTCOME, BRIEFS, "pass.md"), os.path.join(brief_dir, "b.md"))
        out = os.path.join(d, "out")
        proc, err = run_proof("run", "briefs/demo/b.md", "out", cwd=d)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 2:
            reasons.append(f"run wanted exit 2, got {proc.returncode}")
        combined = proc.stdout + proc.stderr
        if "git" not in combined.lower():
            reasons.append(f"run output did not name git: {combined!r}")
        if os.path.exists(out) and os.listdir(out):
            reasons.append(f"run wrote files in out dir: {os.listdir(out)!r}")
        proc, err = run_proof("check", "briefs/demo/b.md", "out", cwd=d)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 2:
            reasons.append(f"check wanted exit 2, got {proc.returncode}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_git_head_moved_during_run():
    name = "run exits 1 with starting sha when a verify command moves HEAD"
    RAN.append(name)
    brief_text = read_pass_brief().replace(
        "test -f check/fixtures/proof/briefs/demo/pass.md",
        "git commit -q --allow-empty -m moved",
    )
    repo = make_repo(brief_text=brief_text)
    try:
        head = git_head(repo)
        proc, err = run_proof("run", f"{BRIEFS}/pass.md", "out", cwd=repo)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 1:
            reasons.append(f"wanted exit 1, got {proc.returncode}")
        if git_head(repo) == head:
            reasons.append("verify command did not move HEAD")
        summary_path = os.path.join(repo, "out", "proof-summary.txt")
        if not os.path.isfile(summary_path):
            reasons.append("missing proof-summary.txt")
        else:
            lines = read_lines(summary_path)
            if f"sha={head}" not in lines:
                reasons.append(f"proof-summary.txt missing sha={head}")
            non_empty = [line for line in lines if line.strip()]
            last = non_empty[-1] if non_empty else ""
            wanted_last = f"VERIFY: FAIL sha={head}"
            if last != wanted_last:
                reasons.append(f"proof-summary.txt last line was {last!r}, wanted {wanted_last!r}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_git_subdir_outdir_in_repo():
    name = "run and check pass from a subdirectory with an in-repo out dir"
    RAN.append(name)
    brief_text = read_pass_brief().replace(
        "test -f check/fixtures/proof/briefs/demo/pass.md",
        "test -f ../check/fixtures/proof/briefs/demo/pass.md",
    )
    repo = make_repo(brief_text=brief_text, extra_files={"sub/keep": "ok\n"})
    try:
        head = git_head(repo)
        sub = os.path.join(repo, "sub")
        brief = f"../{BRIEFS}/pass.md"
        proc, err = run_proof("run", brief, "out", cwd=sub)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        reasons = []
        if proc.returncode != 0:
            reasons.append(f"run wanted exit 0, got {proc.returncode}")
        summary_path = os.path.join(sub, "out", "proof-summary.txt")
        if not os.path.isfile(summary_path):
            reasons.append("missing proof-summary.txt")
        else:
            lines = read_lines(summary_path)
            if f"sha={head}" not in lines:
                reasons.append(f"proof-summary.txt missing sha={head}")
            if "dirty=no" not in lines:
                reasons.append("proof-summary.txt missing dirty=no")
            non_empty = [line for line in lines if line.strip()]
            last = non_empty[-1] if non_empty else ""
            wanted_last = f"VERIFY: PASS sha={head}"
            if last != wanted_last:
                reasons.append(f"proof-summary.txt last line was {last!r}, wanted {wanted_last!r}")
        proc, err = run_proof("check", brief, "out", cwd=sub)
        if err:
            FAILS.append(f"{name}: {err}")
            return
        if proc.returncode != 0:
            reasons.append(f"check wanted exit 0, got {proc.returncode}")
        if reasons:
            FAILS.append(f"{name}: {'; '.join(reasons)}")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


test_run_pass()
test_run_fail()
test_run_slow()
test_run_child()
test_run_binary()
test_run_symlink()
test_run_mode()
test_run_broken()
test_round_trip()
test_check_extra_file()
test_check_none()
test_check_invalid_brief("broken.md")
test_check_invalid_brief("empty.md")
test_check_tampered(
    "check fails when verify-m1.txt is deleted",
    os.remove,
    line_parts=("verify-m1.txt", "no file", "expected", "exit=0", "cmd: true"),
)
test_check_tampered(
    "check fails when line 1 is exit=1",
    lambda p: set_line(p, 0, "exit=1"),
    line_parts=("verify-m1.txt", "line 1", "expected exit=0"),
)
test_check_tampered(
    "check fails when line 1 is removed",
    drop_first_line,
    line_parts=("verify-m1.txt", "line 1", "expected exit=<integer>"),
)
test_check_tampered(
    "check fails when line 2 is cmd: old",
    lambda p: set_line(p, 1, "cmd: old"),
    line_parts=("verify-m1.txt", "line 2", "expected cmd: true"),
)
test_check_empty_dir()
test_check_no_pycache()
test_proof_source()
test_git_clean_ignored_and_outdir_in_repo()
test_git_dirty_after_verify()
test_git_check_missing_summary()
test_git_check_dirty_clean_and_moved_head()
test_git_check_summary_missing_sha_line()
test_not_git_repo()
test_git_head_moved_during_run()
test_git_subdir_outdir_in_repo()

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
