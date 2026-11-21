"""The old test. It passes on the buggy parent, because it only tries spaces."""
import sys

from trim import trim

ok = trim("  hi  ") == "hi"
print("PASS" if ok else "FAIL", "trim strips spaces")
sys.exit(0 if ok else 1)
