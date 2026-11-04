"""Run: python3 shared/test_check_shared.py"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_shared import check_shared  # noqa: E402

FAILS = []
RUN = []
GOOD = {
    "review-pr/SKILL.md": "Run `../shared/skills/blast-radius/SKILL.md`. See [the rules](../shared/writing-rules.md).\n",
    "review-pr/playbooks/review.md": "Load `../shared/writing-rules.md` and [step two](../SKILL.md#run).\n",
    "shared/writing-rules.md": "Rules. See [pstack](https://github.com/x/pstack), `./vendor/bin/tool`, [a PR](<url>) and `[^/]+/[^/]+(x)`.\n",
    "shared/skills/blast-radius/SKILL.md": "---\nname: blast-radius\ndescription: What depends on an entity.\n---\nRead `../../writing-rules.md`.\n",
    "shared/x.py": "print('x')\n",
    "review-pr/cases/a/key.md": "A fixture link to `../missing.md` and a mention of shared/skills.\n",
}


def fails_for(changes):
    d = tempfile.mkdtemp()
    for rel, text in {**GOOD, **changes}.items():
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        open(os.path.join(d, rel), "w").write(text)
    with contextlib.redirect_stdout(io.StringIO()):
        return check_shared(d), d


def expect(name, changes, want):
    RUN.append(name)
    found, _ = fails_for(changes)
    hit = any(want in f for f in found) if want else not found
    if not hit:
        FAILS.append(f"{name}: wanted {want or 'no failure'}, got {found}")


expect("a clean tree passes; cases, URLs, placeholders and regexes skipped", {}, None)
expect("a broken ../ path fails", {"review-pr/SKILL.md": "Run `../shared/skills/blast-radus/SKILL.md`.\n"},
       "review-pr/SKILL.md:1 path does not resolve: ../shared/skills/blast-radus/SKILL.md")
expect("a broken markdown link fails", {"shared/writing-rules.md": "See [voice](voices/engineer.md).\n"},
       "path does not resolve: voices/engineer.md")
expect("a shared skill naming its caller fails",
       {"shared/skills/blast-radius/SKILL.md": GOOD["shared/skills/blast-radius/SKILL.md"] + "review-pr passes the diff.\n"},
       "shared/skills/blast-radius/SKILL.md:6 names the calling skill review-pr")
expect("a caller-like word inside another name passes",
       {"shared/skills/blast-radius/SKILL.md": GOOD["shared/skills/blast-radius/SKILL.md"] + "The pr-reviewer and the old-pr-review step read it.\n"}, None)
expect("a shared reference outside shared/skills may name a caller",
       {"shared/writing-rules.md": "W12 is checked by review-pr.\n"}, None)
expect("a name that is not the folder fails",
       {"shared/skills/blast-radius/SKILL.md": "---\nname: impact\ndescription: x\n---\n"},
       "shared/skills/blast-radius/SKILL.md name is not blast-radius")
expect("a missing description fails",
       {"shared/skills/blast-radius/SKILL.md": "---\nname: blast-radius\n---\n"},
       "shared/skills/blast-radius/SKILL.md has no description")

expect("a bare script path fails", {"review-pr/SKILL.md": "Run `python3 ../shared/x.py <file>`.\n"},
       'review-pr/SKILL.md:1 script path is not anchored: ../shared/x.py. Write it as "$SKILL_DIR"/<path>')
expect("a bare sh path fails", {"review-pr/SKILL.md": "Run `sh check/all.sh`.\n"}, "script path is not anchored: check/all.sh")
expect("an anchored path to a real file passes",
       {"review-pr/SKILL.md": 'Run `python3 "$SKILL_DIR"/../shared/x.py <file>`.\n'}, None)
expect("an anchored path in a code block with flags passes",
       {"review-pr/SKILL.md": 'python3 -I "$SKILL_DIR"/../shared/x.py <file>\n'}, None)
expect("an anchored path to a missing file fails",
       {"review-pr/SKILL.md": 'Run `python3 "$SKILL_DIR"/../shared/y.py`.\n'},
       'review-pr/SKILL.md:1 script does not exist: "$SKILL_DIR"/../shared/y.py')
expect("a shared skill anchors to its own folder",
       {"shared/skills/blast-radius/SKILL.md": GOOD["shared/skills/blast-radius/SKILL.md"] + 'Run `python3 "$SKILL_DIR"/../../x.py`.\n'}, None)
expect("a README.md with a bare path is skipped", {"review-pr/README.md": "Run `python3 check/nope.py`.\n"}, None)
expect("a python path in a case is skipped", {"review-pr/cases/a/key.md": "Run `python3 nope.py`.\n"}, None)

_, clean = fails_for({})
_, broken = fails_for({"review-pr/SKILL.md": "Run `../nope.md`.\n"})
script = os.path.join(HERE, "check_shared.py")
for name, d, want in [("exits 0 on PASS", clean, 0), ("exits 1 on FAIL", broken, 1)]:
    RUN.append(name)
    got = subprocess.run([sys.executable, script, d], capture_output=True).returncode
    if got != want:
        FAILS.append(f"{name}: got {got}")

print("\n".join(FAILS) or f"{len(RUN)}/{len(RUN)} passed")
sys.exit(1 if FAILS else 0)
