"""Run: python3 check/test_moved_drift.py"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from moved_drift import drift  # noqa: E402

passed = failed = 0


def expect(name, ok):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {name}")


def commit(repo, text, msg):
    with open(os.path.join(repo, "SKILL.md"), "w") as f:
        f.write(text)
    subprocess.run(["git", "-C", repo, "add", "SKILL.md"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", msg], check=True)


with tempfile.TemporaryDirectory() as repo:
    subprocess.run(["git", "init", "-q", repo], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.name", "t"], check=True)
    v1 = "# skill\nRun `/review` first.\nSee [the plan](../../docs/plan.md).\n"
    commit(repo, v1, "v1")
    commit(repo, v1 + "Check identity types.\n", "add identity check")
    commit(repo, v1 + "Check identity types.\nPin the patch release.\n", "add pin rule")

    copied_at_v1 = "# skill\nRun `/team:review` first.\nSee [the plan](web-app/docs/plan.md).\n"
    base, commits, missing = drift(repo, "HEAD", "SKILL.md", copied_at_v1, [("/review", "/team:review")])
    expect("finds the version the copy was taken from", len(commits) == 2)
    expect("lists every line added since", missing == ["Check identity types.", "Pin the patch release."])

    resynced = copied_at_v1 + "Check identity types.\nPin the patch release.\n"
    _, _, missing = drift(repo, "HEAD", "SKILL.md", resynced, [("/review", "/team:review")])
    expect("a re-synced copy is missing nothing", missing == [])

    _, _, missing = drift(repo, "HEAD", "SKILL.md", copied_at_v1, [])
    expect("lines already in the copied version are not drift", "Run `/review` first." not in missing)

print(f"{passed}/{passed + failed} passed")
sys.exit(1 if failed else 0)
