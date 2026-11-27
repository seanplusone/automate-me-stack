# Brief: Build a reading-list CLI

- Workstream: demo
- Kind: build
- Plan first: none needed
- Goal: Build a small command-line tool that tracks books to read.
- Decision: Merge the reading-list CLI or send it back for fixes.
- Context: Books are stored in books.json with fields title, author, and status.
- Must-haves:
  - [m1] Adding a book writes a new entry to books.json.
- Taste: Short help text, flag don't filter. Signal is that --help fits in 20 lines.
- Output: A CLI script and its test file in the project folder.
- Verify:
  - m1: `printf 'a\377b\n'`
- If stuck: Stop after 2 failed attempts and report the blocker.
- Skills: none.
- Parking lot: none.
- Unknowns: none.
- Signed-off: Pat, 2026-11-27, via fixture, sha256=667647121cff1ad2845e125759ecb72776b054e14d4e460bd831eba2d6ea385e
