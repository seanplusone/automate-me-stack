# Key: trust-report

Synthetic. The module and the PR are invented. Never show this file to the reviewer.

Planted: yes
Where: report.py:3-4
Catch: returns True | 'ok': False

`accept` returns True when the report says passed and a case has ok False. The tests never send that pair. On the base, the same call returns False.
