"""Run: python3 shared/test_client_sweep.py"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client_sweep import main, sweep  # noqa: E402

FAILS = []
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]


def expect(name, ok, got):
    if not ok:
        FAILS.append(f"{name}: {got}")


def repo(root, name, files):
    path = os.path.join(root, name)
    os.makedirs(path)
    for rel, body in files.items():
        full = os.path.join(path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(body)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(GIT + ["commit", "-q", "-m", "base"], cwd=path, check=True)
    subprocess.run(["git", "update-ref", "refs/remotes/upstream/master", "HEAD"], cwd=path, check=True)
    return path


with tempfile.TemporaryDirectory() as root:
    web = repo(root, "web", {
        "app/Exporter.php": "$row['receipt_url'] = null;",
        "app/SaveHook.php": "if(preg_match('/_url$/', $key)) { copy($value); }",
    })
    mobile = repo(root, "mobile", {
        "src/form.ts": "for (const leaf of orderDraft) { valueMap[leaf.path] = leaf.data; }",
        "src/upload.ts": "const suffix = '_url'; valueMap[path + suffix] = file;",
        "assets/schema.json": '{"receipt_url": null}',
    })
    # A change on the checked-out branch that the base branch does not have.
    subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=web, check=True)
    with open(os.path.join(web, "app/Feature.php"), "w") as f:
        f.write("$row['receipt_url'] = 'x';")
    subprocess.run(["git", "add", "."], cwd=web, check=True)
    subprocess.run(GIT + ["commit", "-q", "-m", "feature"], cwd=web, check=True)

    broken = os.path.join(root, "broken")
    os.makedirs(broken)
    with open(os.path.join(broken, ".git"), "w") as f:
        f.write("gitdir: /nowhere\n")

    repos = {"web": web, "mobile": mobile, "gone": os.path.join(root, "gone"), "broken": broken}
    markers = ["_url$", "'_url'", '"_url"']
    patterns = [("key", "receipt_url")] + [("marker", m) for m in markers]
    report, failed = sweep(repos, patterns, "draft")
    text = "\n".join(report)

    expect("key found by name", "web key 'receipt_url': 1 files" in text, text)
    expect("searches the base branch, not the checkout", "app/Feature.php" not in text and "web at upstream/master" in text, text)
    expect("generic save hook found by shape", "app/SaveHook.php" in text, text)
    expect("runtime-built _url key found", "mobile marker \"'_url'\": 1 files" in text, text)
    expect("carrier flagged even when an asset names the key", "CHECK mobile" in text and "src/form.ts" in text, text)
    expect("repo without the carrier is not flagged", "CHECK web" not in text, text)
    expect("missing checkout is reported, not silent", "gone" in failed and "MISSING gone" in text, text)
    expect("failed search is reported, not read as 0 files", "broken" in failed and "ERROR broken" in text, text)



def run_main(argv):
    with contextlib.redirect_stderr(io.StringIO()):
        return main(argv)


# --repo is required: there are no default repos to fall back on.
try:
    run_main(["receipt_url"])
    expect("--repo is required", False, "main ran without --repo")
except SystemExit as exit_:
    expect("--repo is required", exit_.code == 2, exit_.code)
try:
    run_main(["receipt_url", "--repo", "web"])
    expect("--repo needs NAME=PATH", False, "accepted --repo without =PATH")
except SystemExit as exit_:
    expect("--repo needs NAME=PATH", exit_.code == 2, exit_.code)

if FAILS:
    print("\n".join(FAILS))
    sys.exit(1)
print("PASS test_client_sweep")
