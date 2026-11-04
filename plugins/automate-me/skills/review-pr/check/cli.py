"""Shared entry-point guard: print a script's docstring for -h, or when it gets too few arguments."""
import sys


def usage_or_exit(doc, argv, needed):
    """Exit 0 with the usage for -h/--help, or 2 with it when fewer than `needed` arguments came in."""
    args = argv[1:]
    if any(a in ("-h", "--help") for a in args):
        print((doc or "").strip())
        sys.exit(0)
    if len([a for a in args if not a.startswith("--")]) < needed:
        print((doc or "").strip(), file=sys.stderr)
        sys.exit(2)
