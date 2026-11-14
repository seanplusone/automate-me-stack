"""Tests for propose.py against cases/sample-project.

Run: python3 check/test_propose.py

Copies the fixture to a temp dir, makes it a git repo (same as test_detect.py), runs propose.py,
and checks that only the proposed profile is written, filled values are marked (unconfirmed),
and no fixture secret appears in the file.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
PROPOSE = os.path.join(SKILL, "propose.py")
FIXTURE = os.path.join(SKILL, "cases", "sample-project")
SECRETS = ["compose-fake-secret-123", "envfile-fake-secret-456", "envfile-fake-secret-789", "envfile-fake-secret-000",
           "mcp-fake-secret-aaa", "mcp-fake-secret-bbb", "remote-fake-secret", "pgservice-fake-secret"]
FAILS = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} {name}")
    if not ok:
        FAILS.append(name)
        if detail:
            print("    " + str(detail).replace("\n", "\n    "))


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "-c", "init.defaultBranch=main",
                    *args], cwd=cwd, check=True, capture_output=True, timeout=30)


tmp = tempfile.mkdtemp()
project = os.path.join(tmp, "demo-shop")
shutil.copytree(FIXTURE, project)
git(project, "init", "-q", "-b", "main")
git(project, "add", "-A")
git(project, "commit", "-q", "-m", "initial")
git(project, "remote", "add", "origin", "https://ci-user:remote-fake-secret@github.com/acme/demo-shop.git")
git(project, "update-ref", "refs/remotes/origin/main", "HEAD")
git(project, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

# A confirmed profile must be left untouched.
os.makedirs(os.path.join(project, ".claude"))
confirmed = os.path.join(project, ".claude", "project-profile.md")
open(confirmed, "w").write("- `base_branch`: `keep-me`\n")
before = open(confirmed).read()

env = {k: v for k, v in os.environ.items()}
r = subprocess.run([sys.executable, PROPOSE, project], capture_output=True, text=True, env=env, timeout=60)
check("exits 0", r.returncode == 0, r.stderr)
proposed = os.path.join(project, ".claude", "project-profile.proposed.md")
check("writes the proposed file", os.path.isfile(proposed), r.stdout)
check("does not change project-profile.md", open(confirmed).read() == before, open(confirmed).read())
check("stdout names the proposed path", proposed in r.stdout, r.stdout)

text = open(proposed).read() if os.path.isfile(proposed) else ""
for secret in SECRETS:
    if secret in text or secret in r.stdout + r.stderr:
        check(f"no secret {secret}", False, text)
        break
else:
    check("no fixture secret in the file or output", True)

check("base_branch is main and unconfirmed",
      "- `base_branch`: `main` (unconfirmed)" in text, text)
check("base_remote is origin and unconfirmed",
      "- `base_remote`: `origin` (unconfirmed)" in text, text)
check("tracker is GitHub Issues and unconfirmed",
      "- `tracker`: `GitHub Issues with gh` (unconfirmed)" in text, text)
check("app_url_test is a local url and unconfirmed",
      "- `app_url_test`: `" in text and "(unconfirmed)" in text[text.find("`app_url_test`"):text.find("`app_url_test`") + 80]
      and "localhost" in text, text)
check("test_full is filled and unconfirmed",
      "- `test_full`: `" in text and " (unconfirmed)" in text[text.find("`test_full`"):text.find("`test_full`") + 80], text)
check("ticket_url points at the repo issues and has no token",
      "- `ticket_url`: `https://github.com/acme/demo-shop/issues/<key>` (unconfirmed)" in text, text)
check("every filled value is marked unconfirmed",
      all("(unconfirmed)" in line for line in text.splitlines() if "`: `" in line and not line.strip().endswith(":")),
      text)
check("blank keys from the example are still present",
      "- `review_skill`:" in text and "- `second_model`:" in text, text)
# second_model may not be in the example yet when this test is written; if the profile
# was updated it should be present. The check above will fail if we forget the key.

if FAILS:
    print(f"{len(FAILS)} failed")
    sys.exit(1)
print("PASS test_propose")
