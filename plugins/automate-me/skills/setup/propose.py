#!/usr/bin/env python3
"""Write only .claude/project-profile.proposed.md. Never a secret, project-profile.md, query-db.json, verify-web.yaml, or .mcp.json."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from detect import detect  # noqa: E402

EXAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "working-rules", "project-profile.example.md")
KEY = re.compile(r"^(\s*- `([a-z_][a-z0-9_]*)`\s*:)(.*)$")
UNCONFIRMED = " (unconfirmed)"


def first(items, pick=lambda item: item["value"]):
    if not items:
        return None
    return pick(items[0])


def tracker_label(value):
    if not isinstance(value, dict):
        return None
    via = value.get("via", "")
    name = value.get("tracker", "")
    if via == "gh" or name.startswith("GitHub Issues"):
        return "GitHub Issues with gh"
    if via == "acli" or name.startswith("Jira"):
        return "Jira with acli"
    if "Linear" in name:
        return "Linear MCP"
    return name or None


def derived(detected):
    out = {}
    label = tracker_label(first(detected.get("tracker", [])))
    if label:
        out["tracker"] = label
        if "GitHub Issues" in label:
            out["ticket_key_format"] = "#123"
            out["ticket_search"] = 'gh issue list --search "<words>"'
            out["ticket_view"] = "gh issue view <n>"
            out["ticket_comments"] = "gh issue view <n> --comments"
        elif "Jira" in label:
            out["ticket_search"] = "acli jira workitem search --jql 'project = PROJ AND summary ~ \"<words>\"'"
            out["ticket_view"] = "acli jira workitem view <KEY>"
            out["ticket_comments"] = "acli jira workitem comment list --key <KEY>"
    remote = first(detected.get("base_remote", []))
    if remote:
        out["base_remote"] = remote
    branch = first(detected.get("default_branch", []))
    if branch:
        out["base_branch"] = branch
    tests = [i["value"] for i in detected.get("tests", []) if isinstance(i.get("value"), str)]
    if tests:
        out["test_full"] = tests[0]
        out["test_one"] = tests[0]
    urls = [i["value"] for i in detected.get("app_urls", []) if isinstance(i.get("value"), str)]
    local = [u for u in urls if "localhost" in u or "127.0.0.1" in u]
    if local:
        out["app_url_test"] = local[0]
    elif urls:
        out["app_url_test"] = urls[0]
    url = first(detected.get("remote_url", []))
    if url and "github.com" in url:
        repo = url.rstrip("/").removesuffix(".git")
        repo = repo.split("github.com/", 1)[-1].split("github.com:", 1)[-1]
        out["ticket_url"] = f"https://github.com/{repo}/issues/<key>"
    root = detected.get("project", "")
    copies = []
    for rel in (".env", ".env.local", "node_modules/", "vendor/"):
        path = os.path.join(root, rel.rstrip("/"))
        if os.path.exists(path):
            copies.append(rel)
    if copies:
        out["worktree_copy"] = ", ".join(copies)
    return out


def fill_example(example, values):
    lines = []
    for line in example.splitlines():
        m = KEY.match(line)
        if not m:
            lines.append(line)
            continue
        prefix, key, rest = m.group(1), m.group(2), m.group(3)
        if key in values:
            lines.append(f"{prefix} `{values[key]}`{UNCONFIRMED}")
        else:
            # Keep the key, drop the example placeholder so this is a blank unconfirmed line.
            lines.append(f"{prefix}")
    if example.endswith("\n"):
        return "\n".join(lines) + "\n"
    return "\n".join(lines)


def propose(root):
    root = os.path.abspath(root)
    detected = detect(root)
    values = derived(detected)
    example = open(EXAMPLE, encoding="utf-8").read()
    text = fill_example(example, values)
    dest_dir = os.path.join(root, ".claude")
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, "project-profile.proposed.md")
    confirmed = os.path.join(dest_dir, "project-profile.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, values, os.path.isfile(confirmed)


def main(argv):
    root = argv[1] if len(argv) > 1 else "."
    path, values, _ = propose(root)
    print(path)
    print(f"wrote {len(values)} unconfirmed values; did not change project-profile.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
