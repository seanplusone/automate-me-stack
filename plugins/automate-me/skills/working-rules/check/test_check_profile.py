"""Run: python3 check/test_check_profile.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_profile.py")
SKILL = os.path.join(HERE, "..")
FAILS = []


def run(*args):
    r = subprocess.run([sys.executable, CHECK, *args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def expect(name, cond, out):
    if not cond:
        FAILS.append(f"{name}\n{out}")


def fake_skill(skill_text, playbook_text, profile_text):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "playbooks"))
    for rel, text in (("SKILL.md", skill_text), ("playbooks/fix.md", playbook_text),
                      ("project-profile.example.md", profile_text)):
        with open(os.path.join(d, rel), "w") as f:
            f.write(text)
    return d


# The real skill: every key used is defined in the shipped example.
code, out = run(SKILL)
expect("real skill passes", code == 0 and "PASS" in out, out)

# The real skill uses at least the keys the fix playbook depends on.
sys.path.insert(0, HERE)
import check_profile  # noqa: E402

used = check_profile.used_keys(SKILL)
for key in ("test_one", "test_full", "base_branch", "app_url_test"):
    expect(f"real skill uses {key}", key in used, sorted(used))

# A key used in a playbook but missing from the profile fails, and names the file and line.
d = fake_skill("Run `<profile: test_one>`.\n", "Then\n`<profile: test_full>`.\n", "- `test_one`: pytest x\n")
code, out = run(d)
expect("missing key fails", code == 1 and "test_full" in out and "playbooks/fix.md:2" in out, out)
expect("defined key not reported", "test_one" not in out, out)

# A key used in SKILL.md but missing fails too.
d = fake_skill("Open `<profile: app_url_test>`.\n", "", "- `test_one`: x\n")
code, out = run(d)
expect("missing SKILL.md key fails", code == 1 and "SKILL.md:1" in out, out)

# A definition only counts in the "- `key`: value" form; prose mentioning the key does not define it.
d = fake_skill("`<profile: base_branch>`\n", "", "The base_branch is main.\n")
code, out = run(d)
expect("prose mention is not a definition", code == 1, out)

# A filled-in project profile can be checked in place of the example.
d = fake_skill("`<profile: base_branch>`\n", "", "")
prof = os.path.join(d, "filled.md")
with open(prof, "w") as f:
    f.write("- `base_branch`: main\n")
code, out = run(d, prof)
expect("filled profile passes", code == 0, out)

# --filled fails on a value still holding the example's <...>, and allows a blank value.
d = fake_skill("`<profile: base_branch>` `<profile: test_one>`\n", "", "")
prof = os.path.join(d, "filled.md")
with open(prof, "w") as f:
    f.write("- `base_branch`: `<main>`\n- `test_one`:\n")
code, out = run(d, prof, "--filled")
expect("--filled fails on a placeholder", code == 1 and "base_branch still holds" in out and "test_one" not in out, out)
code, out = run(d, prof)
expect("placeholder passes without --filled", code == 0, out)
with open(prof, "w") as f:
    f.write("- `base_branch`: `main`\n- `test_one`:\n")
code, out = run(d, prof, "--filled")
expect("--filled passes a filled profile with a blank line", code == 0, out)

# The shipped example is all placeholders, so --filled fails on it.
code, out = run(SKILL, os.path.join(SKILL, "project-profile.example.md"), "--filled")
expect("--filled fails on the example", code == 1, out)

# No placeholders at all passes.
d = fake_skill("No placeholders.\n", "", "")
code, out = run(d)
expect("no placeholders passes", code == 0, out)

if FAILS:
    print("FAIL test_check_profile")
    for f in FAILS:
        print("  " + f.replace("\n", "\n    "))
    sys.exit(1)
print("PASS test_check_profile")
