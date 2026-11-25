# Brief: Unread count badge on the bell icon

- Kind: build
- Plan first: none needed. One small widget.
- Goal: Add an unread count badge to the bell icon in the top bar.
  - unknown: What will the person decide or ship with the badge?
- Done:
  - At zero there is no badge. Proof is a screenshot.
  - From 1 to 99 the badge shows the number, and above 99 it shows 99+. Proof is a screenshot of 5 and of 150.
  - The avatar menu's dropdown covers the badge when it opens. Proof is a screenshot with the menu open.
- Output:
  - The badge lives on the top right corner of the bell, in the top bar.
  - What shares that space: the avatar menu next to the bell, whose dropdown covers it, and the Notifications tooltip on hover.
  - States: zero (no badge), 1 to 99, 99+, and loading, which is unknown.
- Constraints:
  - Change only the badge. Stop and ask if the dropdown cannot cover it without changing the menu.
  - out of scope: a pulse animation.
- Tools:
  - A browser at a few widths. Check it opens the app first.
  - write first: the list of counts and widths to screenshot.
- Agents and roles: One agent builds it. The speaker checks the screenshots.
- Run mode: one-at-a-time
- Evals:
  - Pass: at 150 the badge shows 99+ and sits under the open dropdown.
  - Fail: the badge draws over the open dropdown.
- Verification: Every state claim names its browser screenshot, or says guess.
- Parking lot:
  - Making the badge pulse. A separate thing.
- Unknowns:
  - unknown: What will the person decide or ship with the badge?
  - unknown: What does the badge show while the count is loading?
  - unknown: What does the badge do on a narrow screen?

## Questions

1. What does the badge show while the count is loading?
2. What does the badge do on a narrow screen?
3. What will the person decide or ship with the badge?
