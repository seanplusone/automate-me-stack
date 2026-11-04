"""Labels every changed file of each PR as source, test, generated, asset or docs.

Usage: python3 check/classify.py <owner/repo#n> [<owner/repo#n> ...] --out <dir>/classes.json
Writes {"<owner/repo#n>": {"head": "<sha>", "files": {"<path>": "<label>"}}} and prints one
summary line per PR. The line goes into the PR's `Changes:` line in drafts.md.
"""
import json
import os
import re
import subprocess
import sys

# A build hash has a digit or mixed case, so `form-settings.js` is not one.
HASHED = re.compile(r"-(?:(?=[\w-]{0,7}\d)|(?=[\w-]{0,7}[A-Z])(?=[\w-]{0,7}[a-z]))[\w-]{8}\.[a-z0-9]+$")
ASSET_EXT = {"png", "jpg", "jpeg", "gif", "svg", "webp", "ico", "woff", "woff2", "ttf", "eot", "pdf"}
DOC_EXT = {"md", "rst", "txt"}
TEST_DIRS = {"tests", "test", "__tests__"}
TEST_NAME = re.compile(r"(Test\.php|\.test\.tsx?|\.spec\.tsx?|_test\.py)$|^test_.*\.py$")
LONG_LINE = 1000
READ_CAP = 2 * 1024 * 1024
ORDER = ["source", "test", "generated", "asset", "docs"]


def label(path, longest_line=None, binary=False):
    """The class of one path. longest_line is the longest line at the head of a text file, if read."""
    name = path.rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if HASHED.search(name) or name.endswith((".gz", ".map")) or (longest_line or 0) > LONG_LINE:
        return "generated"
    if binary or ext in ASSET_EXT:
        return "asset"
    if TEST_DIRS & set(path.split("/")[:-1]) or TEST_NAME.search(name):
        return "test"
    if ext in DOC_EXT:
        return "docs"
    return "source"


def summary(pr, files):
    """The one-line summary for a PR: '<pr>: <N> files: <a> source, ...' with zero counts left out."""
    counts = {k: sum(1 for v in files.values() if v == k) for k in ORDER}
    parts = ", ".join(f"{counts[k]} {k}" for k in ORDER if counts[k])
    return f"{pr}: {len(files)} files: {parts}" if parts else f"{pr}: 0 files"


def head_of(repo, path, head):
    """The first READ_CAP bytes of a file at the PR head, or None when it cannot be read."""
    proc = subprocess.Popen(["gh", "api", f"repos/{repo}/contents/{path}?ref={head}", "-H", "Accept: application/vnd.github.raw"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    data = proc.stdout.read(READ_CAP)
    capped = len(data) == READ_CAP
    proc.kill()
    proc.wait()
    proc.stdout.close()
    return data if data and (capped or proc.returncode == 0) else None


def longest_line(data):
    return max((len(x) for x in data.split(b"\n")), default=0)


def classify(pr):
    repo, _, num = pr.partition("#")
    view = json.loads(subprocess.run(["gh", "pr", "view", num, "-R", repo, "--json", "files,headRefOid"],
                                     capture_output=True, text=True, check=True).stdout)
    head, files = view["headRefOid"], {}
    for f in view["files"]:
        path = f["path"]
        first = label(path)
        if first in ("generated", "asset") or f.get("changeType") == "DELETED":
            files[path] = first
            continue
        data = head_of(repo, path, head)
        binary = data is not None and b"\0" in data[:8192]
        files[path] = label(path, longest_line(data) if data and not binary else None, binary)
    return {"head": head, "files": files}


def main(argv):
    if "--out" not in argv:
        sys.exit("usage: classify.py <owner/repo#n> [...] --out <dir>/classes.json")
    out = argv[argv.index("--out") + 1]
    prs = [a for a in argv[1:] if "#" in a]
    result = {}
    for pr in prs:
        result[pr] = classify(pr)
        print(summary(pr, result[pr]["files"]))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(result, open(out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 1)
    sys.exit(main(sys.argv))
