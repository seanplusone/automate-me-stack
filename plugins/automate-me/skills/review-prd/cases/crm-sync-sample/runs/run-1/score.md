# Score: run-1

Scored by hand against key.md. The scorer also wrote the key, so treat this as a first pass, not a blind score.

- Found: 16 of 21 (G01, G02, G03, G04, G05, G07, G10, G12, G13, G14, G15, G16, G17, G19, G20, G21)
- Missed: 5 (G06 pull fails or runs late, G08 delete fails, G09 who is admin, G11 what a non-admin sees, G18 which reports)
- Unsupported: 0 (every quote passed the check script)
- Cross-point bonus: X2 (sync loop) found as GAP 6.

## Notes

- G03 (create) was found by the CRUD rule as SCENARIO 1, then dropped. It never became a gap or a comment. Fixed in prd-gaps step 4.
- The evaluator found a real gap missing from the key: edits made in the out-of-scope mobile app. A person decides whether to add it to the key.
- Step 5 failed C5 and C10, so the run stopped before step 6, as the playbook says.
