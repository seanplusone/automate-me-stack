# Key: item-cap

Synthetic. The module and the PR are invented. Never show this file to the reviewer.

Planted: yes
Where: cap.py:3
Catch: within_cap(5) | returns False

`within_cap(5)` returns False. The docstring says the cap is 5, so 5 is still allowed. The tests check 4 and 6, and both still pass.
