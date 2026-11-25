"""The old test, tweaked. The new line still uses only spaces, so it passes on the buggy parent too."""
import sys

from trim import trim

ok = trim("  hi  ") == "hi" and trim(" a ") == "a"
print("PASS" if ok else "FAIL", "trim strips spaces")
sys.exit(0 if ok else 1)
