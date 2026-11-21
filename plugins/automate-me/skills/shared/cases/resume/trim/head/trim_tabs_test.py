"""The new test. It fails on the parent, where tabs and newlines stay, and passes with the fix."""
import sys

from trim import trim

got = trim("\thi\n")
ok = got == "hi"
print("PASS" if ok else "FAIL", f"trim strips tabs and newlines: got {got!r}")
sys.exit(0 if ok else 1)
