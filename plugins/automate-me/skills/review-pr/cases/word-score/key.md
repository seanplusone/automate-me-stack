# Key: word-score

Synthetic. The module and the PR are invented. Never show this file to the reviewer.

Planted: yes
Where: score_review.py:6
Catch: bug line bug line | returns True

`passes` returns True for the text "bug line bug line". That text names no defect. The test only sends "bug at line 3", and that test passes.
