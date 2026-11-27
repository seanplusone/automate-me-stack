"""Run: python3 check/test_check_signoff.py"""
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIGNOFF = HERE / "check_signoff.py"
CHECK_BRIEF = HERE / "check_brief.py"
PROOF = HERE / "proof.py"
FIXTURE = HERE / "fixtures/proof/briefs/demo/pass.md"
BRIEF = "briefs/demo/b.md"
SIGNATURE = "- Signed-off: Pat, 2026-11-27, via chat message 42, sha256="
FAILS = []


def git(repo, *args):
    subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True, timeout=20,
    )


def commit(repo):
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
        "commit", "-qm", "init")


def make_repo(repo):
    git(repo, "init", "-q")
    brief = repo / BRIEF
    brief.parent.mkdir(parents=True)
    (repo / "briefs/WORKSTREAMS").write_text("demo\n")
    content = re.sub(r"^- Signed-off:.*\n?", "", FIXTURE.read_text(), flags=re.M)
    brief.write_text(re.sub(r"test -f [^ `]*md", "true", content))
    (repo / ".gitignore").write_text("out/\n")


def run(repo, script, *args):
    if not script.is_file():
        raise AssertionError(f"missing script {script.name}")
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=repo, capture_output=True, text=True, errors="replace", timeout=20,
    )


def expect(repo, script, *args, code=0, stop=False):
    proc = run(repo, script, *args)
    output = proc.stdout + proc.stderr
    if proc.returncode != code or (stop and "STOP" not in output) or "Traceback" in output:
        expected = f"exit {code}" + (" with STOP" if stop else "")
        raise AssertionError(
            f"{script.name} {' '.join(args)} wanted {expected} without a traceback, "
            f"got exit {proc.returncode}: {output.strip()!r}"
        )
    return proc.stdout


def brief_hash(repo):
    output = expect(repo, SIGNOFF, "hash", BRIEF)
    if not re.fullmatch(r"[0-9a-f]{64}\n?", output):
        raise AssertionError(f"wanted one line of 64 lowercase hex characters, got {output!r}")
    return output.rstrip("\n")


def sign(repo, digest=None):
    digest = brief_hash(repo) if digest is None else digest
    brief = repo / BRIEF
    brief.write_text(brief.read_text().rstrip("\n") + "\n" + SIGNATURE + digest + "\n")
    return digest


def replace(repo, old, new):
    brief = repo / BRIEF
    content = brief.read_text()
    if old not in content:
        raise AssertionError(f"fixture missing {old!r} before edit")
    brief.write_text(content.replace(old, new, 1))


def expect_proof_rejected(repo):
    commit(repo)
    expect(repo, PROOF, "run", BRIEF, "out", code=2)
    expect(repo, PROOF, "check", BRIEF, "out", code=2)
    out = repo / "out"
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise AssertionError("rejected brief left proof output in out/")


def test_hash(repo):
    items = [
        "[m1] Adding a book writes a new entry to books.json.",
        "[m2] Listing books prints each saved title on its own line.",
        "[m3] Marking a book finished updates its status to done.",
    ]
    expected = hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()
    first, second = brief_hash(repo), brief_hash(repo)
    if first != second:
        raise AssertionError(f"hash changed between calls: {first} != {second}")
    if first != expected:
        raise AssertionError(f"wanted SHA-256 of the Must-haves items {expected}, got {first}")


def test_unsigned(repo):
    expect_proof_rejected(repo)
    expect(repo, SIGNOFF, BRIEF, code=2, stop=True)


def test_signed(repo):
    sign(repo)
    commit(repo)
    expect(repo, SIGNOFF, BRIEF)
    expect(repo, PROOF, "run", BRIEF, "out")
    expect(repo, PROOF, "check", BRIEF, "out")


def test_edited_must_have(repo):
    sign(repo)
    replace(repo, "Adding a book writes a new entry", "Adding a book may write an entry")
    expect(repo, SIGNOFF, BRIEF, code=2, stop=True)
    expect_proof_rejected(repo)


def test_edited_verify(repo):
    sign(repo)
    replace(repo, "  - m2: `echo ok`", "  - m2: `echo changed`")
    expect(repo, SIGNOFF, BRIEF)


def test_edited_goal(repo):
    sign(repo)
    replace(repo, "marks them finished.\n", "marks them finished today.\n")
    expect(repo, SIGNOFF, BRIEF)


def test_wrong_hash(repo):
    sign(repo, "0" * 64)
    expect(repo, SIGNOFF, BRIEF, code=2, stop=True)


def test_signed_off_format(repo):
    digest = sign(repo)
    expect(repo, CHECK_BRIEF, BRIEF)
    for bad in ("nothex", digest[:-1]):
        replace(repo, SIGNATURE + digest, SIGNATURE + bad)
        proc = run(repo, CHECK_BRIEF, BRIEF)
        if proc.returncode <= 0 or "Traceback" in proc.stdout + proc.stderr:
            raise AssertionError(f"check_brief.py should reject sha256={bad} without a traceback")
        replace(repo, SIGNATURE + bad, SIGNATURE + digest)


def test_missing_must_haves(repo):
    sign(repo)
    brief = repo / BRIEF
    content, removed = re.subn(r"^- Must-haves:[^\n]*\n(?:^[ \t]+[^\n]*\n)*", "",
                               brief.read_text(), count=1, flags=re.M)
    if removed != 1:
        raise AssertionError("fixture missing Must-haves block before edit")
    brief.write_text(content)
    expect(repo, SIGNOFF, BRIEF, code=2, stop=True)


if __name__ == "__main__":
    cases = (
        test_hash, test_unsigned, test_signed, test_edited_must_have, test_edited_verify,
        test_edited_goal, test_wrong_hash, test_signed_off_format, test_missing_must_haves,
    )
    for case in cases:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                make_repo(repo)
                case(repo)
        except (AssertionError, OSError, subprocess.SubprocessError) as err:
            reason = getattr(err, "stderr", None) or str(err)
            FAILS.append(f"{case.__name__}: {reason.strip()}")
    for failure in FAILS:
        print(f"FAIL {failure}")
    print(f"{len(cases) - len(FAILS)}/{len(cases)} passed")
    sys.exit(1 if FAILS else 0)
