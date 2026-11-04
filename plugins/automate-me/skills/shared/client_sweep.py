"""Find every file in every client repo that reads a key, by name and by value shape.

A search for a key's name misses code that reads values by pattern, such as a save
hook that copies any key ending in `_url`, a client that builds that key at runtime,
and a client that walks the whole payload without naming any key, such as a mobile
app that replays a saved draft. This searches each repo's base branch for the keys,
the shape markers and the payload's carrier name. It flags every repo that handles
the carrier, and reports a repo it could not search, so a missing result never reads
as "nothing reads it".

Run: python3 shared/client_sweep.py <key> [<key> ...] --repo NAME=PATH [--repo NAME=PATH ...]
         [--marker TEXT ...] [--carrier TEXT]

  --repo     A client repo to search, as NAME=PATH to a git checkout. Required, repeat it
             once per repo: every web app, mobile app, worker and service that can read
             the key.
  --marker   Text that matches the value's shape rather than the key's name, such as
             the regex a save hook uses (`_url$`) or the suffix a client appends at
             runtime (`'_url'`). Repeat it. No markers by default.
  --carrier  The name client code uses for the payload the key travels in, such as
             `draft` or `formState`. Searched case-insensitively. None by default.

Exit 1 when a repo is missing or a search fails. Exit 2 on bad arguments.
"""
import argparse
import os
import subprocess
import sys

# Upstream first: in a fork-based workflow `origin` can be a stale fork.
BASE_REFS = ["upstream/master", "upstream/main", "origin/master", "origin/main"]
SHOWN = 8
# Analysis notes, docs and built bundles mention keys without being the code that reads them.
EXCLUDED = [":!.ai", ":!docs", ":!*.md", ":!*.min.js", ":!*.map", ":!*.bundle", ":!*.jsbundle"]


class SearchFailed(Exception):
    pass


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def base_ref(repo):
    for ref in BASE_REFS:
        if git(repo, "rev-parse", "-q", "--verify", ref).returncode == 0:
            return ref
    return "HEAD"


def grep(repo, ref, text, ignore_case=False):
    flags = ["-l", "-F"] + (["-i"] if ignore_case else [])
    out = git(repo, "grep", *flags, "-e", text, ref, "--", ".", *EXCLUDED)
    if out.returncode > 1:
        raise SearchFailed(out.stderr.strip())
    prefix = ref + ":"
    return [line[len(prefix):] if line.startswith(prefix) else line for line in out.stdout.splitlines() if line]


def listing(report, label, files):
    report.append(f"{label}: {len(files)} files")
    report.extend(f"  {f}" for f in files[:SHOWN])
    if len(files) > SHOWN:
        report.append(f"  ... {len(files) - SHOWN} more")


def sweep(repos, patterns, carrier=""):
    report, failed = [], []
    for name, path in repos.items():
        if not os.path.exists(os.path.join(path, ".git")):
            failed.append(name)
            report.append(f"MISSING {name}: no git checkout at {path}. Read it on GitHub before claiming no effect.")
            continue
        ref = base_ref(path)
        age = git(path, "log", "-1", "--format=%cr", ref).stdout.strip()
        report.append(f"== {name} at {ref} (last commit {age}, fetch first if that is old)")
        try:
            for kind, text in patterns:
                listing(report, f"{name} {kind} {text!r}", grep(path, ref, text))
            if carrier:
                carried = grep(path, ref, carrier, ignore_case=True)
                listing(report, f"{name} carrier {carrier!r}", carried)
                if carried:
                    report.append(
                        f"CHECK {name}: these files handle {carrier}. A key search cannot show whether they pass"
                        " every value through. Read what they send back before claiming no effect."
                    )
        except SearchFailed as error:
            failed.append(name)
            report.append(f"ERROR {name}: search failed ({error}). Treat this repo as unchecked.")
    return report, failed


def parse_repo(text):
    name, sep, path = text.partition("=")
    if not sep or not name or not path:
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got {text!r}")
    return name, os.path.expanduser(path)


def main(argv):
    parser = argparse.ArgumentParser(description="Find every client file that reads a key, by name and by value shape.")
    parser.add_argument("keys", nargs="+")
    parser.add_argument("--repo", action="append", type=parse_repo, required=True,
                        help="NAME=PATH of a client repo checkout; repeat once per repo")
    parser.add_argument("--marker", action="append", default=[], help="text matching the value's shape; repeatable")
    parser.add_argument("--carrier", default="", help="the payload's name in client code; omit or empty to skip")
    args = parser.parse_args(argv)
    repos = dict(args.repo)
    patterns = [("key", k) for k in args.keys] + [("marker", m) for m in args.marker]
    report, failed = sweep(repos, patterns, args.carrier)
    print("\n".join(report))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
