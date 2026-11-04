#!/bin/sh
# check_edd.py searches the practice code with `git grep`, so it must be its own git repo.
set -e
cd "$(dirname "$0")/plugins/automate-me/skills/write-edd/cases/order-sync/repo"
[ -d .git ] && exit 0
git init -q && git add -A && git -c user.name=setup -c user.email=setup@localhost commit -qm "practice repo"
echo "practice repo ready"
