"""Prints the summary message to post after a review, in a team chat channel or a PR thread: each PR under the outcome of the review.

Usage: python3 check/summary.py <drafts.md> [--format markdown|slack]

The default format is Markdown, for GitHub, Teams, Discord or any chat tool that reads it. `--format slack` prints
Slack's mrkdwn, for posting through the Slack API.

The buckets follow the verdict: `approve` with no comments is Approved, `approve` with comments
is Approved with comments, `needs answer: <question>` is Needs an answer and lists the question,
and `approve after` or `hold:` is Changes requested, since neither is an approval yet. The page colors
`approve after` yellow, but a reader of the summary message only needs to know whether the PR still
waits on its author. A `scope:` PR was only read where it meets the others, so it is left out. Empty buckets
are left out. Each PR is its linked number alone, since a stack shares one ticket and only the
number tells its PRs apart. Mixed repos add the repo name.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import parse  # noqa: E402

BUCKETS = ["Approved", "Approved with comments", "Needs an answer", "Changes requested"]
NEEDS_ANSWER = re.compile(r"^needs answer: (.+)$")


def bucket(pr, comments):
    verdict = pr["verdict"]
    if NEEDS_ANSWER.match(verdict):
        return "Needs an answer"
    if verdict.startswith("hold:") or verdict.startswith("approve after"):
        return "Changes requested"
    if verdict == "approve" and comments:
        return "Approved with comments"
    if verdict == "approve":
        return "Approved"
    return None


def groups(prs):
    """[(bucket, [(url, label, question), ...]), ...] for the non-empty buckets, in order."""
    one_repo = len({pr["pr"].partition("#")[0] for pr in prs}) == 1
    out = {name: [] for name in BUCKETS}
    for pr in prs:
        comments = len({" ".join(f["comment"]) for f in pr["findings"] if f["match"]})
        name = bucket(pr, comments)
        if name:
            repo, _, num = pr["pr"].partition("#")
            label = f"#{num}" if one_repo else f"{repo.split('/')[-1]}#{num}"
            ask = NEEDS_ANSWER.match(pr["verdict"])
            out[name].append((f"https://github.com/{repo}/pull/{num}", label, ask[1] if ask else None))
    return [(name, rows) for name, rows in out.items() if rows]


def mrkdwn(text):
    """Text safe for Slack's markup, where <, > and & start links and entities."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def markdown(text):
    """Text safe inside a Markdown list item, where [, ], * and _ start links and emphasis."""
    return re.sub(r"([\\\[\]*_`])", r"\\\1", text)


FORMATS = {
    "markdown": lambda name, rows: f"**{name}**\n" + "\n".join(
        f"- [{label}]({url})" + (f", needs an answer: {markdown(ask)}" if ask else "") for url, label, ask in rows),
    "slack": lambda name, rows: f"*{name}*\n" + "\n".join(
        f"• <{url}|{label}>" + (f", needs an answer: {mrkdwn(ask)}" if ask else "") for url, label, ask in rows),
}


def summary(path, fmt="markdown"):
    """The message as Markdown, or as Slack's mrkdwn for posting through the API. Pasted into a composer it stays raw."""
    prs, _ = parse(path)
    return "\n\n".join(FORMATS[fmt](name, rows) for name, rows in groups(prs))


if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 1)
    args, fmt = sys.argv[1:], "markdown"
    if "--format" in args:
        i = args.index("--format")
        fmt = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    if fmt not in FORMATS:
        sys.exit(f"--format must be one of: {', '.join(FORMATS)}")
    print(summary(args[0], fmt))
