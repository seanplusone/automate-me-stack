"""Finds what a moved or copied file is missing from its source.

Picks the source version the copy is closest to, then lists every line the source gained after it
that the copy lacks, with the commits that added them.

Usage: python3 moved_drift.py <source repo dir> <ref:path> <copy file> [--rename OLD=NEW ...]
  e.g. python3 moved_drift.py ../web-app origin/main:.claude/skills/release-notes/SKILL.md \
           /tmp/pr/plugins/team/skills/release-notes/SKILL.md --rename /release-notes=/team:release-notes
Exits 1 when the copy is missing lines.
"""
import difflib
import re
import subprocess
import sys


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def norm(line, renames):
    for old, new in renames:
        line = line.replace(old, new)
    line = re.sub(r"\]\([^)]*\)", "]", line)
    return re.sub(r"\s+", " ", line).strip()


def lines(text, renames):
    return [n for n in (norm(l, renames) for l in text.splitlines()) if n]


def drift(repo, ref, path, copy_text, renames):
    """Returns (base sha, [(sha, subject)] after base, [missing lines])."""
    copy = lines(copy_text, renames)
    best = None
    for sha in git(repo, "log", "--format=%H", ref, "--", path).split():
        try:
            version = lines(git(repo, "show", f"{sha}:{path}"), renames)
        except subprocess.CalledProcessError:
            continue
        distance = sum(1 for d in difflib.ndiff(version, copy) if d[:1] in "+-")
        if best is None or distance < best[1]:
            best = (sha, distance)
    if best is None:
        sys.exit(f"{ref}:{path} has no history in {repo}")
    base = best[0]
    commits = [l.split(" ", 1) for l in git(repo, "log", "--format=%h %s", f"{base}..{ref}", "--", path).splitlines()]
    have = set(copy)
    added = [l[1:] for l in git(repo, "diff", base, ref, "--", path).splitlines()
             if l.startswith("+") and not l.startswith("+++")]
    missing = [n for n in (norm(l, renames) for l in added) if n and n not in have]
    return base, commits, missing


def main(argv):
    renames, args = [], []
    it = iter(argv)
    for a in it:
        if a == "--rename":
            old, _, new = next(it).partition("=")
            renames.append((old, new))
        else:
            args.append(a)
    if len(args) != 3 or ":" not in args[1]:
        sys.exit(__doc__)
    repo, refpath, copy_path = args
    ref, path = refpath.split(":", 1)
    base, commits, missing = drift(repo, ref, path, open(copy_path).read(), renames)
    print(f"copy matches {path} at {base[:7]}; {len(commits)} commit(s) since, {len(missing)} line(s) missing")
    for sha, subject in commits:
        print(f"  {sha} {subject}")
    for m in missing:
        print(f"  missing: {m[:120]}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
