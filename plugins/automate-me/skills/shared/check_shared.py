"""Lint for the skills folder. Keeps shared/ usable by any skill, and keeps every relative path working after a move or rename.

Usage: python3 shared/check_shared.py [<skills dir>]

Fails when:
- a `../` path or markdown link in a skill's .md file does not resolve, from the file's folder or from its skill's folder;
- a file under shared/skills/ names a calling skill's folder;
- a shared/skills/<name>/SKILL.md has no description, or its name is not <name>;
- a command that runs a script (`python3`, `python`, `sh` or `bash` then a path ending in .py or .sh) does not write the path as "$SKILL_DIR"/<path>;
- that path, with $SKILL_DIR set to the file's skill folder, is not a file.
Practice cases and README.md files are skipped. A README.md is a maintainer doc that runs from the skills folder. Prints PASS or FAIL and exits 1 on FAIL.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_writing import FAILED, report  # noqa: E402

LINK = re.compile(r"\]\(([\w./-]+)(?:#[^)]*)?\)|`(\.\./[^`\s]+)`")
SCRIPT = re.compile(r"(?:^|[\s`(])(?:python3?|sh|bash)\s+(?:-\S+\s+)*([^\s`|;&)]+\.(?:py|sh))\b")
SKILL_DIR = re.compile(r'^"?\$SKILL_DIR"?/')


def skill_root(rel):
    parts = rel.split(os.sep)
    return os.sep.join(parts[:3] if parts[:2] == ["shared", "skills"] else parts[:1])


def check_paths(skills, files):
    fails = []
    for rel in files:
        here = os.path.dirname(os.path.join(skills, rel))
        root = os.path.join(skills, skill_root(rel))
        for n, line in enumerate(open(os.path.join(skills, rel)), 1):
            for m in LINK.finditer(line):
                p = m.group(1) or m.group(2)
                if not any(os.path.exists(os.path.join(d, p)) for d in (here, root)):
                    fails.append(f"{rel}:{n} path does not resolve: {p}")
    return fails


def check_script_paths(skills, files):
    fails = []
    for rel in files:
        if os.path.basename(rel) == "README.md":
            continue
        root = os.path.join(skills, skill_root(rel))
        for n, line in enumerate(open(os.path.join(skills, rel)), 1):
            for m in SCRIPT.finditer(line):
                p = m.group(1)
                if not SKILL_DIR.match(p):
                    fails.append(f'{rel}:{n} script path is not anchored: {p}. Write it as "$SKILL_DIR"/<path>')
                elif not os.path.isfile(os.path.join(root, SKILL_DIR.sub("", p))):
                    fails.append(f"{rel}:{n} script does not exist: {p}")
    return fails


def check_no_callers(skills, files):
    callers = sorted(d for d in os.listdir(skills) if os.path.isdir(os.path.join(skills, d)) and d != "shared")
    named = re.compile(r"(?<![\w-])(" + "|".join(map(re.escape, callers)) + r")(?![\w-])")
    fails = []
    for rel in files:
        if not rel.startswith(os.path.join("shared", "skills") + os.sep):
            continue
        for n, line in enumerate(open(os.path.join(skills, rel)), 1):
            for m in named.finditer(line):
                fails.append(f"{rel}:{n} names the calling skill {m.group(1)}. Say what the caller passes in, not who it is")
    return fails


def check_frontmatter(skills):
    fails = []
    for path in sorted(glob.glob(os.path.join(skills, "shared", "skills", "*", "SKILL.md"))):
        folder = os.path.basename(os.path.dirname(path))
        head = open(path).read().split("---")
        meta = head[1] if len(head) > 2 and not head[0].strip() else ""
        name = re.search(r"^name:\s*(\S+)", meta, re.M)
        if not name or name.group(1) != folder:
            fails.append(f"shared/skills/{folder}/SKILL.md name is not {folder}")
        if not re.search(r"^description:\s*\S", meta, re.M):
            fails.append(f"shared/skills/{folder}/SKILL.md has no description")
    return fails


def check_shared(skills):
    files = sorted(os.path.relpath(f, skills) for f in glob.glob(os.path.join(skills, "**", "*.md"), recursive=True)
                   if f"{os.sep}cases{os.sep}" not in f)
    fails = check_paths(skills, files) + check_script_paths(skills, files) + check_no_callers(skills, files) + check_frontmatter(skills)
    report(f"shared: {len(files)} files checked", fails)
    return fails


if __name__ == "__main__":
    check_shared(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    sys.exit(1 if FAILED else 0)
