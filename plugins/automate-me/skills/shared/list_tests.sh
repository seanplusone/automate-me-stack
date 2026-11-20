#!/bin/sh
# Print each suite test, one path per line, from the skills directory.
# Skips head and base directories under cases, so a planted program there is not run.
if [ -n "$1" ]; then
  cd "$1" || exit 1
else
  cd "$(dirname "$0")/.." || exit 1
fi
find . \( -type d \( -name head -o -name base \) -path '*/cases/*' -prune \) -o \( -type f -name 'test_*.py' -print \) | sort
