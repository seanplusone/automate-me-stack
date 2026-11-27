"""Run: python3 shared/test_pr_prose.py"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pr_prose import check, check_body_shape, collect  # noqa: E402

FAILS = []


def run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def expect(name, ok, got):
    if not ok:
        FAILS.append(f"{name}: got {got}")


repo = tempfile.mkdtemp()
run("git", "init", "-q", "-b", "main", cwd=repo)
run("git", "config", "user.email", "t@example.test", cwd=repo)
run("git", "config", "user.name", "t", cwd=repo)
open(os.path.join(repo, "a.php"), "w").write("<?php\n$x = 1;\n")
run("git", "add", ".", cwd=repo)
run("git", "commit", "-q", "-m", "base", cwd=repo)
base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

open(os.path.join(repo, "a.php"), "w").write(
    "<?php\n$x = 1;\n// This serves as the guard for the save.\n$y = 'robust'; // trailing note\n"
    "/**\n * @param int $id\n * Loads the row.\n */\n")
open(os.path.join(repo, "notes.md"), "w").write("# Notes\n\nThe pull runs on a schedule — not instantly.\n")
run("git", "add", ".", cwd=repo)
run("git", "commit", "-q", "-m", "fix: ensure the photos load\n\nCo-Authored-By: Someone <x@example.test>", cwd=repo)

body = os.path.join(repo, "body.md")
open(body, "w").write("Adds the photos.\n\nIn order to match the regions version.\n")

cwd = os.getcwd()
os.chdir(repo)
items = collect(base, "HEAD", body=body)
hits = check(items)
os.chdir(cwd)

texts = [t for _, t in items]
expect("full-line comment collected without its marker", "This serves as the guard for the save." in texts, texts)
expect("code line skipped", not any("$y" in t for t in texts), texts)
expect("docblock tag skipped", not any(t.startswith("@param") for t in texts), texts)
expect("docblock prose collected", "Loads the row." in texts, texts)
expect("trailer skipped", not any("Co-Authored-By" in t for t in texts), texts)
expect("comment hit carries path:line", any(h.startswith("a.php:3 W20") for h in hits), hits)
expect("markdown hit carries path:line", any(h.startswith("notes.md:3 W1") for h in hits), hits)
expect("commit message hit", any(h.startswith("commit ") and "W5" in h for h in hits), hits)
expect("body hit", any(h.startswith(f"body {body}:3 W6") for h in hits), hits)

expect("clean text passes", check([("x:1", "The path is wrong at line 99.")]) == [], "hit on clean text")


def write_body(text):
    path = os.path.join(tempfile.mkdtemp(), "body.md")
    open(path, "w").write(text)
    return path


def shape(text):
    return check_body_shape(write_body(text))


GOOD = (
    "A ui brief must name a Design facts file. The checker fails when that line "
    "is missing or the file does not exist.\n\n"
    "proof.py check ends with VERIFY: PASS.\n\n"
    "```\n" + ("caught\n" * 200) + "```\n"
)
OVER = "word " * 151 + "\n"
SHAPED_24 = (
    "Kind: design already means system design. Briefs that change how something "
    "looks had no kind, and no place to point at locked visual facts.\n\n"
    "This PR adds Kind: ui. A ui brief must have a Design facts path line. "
    "check_brief.py splits that into two checks. The presence check fails when "
    "the line is missing or empty, and passes when the value is non-empty. The "
    "existence check fails when the path does not exist. Paths resolve from the "
    "brief folder. An absolute path is used as given. Only existence is checked. "
    "When no brief path is given, the existence check reports SKIP, not PASS. "
    "Missing or empty Design facts still fails the presence check without a path. "
    "Non-ui briefs do not need the line. A stray Design facts line on a non-ui "
    "brief is allowed and is not checked. When Kind is ui, SKILL.md now asks for "
    "the design facts file path right away, before filling other slots. It may "
    "offer to start that file in the project's own repo, never in this plugin. "
    "Like the workstream question, this ask does not count toward the 3-question "
    "cap. More filler words are added here so the unfenced count goes well over "
    "the cap even after the proof fence is removed from the count. These words "
    "name no extra rule. They only pad the body the way the old descriptions did "
    "when they restated every check and then walked through each commit.\n\n"
    "Tests first: 1021ce3 adds the original tests. b570d97 adds the first check.\n"
    "ed55f86 adds the SKIP tests. 0ef19cb adds the SKIP fix. b4ded1b adds the "
    "skill sentence. Full suite at b4ded1b: 25 test files, 0 failed.\n\n"
    "Each Verify command in the brief gives m1 to m7 exit=0.\n\n"
    "```\n"
    "m1 existence reports PASS when no brief path is given: CAUGHT\n"
    "m2 Design facts path resolves against the current directory: CAUGHT\n"
    "```\n\n"
    "Reviewers: use only the yes/no checklist. Flag a major only if an item is no.\n"
)
ONE_LINE_TF = (
    "Short change and proof.\n\n"
    "Tests first: abc1234 failed 8/12; head passes 12/12.\n"
)
MULTI_TF = (
    "Short change and proof.\n\n"
    "Tests first: abc1234 failed 8/12.\n"
    "head passes 12/12.\n"
)
REVIEWERS = (
    "Short change and proof.\n\n"
    "Reviewers: use only the yes/no checklist.\n"
)

expect("good body passes", shape(GOOD) == [], shape(GOOD))
expect("#24-shaped body fails", shape(SHAPED_24) != [], shape(SHAPED_24))
expect("one-line Tests first passes", shape(ONE_LINE_TF) == [], shape(ONE_LINE_TF))
expect("multi-line Tests first fails", shape(MULTI_TF) != [], shape(MULTI_TF))
expect("body over the cap fails", shape(OVER) != [], shape(OVER))
expect("Reviewers section fails", shape(REVIEWERS) != [], shape(REVIEWERS))

for heading in ("## Reviewers", "### Reviewers:", "**Reviewers:**", "**Reviewers**"):
    hits = shape(f"Short change and proof.\n\n{heading}\nUse the checklist.\n")
    expect(f"{heading} fails", hits == ["W26 Reviewers: section"], hits)

hits = shape("Short change and proof.\n\nPlease tell the reviewers about this change.\n")
expect("mid-line reviewers mention passes", hits == [], hits)
hits = shape("Short change and proof.\n\n## Tests first\nabc1234 failed 8/12.\nhead passes 12/12.\n")
expect("multi-line Tests first heading fails", hits == ["W26 multi-line Tests first narration"], hits)
hits = shape("Short change and proof.\n\n## Tests first: abc1234 failed 8/12; head passes 12/12.\n")
expect("one-line Tests first heading passes", hits == [], hits)

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    total = 23
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
