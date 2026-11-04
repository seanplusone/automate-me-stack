"""Check that every `<profile: key>` placeholder the skill uses is defined in a profile.

Usage: python3 check/check_profile.py [<skill dir>] [<profile file>] [--filled]

Reads the placeholders in <skill dir>/SKILL.md and <skill dir>/playbooks/*.md. A key is defined by a
line of the form "- `key`: value". The profile defaults to <skill dir>/project-profile.example.md;
pass a project's .claude/project-profile.md to check a filled-in copy. With --filled, a value that still
holds a `<...>` placeholder from the example also fails; a blank value is allowed and means "skip this
step". Prints PASS or FAIL and exits 1 on FAIL.
"""
import glob
import os
import re
import sys

USED = re.compile(r"<profile:\s*([a-z_][a-z0-9_]*)\s*>")
DEFINED = re.compile(r"^\s*-\s*`([a-z_][a-z0-9_]*)`\s*:", re.M)
VALUE = re.compile(r"^\s*-\s*`([a-z_][a-z0-9_]*)`\s*:(.*)$", re.M)
PLACEHOLDER = re.compile(r"`<[^`]*>`")


def used_keys(skill_dir):
    keys = {}
    files = [os.path.join(skill_dir, "SKILL.md")] + sorted(glob.glob(os.path.join(skill_dir, "playbooks", "*.md")))
    for path in files:
        if not os.path.isfile(path):
            continue
        for n, line in enumerate(open(path), 1):
            for m in USED.finditer(line):
                keys.setdefault(m.group(1), f"{os.path.relpath(path, skill_dir)}:{n}")
    return keys


def defined_keys(profile):
    return set(DEFINED.findall(open(profile).read()))


def placeholders(profile):
    return [key for key, value in VALUE.findall(open(profile).read()) if PLACEHOLDER.search(value)]


def check(skill_dir, profile=None, filled=False):
    profile = profile or os.path.join(skill_dir, "project-profile.example.md")
    if not os.path.isfile(profile):
        return [f"no profile file: {profile}"]
    defined = defined_keys(profile)
    fails = [f"{where} uses <profile: {key}>, not defined in {os.path.basename(profile)}"
             for key, where in sorted(used_keys(skill_dir).items()) if key not in defined]
    if filled:
        fails += [f"{key} still holds a <...> placeholder; fill it in or leave it blank" for key in placeholders(profile)]
    return fails


def main(argv):
    filled = "--filled" in argv
    argv = [a for a in argv if a != "--filled"]
    skill_dir = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    fails = check(skill_dir, argv[2] if len(argv) > 2 else None, filled)
    print(f"{'FAIL' if fails else 'PASS'} profile keys")
    for f in fails:
        print(f"  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
