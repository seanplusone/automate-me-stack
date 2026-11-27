"""Check role maps and reviewer diversity before a handoff.

Usage:
  python3 check/check_roles.py [map] [--builder MODEL_OR_VENDOR --reviewer MODEL_OR_VENDOR]
  python3 check/check_roles.py [--default PATH] [--user PATH] [--project PATH]

Roles: build, build-hard, review, helper. Any other role name stops.
Layers: references/default-role-map.toml beside the skill's check directory,
~/.automate-me/role-map.toml (AUTOMATE_ME_ROLE_MAP), and .automate-me/role-map.toml
at the git root (AUTOMATE_ME_PROJECT_ROLE_MAP). Project wins over user, and
user wins over default, per role. A positional map is checked on its own.
With any layer flag, only the layers given on the command line are read.

Each TOML or JSON map can define models and roles. Every merged role needs a
default model and effort. Helper is read-only. build-hard and review
cannot use light models as defaults or options. A reviewer must
differ from the builder in vendor and family. A map whose role models come
from one vendor warns instead.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

sys.dont_write_bytecode = True

DEFAULT = Path(__file__).resolve().parents[1] / "references/default-role-map.toml"
ROLE_MAP = ".automate-me/role-map.toml"
ROLES = ("build", "build-hard", "review", "helper")
NO_LIGHT = {"build-hard", "review"}


def stop(reason):
    print(f"STOP: {reason}")
    return 2


class RoleParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(stop(f"Role check arguments: {message}. Fix the command before the handoff."))


def project_map():
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                            capture_output=True, timeout=10)
    if result.returncode == 0:
        return Path(os.fsdecode(result.stdout.rstrip(b"\n"))) / ROLE_MAP
    return None


def layers(args):
    if args.map is not None:
        yield "map", args.map, True
        return
    if any(path is not None for path in (args.default, args.user, args.project)):
        for layer in ("default", "user", "project"):
            yield layer, getattr(args, layer), True
        return
    yield "default", DEFAULT, True
    user = os.environ.get("AUTOMATE_ME_ROLE_MAP")
    yield "user", user or Path.home() / ROLE_MAP, bool(user)
    project = os.environ.get("AUTOMATE_ME_PROJECT_ROLE_MAP")
    yield "project", project or project_map(), bool(project)


def load_map(path, required):
    try:
        with Path(path).expanduser().open("rb") as stream:
            data = json.load(stream) if Path(path).suffix.lower() == ".json" else tomllib.load(stream)
    except FileNotFoundError:
        if required:
            raise
        return {}, {}
    if not isinstance(data, dict):
        raise ValueError("the map must contain tables")
    models, roles = data.get("models", {}), data.get("roles", {})
    if not isinstance(models, dict) or not isinstance(roles, dict):
        raise ValueError("models and roles must be tables")
    return models, roles


def name(value):
    return isinstance(value, str) and bool(value.strip()) and value.isprintable()


def check_role(role, spec, models):
    if not isinstance(spec, dict) or not name(spec.get("default")):
        raise ValueError(f"{role} needs a default model")
    if not name(spec.get("effort")):
        raise ValueError(f"{role} needs an effort")
    if role == "helper" and spec.get("edits", False) is not False:
        raise ValueError("helper must be read-only (edits = false)")
    options = spec.get("options", [])
    if not isinstance(options, list):
        raise ValueError(f"{role} options must be a list of model names")
    for model in [spec["default"], *options]:
        if not name(model) or model not in models:
            raise ValueError(f"{role} names an unknown model {model!r}")
        if role in NO_LIGHT and models[model].get("light", False):
            raise ValueError(f"{role} cannot use light model {model!r}")


def reviewer_problem(builder, reviewer, models, vendors):
    def identity(seat, choice):
        if choice in models:
            return models[choice]["vendor"], models[choice]["family"]
        if choice in vendors:
            return choice, None
        families = {spec["family"]: spec["vendor"] for spec in models.values()}
        if choice in families:
            return families[choice], choice
        raise ValueError(f"{seat} must name a model or vendor in the map ({choice!r})")

    build_vendor, build_family = identity("builder", builder)
    review_vendor, review_family = identity("reviewer", reviewer)
    if build_vendor == review_vendor or (build_family and build_family == review_family):
        return f"reviewer {reviewer!r} shares a vendor or family with builder {builder!r}"
    return None


def main():
    parser = RoleParser(description=__doc__.splitlines()[0])
    parser.add_argument("map", nargs="?")
    for flag in ("default", "user", "project", "builder", "reviewer"):
        parser.add_argument(f"--{flag}")
    args = parser.parse_args()
    if args.map is not None and any(path is not None for path in
                                    (args.default, args.user, args.project)):
        parser.error("choose a single map or layer flags")
    if (args.builder is None) != (args.reviewer is None):
        parser.error("--builder and --reviewer must be used together")

    models, roles = {}, {}
    try:
        for layer, path, required in layers(args):
            if path is None:
                continue
            try:
                layer_models, layer_roles = load_map(path, required)
            except (OSError, ValueError, RecursionError) as err:
                raise ValueError(f"cannot read {layer} role map {path!r} ({err})") from err
            models.update(layer_models)
            roles.update({role: (layer, spec) for role, spec in layer_roles.items()})

        for model, spec in models.items():
            if (not isinstance(spec, dict) or not name(spec.get("vendor"))
                    or not name(spec.get("family"))
                    or not isinstance(spec.get("light", False), bool)):
                raise ValueError(f"model {model!r} needs a vendor, family, and a boolean light flag if set")
        unknown = sorted(set(roles) - set(ROLES))
        if unknown:
            raise ValueError(f"unknown role {', '.join(unknown)}; the roles are {', '.join(ROLES)}")
        for role in ROLES:
            if role not in roles:
                raise ValueError(f"{role} is missing")
            check_role(role, roles[role][1], models)

        if args.builder is not None:
            used = {model for _, spec in roles.values() for model in [spec["default"], *spec.get("options", [])]}
            vendors = {models[model]["vendor"] for model in used}
            problem = reviewer_problem(args.builder, args.reviewer, models, vendors)
            if problem:
                if len(vendors) > 1:
                    return stop(f"{problem}. Pick another reviewer before the handoff.")
                print(f"WARN: {problem}. The map has one vendor.")
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as err:
        return stop(f"{err}. Fix the map before the handoff.")

    for role in ROLES:
        layer, spec = roles[role]
        print(f"{role}={layer} default={spec['default']} effort={spec['effort']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
