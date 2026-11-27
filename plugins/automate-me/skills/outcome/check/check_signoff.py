"""Checks human sign-off for the current Done.

Usage:
  python3 check/check_signoff.py hash <brief.md>
  python3 check/check_signoff.py <brief.md>

The hash covers the parsed Must-haves items joined by newlines. Verify commands
are outside the hash. Only the human's yes about that Done allows writing:
- Signed-off: <who>, <YYYY-MM-DD>, via <where the yes was given>, sha256=<hash>
The check cannot tell who typed the line.
"""
import hashlib
import sys

sys.dont_write_bytecode = True
from check_brief import SIGNOFF_HASH, parse

NO_DONE = "The brief has no Must-haves slot."
STOP_SIGNOFF = ("The brief has no human sign-off for its current Done. "
                "Show the human the Done and ask them to sign off again.")


def stop(reason):
    print(f"STOP: {reason} Do not write the Signed-off line without the human's yes.")
    return 2


def done_hash(text):
    slots, _, _ = parse(text)
    return hashlib.sha256("\n".join(slots["Must-haves"]).encode("utf-8")).hexdigest()


def signoff_problem(text):
    slots, _, _ = parse(text)
    if "Must-haves" not in slots:
        return NO_DONE
    if "Signed-off" not in slots:
        return "The brief has no Signed-off line."
    signed_off = slots["Signed-off"]
    match = SIGNOFF_HASH.search(signed_off[0]) if signed_off else None
    if not match:
        return "Signed-off needs sha256= followed by 64 lowercase hex characters."
    if match[1] != done_hash(text):
        return "The Signed-off hash does not match the current Done."
    return None


def main(path, hash_only=False):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if hash_only:
        try:
            print(done_hash(text))
        except KeyError:
            return stop(NO_DONE)
        return 0
    problem = signoff_problem(text)
    if problem:
        print(problem)
        return stop(STOP_SIGNOFF)
    print(f"PASS sign-off: {path}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "hash":
        sys.exit(main(args[1], hash_only=True))
    if len(args) == 1 and args[0] not in ("hash", "-h", "--help"):
        sys.exit(main(args[0]))
    print(__doc__.strip())
    sys.exit(0 if args in (["-h"], ["--help"]) else 2)
