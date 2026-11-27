"""Run: python3 check/test_check_roles.py"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK_ROLES = HERE / "check_roles.py"
FIXTURES = HERE / "fixtures/roles"
EXAMPLE = FIXTURES / "example-map.toml"
TWO_VENDOR = FIXTURES / "two-vendor-same-family.toml"
DEFAULT = FIXTURES / "layer-default.toml"
USER = FIXTURES / "layer-user.toml"
PROJECT = FIXTURES / "layer-project.toml"
FAILS = []


def run(repo, *args, env=None):
    if not CHECK_ROLES.is_file():
        raise AssertionError(f"missing script {CHECK_ROLES.name}")
    return subprocess.run(
        [sys.executable, str(CHECK_ROLES), *map(str, args)],
        cwd=repo, env=env, capture_output=True, text=True, errors="replace", timeout=20,
    )


def expect(repo, *args, code=0, warn=False, env=None):
    proc = run(repo, *args, env=env)
    output = proc.stdout + proc.stderr
    has_warn = any(line.startswith("WARN") for line in output.splitlines())
    if (proc.returncode != code or ("STOP" in output) != (code == 2)
            or (warn and not has_warn) or "Traceback" in output):
        diagnostic = " with STOP" if code == 2 else " without STOP"
        if warn:
            diagnostic += " and with a WARN line"
        raise AssertionError(
            f"{CHECK_ROLES.name} {args!r} wanted exit {code}{diagnostic} "
            f"without a traceback, got exit {proc.returncode}: {output.strip()!r}"
        )
    return proc.stdout


def expect_roles(output, *expected):
    lines = output.splitlines()
    for line in expected:
        role, _ = line.split("=", 1)
        matches = [actual for actual in lines if actual.startswith(f"{role}=")]
        if matches != [line]:
            raise AssertionError(f"wanted one line {line!r}, got {matches!r} in {output!r}")


def test_example_map(repo):
    output = expect(repo, EXAMPLE)
    expect_roles(
        output,
        "helper=map default=acme-mini effort=low",
        "build=map default=acme-large effort=high",
        "build-hard=map default=acme-large effort=xhigh",
        "review=map default=acme-large effort=high",
    )


def test_missing_role_or_default(repo):
    expect(repo, FIXTURES / "empty-role.toml", code=2)
    content, removed = re.subn(
        r"(?m)^\[roles\.build-hard\]\n[^\[]*", "", EXAMPLE.read_text(),
    )
    if removed != 1:
        raise AssertionError("wanted one build-hard table to remove from example-map.toml")
    missing = repo / "missing-role.toml"
    missing.write_text(content)
    expect(repo, missing, code=2)


def test_reviewer_diversity(repo):
    expect(repo, TWO_VENDOR, "--builder", "acme", "--reviewer", "acme", code=2)
    expect(repo, TWO_VENDOR, "--builder", "acme", "--reviewer", "globex")
    expect(repo, EXAMPLE, "--builder", "acme", "--reviewer", "acme", warn=True)
    expect(repo, TWO_VENDOR, "--builder", "acme-large", "--reviewer", "acme-mid", code=2)


def test_light_model(repo):
    expect(repo, FIXTURES / "light-on-review.toml", code=2)
    content = EXAMPLE.read_text()
    section = '[roles.build-hard]\ndefault = "acme-large"\n'
    if content.count(section) != 1:
        raise AssertionError("wanted one build-hard default in example-map.toml")
    light_option = repo / "light-build-hard-option.toml"
    light_option.write_text(content.replace(section, section + 'options = ["acme-mini"]\n'))
    expect(repo, light_option, code=2)


def test_helper_edits(repo):
    expect(repo, FIXTURES / "helper-can-edit.toml", code=2)
    expect(repo, EXAMPLE)


def test_layer_precedence(repo):
    output = expect(repo, "--default", DEFAULT, "--user", USER, "--project", PROJECT)
    expect_roles(
        output,
        "build=project default=globex-pro effort=low",
        "review=user default=acme-mid effort=medium",
        "helper=default default=acme-mini effort=low",
    )
    output = expect(repo, "--default", DEFAULT, "--user", USER)
    expect_roles(output, "build=user default=acme-mid effort=medium")


def test_env_lookup(repo):
    home = repo / "home"
    home.mkdir()
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["HOME"] = str(home)
    env["AUTOMATE_ME_ROLE_MAP"] = str(USER)
    env.pop("AUTOMATE_ME_PROJECT_ROLE_MAP", None)
    subprocess.run(
        ["git", "init", "-q"], cwd=repo, env=env, capture_output=True,
        text=True, check=True, timeout=20,
    )
    project_map = repo / ".automate-me/role-map.toml"
    project_map.parent.mkdir()
    project_map.write_text(PROJECT.read_text())

    workdir = repo / "nested"
    workdir.mkdir()
    output = expect(workdir, env=env)
    expect_roles(
        output,
        "build=project default=globex-pro effort=low",
        "review=user default=acme-mid effort=medium",
    )

    del env["AUTOMATE_ME_ROLE_MAP"]
    env["AUTOMATE_ME_PROJECT_ROLE_MAP"] = str(USER)
    output = expect(workdir, env=env)
    expect_roles(
        output,
        "build=project default=acme-mid effort=medium",
        "review=project default=acme-mid effort=medium",
    )


def test_unknown_role(repo):
    old = repo / "old-role-name.toml"
    old.write_text(EXAMPLE.read_text() + '\n[roles.plan]\ndefault = "acme-large"\neffort = "high"\n')
    expect(repo, old, code=2)
    bad = repo / "bad-extra-role.toml"
    bad.write_text(EXAMPLE.read_text() + '\n[roles.review-second]\neffort = "high"\n')
    expect(repo, bad, "--builder", "acme", "--reviewer", "acme", code=2)


def test_broken_toml(repo):
    broken = repo / "broken.toml"
    broken.write_text("[roles.helper\n")
    expect(repo, broken, code=2)


def test_synthetic_fixtures(repo):
    product = re.compile(r"\b(opus|sonnet|haiku|neon|hydrogen|codex|sol|gemini|claude|gpt)\b",
                         re.IGNORECASE)
    bad = []
    for fixture in sorted(FIXTURES.glob("*.toml")):
        match = product.search(fixture.read_text())
        if match:
            bad.append(f"{fixture.name} contains {match.group()!r}")
    if bad:
        raise AssertionError("; ".join(bad))


if __name__ == "__main__":
    cases = (
        test_example_map, test_missing_role_or_default, test_reviewer_diversity,
        test_light_model, test_helper_edits, test_layer_precedence, test_env_lookup,
        test_unknown_role, test_broken_toml, test_synthetic_fixtures,
    )
    for case in cases:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                case(Path(tmp))
        except (AssertionError, OSError, subprocess.SubprocessError) as err:
            reason = getattr(err, "stderr", None) or str(err)
            FAILS.append(f"{case.__name__}: {reason.strip()}")
    for failure in FAILS:
        print(f"FAIL {failure}")
    print(f"{len(cases) - len(FAILS)}/{len(cases)} passed")
    sys.exit(1 if FAILS else 0)
