"""Fails when a decode-ask page's first screen runs over 150 words.

The first screen is the visible text: comments, scripts and styles are dropped, and each closed <details> keeps only its <summary>.

Usage: python3 check_page.py <page.html>
"""
import html as htmllib
import re
import sys

LIMIT = 150


def first_screen_words(page):
    body = re.sub(r"<!--.*?-->", " ", page, flags=re.S)
    body = re.sub(r"<(style|script|svg|title|head)\b.*?</\1>", " ", body, flags=re.S | re.I)
    closed = re.compile(r"<details\b(?![^>]*\bopen\b)[^>]*>((?:(?!<details\b).)*?)</details>", re.S | re.I)
    summary = re.compile(r"<summary\b[^>]*>(.*?)</summary>", re.S | re.I)
    while True:
        new = closed.sub(lambda m: " ".join(summary.findall(m.group(1))), body)
        if new == body:
            break
        body = new
    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", body)).replace("\xa0", " ")
    return len(text.split())


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1])
        return 2
    words = first_screen_words(open(argv[1], encoding="utf-8").read())
    if words > LIMIT:
        print(f"FAIL page: first screen is {words} words, limit {LIMIT}. Fold the rest into closed <details>.")
        return 1
    print(f"PASS page: first screen is {words} words")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
