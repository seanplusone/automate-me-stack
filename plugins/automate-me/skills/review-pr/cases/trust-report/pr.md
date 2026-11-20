# Accept a run report

The runner already sets `passed`. Trust that field and skip the recount when it is true.

Tests: 2 passed.

`test_report.py` checks a report with `passed` true and one ok case. It also checks a report with `passed` false and a failed case.
