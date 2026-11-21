"""Judges whether a read is too big for an agent's main context, and names a smaller way to read it.

Usage:
  python3 check_read_size.py [--threshold N] [--offset N] [--limit N] PATH
  python3 check_read_size.py [--threshold N] --command "SHELL"

The threshold is in lines: 350 by default, or READ_SIZE_THRESHOLD, or --threshold, which wins.

Blocks when:
- PATH has more lines than the threshold and no --limit is set. --offset alone still reads to the end, so it does not count as targeted;
- the shell command runs cat, head, tail or less on a file over the threshold, anywhere in a pipe, list or group.
  head and tail with a line count at or under the threshold (-n N, -N, --lines=N), or a byte count (-c), are targeted reads.

A missing or unreadable file is allowed, because the read itself will fail. Other commands are not judged by name.
Exits 0 to allow and prints nothing, 2 to block with one line on stderr naming the read and the alternative,
and 3 on a usage error.
"""
import argparse
import glob
import os
import re
import shlex
import sys

DEFAULT_THRESHOLD = 350
READERS = {"cat", "head", "tail", "less"}
SEPARATORS = re.compile(r"\|\||&&|\$\(|[|;&\n(){}`]")
ALTERNATIVE = ("Use a targeted read with an offset and a limit, or a bulk-read tool that keeps the file out of the main "
               "context (for example context-mode's execute_file or batch tools).")


def count_lines(path):
    """Newlines in the file, like wc -l, read in chunks. None when it can't be read as a file."""
    try:
        n = 0
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                n += chunk.count(b"\n")
        return n
    except OSError:
        return None


def too_big(path, threshold):
    n = count_lines(path) if os.path.isfile(path) else None
    return n if n is not None and n > threshold else None


def check_path(path, threshold=DEFAULT_THRESHOLD, offset=None, limit=None):
    """The block reason for a full read of path, or None to allow."""
    if limit:
        return None
    n = too_big(path, threshold)
    if n is None:
        return None
    start = f" from line {offset}" if offset else ""
    return f"{path} has {n} lines, over the {threshold}-line limit for a full read{start}. {ALTERNATIVE}"


def segments(command):
    for part in SEPARATORS.split(command):
        try:
            words = shlex.split(part)
        except ValueError:
            words = part.split()
        while words and re.match(r"^\w+=", words[0]):
            words = words[1:]
        if words:
            yield words


def count_is_small(word, nxt, threshold):
    m = re.match(r"^(?:-n|--lines=?|-)(\+?\d+)$", word)
    if m or word in ("-n", "--lines"):
        value = m.group(1) if m else (nxt or "")
        return value.lstrip("+").isdigit() and int(value.lstrip("+")) <= threshold
    return word.startswith("-c") or word.startswith("--bytes")


def file_args(words, threshold):
    """The files a reader command reads in full, or None when its count makes it a targeted read."""
    tool, args, files = os.path.basename(words[0]), words[1:], []
    skip = False
    for i, w in enumerate(args):
        if skip:
            skip = False
            continue
        nxt = args[i + 1] if i + 1 < len(args) else None
        if tool in ("head", "tail") and count_is_small(w, nxt, threshold):
            return None
        if w == "<":
            continue
        if tool in ("head", "tail") and w in ("-n", "--lines", "-c", "--bytes") or re.match(r"^\d*>&?$|^&>$", w):
            skip = True
            continue
        if w.startswith("-") and w != "-" or re.match(r"^\d*>", w):
            continue
        files.append(w)
    return files


def check_command(command, threshold=DEFAULT_THRESHOLD, cwd=None):
    """The block reason for the first oversized cat, head, tail or less in command, or None to allow."""
    base = cwd or os.getcwd()
    for words in segments(command):
        if os.path.basename(words[0]) not in READERS:
            continue
        for arg in file_args(words, threshold) or []:
            path = os.path.join(base, os.path.expanduser(arg))
            for p in glob.glob(path) if glob.has_magic(path) else [path]:
                n = too_big(p, threshold)
                if n is not None:
                    shown = " ".join(command.split())
                    return (f"`{shown}` runs {words[0]} on {arg}, which has {n} lines, over the {threshold}-line limit. "
                            f"{ALTERNATIVE}")
    return None


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"usage error: {message}", file=sys.stderr)
        sys.exit(3)


def positive(text):
    if not re.fullmatch(r"\d+", text or "") or int(text) < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer: {text!r}")
    return int(text)


def nonnegative(text):
    if not re.fullmatch(r"\d+", text or ""):
        raise argparse.ArgumentTypeError(f"must be a non-negative integer: {text!r}")
    return int(text)


def main(argv=None):
    ap = Parser(prog="check_read_size.py", description="Judge whether a read is too big.")
    ap.add_argument("--threshold", type=positive)
    ap.add_argument("--offset", type=nonnegative)
    ap.add_argument("--limit", type=positive)
    ap.add_argument("--command")
    ap.add_argument("path", nargs="?")
    a = ap.parse_args(argv)
    if a.threshold is None:
        env = os.environ.get("READ_SIZE_THRESHOLD")
        try:
            a.threshold = positive(env) if env is not None else DEFAULT_THRESHOLD
        except argparse.ArgumentTypeError as e:
            ap.error(f"READ_SIZE_THRESHOLD {e}")
    if a.command is not None:
        if a.path is not None or a.offset is not None or a.limit is not None:
            ap.error("give a PATH or --command, not both; --offset and --limit go with a PATH")
        if not a.command.strip():
            ap.error("--command is empty")
        reason = check_command(a.command, a.threshold)
    elif a.path:
        reason = check_path(a.path, a.threshold, a.offset, a.limit)
    else:
        ap.error("give a PATH or --command")
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
