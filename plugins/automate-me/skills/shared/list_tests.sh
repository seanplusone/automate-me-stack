#!/bin/sh
cd "$(dirname "$0")/.." || exit 1
find . -type f \( -name 'test_*.py' -o -name 'test_*.mjs' -o -name 'test_*.js' \) \
  ! -path '*/node_modules/*' ! -path '*/.git/*' | sort
