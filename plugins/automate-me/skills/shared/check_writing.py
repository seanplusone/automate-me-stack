"""Shared writing check for automate-me. Checks the [script] rules in shared/writing-rules.md.

Usage: python3 check_writing.py <file>
"""
import re
import sys


def norm(s):
    s = s.strip().strip('"').strip("'").strip()
    return re.sub(r"\s+", " ", s)


def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+", norm(text)) if s]


CHATBOT = ["great question", "i hope this helps", "let me know if", "certainly!", "of course!", "absolutely right"]
PLAIN = ["utilize", "leverage", "facilitate", "crucial", "pivotal", "robust", "seamless", "delve", "enhance", "ensure",
         "additionally", "garner", "interplay", "intricate", "showcase", "testament", "tapestry", "vibrant", "fostering"]
FILLER = ["in order to", "due to the fact that", "it is important to note"]
FANCY_IS = ["serves as", "stands as", "boasts"]
NOT_JUST = re.compile(r"\bnot (just|only|merely)\b[^.?!]*\bbut\b")
ABSTRACT_NOUNS = ["substrate", "locus", "vantage", "nexus", "bedrock", "paradigm", "modality", "north star",
                  "flywheel", "endgame"]


def check_writing(path):
    """Checks the [script] rules in ../shared/writing-rules.md.

    Skips PRD quotes, code blocks, inline code and "- Bad:" counter-examples, which name a banned form on purpose.
    """
    fails = []
    fenced = False
    for n, raw in enumerate(open(path), 1):
        line = raw.rstrip("\n")
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced or line.strip().startswith(("Quote:", "- Bad:")):
            continue
        line = re.sub(r"`[^`]*`", "", line)
        low = line.lower()
        where = f"line {n}"
        if "—" in line or "–" in line:
            fails.append(f"{where} W1 long dash")
        if re.search("[‘’“”]", line):
            fails.append(f"{where} W3 curly quote")
        for p in CHATBOT:
            if p in low:
                fails.append(f"{where} W4 chatbot phrase: {p}")
        for w in PLAIN:
            if re.search(rf"\b{w}\w*", low):
                fails.append(f"{where} W5 plain word: {w}")
        for p in FILLER:
            if p in low:
                fails.append(f"{where} W6 filler: {p}")
        for p in FANCY_IS:
            if p in low:
                fails.append(f"{where} W20 say is: {p}")
        if NOT_JUST.search(low):
            fails.append(f"{where} W21 not just X but Y")
        for w in ABSTRACT_NOUNS:
            if re.search(rf"\b{w}s?\b", low):
                fails.append(f"{where} W22 abstract noun: {w}")
        for sent in sentences(re.sub(r"^[#>*\-\s]+", "", line)):
            if len(sent.split()) > 30:
                fails.append(f"{where} W9 sentence over 30 words; split it, keeping the articles (W11)")
        if re.search(r"(→|->|=>)", line):
            fails.append(f"{where} W11 arrow in prose")
    report(f"writing: {path}", fails)
    return fails


FAILED = []


def report(label, fails):
    if fails:
        FAILED.append(label)
    print(f"{'FAIL' if fails else 'PASS'} {label}")
    for f in fails:
        print(f"  {f}")


if __name__ == "__main__":
    sys.exit(1 if check_writing(sys.argv[1]) else 0)
